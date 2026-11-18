# Legacy / archived code

This folder holds an earlier iteration of OPS Agent that has been superseded by the
current stack documented in the root [README.md](../../README.md) (React + Vite
frontend, `api/server.py` FastAPI backend, the hand-written agent pipeline in
`src/agent/`). None of this is imported or used by the live application — it is
kept only for reference.

It is **not part of the submitted/current project** and is not covered by the
test suite.

## What's here

| Path | What it was |
|---|---|
| `dashboard/app.py`, `dashboard/v2_plan.md` | The original Streamlit dashboard/control UI, later replaced by the React frontend. Still imports the *current* `src.simulation`, `src.detection`, `src.integration`, `src.agent.rca_agent`, and `src.orchestration.policy_engine` modules at the project root. |
| `src/api/main.py` | An earlier, self-contained FastAPI prototype, superseded by `api/server.py`. Not imported by anything else. |
| `src/agents/*` | An earlier set of agents (Supervisor, Knowledge, Diagnostics, Resolution, Escalation, Ticketing) built around a real LangGraph `StateGraph`. Superseded by the simpler, dependency-free pipeline in `src/agent/` (singular) that the live orchestrator (`src/agent/orchestrator.py`) actually uses today. |
| `src/orchestration/langgraph_pipeline.py` | The real LangGraph `OpsPilotPipeline` that wired `src/agents/*` together. This is the **only** place in the whole repo that genuinely uses the `langgraph` library. The live `src/simulation/engine.py` no longer references it. |
| `src/integration/webhook_server.py` | A Flask app that received Slack button callbacks and forwarded them, used with ngrok for local tunneling. The live app handles Slack callbacks directly via FastAPI's `POST /slack/actions` in `api/server.py` instead. |
| `run.py`, `run_api.py`, `run_demo_server.py`, `startup.sh` | Launcher scripts for the stack above (Flask/ngrok + `src/api/main.py` + Streamlit). Replaced by `./start.sh` at the project root. |

## Why it's archived instead of deleted

So the real LangGraph-based multi-agent implementation isn't lost, in case it's
useful as a reference or starting point later. The current README and interview
notes describe the pipeline that is actually deployed (`src/agent/orchestrator.py`,
no LangGraph dependency) rather than this one.

## Running it (best effort, not verified after archiving)

This code was moved as a unit but still depends on modules that remain live at
the project root (`src/simulation`, `src/detection`, `src/integration/slack_client.py`,
`src/integration/jira_client.py`, `src/agent/rca_agent.py`, `src/orchestration/policy_engine.py`,
`src/tools`, `src/rag`). Because `src/` has no `__init__.py` (it's a namespace
package), the two halves can be merged on the import path by adding both the
project root and this folder to `PYTHONPATH`, run from the project root:

```bash
pip install -r requirements.txt -r archive/legacy/requirements-legacy.txt
PYTHONPATH=.:archive/legacy python archive/legacy/run.py
```

On Windows PowerShell:

```powershell
pip install -r requirements.txt -r archive/legacy/requirements-legacy.txt
$env:PYTHONPATH = ".;archive/legacy"
python archive/legacy/run.py
```
