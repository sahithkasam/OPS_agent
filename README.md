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

The system is split into a React frontend, a FastAPI backend, and a multi-agent pipeline that runs five specialized agents through a custom Python orchestrator (`src/agent/orchestrator.py`).

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

- **Backend** — Python, FastAPI, custom multi-agent orchestrator
- **Frontend** — React, Vite
- **LLM** — Groq (GPT-OSS 120B)
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

## Knowledge base (real postmortems)

The RAG knowledge base (`data/historical_incidents.json`) contains 220 real public production postmortems from companies such as AWS, Google, Cloudflare, GitHub and Stripe, taken from [Dan Luu's post-mortems list](https://github.com/danluu/post-mortems). Security breaches are excluded. Each entry keeps a link to the original write-up and is normalized into the incident schema (category, symptoms, root cause, resolution, recommended action, severity).

Every entry is assigned one of the simulator's 10 incident types. The RCA agent first searches only the injected incident's category (ChromaDB, `all-MiniLM-L6-v2` embeddings, cosine similarity), so a DNS incident is compared with past DNS outages.

Rebuild it with:
```bash
python scripts/build_kb_from_postmortems.py           # uses the LLM if GROQ_API_KEY is set
python scripts/build_kb_from_postmortems.py --no-llm  # deterministic rule-based extraction
```
The committed file was LLM-normalized with the same prompt rules for every entry: 28 entries by Groq (`openai/gpt-oss-120b`) and the remaining 192 by Claude after Groq's free-tier daily token limit was reached. Each record's `extraction` field says which model produced it. Every entry uses only facts stated in its summary, so the resolution is left empty when the summary doesn't say how the outage was fixed. Progress is saved after each entry, so an interrupted build resumes when you rerun the command; `--fresh` redoes everything with the configured LLM. The index rebuilds automatically when the file changes. The original synthetic dataset is kept in `archive/synthetic_incidents.json`.

---

## Features

- Real-time incident dashboard with live metrics and logs
- One-click incident injection for testing (CPU spike, memory leak, service down, etc.)
- Human-in-the-loop approval flow — approve or deny fixes from the dashboard
- Knowledge base viewer with historical incidents
- Incident history with KPIs (auto-resolved rate, average resolution time)
- Slack interactive buttons for remote approvals

---

## Project layout notes

- The test suite lives in `tests/` and covers the RCA agent, policy engine, and diagnostic tools (`pytest`).
- `archive/legacy/` holds an earlier iteration of this project (a Streamlit dashboard, a Flask/ngrok webhook relay, and a real LangGraph-based agent pipeline) that predates the current React/FastAPI stack above. It isn't used by the live app — see [archive/legacy/README.md](archive/legacy/README.md) for details.
