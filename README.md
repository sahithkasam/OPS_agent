# OPS Agent

An AI-powered incident management system that detects, analyzes, and helps resolve production incidents automatically. Built as a group project to explore multi-agent systems and real-world DevOps automation.

**Live Demo:** https://ops-agent-flax.vercel.app/

---

## What it does

The system simulates a production environment and runs a multi-agent pipeline that handles incidents from detection to resolution:

1. **Detects** anomalies in system metrics (CPU, memory, latency) and application logs
2. **Analyzes** the incident using RAG — searches a knowledge base of past incidents to find root causes
3. **Notifies** via Slack and creates a Jira ticket automatically
4. **Waits for approval** — a human reviews the proposed fix on the dashboard or Slack
5. **Executes** the recovery playbook if approved, or escalates to L3 if denied

---

## Architecture

The system is split into a React frontend, a FastAPI backend, and a multi-agent pipeline built with LangGraph.

```
Frontend (React/Vite)
      ↓
Backend (FastAPI)
      ↓
Simulation Engine → Anomaly Detector → Agent Pipeline
                                            ↓
                         Triage → Diagnostics → RCA → Remediation → Comms
                                                ↑
                                        ChromaDB (RAG)
```

### Agents

| Agent | Role |
|-------|------|
| Triage | Classifies incident severity and type |
| Diagnostics | Pulls relevant metrics and log patterns |
| RCA | Root cause analysis using RAG + Groq LLM |
| Remediation | Builds a recovery playbook |
| Communications | Sends Slack alerts and creates Jira tickets |
| Orchestrator | Coordinates the full pipeline |

---

## Tech Stack

- **Backend** — Python, FastAPI, LangGraph, LangChain
- **Frontend** — React, Vite
- **LLM** — Groq (Llama 3.3 70B)
- **Vector DB** — ChromaDB
- **Integrations** — Slack, Jira
- **Deployment** — Render (backend), Vercel (frontend)

---

## Running locally

**Backend**
```bash
pip install -r requirements.txt
cp .env.example .env   # add your API keys
uvicorn api.server:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API calls to the backend at port 8000.

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key for LLM inference |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook for alerts |
| `JIRA_URL` | Your Jira instance URL |
| `JIRA_USERNAME` | Jira account email |
| `JIRA_API_TOKEN` | Jira API token |
| `JIRA_PROJECT_KEY` | Jira project key (default: KAN) |

---

## Features

- Real-time incident dashboard with live metrics and logs
- One-click incident injection for testing (CPU spike, memory leak, service down, etc.)
- Human-in-the-loop approval flow — approve or deny fixes from the dashboard
- Knowledge base viewer with historical incidents
- Incident history with KPIs (auto-resolved rate, average resolution time)
- Slack interactive buttons for remote approvals
