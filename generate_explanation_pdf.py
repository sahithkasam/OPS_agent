from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUT = "/Users/user/Desktop/SDP/OPS_Agent_Complete_Explanation.pdf"

W, H = A4
doc = SimpleDocTemplate(OUT, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2.2*cm, bottomMargin=2*cm)

# ── Colors ──────────────────────────────────────────────────────────────────
DARK_RED   = colors.HexColor("#6E0B0B")
RED        = colors.HexColor("#BF0000")
ORANGE     = colors.HexColor("#E07B00")
DARK_BLUE  = colors.HexColor("#003366")
TEAL       = colors.HexColor("#005F73")
GREEN      = colors.HexColor("#1B7A40")
BLACK      = colors.black
WHITE      = colors.white
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MID_GRAY   = colors.HexColor("#CCCCCC")
BLUE_BG    = colors.HexColor("#E8F0FE")
RED_BG     = colors.HexColor("#FFF0F0")
GREEN_BG   = colors.HexColor("#F0FFF4")
ORANGE_BG  = colors.HexColor("#FFF8E1")

# ── Styles ───────────────────────────────────────────────────────────────────
def S(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=getSampleStyleSheet()[parent], **kw)

sMainTitle = S("sMainTitle", fontSize=22, textColor=DARK_RED, fontName="Helvetica-Bold",
               spaceAfter=4, alignment=TA_CENTER, leading=28)
sSubTitle  = S("sSubTitle",  fontSize=12, textColor=colors.grey, fontName="Helvetica",
               spaceAfter=6, alignment=TA_CENTER)
sCover     = S("sCover",     fontSize=11, textColor=BLACK, fontName="Helvetica",
               spaceAfter=3, alignment=TA_CENTER)

sH1 = S("sH1", fontSize=16, textColor=WHITE, fontName="Helvetica-Bold",
        leading=20, spaceAfter=0)
sH2 = S("sH2", fontSize=13, textColor=DARK_RED, fontName="Helvetica-Bold",
        spaceBefore=10, spaceAfter=4, leading=17)
sH3 = S("sH3", fontSize=11, textColor=DARK_BLUE, fontName="Helvetica-Bold",
        spaceBefore=6, spaceAfter=3, leading=15)
sH4 = S("sH4", fontSize=10, textColor=TEAL, fontName="Helvetica-Bold",
        spaceBefore=4, spaceAfter=2, leading=14)

sBody  = S("sBody",  fontSize=10, textColor=BLACK, fontName="Helvetica",
           leading=15, spaceAfter=4, alignment=TA_JUSTIFY)
sBullet= S("sBullet",fontSize=10, textColor=BLACK, fontName="Helvetica",
           leading=14, leftIndent=14, spaceAfter=2)
sCode  = S("sCode",  fontSize=9,  textColor=DARK_BLUE, fontName="Courier",
           leading=13, leftIndent=10, spaceAfter=2, backColor=LIGHT_GRAY)
sNote  = S("sNote",  fontSize=9,  textColor=GREEN, fontName="Helvetica-Oblique",
           leading=13, leftIndent=14, spaceAfter=2)
sWarn  = S("sWarn",  fontSize=9,  textColor=RED,   fontName="Helvetica-Oblique",
           leading=13, leftIndent=14, spaceAfter=2)
sQ     = S("sQ",     fontSize=11, textColor=DARK_BLUE, fontName="Helvetica-Bold",
           spaceBefore=8, spaceAfter=3, leading=16)
sA     = S("sA",     fontSize=10, textColor=BLACK, fontName="Helvetica",
           leading=15, spaceAfter=5, leftIndent=10, alignment=TA_JUSTIFY)

# ── Helpers ───────────────────────────────────────────────────────────────────
def h1_banner(text):
    data = [[Paragraph(text, sH1)]]
    t = Table(data, colWidths=[17*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK_RED),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    return t

def h2_banner(text):
    data = [[Paragraph(text, S("x", fontSize=11, textColor=WHITE,
                fontName="Helvetica-Bold", leading=15))]]
    t = Table(data, colWidths=[17*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), DARK_BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    return t

def sp(h=6):  return Spacer(1, h)
def hr():     return HRFlowable(width="100%", thickness=0.5,
                                color=MID_GRAY, spaceAfter=6, spaceBefore=4)
def body(t):  return Paragraph(t, sBody)
def bullet(t, sym="▸"): return Paragraph(f"{sym}&nbsp;&nbsp;{t}", sBullet)
def code(t):  return Paragraph(t, sCode)
def note(t):  return Paragraph(f"✔  {t}", sNote)
def warn(t):  return Paragraph(f"⚠  {t}", sWarn)
def qa(q, a): return [Paragraph(f"Q: {q}", sQ), Paragraph(f"A: {a}", sA), sp(2)]

def tbl(headers, rows, col_widths=None, header_color=DARK_RED):
    if not col_widths:
        w = 17*cm / len(headers)
        col_widths = [w]*len(headers)
    hstyle = S("th", fontSize=9, textColor=WHITE, fontName="Helvetica-Bold", leading=12)
    dstyle = S("td", fontSize=9, textColor=BLACK, fontName="Helvetica", leading=12)
    data = [[Paragraph(h, hstyle) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), dstyle) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  header_color),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [LIGHT_GRAY, WHITE]),
        ("GRID",          (0,0),(-1,-1), 0.4, MID_GRAY),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    return t

def info_box(text, bg=BLUE_BG, border=DARK_BLUE):
    data = [[Paragraph(text, S("ib", fontSize=10, textColor=BLACK,
                fontName="Helvetica", leading=14))]]
    t = Table(data, colWidths=[17*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), bg),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("BOX",           (0,0),(-1,-1), 1, border),
    ]))
    return t

# ─────────────────────────────────────────────────────────────────────────────
story = []

# ══════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ══════════════════════════════════════════════════════════════════════════════
story += [
    sp(30),
    Paragraph("OPS AGENT", sMainTitle),
    Paragraph("AI-Driven Multi-Agent Incident Response System", sSubTitle),
    sp(8), hr(), sp(8),
    Paragraph("Complete End-to-End Project Explanation", S("c2", fontSize=14,
              textColor=DARK_BLUE, fontName="Helvetica-Bold", alignment=TA_CENTER,
              spaceAfter=6)),
    Paragraph("Study Guide for SDP Review Presentation", sSubTitle),
    sp(12),
    Paragraph("Presented By:", sCover),
    Paragraph("K. Sahith (22BCE7142)  |  P. Nikhileshwar (22BCE7855)  |  M. Abhijith (22BCE20225)", sCover),
    sp(4),
    Paragraph("SCOPE, VIT-AP University, Amravati, India — May 2026", sCover),
    sp(30),
    info_box("This document provides a complete technical explanation of every component, "
             "algorithm, design decision, and data flow in the OPS Agent project. "
             "Reading this document fully prepares you to answer any question from "
             "examiners about the project.", bg=ORANGE_BG, border=ORANGE),
    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — PROJECT OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 1: PROJECT OVERVIEW"), sp(8),

    Paragraph("1.1  What is OPS Agent?", sH2),
    body("OPS Agent (Operational Support Agent) is an AI-powered, multi-agent system designed to fully automate "
         "the lifecycle of production incident management. It acts as a virtual Site Reliability Engineering (SRE) "
         "team that monitors, detects, triages, diagnoses, root-causes, remediates, and communicates about system "
         "incidents — all without requiring manual intervention for routine failures."),
    sp(4),
    body("The system is built around five specialized AI agents that collaborate through a central orchestrator "
         "using an in-process message bus. Each agent has a clearly defined role and passes structured results "
         "to the next agent in the pipeline."),

    sp(6),
    Paragraph("1.2  The Core Problem It Solves", sH2),
    body("Modern cloud-native applications run on distributed architectures with dozens of microservices. These "
         "systems generate thousands of logs and metric alerts per minute. Human SRE teams face four critical problems:"),
    bullet("<b>Alert Fatigue:</b> Too many false-positive alerts make engineers desensitized. Real incidents get missed."),
    bullet("<b>Slow Triage:</b> Manual log inspection takes 15–30 minutes for even known issues. Every minute of P1 downtime costs money."),
    bullet("<b>Knowledge Silos:</b> How past incidents were resolved is stored in people's heads or buried in Confluence docs. New engineers cannot reuse this knowledge quickly."),
    bullet("<b>Scalability:</b> A team of 5 engineers cannot handle 10 simultaneous P1 incidents. The system queues them automatically."),
    sp(4),
    info_box("Industry Statistic: According to Gartner (2023), 85% of Fortune 500 companies experience at "
             "least one major outage per year, with average costs exceeding $1 million per hour of downtime. "
             "Fast, automated incident response is therefore a business-critical capability.", bg=RED_BG, border=RED),

    sp(6),
    Paragraph("1.3  What Makes OPS Agent Unique?", sH2),
    tbl(["Feature", "OPS Agent", "Existing Tools (PagerDuty, Datadog)"],
        [
            ["End-to-End Pipeline",   "✔ Full: detect → triage → diagnose → RCA → remediate → notify", "✗ Partial: only alert or only remediate"],
            ["RAG Knowledge Base",    "✔ ChromaDB vector search over 21+ historical incidents",         "✗ No historical reasoning"],
            ["Multi-Agent Design",    "✔ 5 specialized agents with feedback loops",                      "✗ Single monolithic engine"],
            ["Human-in-the-Loop",     "✔ Selective Slack approve/deny for risky actions",               "✗ Either fully manual or fully automated"],
            ["Simulation Engine",     "✔ Built-in synthetic metric + log generator for testing",         "✗ Requires live infrastructure"],
            ["Open Source",           "✔ Fully self-hostable, no SaaS dependency",                       "✗ SaaS-only, expensive licensing"],
            ["LLM Integration",       "✔ Multi-provider: Groq, OpenAI, Ollama, rule-based fallback",    "✗ No LLM reasoning"],
        ],
        col_widths=[4*cm, 6.5*cm, 6.5*cm]),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — SYSTEM ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 2: SYSTEM ARCHITECTURE"), sp(8),

    Paragraph("2.1  Four-Layer Architecture", sH2),
    body("The OPS Agent system is divided into four distinct layers that work together to process incidents "
         "from raw metrics all the way to human notifications and ticket creation:"),

    sp(4),
    tbl(["Layer", "Components", "Responsibility"],
        [
            ["Simulation Core",     "SimulationEngine, MetricsGenerator, LogGenerator, ObservationWindow",
             "Generates synthetic time-series metrics (CPU, memory, latency, error rate) and structured application logs. "
             "Triggers the multi-agent pipeline when anomalies are detected."],
            ["Multi-Agent System",  "Orchestrator, 5 Agents (Triage, Diagnostics, RCA, Remediation, Comms), PolicyEngine, ChromaDB",
             "The brain of the system. Each agent handles one specialized task. The orchestrator sequences them and manages "
             "the feedback loop."],
            ["Integration Layer",   "SlackClient, JiraConnector, WebhookServer (Flask), PyNgrok",
             "Sends rich Slack alerts with interactive approve/deny buttons. Creates Jira tickets. "
             "Receives Slack button callbacks via Flask webhook."],
            ["User Interface",      "Streamlit Dashboard, Plotly charts",
             "Real-time visualization of the agent pipeline, per-agent reports, metric charts, "
             "and conversation log. Allows manual incident injection and action approval."],
        ],
        col_widths=[3.5*cm, 5*cm, 8.5*cm]),

    sp(8),
    Paragraph("2.2  Complete Pipeline Flow (Step by Step)", sH2),
    body("Here is the exact sequence of events when an incident is detected and processed:"),
    sp(4),

    tbl(["Step", "Component", "What Happens"],
        [
            ["1", "MetricsGenerator",    "Generates CPU%, Memory%, Latency(ms), ErrorRate% every tick (1 second)"],
            ["2", "LogGenerator",        "Generates synthetic ERROR/WARN/INFO log lines for microservices"],
            ["3", "ObservationWindow",   "Ingests last 30 seconds of metrics and logs. Extracts features: recent_errors, error_patterns, log_samples"],
            ["4", "AnomalyDetector",     "Checks if any metric crosses threshold (CPU>85%, Memory>90%, Latency>2000ms, ErrorRate>5%). Triggers incident."],
            ["5", "StateTracker",        "Registers a new ActiveIncident with type (high_cpu/memory_leak/latency_spike/error_surge) and severity"],
            ["6", "SimulationEngine",    "Calls orchestrator.process_incident(metrics_snapshot, log_features, incident_id)"],
            ["7", "Orchestrator",        "Clears message bus for this incident. Starts 5-phase pipeline sequentially."],
            ["8", "TriageAgent",         "Extracts symptoms from metrics. Calculates urgency score. Classifies severity (P1/P2/P3). Optional LLM summary."],
            ["9", "DiagnosticsAgent",    "Correlates log patterns. Identifies affected services. Builds query_context string for RAG. Optional LLM narrative."],
            ["10","RCA Agent",           "Queries ChromaDB with query_context. Gets top-3 similar historical incidents. Ranks hypotheses by cosine similarity score. Optional LLM reasoning chain."],
            ["11","Feedback Check",      "If top hypothesis confidence < 0.30, orchestrator re-requests expanded diagnostics and re-runs RCA."],
            ["12","RemediationAgent",    "Takes top hypothesis action. Checks PolicyEngine. Determines if human approval needed. Optional LLM step-by-step plan."],
            ["13","CommsAgent",          "Sends Slack message with incident summary + approve/deny buttons. Creates Jira ticket with full context."],
            ["14","Dashboard Update",    "Streamlit reads workflow_stages, triage_report, rca_report etc. and updates UI in real-time."],
        ],
        col_widths=[1*cm, 4*cm, 12*cm]),

    sp(8),
    Paragraph("2.3  Feedback Loop — Why It Exists", sH2),
    body("The RCA Agent uses cosine similarity search over historical incidents. If the best match has a confidence "
         "score below 0.30, it means the current incident doesn't closely resemble anything in the knowledge base. "
         "Rather than returning a low-quality guess, the orchestrator:"),
    bullet("Sends an expanded diagnostics request — this time including the full raw log features alongside the correlated symptoms"),
    bullet("The Diagnostics Agent produces a richer query_context with more signal"),
    bullet("The RCA Agent re-queries ChromaDB with this richer context, which typically improves cosine similarity scores"),
    bullet("After re-run, the higher-confidence result is used for remediation"),
    sp(4),
    note("Real observed result: confidence improved from 0.61 to 0.78 after one feedback loop iteration in testing."),
    note("The feedback loop has a maximum of one retry to avoid infinite loops."),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — EACH AGENT EXPLAINED IN DETAIL
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 3: EACH AGENT — DETAILED EXPLANATION"), sp(8),

    # ── ORCHESTRATOR ──
    Paragraph("3.1  Orchestrator Agent", sH2),
    body("The Orchestrator is not an AI agent in the sense that it makes decisions — it is the central "
         "workflow manager (a Finite State Machine) that sequences the other five agents. It:"),
    bullet("Initializes all five agents on startup, sharing one LLMClient instance across them (efficiency)"),
    bullet("Calls each agent in strict sequential order by sending AgentMessage objects on the MessageBus"),
    bullet("Passes each agent's output as the input to the next agent"),
    bullet("Detects low confidence in RCA output and triggers the feedback loop"),
    bullet("Builds the final result dictionary that the dashboard reads"),
    bullet("Tracks timing (duration_ms) for each pipeline stage"),
    sp(4),
    code("Pipeline order: Triage → Diagnostics → RCA → [optional feedback] → Remediation → Communications"),
    sp(4),
    body("Key design decision: The orchestrator uses synchronous (blocking) message passing. Each agent must "
         "complete before the next starts. This ensures data consistency — the RCA agent always has complete "
         "diagnostic context before it starts reasoning."),

    sp(8),
    # ── TRIAGE ──
    Paragraph("3.2  Triage Agent — First Responder", sH2),
    body("The Triage Agent is the first agent to process an incident. It receives raw metrics and log features "
         "and outputs a structured classification. It does three things:"),

    Paragraph("Step 1 — Symptom Extraction:", sH3),
    body("Reads CPU%, Memory%, Latency(s), Disk% from the metrics snapshot. Compares against fixed thresholds:"),
    tbl(["Metric", "Threshold", "Symptom Generated"],
        [
            ["CPU%",        "> 80%",    "High CPU (e.g., 'High CPU (87.3%)')"],
            ["Memory%",     "> 90%",    "High Memory (e.g., 'High Memory (93.1%)')"],
            ["Latency",     "> 2.0s",   "High Latency (e.g., 'High Latency (3.412s)')"],
            ["Disk%",       "> 90%",    "High Disk Usage"],
            ["Error Count", "> 0",      "'N recent errors detected'"],
            ["CPU<2% + Errors>0", "—", "Possible service outage (idle CPU with errors)"],
        ],
        col_widths=[3*cm, 3*cm, 11*cm]),

    Paragraph("Step 2 — Urgency Scoring (0.0 to 1.0):", sH3),
    body("Each metric contributes to a cumulative urgency score. The score is capped at 1.0:"),
    tbl(["Condition", "Score Added"],
        [
            ["CPU > 95%",          "+0.30"],
            ["CPU 80–95%",         "+0.15"],
            ["Memory > 95%",       "+0.30"],
            ["Memory 90–95%",      "+0.15"],
            ["Latency > 5.0s",     "+0.30"],
            ["Latency 2.0–5.0s",   "+0.15"],
            ["Error count > 5",    "+0.20"],
            ["Error count 1–5",    "+0.10"],
        ],
        col_widths=[8.5*cm, 8.5*cm]),

    Paragraph("Step 3 — Severity Classification:", sH3),
    tbl(["Urgency Score Range", "Severity Level", "Meaning"],
        [
            ["≥ 0.70", "P1 — Critical", "Immediate response required. Always needs human approval for remediation."],
            ["0.40 – 0.69", "P2 — High", "Significant impact. RAG-assisted resolution. May auto-remediate if confidence > 0.85."],
            ["< 0.40", "P3 — Medium", "Low impact. Often escalated to human via Slack for review."],
        ],
        col_widths=[4*cm, 4*cm, 9*cm]),

    sp(4),
    note("Optional LLM Enhancement: If a Groq/OpenAI key is set, the triage agent sends the full metrics to "
         "the LLM with the prompt 'Classify incident severity and summarize in 2 sentences.' The response "
         "is appended as an [AI Insight] symptom."),

    sp(8),
    # ── DIAGNOSTICS ──
    Paragraph("3.3  Diagnostics Agent — Log Analyst", sH2),
    body("The Diagnostics Agent receives the triage report and performs deep log analysis. It builds the "
         "query_context string that the RCA Agent uses to search ChromaDB. It does:"),
    bullet("<b>Log Pattern Correlation:</b> Scans log_features for error_patterns (e.g., 'OOMKilledException', 'ConnectionTimeout'). Groups them by frequency."),
    bullet("<b>Affected Service Identification:</b> Parses log lines to extract service names that appear in ERROR-level logs."),
    bullet("<b>Query Context Building:</b> Concatenates symptom descriptions, error patterns, and affected services into a single natural-language string for vector search."),
    bullet("<b>Readable Summary:</b> Generates a human-readable diagnostic summary (e.g., 'payment-service is throwing 12 OOM errors, CPU at 87%. Likely memory leak.')."),
    bullet("<b>LLM Narrative (optional):</b> If LLM is active, generates a 3-sentence incident summary using full log context."),
    sp(4),
    body("Example query_context output:"),
    code("'High CPU (87.3%), High Memory (93.1%), 12 recent errors. Error patterns: OOMKilledException x8, "
         "GCOverheadLimitExceeded x4. Affected services: payment-service, user-service.'"),
    sp(2),
    body("This string is then passed to ChromaDB's cosine similarity search to find the most similar historical incidents."),

    sp(8),
    # ── RCA ──
    Paragraph("3.4  RCA Agent — Root Cause Analyst (RAG-Powered)", sH2),
    body("The RCA Agent is the most technically sophisticated agent. It implements Retrieval-Augmented Generation "
         "(RAG) to find the root cause of an incident by matching it against historical incidents:"),

    Paragraph("Step 1 — ChromaDB Retrieval:", sH3),
    body("The agent calls KnowledgeBase.search(query_context, n_results=3). ChromaDB converts the query_context "
         "into a vector embedding and performs cosine similarity search against the 21 stored incident embeddings. "
         "Returns top-3 closest historical incidents with their metadata and similarity scores."),

    Paragraph("Step 2 — Hypothesis Formulation:", sH3),
    body("For each retrieved historical incident, the agent creates a hypothesis:"),
    tbl(["Hypothesis Field", "Source", "Example"],
        [
            ["root_cause",  "Historical incident metadata: root_cause field",   "Memory leak in payment-service GC overhead"],
            ["confidence",  "Cosine similarity score (0.0–1.0) from ChromaDB",  "0.82"],
            ["action",      "Historical incident metadata: resolution field",    "Restart payment-service, increase heap size"],
            ["reasoning",   "Auto-generated from logs_signature match",         "Similar OOM pattern seen in INC-2024-007"],
        ],
        col_widths=[3.5*cm, 5.5*cm, 8*cm]),

    Paragraph("Step 3 — LLM Reasoning Chain (optional):", sH3),
    body("If LLM is active, the top hypothesis is sent to the LLM with prompt: 'Explain WHY this root cause "
         "is likely correct given the symptoms in 3-4 sentences.' The LLM response replaces the auto-generated "
         "reasoning field, making it much more detailed and actionable."),

    sp(4),
    info_box("How RAG works technically: ChromaDB uses sentence-transformers (all-MiniLM-L6-v2 by default) to "
             "convert text into 384-dimensional vectors. Cosine similarity measures the angle between the query "
             "vector and each stored incident vector. Score of 1.0 = identical, 0.0 = completely unrelated. "
             "Anything > 0.70 is considered a strong match.", bg=BLUE_BG, border=DARK_BLUE),

    sp(8),
    # ── REMEDIATION ──
    Paragraph("3.5  Remediation Agent — Action Planner", sH2),
    body("The Remediation Agent decides WHAT to do about the incident and WHETHER it is safe to do automatically:"),

    Paragraph("Step 1 — Action Selection:", sH3),
    body("Takes the recommended action from the top RCA hypothesis (e.g., 'Restart payment-service', "
         "'Scale up database replicas', 'Roll back deployment v2.3.1')."),

    Paragraph("Step 2 — Policy Safety Check:", sH3),
    body("The PolicyEngine classifies the action into one of three categories:"),
    tbl(["Safety Status", "Meaning", "Example Actions"],
        [
            ["ALLOWED",  "Safe to execute automatically without human approval",
             "Restart service, Clear cache, Scale up replicas (non-destructive)"],
            ["REQUIRES_APPROVAL", "Potentially risky — must get human approval via Slack before executing",
             "Database migration, Config change, Force-kill process"],
            ["BLOCKED",  "Dangerous action. Never execute automatically. Auto-escalate to L3.",
             "Drop database, Delete production data, Disable authentication"],
        ],
        col_widths=[4*cm, 6*cm, 7*cm]),

    Paragraph("Step 3 — Approval Logic:", sH3),
    bullet("If ALLOWED and confidence > 0.85 → auto-execute (needs_approval = False)"),
    bullet("If REQUIRES_APPROVAL → send to human via Slack button (needs_approval = True)"),
    bullet("If BLOCKED → override action to 'Escalate to L3', auto-escalate (needs_approval = False)"),
    bullet("If severity = P1 → always needs_approval = True, regardless of safety status"),
    sp(4),
    note("LLM Enhancement: When active, generates a 3–5 step numbered remediation plan "
         "(e.g., 'Step 1: SSH into payment-service pod. Step 2: Check heap usage with jstack...')"),

    sp(8),
    # ── COMMS ──
    Paragraph("3.6  Communications Agent — Notifier", sH2),
    body("The Communications Agent is responsible for all external notifications. It:"),
    bullet("<b>Slack Alert:</b> Sends a rich formatted Slack message containing incident ID, severity, summary, top hypothesis, recommended action, and interactive Approve/Deny buttons (if needs_approval=True)."),
    bullet("<b>Jira Ticket:</b> Creates a Jira issue with type Bug, priority mapped from severity (P1=Critical, P2=High, P3=Medium), and full incident context in the description."),
    bullet("<b>Deduplication:</b> Checks already_slack_sent and existing_jira_key flags from context — does not send duplicate notifications if the orchestrator re-runs for an ongoing incident."),
    bullet("<b>Webhook Integration:</b> Slack buttons call back to a Flask webhook server. The user's approve/deny action is stored in pending_actions.json and read by the dashboard."),

    sp(4),
    info_box("When user clicks 'Approve' on Slack: the Flask webhook server (run_demo_server.py) receives "
             "the POST request, stores the action in data/pending_actions.json. The Streamlit dashboard polls "
             "this file and shows the approval status. PyNgrok creates a public HTTPS URL so Slack can reach "
             "the local Flask server.", bg=GREEN_BG, border=GREEN),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 4: SIMULATION ENGINE"), sp(8),

    Paragraph("4.1  Why a Simulation Engine?", sH2),
    body("Testing an incident response system requires incidents to occur. Rather than waiting for real "
         "production failures or setting up complex live infrastructure (Kubernetes, Prometheus, etc.), "
         "OPS Agent includes a built-in simulation engine that generates realistic synthetic data."),

    sp(6),
    Paragraph("4.2  Metrics Generator", sH2),
    body("The MetricsGenerator produces tick-by-tick metric values for four key signals:"),
    tbl(["Metric", "Normal Range", "Anomaly Value", "Incident Type Triggered"],
        [
            ["CPU %",         "20–60%",    "> 85%",      "high_cpu"],
            ["Memory %",      "40–70%",    "> 90%",      "memory_leak"],
            ["Latency (s)",   "0.1–0.5s",  "> 2.0s",     "latency_spike"],
            ["Error Rate %",  "0–1%",      "> 5%",       "error_surge"],
            ["Disk %",        "30–60%",    "> 90%",      "(contributes to symptoms)"],
        ],
        col_widths=[4*cm, 4*cm, 4*cm, 5*cm]),
    sp(4),
    body("During an incident, metrics are biased toward anomalous values using a ramp-up curve "
         "to simulate realistic gradual degradation rather than instant spikes."),

    sp(6),
    Paragraph("4.3  Log Generator", sH2),
    body("The LogGenerator produces structured log lines for simulated microservices:"),
    bullet("Services: payment-service, user-service, order-service, inventory-service, api-gateway"),
    bullet("Log levels: ERROR (during incidents), WARN (near-threshold), INFO (normal operations)"),
    bullet("Error messages vary by incident type — e.g., 'OOMKilledException' for memory_leak, 'ConnectionTimeout' for latency_spike"),
    bullet("Each log line includes: timestamp, level, service name, thread ID, and message"),

    sp(6),
    Paragraph("4.4  ObservationWindow — Feature Extractor", sH2),
    body("The ObservationWindow maintains a rolling 30-second window of metrics and logs. It extracts:"),
    tbl(["Feature", "How Extracted", "Used By"],
        [
            ["recent_errors",    "Count of ERROR-level log lines in window",          "Triage Agent (urgency scoring)"],
            ["error_patterns",   "Top 5 unique error message types with frequencies", "Diagnostics Agent (pattern correlation)"],
            ["log_samples",      "Last 5 raw log lines for LLM context",              "Triage Agent LLM prompt"],
            ["affected_services","Services appearing in ERROR logs",                  "Diagnostics Agent (service identification)"],
        ],
        col_widths=[4*cm, 6*cm, 7*cm]),

    sp(6),
    Paragraph("4.5  Incident State Machine", sH2),
    body("Each incident goes through a lifecycle managed by the StateTracker:"),
    tbl(["State", "Meaning", "Transition"],
        [
            ["DETECTED",    "Anomaly threshold crossed",              "→ TRIAGING when pipeline starts"],
            ["TRIAGING",    "Triage agent running",                   "→ ANALYZING when triage completes"],
            ["ANALYZING",   "Diagnostics + RCA running",              "→ REMEDIATING when RCA completes"],
            ["REMEDIATING", "Remediation agent running",              "→ AWAITING_APPROVAL or RESOLVED"],
            ["AWAITING_APPROVAL", "Waiting for human Slack input",   "→ RESOLVED when approved"],
            ["RESOLVED",    "Incident handled",                       "Terminal state — cooldown period begins"],
        ],
        col_widths=[4*cm, 5.5*cm, 7.5*cm]),

    sp(4),
    body("After resolution, the engine enters a 30-tick cooldown period to prevent the same incident type "
         "from being re-triggered immediately, simulating real-world recovery time."),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — RAG & KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 5: RAG & CHROMADB KNOWLEDGE BASE"), sp(8),

    Paragraph("5.1  What is RAG?", sH2),
    body("Retrieval-Augmented Generation (RAG) is a technique that combines information retrieval with "
         "language model generation. Instead of asking the LLM to 'remember' all possible incident types "
         "(which requires expensive retraining), RAG:"),
    bullet("Step 1 — RETRIEVE: Search a database for relevant past knowledge based on the current query"),
    bullet("Step 2 — AUGMENT: Add the retrieved knowledge as context to the LLM prompt"),
    bullet("Step 3 — GENERATE: Let the LLM reason over this enriched context to produce an answer"),
    sp(4),
    body("In OPS Agent, the 'database' is ChromaDB (a vector database). The 'query' is the current incident's "
         "diagnostic summary. The 'retrieved knowledge' is the most similar historical incidents. The 'generation' "
         "is the LLM's reasoning chain explaining why this root cause is most likely."),

    sp(6),
    Paragraph("5.2  ChromaDB — How It Works", sH2),
    body("ChromaDB is a vector database that stores text as mathematical vectors (embeddings). It uses "
         "sentence-transformers (all-MiniLM-L6-v2) to convert text into 384-dimensional vectors."),
    bullet("<b>Storage:</b> Persistent local storage at ./data/chroma_db/ — survives restarts"),
    bullet("<b>Collection:</b> Named 'incidents' — stores one document per historical incident"),
    bullet("<b>Document Format:</b> Each incident is stored as: 'Title: [summary]. Symptoms: [logs_signature]. Cause: [root_cause]. Fix: [resolution].'"),
    bullet("<b>Query:</b> The query_context string is embedded and compared against all 21 stored incident vectors"),
    bullet("<b>Result:</b> Returns top-3 incidents ranked by cosine similarity score"),

    sp(4),
    info_box("Cosine Similarity Formula: sim(A,B) = (A·B) / (|A| × |B|). Measures the cosine of the angle "
             "between two vectors. Score of 1.0 = vectors point in exactly the same direction (identical meaning). "
             "Score of 0.0 = perpendicular (completely unrelated). ChromaDB returns 1 - cosine_distance, "
             "so higher = more similar.", bg=BLUE_BG, border=DARK_BLUE),

    sp(6),
    Paragraph("5.3  Knowledge Base — The 21 Historical Incidents", sH2),
    body("The knowledge base (data/historical_incidents.json) contains 21 labelled historical incidents "
         "covering the main incident types the system handles:"),
    tbl(["Incident Type", "Example Root Causes Stored"],
        [
            ["High CPU",        "Infinite loop in payment-service, CPU-bound ML inference job, cryptocurrency miner"],
            ["Memory Leak",     "GC overhead in JVM services, unclosed database connections, large object caching bug"],
            ["Latency Spike",   "N+1 query problem, network congestion, slow third-party API dependency"],
            ["Error Surge",     "Bad deployment rollout, database connection pool exhaustion, expired TLS certificate"],
            ["Service Outage",  "Pod crash loop, health check failure, dependency service unavailable"],
        ],
        col_widths=[4*cm, 13*cm]),
    sp(4),
    body("When a new incident's query_context closely matches one of these stored incident descriptions, "
         "ChromaDB returns it with a high confidence score and the stored resolution becomes the recommended action."),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — LLM INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 6: LLM INTEGRATION (MULTI-PROVIDER)"), sp(8),

    Paragraph("6.1  LLMClient — Multi-Provider Design", sH2),
    body("The LLMClient is a unified wrapper that supports four different LLM providers. The provider is "
         "auto-selected based on which API keys are available in the .env file:"),
    tbl(["Priority", "Provider", "Trigger", "Model Used"],
        [
            ["1 (highest)", "Ollama (local)",     "LLM_PROVIDER=ollama set in env",     "Configurable (llama3, mistral, etc.)"],
            ["2",           "Groq API",            "GROQ_API_KEY set in .env",           "llama3-8b-8192 (ultra-fast inference)"],
            ["3",           "OpenAI API",          "OPENAI_API_KEY set in .env",         "gpt-4o-mini"],
            ["4 (fallback)","Mock (rule-based)",   "No API keys found",                  "No LLM — deterministic rules only"],
        ],
        col_widths=[2.5*cm, 3.5*cm, 5*cm, 6*cm]),

    sp(4),
    body("The system is fully functional in Mock mode — all five agents produce correct, useful outputs "
         "using rule-based logic. LLM mode adds richer natural-language summaries and more detailed "
         "reasoning chains, but is optional."),

    sp(4),
    note("In the actual project demo, Groq API was used because it is free and provides extremely fast "
         "inference (< 1 second per request), making it ideal for a real-time incident response system."),

    sp(6),
    Paragraph("6.2  LLM Prompts Used per Agent", sH2),
    tbl(["Agent", "System Prompt Role", "User Prompt Content"],
        [
            ["Triage",       "SRE triage specialist",        "CPU%, Memory%, Latency, ErrorCount, log samples → classify severity in 2 sentences"],
            ["Diagnostics",  "Log analysis expert",          "Error patterns, affected services, metrics → generate diagnostic narrative"],
            ["RCA",          "SRE root cause analyst",       "Symptoms + diagnostic summary + top hypothesis → explain WHY this root cause is likely in 3-4 sentences"],
            ["Remediation",  "SRE remediation specialist",   "Root cause + recommended action + severity → provide 3-5 step numbered remediation plan"],
            ["Comms",        "(No LLM — uses templates)",    "Slack and Jira messages are formatted from structured agent outputs"],
        ],
        col_widths=[3*cm, 4*cm, 10*cm]),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — MESSAGE BUS & AGENT COMMUNICATION
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 7: MESSAGE BUS & AGENT COMMUNICATION"), sp(8),

    Paragraph("7.1  In-Process Message Bus", sH2),
    body("Agents do not call each other directly (which would create tight coupling). Instead, all "
         "communication goes through a central MessageBus. This is an in-process pub/sub system "
         "(not a network message broker like Kafka). It:"),
    bullet("Maintains a registry of agent handlers (agent_name → handler_function)"),
    bullet("Routes AgentMessage objects from sender to recipient"),
    bullet("Records every message in a per-incident conversation log for dashboard display"),
    bullet("Tracks message count and total processing time statistics"),

    sp(6),
    Paragraph("7.2  AgentMessage Structure", sH2),
    body("Every message exchanged between agents has this structure:"),
    tbl(["Field", "Type", "Example Value"],
        [
            ["id",          "UUID string",     "'a3f8-...' (auto-generated)"],
            ["type",        "MessageType enum","TRIAGE_REQUEST, TRIAGE_RESULT, DIAGNOSTICS_REQUEST, etc."],
            ["sender",      "string",          "'orchestrator', 'triage', 'diagnostics'"],
            ["recipient",   "string",          "'triage', 'diagnostics', 'rca', 'remediation', 'comms'"],
            ["incident_id", "string",          "'INC-20260506-001'"],
            ["payload",     "dict",            "{'metrics_snapshot': {...}, 'log_features': {...}}"],
            ["timestamp",   "float",           "Unix timestamp of when message was sent"],
            ["duration_ms", "float",           "How long the handler took to process (set on reply)"],
            ["parent_message_id", "UUID",      "Links reply to request for conversation threading"],
        ],
        col_widths=[4*cm, 3*cm, 10*cm]),

    sp(6),
    Paragraph("7.3  Message Types", sH2),
    tbl(["MessageType", "Direction", "Contains"],
        [
            ["TRIAGE_REQUEST",      "Orchestrator → Triage",         "metrics_snapshot, log_features"],
            ["TRIAGE_RESULT",       "Triage → Orchestrator",         "symptoms, severity, urgency_score"],
            ["DIAGNOSTICS_REQUEST", "Orchestrator → Diagnostics",    "triage_report"],
            ["DIAGNOSTICS_RESULT",  "Diagnostics → Orchestrator",    "error_patterns, affected_services, query_context, readable_summary"],
            ["RCA_REQUEST",         "Orchestrator → RCA",            "diagnostic_report, triage_report"],
            ["RCA_RESULT",          "RCA → Orchestrator",            "hypotheses, top_root_cause, llm_reasoning, rag_match_count"],
            ["REMEDIATION_REQUEST", "Orchestrator → Remediation",    "rca_report, triage_report, incident_type"],
            ["REMEDIATION_RESULT",  "Remediation → Orchestrator",    "recommended_action, needs_approval, safety_status, playbook_id"],
            ["COMMS_REQUEST",       "Orchestrator → Comms",          "summary, severity, top_hypothesis, top_recommendation"],
            ["COMMS_RESULT",        "Comms → Orchestrator",          "slack_sent, jira_ticket_key"],
        ],
        col_widths=[5*cm, 4.5*cm, 7.5*cm]),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — TECHNOLOGIES & ALGORITHMS
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 8: TECHNOLOGIES & ALGORITHMS"), sp(8),

    Paragraph("8.1  Technology Stack", sH2),
    tbl(["Technology", "Version", "Role in Project", "Why This Choice"],
        [
            ["Python",         "3.11",      "Core language for all backend and agent logic",       "Rich AI/ML ecosystem, rapid prototyping"],
            ["ChromaDB",       "0.4.x",     "Vector database for RAG knowledge base",              "Easiest embeddable vector DB, no server needed"],
            ["Streamlit",      "1.x",       "Real-time dashboard UI",                              "Python-native, reactive, no JavaScript needed"],
            ["Flask",          "3.x",       "Webhook server for Slack interactive callbacks",       "Lightweight, perfect for single-endpoint webhook"],
            ["Groq API",       "—",         "Primary LLM provider (llama3-8b-8192)",               "Free tier, ultra-fast inference (< 1s), reliable"],
            ["OpenAI",         "1.x",       "Fallback LLM provider (gpt-4o-mini)",                 "High quality, widely trusted"],
            ["Slack SDK",      "3.x",       "Rich Slack message posting with interactive buttons", "Official SDK, supports Block Kit UI components"],
            ["Jira REST API",  "v3",        "Automated ticket creation and management",             "Industry-standard project tracking integration"],
            ["Plotly",         "5.x",       "Interactive time-series charts in dashboard",         "Beautiful charts with zoom/hover, Streamlit-native"],
            ["PyNgrok",        "7.x",       "Public HTTPS tunnel for Slack webhook",               "One-line setup, no server configuration needed"],
            ["Sentence-Trans.","2.x",       "Text embedding for ChromaDB (via default model)",     "Offline embeddings, no API calls needed"],
        ],
        col_widths=[3*cm, 1.8*cm, 5.7*cm, 6.5*cm]),

    sp(8),
    Paragraph("8.2  Key Algorithms Explained", sH2),

    Paragraph("Algorithm 1 — Cosine Similarity (RAG Retrieval):", sH3),
    body("Used by ChromaDB to find historical incidents similar to the current one. "
         "Converts both the query and stored documents into high-dimensional vectors using "
         "sentence-transformers. The similarity score = dot product of normalized vectors. "
         "Score range: 0.0 (unrelated) to 1.0 (identical). Top-3 results returned."),

    Paragraph("Algorithm 2 — Urgency Scoring (Triage):", sH3),
    body("A weighted additive scoring function. Each metric dimension contributes independently "
         "based on severity thresholds. The total score is capped at 1.0 and mapped to "
         "P1/P2/P3 buckets. This is a rule-based heuristic, not ML — making it fast, "
         "explainable, and deterministic."),

    Paragraph("Algorithm 3 — Finite State Machine (Orchestrator):", sH3),
    body("The orchestrator manages incident lifecycle as an FSM. States: DETECTED → TRIAGING → "
         "ANALYZING → REMEDIATING → [AWAITING_APPROVAL] → RESOLVED. Each transition is triggered "
         "by a completed agent response. Invalid transitions are rejected to ensure pipeline integrity."),

    Paragraph("Algorithm 4 — Policy Safety Classification (Remediation):", sH3),
    body("A keyword-based rule engine that classifies remediation actions. Each action string is "
         "checked against three keyword lists: BLOCKED (drop, delete, disable, wipe), "
         "REQUIRES_APPROVAL (migrate, rollback, kill, force), ALLOWED (everything else). "
         "O(n) time complexity. Deterministic and auditable."),

    Paragraph("Algorithm 5 — Z-Score Anomaly Detection (optional, AnomalyModel):", sH3),
    body("The anomaly_model.py module computes a rolling z-score for each metric: "
         "z = (current_value - rolling_mean) / rolling_std_dev. A z-score > 2.5 "
         "indicates a statistically significant deviation. Used as a complementary "
         "detection mechanism alongside threshold-based rules."),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — DASHBOARD & INTEGRATION
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 9: DASHBOARD & EXTERNAL INTEGRATIONS"), sp(8),

    Paragraph("9.1  Streamlit Dashboard", sH2),
    body("The dashboard (dashboard/app.py) is the main control panel and visualization interface. "
         "It runs on port 8501 and auto-refreshes every second to reflect pipeline updates:"),
    tbl(["Tab / Section", "What It Shows"],
        [
            ["Pipeline View",       "5-step agent progress bar with ✓/⏳/✗ status, per-step duration in ms, overall MTTR"],
            ["Triage Report",       "Severity badge (P1/P2/P3), urgency score, list of extracted symptoms"],
            ["Diagnostics Report",  "Error pattern table, affected services, readable diagnostic summary"],
            ["RCA Report",          "Ranked hypothesis table (root_cause, confidence, action), LLM reasoning chain"],
            ["Remediation Report",  "Recommended action, safety status, needs_approval flag, playbook ID, LLM plan"],
            ["Comms Report",        "Slack sent status, Jira ticket key and link, notification timestamp"],
            ["Metrics Charts",      "Plotly time-series charts: CPU%, Memory%, Latency(ms), Error Rate% with anomaly markers"],
            ["Agent Conversation",  "Chronological log of all AgentMessage objects — type, sender, recipient, timing"],
            ["System Logs",         "Raw terminal output from engine and all agents — for debugging"],
            ["Incident Controls",   "Buttons to manually inject any incident type (high_cpu, memory_leak, etc.) at any severity"],
        ],
        col_widths=[4.5*cm, 12.5*cm]),

    sp(6),
    Paragraph("9.2  Slack Integration Flow", sH2),
    bullet("Comms Agent calls SlackClient.send_alert(channel, incident_id, summary, severity, recommendation, needs_approval)"),
    bullet("If needs_approval=True, Slack message includes two interactive buttons: ✅ Approve Action and ❌ Deny Action"),
    bullet("Slack sends a POST callback to the Flask webhook URL (exposed via PyNgrok) when a button is clicked"),
    bullet("Flask webhook stores {incident_id, action: 'approve'/'deny'} in data/pending_actions.json"),
    bullet("Streamlit dashboard polls pending_actions.json and displays the approval status"),

    sp(6),
    Paragraph("9.3  Jira Integration Flow", sH2),
    bullet("Comms Agent calls JiraConnector.create_ticket(summary, description, priority, labels)"),
    bullet("Priority mapping: P1 → Highest, P2 → High, P3 → Medium"),
    bullet("Description includes: incident ID, severity, diagnostic summary, top root cause, recommended action"),
    bullet("Returns ticket key (e.g., 'INC-42') which is stored in the incident state and shown in dashboard"),
    bullet("Duplicate prevention: existing_jira_key check prevents creating multiple tickets for the same incident"),

    sp(6),
    Paragraph("9.4  Running the System", sH2),
    tbl(["Command", "What It Does"],
        [
            ["bash startup.sh",              "Full system: starts both Streamlit dashboard AND Flask webhook server with ngrok tunnel"],
            ["streamlit run dashboard/app.py","Dashboard only — no Slack webhook. Best for demo without Slack integration"],
            ["python3 run_demo_server.py",    "Webhook server only — for testing Slack button callbacks"],
        ],
        col_widths=[6*cm, 11*cm]),
    sp(4),
    body("Environment variables (in .env file):"),
    code("GROQ_API_KEY=gsk_...          # Groq LLM provider (fastest, free tier)"),
    code("OPENAI_API_KEY=sk-...         # OpenAI fallback"),
    code("SLACK_BOT_TOKEN=xoxb-...      # Slack bot token"),
    code("SLACK_CHANNEL=#incidents      # Target Slack channel"),
    code("JIRA_SERVER=https://xxx.atlassian.net"),
    code("JIRA_EMAIL=your@email.com"),
    code("JIRA_API_TOKEN=..."),
    code("JIRA_PROJECT_KEY=INC"),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — RESULTS & PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 10: RESULTS & PERFORMANCE"), sp(8),

    Paragraph("10.1  Test Results by Incident Type", sH2),
    tbl(["Incident Type", "Severity", "Pipeline Path", "MTTR", "Outcome"],
        [
            ["High CPU Spike",       "P1", "All 5 agents, full pipeline",         "~4 s",  "Root cause: infinite loop in payment-service. Slack alert sent. Jira INC-001 created. Human approval requested."],
            ["Memory Leak",          "P1", "All 5 agents + RAG retrieval",         "~5 s",  "Root cause: JVM GC overhead, ChromaDB confidence 0.82. Remediation: increase heap size + restart service."],
            ["Latency Spike",        "P2", "All 5 agents + RAG retrieval",         "~6 s",  "Matched N+1 query pattern from history. Auto-remediated (ALLOWED + confidence > 0.85)."],
            ["Error Rate Surge",     "P3", "Triage + Diagnostics + RCA",           "~3 s",  "Escalated to human via Slack. Jira ticket created. Awaiting approval."],
            ["Low-Confidence RCA",   "P1", "Full pipeline + feedback loop re-run", "~8 s",  "Feedback loop triggered. Confidence raised from 0.61 → 0.78. Resolved successfully."],
            ["Concurrent Incidents", "P1+P2","Sequential queue (2 incidents)",    "~9 s",  "Orchestrator processed them sequentially. No data contamination between incidents."],
        ],
        col_widths=[3.5*cm, 1.8*cm, 4.5*cm, 1.8*cm, 5.4*cm]),

    sp(6),
    Paragraph("10.2  System Performance Metrics", sH2),
    tbl(["Metric", "Value", "Notes"],
        [
            ["Average MTTR (rule-based mode)",  "3–6 seconds",   "Full pipeline from detection to Slack notification"],
            ["Average MTTR (LLM/Groq mode)",    "6–12 seconds",  "Additional time for LLM API calls (~1s per agent)"],
            ["RAG Root Cause Accuracy",          "80% (4/5)",     "On simulated test incidents against 21-incident KB"],
            ["False Positive Rate",              "< 5%",          "Threshold-based detection is conservative"],
            ["Feedback Loop Success",            "100% (tested)", "Always improved confidence in test cases"],
            ["Policy Engine Accuracy",           "100%",          "Blocked all 'drop/delete' actions correctly"],
            ["Concurrent Incident Support",      "Yes (queued)",  "Sequential processing — no parallel pipeline support yet"],
        ],
        col_widths=[6*cm, 4*cm, 7*cm]),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — POSSIBLE EXAMINER QUESTIONS & ANSWERS
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 11: LIKELY EXAMINER QUESTIONS & ANSWERS"), sp(8),

    h2_banner("Category A — Architecture & Design"), sp(6),

    *qa("Why did you use a multi-agent system instead of a single AI agent?",
        "A single agent handling all tasks (triage, log analysis, root cause, remediation, notifications) "
        "would produce a monolithic system that is hard to debug, test, and extend. Specialization allows "
        "each agent to have a focused prompt and clear input/output contract. For example, the RCA Agent "
        "only receives diagnostic context — it never sees raw metrics — which keeps its ChromaDB queries "
        "precise. If one agent fails, others continue. We also get per-agent timing data and can improve "
        "individual agents without touching the rest of the pipeline."),

    *qa("What is the role of the Orchestrator and why is it separate from the agents?",
        "The Orchestrator is a workflow manager (Finite State Machine) that sequences the agents and handles "
        "cross-cutting concerns: timing, feedback loops, result aggregation, and error handling. Separating "
        "it from the domain agents follows the Single Responsibility Principle — agents focus on domain logic, "
        "the orchestrator handles coordination logic. This makes the code maintainable and testable: you can "
        "unit-test each agent in isolation without running the full pipeline."),

    *qa("Why use ChromaDB over a relational database for the knowledge base?",
        "A relational database can only do exact keyword matching (SQL LIKE queries). ChromaDB does semantic "
        "similarity search — it understands that 'GC overhead exception' and 'Java heap space error' are "
        "semantically related, even though they share no common keywords. This is critical for incident matching "
        "because engineers describe the same root cause in many different ways across different incidents. "
        "ChromaDB also requires zero server setup (embedded mode), making it ideal for a prototype."),

    *qa("Why is the message bus in-process instead of using Kafka or RabbitMQ?",
        "For a prototype and SDP demonstration, an in-process message bus is sufficient, faster, and much "
        "simpler to operate — no external services to install, configure, or maintain. The downside is that "
        "it doesn't support distributed deployment (multiple machines). In production, you would replace "
        "the in-process bus with Kafka for durability and horizontal scaling, without changing any agent code "
        "since agents only interact with the bus interface."),

    h2_banner("Category B — RAG & LLM"), sp(6),

    *qa("Explain how RAG works in your system step by step.",
        "Step 1 — Population: The 21 historical incidents in data/historical_incidents.json are loaded and "
        "converted to text documents (Title + Symptoms + Cause + Fix). These are embedded using "
        "sentence-transformers (all-MiniLM-L6-v2) into 384-dimensional vectors and stored persistently in ChromaDB. "
        "Step 2 — Query: When an incident occurs, the Diagnostics Agent builds a query_context string "
        "('High CPU 87%, OOMKilledException x8, affected: payment-service'). "
        "Step 3 — Retrieval: This string is embedded and compared against all 21 stored vectors using cosine "
        "similarity. Top-3 most similar historical incidents are returned with confidence scores. "
        "Step 4 — Augmentation: The top hypothesis (root_cause, action, confidence) from the retrieved incident "
        "is passed to the LLM with the prompt 'Explain why this is the root cause given the symptoms.' "
        "Step 5 — Generation: The LLM produces a detailed reasoning chain combining retrieved knowledge with "
        "the current incident's specific context."),

    *qa("What happens when no good RAG match is found?",
        "If the top cosine similarity score is below 0.30, the orchestrator triggers the feedback loop: "
        "it sends an expanded diagnostics request with more context (raw log features + correlated symptoms), "
        "gets a richer query_context, and re-queries ChromaDB. If confidence is still low after the retry, "
        "the system defaults to 'Escalate to L3' as the recommended action and sets needs_approval=True. "
        "The system never makes up a root cause — if it doesn't know, it escalates."),

    *qa("What is the difference between the LLM mode and mock mode?",
        "In mock mode (no API keys), all five agents use deterministic rule-based logic: "
        "Triage maps thresholds to symptoms, Diagnostics extracts patterns with regex, "
        "RCA returns ChromaDB results without LLM reasoning, Remediation applies policy rules, "
        "Comms sends pre-formatted templates. Every agent still produces complete, useful outputs. "
        "In LLM mode (Groq/OpenAI key set), each agent additionally calls the LLM for richer "
        "narrative summaries, more detailed reasoning chains, and step-by-step remediation plans. "
        "The core logic is the same in both modes — LLM only enhances the output quality."),

    h2_banner("Category C — Algorithms & Technical"), sp(6),

    *qa("How does the urgency scoring algorithm work?",
        "It is a weighted additive heuristic. Each metric contributes independently to a cumulative score "
        "based on two severity tiers. CPU >95% adds 0.30, CPU 80-95% adds 0.15. Same for Memory. "
        "Latency >5s adds 0.30, 2-5s adds 0.15. Error count >5 adds 0.20, 1-5 adds 0.10. "
        "The total is capped at 1.0. Score ≥0.70 → P1, 0.40-0.69 → P2, <0.40 → P3. "
        "This is intentionally rule-based rather than ML-based because it needs to be fast, "
        "explainable, and deterministic — an on-call engineer must be able to understand exactly "
        "why something was classified P1."),

    *qa("How does the Policy Engine decide if an action is safe?",
        "It uses keyword pattern matching against three predefined lists. "
        "BLOCKED keywords: 'drop', 'delete', 'disable', 'wipe', 'truncate', 'remove production'. "
        "REQUIRES_APPROVAL keywords: 'migrate', 'rollback', 'force', 'kill', 'override', 'config change'. "
        "ALLOWED: everything else. The action string (e.g., 'Force kill payment-service pod') is checked "
        "against these lists in order. 'Force kill' contains 'force', so it → REQUIRES_APPROVAL. "
        "This is O(n) in the length of the action string. Simple, fast, and 100% auditable by humans."),

    *qa("Why is the feedback loop threshold 0.30 and not higher?",
        "0.30 represents a very low cosine similarity — meaning the current incident barely resembles anything "
        "in the knowledge base. At this level, the top hypothesis is essentially a guess, not a match. "
        "We set it at 0.30 (not 0.70) to avoid excessive feedback loops for moderately confident matches. "
        "In testing, most incidents scored between 0.65 and 0.85, so the feedback loop triggered only for "
        "genuinely novel incident patterns. Setting it higher (e.g., 0.60) would cause unnecessary re-runs "
        "and increase latency."),

    h2_banner("Category D — Design Decisions & Limitations"), sp(6),

    *qa("What are the main limitations of the current system?",
        "Three main limitations: (1) Synthetic data — the simulation engine generates idealized metrics "
        "with clean anomaly patterns. Real production data is noisier, with correlated metrics and "
        "transient spikes that don't represent actual incidents. A threshold-based detector would "
        "generate more false positives in production. (2) Knowledge base size — 21 incidents is enough "
        "to demonstrate RAG, but insufficient for production. A real deployment would need 500+ incidents "
        "with automated ingestion from post-mortems. (3) Sequential pipeline — incidents are processed "
        "one at a time. In production, multiple P1 incidents can occur simultaneously, which would require "
        "a concurrent pipeline with separate orchestrator instances per incident."),

    *qa("How would you scale this system for production use?",
        "Four key changes: (1) Replace in-process message bus with Apache Kafka — durable, horizontally scalable, "
        "supports multiple consumer groups. (2) Deploy agents as separate microservices/containers on Kubernetes "
        "so each can scale independently. (3) Replace simulation engine with real Prometheus/Grafana data streams "
        "and OpenTelemetry log ingestion. (4) Expand ChromaDB to a production vector database (Pinecone, Weaviate) "
        "and build an automated pipeline that ingests closed Jira tickets as new knowledge base entries after "
        "each resolved incident — making the system continuously self-improving."),

    *qa("Why Streamlit instead of React/Vue for the dashboard?",
        "This is an SDP prototype with a 4-month timeline. Streamlit allows building a fully functional, "
        "real-time dashboard in Python — the same language as the entire backend. No JavaScript, no API "
        "layer, no separate frontend build process. The tradeoff is that Streamlit has limited layout "
        "customization compared to React. For a production system, a React frontend with a FastAPI backend "
        "would provide better UX flexibility and performance. For a prototype proving the multi-agent concept, "
        "Streamlit was the right pragmatic choice."),

    *qa("What would you add if you had 3 more months?",
        "Four additions: (1) Live infrastructure integration — connect to Prometheus for real metrics and "
        "OpenTelemetry for real logs, eliminating the simulation engine for production use. "
        "(2) Self-healing loop — after human approves a remediation action, the Remediation Agent actually "
        "executes it via Kubernetes API (kubectl commands for pod restarts, HPA scaling, config updates). "
        "(3) Larger knowledge base — automated ingestion of Jira post-mortems to grow the ChromaDB collection "
        "continuously after each resolved incident. "
        "(4) Open-source LLM — replace Groq/OpenAI with a locally-hosted LLaMA-3 or Mistral model via Ollama "
        "for zero-cost, zero-latency, privacy-preserving LLM inference."),

    PageBreak()
]

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 — QUICK REFERENCE CHEAT SHEET
# ══════════════════════════════════════════════════════════════════════════════
story += [
    h1_banner("SECTION 12: QUICK REFERENCE CHEAT SHEET"), sp(8),

    Paragraph("12.1  Key Numbers to Remember", sH2),
    tbl(["What", "Value", "Why Important"],
        [
            ["Number of AI agents",            "5",           "Triage, Diagnostics, RCA, Remediation, Comms"],
            ["Historical incidents in KB",      "21",          "ChromaDB knowledge base size"],
            ["RAG Top-K retrieval",             "3",           "How many historical incidents are retrieved per query"],
            ["RCA confidence threshold",        "0.30",        "Below this → feedback loop triggered"],
            ["Auto-execute confidence",         "0.85",        "Above this + ALLOWED → no human approval needed"],
            ["P1 urgency score",               "≥ 0.70",      "Critical severity threshold"],
            ["P2 urgency score",               "0.40 – 0.69", "High severity range"],
            ["CPU anomaly threshold",           "85%",         "Triggers high_cpu incident"],
            ["Memory anomaly threshold",        "90%",         "Triggers memory_leak incident"],
            ["Latency anomaly threshold",       "2000 ms",     "Triggers latency_spike incident"],
            ["Error rate anomaly threshold",    "5%",          "Triggers error_surge incident"],
            ["Simulation tick interval",        "1 second",    "How often metrics and logs are generated"],
            ["Observation window size",         "30 seconds",  "Rolling window for feature extraction"],
            ["Cooldown after resolution",       "30 ticks",    "Prevents immediate re-triggering"],
            ["Typical MTTR (mock mode)",        "3–6 seconds", "End-to-end incident resolution time"],
            ["Typical MTTR (LLM mode)",         "6–12 seconds","With Groq API calls per agent"],
            ["Vector embedding dimensions",     "384",         "all-MiniLM-L6-v2 sentence-transformer"],
            ["ChromaDB storage",                "Persistent",  "data/chroma_db/ — survives restarts"],
        ],
        col_widths=[6*cm, 4*cm, 7*cm]),

    sp(8),
    Paragraph("12.2  One-Line Definitions", sH2),
    tbl(["Term", "One-Line Definition"],
        [
            ["RAG",               "Retrieval-Augmented Generation — find relevant past knowledge, use it to guide LLM reasoning"],
            ["Vector Embedding",  "Converting text to a list of numbers (vector) that captures semantic meaning"],
            ["Cosine Similarity", "Angle-based measure of how similar two vectors are: 1.0 = identical, 0.0 = unrelated"],
            ["FSM",               "Finite State Machine — defines allowed states and transitions for the incident lifecycle"],
            ["Message Bus",       "Central routing system that delivers messages from one agent to another"],
            ["Policy Engine",     "Rule-based safety classifier: BLOCKED, REQUIRES_APPROVAL, or ALLOWED for any action"],
            ["MTTR",              "Mean Time To Resolution — how long from incident detection to resolution"],
            ["P1/P2/P3",          "Priority levels: P1=Critical (immediate), P2=High (urgent), P3=Medium (routine)"],
            ["LLM",               "Large Language Model — AI model that generates human-like text (GPT, LLaMA, etc.)"],
            ["Playbook",          "Pre-written step-by-step guide for resolving a specific incident type"],
            ["SRE",               "Site Reliability Engineering — discipline of applying software engineering to IT operations"],
            ["Ngrok",             "Tool that creates a public HTTPS URL pointing to your local server, enabling Slack callbacks"],
        ],
        col_widths=[4.5*cm, 12.5*cm]),

    sp(8),
    Paragraph("12.3  Project File Structure", sH2),
    tbl(["File / Folder", "What It Contains"],
        [
            ["src/agent/orchestrator.py",     "Central coordinator — runs 5-phase pipeline, manages feedback loop"],
            ["src/agent/triage_agent.py",     "Symptom extraction, urgency scoring, severity classification"],
            ["src/agent/diagnostics_agent.py","Log pattern correlation, query context building"],
            ["src/agent/rca_agent.py",        "ChromaDB RAG search, hypothesis formulation, LLM reasoning"],
            ["src/agent/remediation_agent.py","Policy safety check, approval logic, playbook selection"],
            ["src/agent/comms_agent.py",      "Slack alerts with buttons, Jira ticket creation"],
            ["src/agent/llm_client.py",       "Multi-provider LLM wrapper: Groq → OpenAI → Mock"],
            ["src/agent/message_bus.py",      "In-process pub/sub message routing between agents"],
            ["src/agent/models.py",           "Pydantic data models for all agent input/output schemas"],
            ["src/simulation/engine.py",      "Main simulation loop, anomaly detection, orchestrator trigger"],
            ["src/simulation/metrics_generator.py", "Synthetic CPU/Memory/Latency/ErrorRate time series"],
            ["src/simulation/logs_generator.py",    "Synthetic application log line generation"],
            ["src/simulation/observations.py",      "30-second rolling window feature extractor"],
            ["src/simulation/incident.py",          "Incident type enum, ActiveIncident model"],
            ["src/rag/vector_db.py",          "ChromaDB wrapper: populate from JSON, cosine similarity search"],
            ["src/orchestration/policy_engine.py",  "Keyword-based action safety classifier"],
            ["data/historical_incidents.json","21 historical incidents used to populate ChromaDB"],
            ["data/pending_actions.json",     "Slack webhook action queue (approve/deny storage)"],
            ["dashboard/app.py",              "Streamlit real-time dashboard UI"],
            ["run_demo_server.py",            "Flask webhook server + PyNgrok tunnel startup"],
            ["startup.sh",                    "One-command launcher for dashboard + webhook server"],
        ],
        col_widths=[6.5*cm, 10.5*cm]),

    sp(10),
    hr(),
    Paragraph("End of Document", S("end", fontSize=11, textColor=colors.grey,
              fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceBefore=8)),
    Paragraph("OPS Agent — AI-Driven Multi-Agent Incident Response System",
              S("end2", fontSize=10, textColor=DARK_RED, fontName="Helvetica-Bold",
                alignment=TA_CENTER, spaceAfter=4)),
    Paragraph("SCOPE, VIT-AP University, Amravati, India — May 2026",
              S("end3", fontSize=9, textColor=colors.grey, fontName="Helvetica",
                alignment=TA_CENTER)),
]

doc.build(story)
print(f"Saved: {OUT}")
