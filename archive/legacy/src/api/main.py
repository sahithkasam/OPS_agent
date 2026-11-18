"""
FastAPI Backend — OpsPilot
Async API backend for tools & services.
Replaces the Flask webhook server with a production-grade FastAPI app.
Maps to Proposal Section 4.1: FastAPI (async backend for tools & services)
"""

import os
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="OpsPilot API",
    description="Autonomous IT Help Desk & Ticket Resolution — FastAPI Backend",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PENDING_ACTIONS_FILE = "./data/pending_actions.json"


# ─────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────

class IncidentInjectRequest(BaseModel):
    incident_type: str
    severity: Optional[str] = "P2"
    source: Optional[str] = "api"

class NaturalLanguageRequest(BaseModel):
    message: str
    source: Optional[str] = "slack"
    user: Optional[str] = "unknown"

class ActionRequest(BaseModel):
    incident_id: str
    action: str  # "approve" or "deny"
    operator: Optional[str] = "ops-team"


# ─────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────

def _write_pending_action(action_type: str, incident_id: str, metadata: dict = {}):
    """Writes a pending action to the shared file (picked up by Streamlit dashboard)."""
    payload = {
        "action": action_type,
        "incident_id": incident_id,
        "timestamp": datetime.utcnow().isoformat(),
        **metadata
    }
    try:
        with open(PENDING_ACTIONS_FILE, "w") as f:
            json.dump(payload, f)
    except Exception as e:
        print(f"[API] Failed to write pending action: {e}")


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "OpsPilot API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health endpoint for monitoring and diagnostics agents."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "jira_configured": bool(os.getenv("JIRA_URL")),
        "slack_configured": bool(os.getenv("SLACK_WEBHOOK_URL")),
    }


@app.post("/incident/inject", tags=["Incidents"])
async def inject_incident(req: IncidentInjectRequest):
    """
    Injects a synthetic incident into the simulation engine.
    Maps to Proposal Use Case 8.1: Automated Ticket Resolution
    """
    valid_types = [
        "high_cpu", "memory_leak", "latency_spike",
        "service_down", "disk_usage_high", "process_crash",
        "database_lock", "ssl_expiry"
    ]
    if req.incident_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid incident_type. Must be one of: {valid_types}"
        )

    _write_pending_action("inject", req.incident_type, {
        "severity": req.severity,
        "source": req.source
    })

    return {
        "status": "injected",
        "incident_type": req.incident_type,
        "severity": req.severity,
        "message": f"Incident '{req.incident_type}' injected. Pipeline will process automatically."
    }


@app.post("/incident/parse", tags=["Incidents"])
async def parse_natural_language(req: NaturalLanguageRequest):
    """
    Parses a natural language IT complaint and maps it to an incident type.
    Maps to Proposal Section 8.2: Slack/Email Incident Parsing.
    Example: "VPN is not working" → service_down
    """
    from src.agents.supervisor_agent import SupervisorAgent
    agent = SupervisorAgent()
    result = agent.parse_natural_language_incident(req.message)

    # Auto-inject the parsed incident
    _write_pending_action("inject", result["incident_type"], {
        "severity": result.get("severity", "P2"),
        "source": req.source,
        "original_message": req.message,
        "parsed_intent": result.get("parsed_intent", "")
    })

    return {
        "status": "parsed_and_injected",
        "original_message": req.message,
        "mapped_incident_type": result["incident_type"],
        "severity": result.get("severity", "P2"),
        "parsed_intent": result.get("parsed_intent", ""),
        "source": req.source
    }


@app.post("/incident/{incident_id}/approve", tags=["Actions"])
async def approve_incident(incident_id: str, operator: str = "ops-team"):
    """
    Approves the AI-recommended action for an incident.
    Triggers the recovery playbook.
    """
    _write_pending_action("approve", incident_id, {"operator": operator})
    return {
        "status": "approved",
        "incident_id": incident_id,
        "operator": operator,
        "message": "Recovery playbook will execute on next simulation tick."
    }


@app.post("/incident/{incident_id}/deny", tags=["Actions"])
async def deny_incident(incident_id: str, operator: str = "ops-team"):
    """
    Denies the AI-recommended action — triggers escalation to L3.
    """
    _write_pending_action("deny", incident_id, {"operator": operator})
    return {
        "status": "denied",
        "incident_id": incident_id,
        "operator": operator,
        "message": "Incident escalated to L3 support."
    }


@app.post("/slack/actions", tags=["Integrations"])
async def slack_webhook(request: Request):
    """
    Handles Slack interactive button callbacks (Approve / Escalate).
    Replaces the Flask webhook server.
    Maps to Proposal Section 4.1: Slack APIs for notifications.
    """
    try:
        body = await request.body()
        content_type = request.headers.get("content-type", "")

        if "application/x-www-form-urlencoded" in content_type:
            from urllib.parse import parse_qs
            parsed = parse_qs(body.decode())
            payload_str = parsed.get("payload", ["{}"])[0]
            payload = json.loads(payload_str)
        else:
            payload = await request.json()

        # Extract action and ticket_id from payload
        actions = payload.get("actions", [])
        if not actions:
            return JSONResponse({"ok": True, "message": "No actions"})

        action = actions[0]
        action_id = action.get("action_id", "")
        ticket_id = action.get("value", "")

        if action_id == "approve_action":
            _write_pending_action("approve", ticket_id)
            return JSONResponse({"ok": True, "action": "approve", "ticket": ticket_id})
        elif action_id == "escalate_action":
            _write_pending_action("deny", ticket_id)
            return JSONResponse({"ok": True, "action": "escalate", "ticket": ticket_id})

        return JSONResponse({"ok": True, "message": "Unknown action"})

    except Exception as e:
        print(f"[Slack Webhook Error] {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=200)


@app.get("/diagnostics/run/{incident_type}", tags=["Diagnostics"])
async def run_diagnostics(incident_type: str):
    """
    Runs real diagnostic tools for a given incident type.
    Maps to Proposal Section 8.3: Knowledge-based Troubleshooting
    """
    from src.tools.diagnostic_tools import run_full_diagnostic
    result = run_full_diagnostic(incident_type)
    return {
        "status": "completed",
        "incident_type": incident_type,
        "report": result
    }


@app.get("/agents/status", tags=["Agents"])
async def agents_status():
    """
    Returns the status of all multi-agents in the pipeline.
    """
    groq_key = os.getenv("GROQ_API_KEY")
    return {
        "pipeline": "OpsPilot Multi-Agent Pipeline (LangGraph)",
        "agents": [
            {"name": "Supervisor Agent", "role": "Orchestrator — intent analysis, severity", "llm": bool(groq_key)},
            {"name": "Knowledge Agent", "role": "Agentic RAG — KB/SOP retrieval", "llm": bool(groq_key)},
            {"name": "Diagnostics Agent", "role": "Shell/HTTP tools — ping, curl, health checks", "llm": bool(groq_key)},
            {"name": "Resolution Agent", "role": "LLM-powered action recommendation", "llm": bool(groq_key)},
            {"name": "Ticketing Agent", "role": "Jira ticket lifecycle management", "llm": False},
            {"name": "Escalation Agent", "role": "Guardrails + human escalation", "llm": bool(groq_key)},
        ],
        "llm_model": "llama-3.1-70b-versatile (Groq)",
        "llm_active": bool(groq_key),
        "orchestration": "LangGraph StatefulGraph"
    }
