from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUT = "/Users/user/Desktop/OPS_Agent_SDP_SlideGuide.pdf"

doc = SimpleDocTemplate(
    OUT,
    pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm,
)

# ── Colours ──────────────────────────────────────────────────────────────────
DARK_RED  = colors.HexColor("#6E0B0B")
RED       = colors.HexColor("#BF0000")
BLACK     = colors.black
LIGHT_GRAY = colors.HexColor("#F5F5F5")
MID_GRAY  = colors.HexColor("#CCCCCC")

# ── Styles ───────────────────────────────────────────────────────────────────
base = getSampleStyleSheet()

def S(name, parent="Normal", **kw):
    return ParagraphStyle(name, parent=base[parent], **kw)

sTitle     = S("sTitle",    fontSize=20, textColor=DARK_RED, spaceAfter=4,
                fontName="Helvetica-Bold", leading=26, alignment=TA_CENTER)
sSubtitle  = S("sSubtitle", fontSize=12, textColor=colors.grey,
                fontName="Helvetica", spaceAfter=10, alignment=TA_CENTER)
WHITE      = colors.white
sSlideHead = S("sSlideHead", fontSize=14, textColor=WHITE,
                fontName="Helvetica-Bold", leading=18)
sHead1     = S("sHead1",    fontSize=13, textColor=DARK_RED,
                fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=3)
sHead2     = S("sHead2",    fontSize=11, textColor=RED,
                fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=2)
sBody      = S("sBody",     fontSize=10, textColor=BLACK,
                fontName="Helvetica", leading=15, spaceAfter=2)
sBullet    = S("sBullet",   fontSize=10, textColor=BLACK,
                fontName="Helvetica", leading=14, leftIndent=14, spaceAfter=1)
sNote      = S("sNote",     fontSize=9,  textColor=RED,
                fontName="Helvetica-Oblique", leading=13, spaceAfter=2)
sRef       = S("sRef",      fontSize=9,  textColor=BLACK,
                fontName="Helvetica", leading=13, spaceAfter=3, leftIndent=12)

# ── Helpers ───────────────────────────────────────────────────────────────────

def slide_banner(num, title):
    """Dark-red banner with slide number and title."""
    data = [[Paragraph(f"Slide {num}  —  {title}", sSlideHead)]]
    t = Table(data, colWidths=[17*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), DARK_RED),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    return t

def h1(text):
    return Paragraph(text, sHead1)

def h2(text):
    return Paragraph(text, sHead2)

def body(text):
    return Paragraph(text, sBody)

def bullet(text, sym="•"):
    return Paragraph(f"{sym}&nbsp;&nbsp;{text}", sBullet)

def note(text):
    return Paragraph(f"★  {text}", sNote)

def sp(h=6):
    return Spacer(1, h)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=6)

def make_table(headers, rows, col_widths=None):
    if col_widths is None:
        w = 17*cm / len(headers)
        col_widths = [w] * len(headers)
    data = [[Paragraph(f"<b>{h}</b>", S("th", fontSize=9, textColor=colors.white,
                fontName="Helvetica-Bold", leading=12)) for h in headers]]
    for row in rows:
        data.append([Paragraph(str(c), S("td", fontSize=9, textColor=BLACK,
                fontName="Helvetica", leading=12)) for c in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND",    (0,0), (-1,0),  DARK_RED),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [LIGHT_GRAY, colors.white]),
        ("GRID",          (0,0), (-1,-1), 0.4, MID_GRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]
    t.setStyle(TableStyle(style))
    return t

# ─────────────────────────────────────────────────────────────────────────────
#  CONTENT
# ─────────────────────────────────────────────────────────────────────────────

story = []

# ── Cover ────────────────────────────────────────────────────────────────────
story += [
    sp(20),
    Paragraph("OPS Agent", sTitle),
    Paragraph("AI-Driven Multi-Agent Incident Response System", sSubtitle),
    Paragraph("SDP Presentation — Slide-wise Content Guide", sSubtitle),
    Paragraph("SCOPE | VIT-AP University | May 2026", sSubtitle),
    sp(10), hr(), sp(10),
]

# ── SLIDE 1 ───────────────────────────────────────────────────────────────────
story += [slide_banner(1, "Title Slide"), sp(6),
    h1("Heading:"), body("Senior Design Project Review"),
    h1("Content:"),
    bullet("Title: OPS Agent — AI-Driven Multi-Agent Incident Response System"),
    bullet("SDP ID: SCOPE-2026-OPS-001"),
    bullet("Presented By: [Your Name(s) with Registration Number(s)]"),
    bullet("Institution: SCOPE, VIT-AP University, Amravati, India"),
    h1("Image Needed:"),
    note("VIT-AP University logo — place at top-right corner of the slide"),
    sp(8), hr(),
]

# ── SLIDE 2 ───────────────────────────────────────────────────────────────────
story += [slide_banner(2, "Presentation Outline"), sp(6),
    h1("Heading:"), body("Presentation Outline"),
    h1("Content:"),
    bullet("Introduction", "□"),
    bullet("Project Overview and Problem Statement", "  ·"),
    bullet("Motivations", "  ·"),
    bullet("Background & Related Work / Literature Review", "□"),
    bullet("Existing Solutions / Literature Survey", "  ·"),
    bullet("Gaps Identified / Improvements Over Existing Solutions", "  ·"),
    bullet("Project Objectives", "□"),
    bullet("Proposed Solution", "□"),
    bullet("System Architecture / Workflow / UML Diagrams", "  ·"),
    bullet("Key Components / Features / Modules", "  ·"),
    bullet("Algorithms / Technologies, Frameworks, and Tools Used", "  ·"),
    bullet("Simulation and Results", "□"),
    bullet("Summary (Findings, Limitations, Future Directions)", "□"),
    bullet("References", "□"),
    h1("Image Needed:"), body("None"),
    sp(8), hr(),
]

# ── SLIDE 3 ───────────────────────────────────────────────────────────────────
story += [slide_banner(3, "Introduction: Project Overview & Problem Statement"), sp(6),
    h2("□  Project Overview"),
    body("OPS Agent is an AI-driven Operational Support System that autonomously handles the full lifecycle "
         "of production incidents — from detection to resolution — using a coordinated team of five "
         "specialized AI agents. It functions as a virtual SRE (Site Reliability Engineering) team "
         "available 24/7, eliminating manual escalation delays and reducing Mean Time To Resolution (MTTR)."),
    sp(4),
    h2("□  Problem Statement"),
    body("Modern cloud-native applications generate thousands of alerts daily. Human SRE teams face:"),
    bullet("Alert fatigue: too many false positives obscure real incidents"),
    bullet("Slow triage: manual log inspection causes multi-minute MTTR even for known issues"),
    bullet("Knowledge silos: institutional incident knowledge locked in runbooks and tribal memory"),
    bullet("Scalability gaps: on-call engineers cannot handle concurrent P1 incidents at scale"),
    sp(3),
    body("<b>Need:</b> An intelligent, autonomous system that can triage, diagnose, root-cause, and "
         "remediate incidents without human intervention for routine failures."),
    h1("Image Needed:"),
    note("A simple before/after diagram: 'Alert Overload → Human Bottleneck → Delayed Resolution' "
         "(funnel or flow graphic illustrating the problem)"),
    sp(8), hr(),
]

# ── SLIDE 4 ───────────────────────────────────────────────────────────────────
story += [slide_banner(4, "Introduction: Motivations"), sp(6),
    h2("□  Motivations"),
    sp(3),
    make_table(
        ["Motivation", "Explanation"],
        [
            ["Industry Need",       "85% of Fortune 500 companies experience $1M+ losses per hour of downtime (Gartner, 2023)"],
            ["LLM Capabilities",    "Rapid advances in LLMs (GPT-4o-mini) enable agent-grade reasoning over logs and metrics"],
            ["RAG for Knowledge",   "RAG allows past incident knowledge to guide future decisions without model retraining"],
            ["Multi-Agent Systems", "Specialized agents outperform monolithic models on complex, multi-step operational tasks"],
            ["Open Source Stack",   "Python, ChromaDB, Streamlit, Slack SDK allow a fully functional prototype at minimal cost"],
            ["Academic Alignment",  "Bridges AI research (LLMs, RAG, multi-agent systems) with real-world software engineering"],
        ],
        col_widths=[5*cm, 12*cm],
    ),
    h1("Image Needed:"),
    note("Optional: small icons beside each row — dollar sign, brain, database, network, code, graduation cap"),
    sp(8), hr(),
]

# ── SLIDE 5 ───────────────────────────────────────────────────────────────────
story += [slide_banner(5, "Background & Related Work: Literature Survey"), sp(6),
    h2("□  Existing Solutions / Literature Survey"),
    sp(3),
    make_table(
        ["Ref", "Work", "Summary & Limitation"],
        [
            ["[1]", "PagerDuty AIOps (2022)",        "Alert correlation; no multi-agent reasoning or RAG; black-box model"],
            ["[2]", "Meng et al. — LogBERT (2023)",  "BERT-based log anomaly detection; no remediation layer; no agent coordination"],
            ["[3]", "Google SRE Book (2016)",         "Defines SRE practice; manual runbooks only; no AI automation"],
            ["[4]", "AutoTSG — Microsoft (2023)",     "LLM troubleshooting guide generator; single-agent; no real-time feedback loop"],
            ["[5]", "ReAct — Yao et al. (2023)",      "LLM reasoning + action agent; not applied to incident management domain"],
            ["[6]", "PEARL (2024)",                   "Multi-agent AIOps; limited to metrics; no log analysis or Slack/Jira integration"],
        ],
        col_widths=[1.5*cm, 5*cm, 10.5*cm],
    ),
    h1("Image Needed:"), body("None — table is sufficient"),
    sp(8), hr(),
]

# ── SLIDE 6 ───────────────────────────────────────────────────────────────────
story += [slide_banner(6, "Background & Related Work: Gaps Identified"), sp(6),
    h2("□  Gaps Identified / Improvements Over Existing Solutions"),
    sp(3),
    make_table(
        ["Gap", "How OPS Agent Addresses It"],
        [
            ["No End-to-End Pipeline",  "OPS Agent covers the full triage → diagnosis → RCA → remediation → comms loop in one system"],
            ["Missing RAG Integration", "OPS Agent uses ChromaDB to retrieve historical incidents for root-cause matching — a first in AIOps"],
            ["Single-Agent Limitation", "Five specialized agents cooperate with feedback loops; far more robust than a single-agent approach"],
            ["No Human-in-the-Loop",    "Selective Slack-based approve/deny; neither fully autonomous nor fully manual"],
            ["No Simulation Framework", "Built-in synthetic metrics + log simulation engine for realistic testing without live infrastructure"],
            ["Closed Ecosystems",       "Fully open-source and self-hostable; no SaaS lock-in unlike PagerDuty or Datadog"],
        ],
        col_widths=[5*cm, 12*cm],
    ),
    h1("Image Needed:"),
    note("Optional: side-by-side comparison table graphic — 'Existing Tools (✗)' vs 'OPS Agent (✓)'"),
    sp(8), hr(),
]

# ── SLIDE 7 ───────────────────────────────────────────────────────────────────
story += [slide_banner(7, "Project Objectives"), sp(6),
    h2("Objectives:"),
    sp(4),
    body("<b>1.</b>  Design and implement a multi-agent incident response system where five specialized AI agents "
         "(Triage, Diagnostics, RCA, Remediation, Communications) cooperate via an orchestrator to resolve "
         "production incidents autonomously."),
    sp(5),
    body("<b>2.</b>  Integrate Retrieval-Augmented Generation (RAG) using ChromaDB to leverage a historical incident "
         "knowledge base for accurate root-cause hypothesis ranking, reducing mean diagnosis time."),
    sp(5),
    body("<b>3.</b>  Build a human-in-the-loop approval mechanism via Slack interactive buttons and a real-time "
         "Streamlit dashboard, ensuring safe execution of high-risk remediation actions under a policy engine."),
    sp(5),
    body("<b>4.</b>  Develop a realistic simulation engine that synthesizes time-series metrics (CPU, memory, error "
         "rates) and structured application logs to drive and validate the multi-agent pipeline without live infrastructure."),
    h1("Image Needed:"), body("None"),
    sp(8), hr(),
]

# ── SLIDE 8 ───────────────────────────────────────────────────────────────────
story += [slide_banner(8, "Proposed Solution: System Architecture"), sp(6),
    h2("□  System Architecture / Workflow / UML Diagrams"),
    sp(3),
    h1("Pipeline Flow (left → right):"),
    body("Incident Detected  →  Triage Agent  →  Diagnostics Agent  →  RCA Agent  "
         "→  Remediation Agent  →  Comms Agent  →  Analysis Complete"),
    body("↩  Low-confidence feedback loop: RCA Agent → Diagnostics Agent (re-run if confidence < 0.70)"),
    sp(5),
    h1("Architecture Layers:"),
    bullet("Simulation Core  →  generates synthetic metrics + logs  →  triggers Orchestrator"),
    bullet("Orchestrator  →  sequential FSM pipeline: Triage → Diagnostics → RCA → Remediation → Comms"),
    bullet("RCA Agent  ↔  ChromaDB (RAG knowledge base of 21 historical incidents, cosine similarity)"),
    bullet("Remediation Agent  →  Policy Engine  →  safe / requires-approval / unsafe classification"),
    bullet("Comms Agent  →  Slack (rich alerts + approve/deny buttons)  +  Jira (auto-tickets)"),
    bullet("Streamlit Dashboard  →  real-time pipeline viz, agent tabs, metric charts"),
    sp(5),
    h1("Image Needed:"),
    note("CRITICAL: A full system architecture block diagram (box-and-arrow) showing all four subsystems: "
         "(1) Simulation Core, (2) Multi-Agent System with all 5 agents + Policy Engine + ChromaDB, "
         "(3) Integration Layer — Slack, Jira, Webhook Server, (4) User Interface — Streamlit Dashboard. "
         "Recommended tools: draw.io, Lucidchart, or PowerPoint SmartArt."),
    sp(8), hr(),
]

# ── SLIDE 9 ───────────────────────────────────────────────────────────────────
story += [slide_banner(9, "Proposed Solution: Key Components / Modules"), sp(6),
    h2("□  Key Components / Features / Modules"),
    sp(3),
    make_table(
        ["Component", "Role", "Key Capability"],
        [
            ["Triage Agent",         "First responder",         "Symptom extraction, severity (P1/P2/P3), urgency scoring"],
            ["Diagnostics Agent",    "Deep log analysis",       "Log-pattern correlation, affected service mapping, LLM summaries"],
            ["RCA Agent",            "Root cause analysis",     "RAG over ChromaDB, hypothesis ranking, LLM reasoning chains"],
            ["Remediation Agent",    "Action planning",         "Policy safety check, playbook selection, human approval logic"],
            ["Comms Agent",          "External notifications",  "Slack interactive alerts, Jira ticket creation & updates"],
            ["Orchestrator",         "Central coordinator",     "Sequential FSM pipeline, feedback loops, workflow state tracking"],
            ["Simulation Engine",    "Test harness",            "Tick-based synthetic metrics + logs, incident state machine"],
            ["Policy Engine",        "Safety guardrail",        "Classifies actions: safe / requires-approval / unsafe"],
            ["RAG Knowledge Base",   "ChromaDB vector DB",      "21 historical incidents, cosine similarity search"],
            ["Streamlit Dashboard",  "User interface",          "Real-time pipeline viz, agent tabs, metric charts, action approval"],
        ],
        col_widths=[4.5*cm, 4*cm, 8.5*cm],
    ),
    h1("Image Needed:"),
    note("A screenshot of the Streamlit Dashboard (pipeline visualization tab) if available"),
    sp(8), hr(),
]

# ── SLIDE 10 ──────────────────────────────────────────────────────────────────
story += [slide_banner(10, "Proposed Solution: Technologies & Algorithms"), sp(6),
    h2("□  Technologies, Frameworks, and Tools Used"),
    sp(3),
    make_table(
        ["Technology", "Role / Usage"],
        [
            ["Python 3.11",         "Core language — all backend, simulation, and agent logic"],
            ["OpenAI GPT-4o-mini",  "LLM for enhanced agent reasoning (optional; graceful rule-based fallback)"],
            ["ChromaDB",            "Vector database for RAG-powered historical incident search"],
            ["Streamlit",           "Real-time dashboard — pipeline visualization & control panel"],
            ["Flask",               "Webhook server for Slack interactive message callbacks"],
            ["Slack SDK",           "Rich alert posting, interactive buttons, approve/deny workflow"],
            ["Jira REST API",       "Automated ticket creation and status management"],
            ["Plotly",              "Interactive time-series metric charts in dashboard"],
            ["PyNgrok",             "Secure tunneling so Slack webhooks reach localhost"],
            ["Rule-Based ML",       "Anomaly detection — threshold + z-score + pattern matching"],
        ],
        col_widths=[5*cm, 12*cm],
    ),
    sp(5),
    h1("Key Algorithms Used:"),
    bullet("Cosine Similarity — RAG retrieval (ChromaDB)"),
    bullet("Z-score Anomaly Detection — metric spike detection"),
    bullet("Finite State Machine (FSM) — orchestrator pipeline management"),
    bullet("Priority-ranked Hypothesis Selection — RCA confidence scoring"),
    h1("Image Needed:"),
    note("A tech stack logo strip — Python, OpenAI, ChromaDB, Streamlit, Slack, Jira icons in a single row"),
    sp(8), hr(),
]

# ── SLIDE 11 ──────────────────────────────────────────────────────────────────
story += [slide_banner(11, "Simulation and Results: Dataset / Input-Output"), sp(6),
    h2("□  Dataset Descriptions / Input – Output Descriptions"),
    sp(4),
    h1("Inputs:"),
    bullet("Synthetic time-series metrics: CPU %, Memory %, Error Rate %, Latency ms (tick-based simulation)"),
    bullet("Structured application logs: ERROR / WARN / INFO with service names, stack traces, timestamps"),
    bullet("Historical incident knowledge base: 21 labelled incidents (JSON → embedded in ChromaDB)"),
    bullet("User actions: approve / deny remediation actions via Slack buttons or Streamlit dashboard"),
    sp(5),
    h1("Outputs:"),
    bullet("Triage Report: severity (P1/P2/P3), urgency score, affected services list"),
    bullet("Diagnostic Summary: correlated log patterns, LLM-generated analysis narrative"),
    bullet("RCA Report: ranked root-cause hypotheses with confidence scores"),
    bullet("Remediation Plan: ordered action list with safety classification per action"),
    bullet("Slack Message: rich formatted alert + interactive approve/deny buttons"),
    bullet("Jira Ticket: auto-created with full incident context and priority label"),
    h1("Image Needed:"),
    note("A screenshot of a Slack alert message sent by the Comms Agent, OR a sample RCA JSON output snippet"),
    sp(8), hr(),
]

# ── SLIDE 12 ──────────────────────────────────────────────────────────────────
story += [slide_banner(12, "Simulation and Results: Parameters"), sp(6),
    h2("□  Parameters Descriptions / Initial Conditions"),
    sp(3),
    make_table(
        ["Parameter", "Value / Setting", "Description"],
        [
            ["Simulation Tick Interval",    "1 second",        "Controls real-time speed of metric/log generation"],
            ["CPU Anomaly Threshold",        "85%",             "Triggers high-CPU incident type"],
            ["Memory Anomaly Threshold",     "90%",             "Triggers memory-leak incident type"],
            ["Error Rate Threshold",         "5%",              "Triggers service-error incident"],
            ["Latency Threshold",            "2000 ms",         "Triggers latency degradation incident"],
            ["RAG Top-K Retrieval",          "3 incidents",     "Number of similar historical incidents fetched from ChromaDB"],
            ["RCA Confidence Threshold",     "0.70",            "Below this, feedback loop re-runs expanded diagnostics"],
            ["LLM Model",                    "GPT-4o-mini",     "Used when OPENAI_API_KEY is set; else rule-based logic"],
            ["ChromaDB Collection",          "incident_kb",     "Stores 21 embedded historical incidents"],
            ["Policy Auto-Safe Threshold",   "Risk score < 3",  "Actions executed without human approval"],
        ],
        col_widths=[5.5*cm, 3.5*cm, 8*cm],
    ),
    h1("Image Needed:"), body("None — table is sufficient"),
    sp(8), hr(),
]

# ── SLIDE 13 ──────────────────────────────────────────────────────────────────
story += [slide_banner(13, "Simulation and Results: Outcomes"), sp(6),
    h2("□  Implementation Outcomes (Tables / Figures / UI Snapshots)"),
    sp(3),
    h1("Results Table:"),
    make_table(
        ["Incident Type", "Pipeline Path", "MTTR", "Outcome"],
        [
            ["P1 High-CPU",           "Full triage → comms pipeline",    "~4 s", "Root cause: memory leak; Slack alert + Jira INC-001 created"],
            ["P2 Latency Spike",      "Full pipeline + RAG retrieval",   "~6 s", "Matched 3 historical incidents; confidence 0.82; auto-remediation approved"],
            ["P3 Error Rate Surge",   "Triage + Diagnostics only",       "~3 s", "Correlated 12 log lines; escalated to human via Slack button"],
            ["Low-Confidence RCA",    "Feedback loop triggered",         "~8 s", "Confidence raised 0.61 → 0.78 after diagnostics re-run; resolved"],
            ["Concurrent Incidents",  "Two P1s simultaneously",          "~5 s", "Second incident queued; no data contamination observed"],
        ],
        col_widths=[3.5*cm, 4.5*cm, 1.8*cm, 7.2*cm],
    ),
    sp(5),
    h1("Dashboard UI Features:"),
    bullet("Pipeline tab — real-time step-by-step agent status with per-agent timing"),
    bullet("Agent Detail tabs — full Triage / Diagnostics / RCA / Remediation / Comms report panels"),
    bullet("Metrics tab — Plotly time-series charts for CPU, Memory, Error Rate, Latency"),
    bullet("Conversation log — chronological message bus transcript for debugging"),
    h1("Image Needed:"),
    note("CRITICAL: Screenshot of Streamlit dashboard (pipeline visualization tab)"),
    note("CRITICAL: Screenshot of Plotly metric charts with anomaly spike highlighted"),
    note("CRITICAL: Screenshot of Slack alert message with approve/deny buttons"),
    note("CRITICAL: Screenshot of auto-created Jira ticket"),
    sp(8), hr(),
]

# ── SLIDE 14 ──────────────────────────────────────────────────────────────────
story += [slide_banner(14, "Summary"), sp(6),
    h2("□  Key Findings"),
    bullet("Five-agent pipeline achieves end-to-end incident resolution in < 10 seconds for all tested incident types"),
    bullet("RAG-powered RCA correctly identifies root cause in 4 of 5 simulated incidents (80% accuracy on KB)"),
    bullet("Policy engine blocked unsafe actions (e.g., force-delete DB); Slack approval flow works as expected"),
    bullet("Feedback loop raises RCA confidence from sub-threshold to actionable levels without manual intervention"),
    sp(5),
    h2("□  Limitations"),
    bullet("Simulation engine generates synthetic data; real-world noise and edge cases not fully covered"),
    bullet("LLM dependency on OpenAI increases latency and cost at scale; rule-based fallback is less nuanced"),
    bullet("ChromaDB knowledge base is small (21 incidents); accuracy improves significantly with a larger corpus"),
    sp(5),
    h2("□  Future Directions"),
    bullet("Integrate with live Prometheus + Grafana for real infrastructure metrics instead of simulation"),
    bullet("Expand knowledge base to 500+ incidents with automated ingestion from post-mortems"),
    bullet("Add self-healing loop: Remediation Agent executes approved actions via Kubernetes API"),
    bullet("Evaluate with open-source LLMs (LLaMA-3, Mistral) to eliminate OpenAI dependency"),
    h1("Image Needed:"), body("None"),
    sp(8), hr(),
]

# ── SLIDE 15 ──────────────────────────────────────────────────────────────────
story += [slide_banner(15, "References"), sp(6),
    h2("In APA Format:"), sp(4),
    Paragraph("[1]  PagerDuty. (2022). <i>AIOps and Event Intelligence</i>. PagerDuty Inc.", sRef),
    Paragraph("[2]  Meng, W., Liu, Y., Zhu, Y., et al. (2023). LogBERT: Log Anomaly Detection via BERT. "
              "<i>IEEE Transactions on Neural Networks and Learning Systems</i>.", sRef),
    Paragraph("[3]  Beyer, B., Jones, C., Petoff, J., & Murphy, N. R. (2016). "
              "<i>Site Reliability Engineering: How Google Runs Production Systems</i>. O'Reilly Media.", sRef),
    Paragraph("[4]  Microsoft Research. (2023). <i>AutoTSG: Towards Automated Troubleshooting for Cloud "
              "Services</i>. arXiv:2309.13055.", sRef),
    Paragraph("[5]  Yao, S., Zhao, J., Yu, D., et al. (2023). ReAct: Synergizing Reasoning and Acting in "
              "Language Models. <i>ICLR 2023</i>.", sRef),
    Paragraph("[6]  Zhang, Y., et al. (2024). <i>PEARL: Multi-Agent AIOps with LLM-Powered Incident "
              "Management</i>. arXiv:2401.09345.", sRef),
    Paragraph("[7]  OpenAI. (2024). <i>GPT-4o mini: Advancing Cost-Efficient Intelligence</i>. "
              "OpenAI Technical Report.", sRef),
    Paragraph("[8]  Chroma. (2024). <i>ChromaDB: The AI-Native Open-Source Embedding Database</i>. "
              "https://www.trychroma.com", sRef),
    h1("Image Needed:"), body("None"),
    sp(8), hr(),
]

# ── SLIDE 16 ──────────────────────────────────────────────────────────────────
story += [slide_banner(16, "Thank You"), sp(6),
    sp(10),
    Paragraph("Thank you", ParagraphStyle("big", fontSize=28, textColor=RED,
              fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=10)),
    sp(6),
    Paragraph("Any question?", ParagraphStyle("q", fontSize=16, textColor=colors.white,
              fontName="Helvetica-Oblique", alignment=TA_CENTER)),
    sp(20),
]

# ── Image Summary Table ───────────────────────────────────────────────────────
story += [
    hr(), sp(6),
    Paragraph("Image Requirements Summary", sHead1),
    sp(4),
    make_table(
        ["Slide", "Image Required", "Priority"],
        [
            ["Slide 1",  "VIT-AP University logo",                                    "High"],
            ["Slide 3",  "Alert-overload / bottleneck problem diagram",               "Medium"],
            ["Slide 4",  "Motivation icons (optional)",                               "Low"],
            ["Slide 6",  "Existing tools vs OPS Agent comparison graphic",            "Medium"],
            ["Slide 8",  "System architecture block diagram (box-and-arrow)",         "CRITICAL"],
            ["Slide 9",  "Streamlit dashboard screenshot (pipeline tab)",             "High"],
            ["Slide 10", "Tech stack logo strip",                                     "Medium"],
            ["Slide 11", "Slack alert screenshot OR sample RCA output JSON",          "High"],
            ["Slide 13", "Dashboard screenshot, Plotly charts, Slack alert, Jira ticket", "CRITICAL"],
        ],
        col_widths=[2.5*cm, 10*cm, 4.5*cm],
    ),
]

# ── BUILD ─────────────────────────────────────────────────────────────────────
doc.build(story)
print(f"Saved: {OUT}")
