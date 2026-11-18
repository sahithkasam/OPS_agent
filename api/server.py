"""FastAPI bridge to the SimulationEngine + multi-agent orchestrator.

Run: uvicorn api.server:app --reload --port 8000
"""
import os

# Keep numeric libraries single-threaded. Each extra BLAS/ONNX thread reserves
# its own buffers, and small hosts (Render free tier: 512 MB, shared CPU) gain
# nothing from them. Must be set before numpy / onnxruntime are imported.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import asyncio
import json
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel


def _safe(obj, depth=0, ancestors=None):
    """Strip non-JSON-safe values and break cycles.

    Only objects on the current path (ancestors) count as cycles. The same
    dict can legitimately appear twice (e.g. rca_report.top_root_cause is
    also hypotheses[0]) and must be serialized both times.
    """
    if ancestors is None:
        ancestors = set()
    if depth > 10:
        return None
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    oid = id(obj)
    if oid in ancestors:
        return None
    if isinstance(obj, dict):
        ancestors.add(oid)
        out = {}
        for k, v in obj.items():
            try:
                out[str(k)] = _safe(v, depth + 1, ancestors)
            except Exception:
                out[str(k)] = None
        ancestors.discard(oid)
        return out
    if isinstance(obj, (list, tuple, set)):
        ancestors.add(oid)
        out = [_safe(v, depth + 1, ancestors) for v in obj]
        ancestors.discard(oid)
        return out
    # Don't dive into arbitrary objects — too risky for cycles. Stringify.
    return str(obj)


def json_response(payload: dict) -> Response:
    return Response(
        content=json.dumps(_safe(payload), default=str),
        media_type="application/json",
    )

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.simulation.engine import SimulationEngine, SimulationMode
from src.simulation.observations import FileLogSource
from src.detection.anomaly_model import AnomalyDetector
from src.integration.slack_client import SlackNotifier
from src.integration.jira_client import JiraConnector
from src.agent.orchestrator import OrchestratorAgent
from src.agent.llm_client import LLMClient
from src.agent.message_bus import MessageBus
from src.simulation.incident import IncidentType

INCIDENT_TYPES = [t.value for t in IncidentType]


class EngineRuntime:
    def __init__(self):
        self.engine = SimulationEngine()
        self.engine.log_source = FileLogSource(str(ROOT / "data" / "app_logs.log"))
        self.engine.detector = AnomalyDetector()
        self.engine.slack_notifier = SlackNotifier(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL"), mock=False
        )
        self.engine.jira_connector = JiraConnector(
            url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            token=os.getenv("JIRA_API_TOKEN"),
            project_key=os.getenv("JIRA_PROJECT_KEY", "KAN"),
            mock=False,
        )
        self.engine.set_mode(SimulationMode.SIMULATION)
        self.engine.message_bus = MessageBus()
        self.engine.llm_client = LLMClient()
        self.engine.orchestrator = OrchestratorAgent(
            bus=self.engine.message_bus,
            slack_notifier=self.engine.slack_notifier,
            jira_connector=self.engine.jira_connector,
            llm_client=self.engine.llm_client,
        )
        self.tick_history: list[dict] = []
        self.auto_run = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.tick_interval = 2.0

    def snapshot(self) -> dict:
        eng = self.engine
        active = eng.state_tracker.get_active()
        running_id = getattr(eng, "pipeline_running_id", None)

        # Compute per-incident queue state.
        incidents = []
        seen_running = False
        for inc in active:
            data = _serialize_incident(inc)
            if data["analysis"]:
                data["pipeline_state"] = "done"
            elif running_id and data["id"] == running_id:
                data["pipeline_state"] = "running"
                seen_running = True
            else:
                # If something's running already, others are queued.
                # Otherwise this one is itself next-in-line (running soon).
                data["pipeline_state"] = "queued" if seen_running or running_id else "running"
            incidents.append(data)

        # Strip references to analysis from metrics — those would alias incidents'
        # analysis dicts and confuse the cycle-detection in _safe().
        metrics_clean = {k: v for k, v in (eng.metrics or {}).items()
                         if k not in ("latest_analysis", "agent_active")}
        history_clean = [
            {k: v for k, v in (s.get("metrics", {}) or {}).items()
             if k not in ("latest_analysis", "agent_active")}
            for s in self.tick_history[-180:]
        ]

        return {
            "tick": eng.tick_count,
            "mode": eng.mode.value,
            "auto_run": self.auto_run,
            "llm_active": bool(eng.llm_client and eng.llm_client.is_active),
            "pipeline_running_id": running_id,
            "metrics": metrics_clean,
            "metrics_history": history_clean,
            "incidents": incidents,
            "logs": list(eng.system_logs[-80:]),
            "agent_stats": eng.orchestrator.get_agent_stats() if eng.orchestrator else {},
        }

    def step(self) -> dict:
        with self._lock:
            state = self.engine.tick()
            self.tick_history.append(state)
            if len(self.tick_history) > 200:
                self.tick_history.pop(0)
            return state

    def start_auto(self):
        if self._thread and self._thread.is_alive():
            self.auto_run = True
            return
        self.auto_run = True
        self._stop.clear()

        def loop():
            while not self._stop.is_set() and self.auto_run:
                try:
                    self.step()
                except Exception as e:
                    print(f"[engine] tick error: {e}")
                self._stop.wait(self.tick_interval)

        self._thread = threading.Thread(target=loop, daemon=True, name="engine-loop")
        self._thread.start()

    def stop_auto(self):
        self.auto_run = False
        self._stop.set()


def _serialize_incident(inc) -> dict:
    return {
        "id": inc.id,
        "type": inc.type.value,
        "state": inc.state.value,
        "start_tick": inc.start_tick,
        "severity_hint": getattr(inc, "severity", None),
        "jira_ticket_key": getattr(inc, "jira_ticket_key", None),
        "slack_sent": getattr(inc, "slack_sent", False),
        "analysis": inc.analysis,
        "history": [(t, s.value) for t, s in (getattr(inc, "history", []) or [])],
    }


runtime: EngineRuntime | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runtime
    runtime = EngineRuntime()
    yield
    if runtime:
        runtime.stop_auto()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class InjectBody(BaseModel):
    incident_type: str
    severity: str | None = None  # optional operator hint: P1 / P2 / P3


class CommandBody(BaseModel):
    text: str


@app.get("/api/state")
def get_state():
    return json_response(runtime.snapshot())


@app.post("/api/tick")
def post_tick():
    runtime.step()
    return json_response(runtime.snapshot())


@app.post("/api/auto")
def post_auto(on: bool = True):
    if on:
        runtime.start_auto()
    else:
        runtime.stop_auto()
    return {"auto_run": runtime.auto_run}


@app.post("/api/inject")
def post_inject(body: InjectBody):
    if body.incident_type not in INCIDENT_TYPES:
        raise HTTPException(400, f"Unknown incident type: {body.incident_type}")
    if body.severity not in (None, "P1", "P2", "P3"):
        raise HTTPException(400, f"Invalid severity: {body.severity}")
    runtime.engine.inject_incident(body.incident_type, body.severity)
    return json_response(runtime.snapshot())


@app.post("/api/incidents/{incident_id}/approve")
def approve(incident_id: str):
    runtime.engine.approve_action(incident_id)
    return json_response(runtime.snapshot())


@app.post("/api/incidents/{incident_id}/deny")
def deny(incident_id: str):
    runtime.engine.deny_action(incident_id)
    return json_response(runtime.snapshot())


@app.post("/api/reanalyze")
def reanalyze():
    runtime.engine.trigger_reanalysis()
    return {"ok": True}


@app.post("/api/logs/inject")
def inject_logs(body: CommandBody):
    log_path = ROOT / "data" / "app_logs.log"
    with open(log_path, "a") as f:
        f.write("\n" + body.text + "\n")
    runtime.engine.cooldown_until = 0
    runtime.engine.trigger_reanalysis()
    runtime.step()
    return json_response(runtime.snapshot())


@app.get("/api/events")
async def events():
    async def gen():
        last_tick = -1
        last_push = 0.0
        while True:
            snap = runtime.snapshot()
            now = time.time()
            # push on new tick OR at least every 1s as a heartbeat
            if snap["tick"] != last_tick or (now - last_push) > 1.0:
                last_tick = snap["tick"]
                last_push = now
                yield f"data: {json.dumps(_safe(snap), default=str)}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/history")
def get_history():
    eng = runtime.engine
    resolved = list(getattr(eng.state_tracker, "resolved_log", []))
    items = [_serialize_incident(i) for i in resolved]
    items.reverse()  # newest first

    # Compute KPIs
    total = len(resolved) + len(eng.state_tracker.get_active())
    auto_resolved = sum(
        1 for i in resolved
        if i.state.value == "RESOLVED"
        and not (i.analysis and i.analysis.get("needs_approval"))
    )
    durations = [
        (i.history[-1][0] - i.start_tick) if getattr(i, "history", None) else 0
        for i in resolved
    ]
    avg_ticks = (sum(durations) / len(durations)) if durations else 0

    return json_response({
        "kpis": {
            "incidents": total,
            "resolved": len(resolved),
            "auto_resolved": auto_resolved,
            "avg_ticks": round(avg_ticks, 1),
        },
        "items": items,
    })


class KBIngestBody(BaseModel):
    incident_id: str


def _kb():
    """The RCA agent's knowledge base (single shared Chroma client)."""
    return runtime.engine.orchestrator.rca.kb


@app.post("/api/kb/ingest")
def kb_ingest(body: KBIngestBody):
    """Add a resolved incident from this session to the ChromaDB knowledge base."""
    eng = runtime.engine
    inc = next(
        (i for i in getattr(eng.state_tracker, "resolved_log", [])
         if i.id == body.incident_id),
        None,
    )
    if not inc:
        raise HTTPException(404, f"Resolved incident {body.incident_id} not found")
    a = inc.analysis or {}
    symptoms = [s for s in a.get("triage_report", {}).get("symptoms", [])
                if isinstance(s, str) and not s.startswith("[AI Insight]")][:5]
    root_cause = a.get("root_cause") or (a.get("hypotheses") or [{}])[0].get("root_cause", "")
    item = {
        "id": f"live-{inc.id}",
        "company": "This deployment",
        "source": "live",
        "source_url": "",
        "section": "Live session",
        "category": inc.type.value,
        "summary": f"{inc.type.value.replace('_', ' ')} — {a.get('summary', '')}"[:200],
        "description": a.get("summary", ""),
        "symptoms": symptoms,
        "logs_signature": ", ".join(symptoms),
        "root_cause": root_cause,
        "resolution": (
            f"Escalated to L3 (operator denied '{a.get('top_recommendation', '')}')."
            if inc.state.value == "ESCALATED"
            else f"Operator approved and executed: {a.get('top_recommendation', '')}."
        ),
        "recommended_action": a.get("top_recommendation", ""),
        "severity": a.get("severity", "P2"),
        "duration": "",
        "extraction": "live",
    }
    try:
        _kb().add_incident(item)
    except Exception as e:
        raise HTTPException(500, f"KB ingest failed: {e}")
    return {"ok": True, "indexed_id": item["id"]}


@app.get("/api/kb")
def get_kb():
    """Everything in the knowledge base, plus per-category counts and index stats."""
    from src.rag.vector_db import EMBEDDING_MODEL, EMBEDDING_DIMS
    kb = _kb()
    items = kb.load_items()
    live = kb.live_items()
    for it in live:
        if isinstance(it.get("symptoms"), str):
            it["symptoms"] = [s for s in it["symptoms"].split(", ") if s]
    all_items = live[::-1] + items  # newest live incidents first
    counts = {t: 0 for t in INCIDENT_TYPES}
    for it in all_items:
        cat = it.get("category")
        if cat in counts:
            counts[cat] += 1
    return json_response({
        "items": all_items,
        "count": len(all_items),
        "categories": counts,
        "index": {
            "collection": kb.collection_name,
            "documents": kb.collection.count(),
            "embedding_model": EMBEDDING_MODEL,
            "dims": EMBEDDING_DIMS,
            "distance": "cosine",
            "source": "github.com/danluu/post-mortems",
        },
    })


def verify_slack_signature(raw_body: bytes, timestamp: str | None, signature: str | None,
                           secret: str, now: float | None = None) -> bool:
    """Check Slack's request signature (https://api.slack.com/authentication/verifying-requests-from-slack).

    Slack signs every request with the app's Signing Secret:
      v0=HMAC_SHA256(secret, "v0:{timestamp}:{raw body}")
    Requests older than 5 minutes are rejected to stop replay attacks.
    """
    import hashlib
    import hmac
    if not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs((now or time.time()) - ts) > 60 * 5:
        return False
    base = b"v0:" + timestamp.encode() + b":" + raw_body
    expected = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.post("/slack/actions")
async def slack_actions(request: Request):
    raw_body = await request.body()
    secret = os.getenv("SLACK_SIGNING_SECRET")
    if secret:
        if not verify_slack_signature(
            raw_body,
            request.headers.get("X-Slack-Request-Timestamp"),
            request.headers.get("X-Slack-Signature"),
            secret,
        ):
            raise HTTPException(401, "Invalid Slack signature")
    else:
        print("[Slack] WARNING: SLACK_SIGNING_SECRET not set; /slack/actions accepts unsigned requests.")

    content_type = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in content_type:
        from urllib.parse import parse_qs
        body = raw_body.decode()
        form = parse_qs(body)
        raw = form.get("payload", [None])[0]
        if not raw:
            raise HTTPException(400, "No payload")
        payload = json.loads(raw)
    else:
        payload = json.loads(raw_body or b"{}")

    actions = payload.get("actions", [])
    if not actions:
        return {"replace_original": False, "text": "No Slack action received"}

    action = actions[0]
    action_id = action.get("action_id")
    incident_id = action.get("value")
    if not incident_id:
        raise HTTPException(400, "No incident id in Slack action")

    if action_id == "approve_action":
        runtime.engine.approve_action(incident_id)
        text = f"✅ Approved action for {incident_id}"
    elif action_id in ("escalate_action", "deny_action"):
        runtime.engine.deny_action(incident_id)
        text = f"🚨 Escalated {incident_id} to L3"
    else:
        return {"replace_original": False, "text": f"Unknown Slack action: {action_id}"}

    return {"replace_original": True, "text": text}


@app.get("/api/health")
def health():
    return {"ok": True}
