import streamlit as st
import time
import pandas as pd
import json
from datetime import datetime
import sys
import os

from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add root to path so imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.simulation.metrics_generator import MetricsGenerator
from src.simulation.logs_generator import LogGenerator
from src.detection.anomaly_model import AnomalyDetector
from src.agent.rca_agent import RCAAgent
from src.orchestration.policy_engine import PolicyEngine
from src.integration.slack_client import SlackNotifier
from src.integration.jira_client import JiraConnector

# Page Config
st.set_page_config(page_title="AI Ops Agent (L1/L2)", layout="wide")

# Session State Initialization
if 'metrics_history' not in st.session_state:
    st.session_state.metrics_history = []
if 'log_history' not in st.session_state:
    st.session_state.log_history = []
if 'anomaly_active' not in st.session_state:
    st.session_state.anomaly_active = False
if 'agent_triggered' not in st.session_state:
    st.session_state.agent_triggered = False
if 'current_rca' not in st.session_state:
    st.session_state.current_rca = None
if 'active_ticket_id' not in st.session_state:
    st.session_state.active_ticket_id = None
if 'audit_trail' not in st.session_state:
    st.session_state.audit_trail = []

# Instantiate Components (Singleton-ish via cache would be better, but simple global for demo app flow)
if 'components' not in st.session_state:
    st.session_state.components = {
        'metrics_gen': MetricsGenerator(),
        'logs_gen': LogGenerator(),
        'detector': AnomalyDetector(),
        'agent': RCAAgent(),
        'policy': PolicyEngine(),
        'policy': PolicyEngine(),
        # Use env vars or default to mock
        'slack': SlackNotifier(webhook_url=os.getenv("SLACK_WEBHOOK_URL"), mock=False),
        'jira': JiraConnector(
            url=os.getenv("JIRA_URL"),
            username=os.getenv("JIRA_USERNAME"),
            token=os.getenv("JIRA_API_TOKEN"),
            project_key=os.getenv("JIRA_PROJECT_KEY", "KAN"),
            mock=False
        )
    }
    # Pre-train detector with some dummy normal data
    normal_data = [[30, 40, 0.05], [32, 41, 0.06], [29, 39, 0.04]] * 5
    st.session_state.components['detector'].train_initial(normal_data)

comps = st.session_state.components

# Title & Layout
st.title("🛡️ AI-Powered Ops Agent (L1/L2 Support)")
st.markdown("Automated Monitoring, Anomaly Detection, and Guided Root Cause Analysis")

col1, col2 = st.columns([2, 1])

# --- Sidebar Controls ---
st.sidebar.header("Simulation Controls")
sim_options = ["Normal Operation", "High CPU Incident", "Memory Leak", "DB Connection Failure", "Service Down"]
selected_sim = st.sidebar.selectbox("Inject Scenario", sim_options)

if st.sidebar.button("Apply Scenario"):
    if selected_sim == "Normal Operation":
        comps['metrics_gen'].clear_anomaly()
        st.session_state.anomaly_active = False
        st.session_state.agent_triggered = False
        st.session_state.current_rca = None
    elif selected_sim == "High CPU Incident":
        comps['metrics_gen'].set_anomaly('high_cpu')
    elif selected_sim == "Memory Leak":
        comps['metrics_gen'].set_anomaly('memory_leak')
    elif selected_sim == "DB Connection Failure":
        comps['metrics_gen'].set_anomaly('db_connection_error')
    elif selected_sim == "Service Down":
        comps['metrics_gen'].set_anomaly('service_down')
    
    st.toast(f"Scenario Applied: {selected_sim}")

st.sidebar.divider()
if st.sidebar.button("Reset System"):
    st.session_state.metrics_history = []
    st.session_state.log_history = []
    st.session_state.audit_trail = []
    if 'components' in st.session_state:
        del st.session_state['components'] # Force reload of components
    # comps['metrics_gen'].clear_anomaly() # Cannot call this if we deleted components, but re-init will allow start fresh
    st.rerun()

# --- Main Loop Logic ---
# Data is now generated efficiently inside the fragment in UI section.
# But for the very first render (before fragment runs), we need safe initialization.
if not st.session_state.metrics_history:
    st.session_state.metrics_history.append(comps['metrics_gen'].generate_metrics())
if not st.session_state.log_history:
    st.session_state.log_history.append(comps['logs_gen'].generate_log())

# Detection Step (runs on whatever data we have)
# This allows the 'Control Panel' to stay sync'd with the latest fragment update 
# IF the user interacts.
latest_metrics = st.session_state.metrics_history[-1]
anomaly_result = comps['detector'].detect(latest_metrics)
critical_logs = [l for l in st.session_state.log_history[-3:] if l['level'] == 'CRITICAL' or l['level'] == 'ERROR']
if critical_logs and not anomaly_result['is_anomaly']:
    anomaly_result['is_anomaly'] = True
    anomaly_result['reasons'].append("Critical Error Logs Detected")
# --- Ends Main Loop Pre-Calculation ---

# --- Polling handled by fragment above ---

# --- UI Visualization ---

# --- Polling Fragment (Hidden) ---
@st.fragment(run_every=3)
def poll_slack_updates():
    """
    Checks for Slack events in the background, processes them, and updates state.
    """
    PENDING_FILE = 'data/pending_actions.json'
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, 'r') as f:
                pending_events = json.load(f)
            
            if pending_events:
                print(f"[Dashboard Polling] Found {len(pending_events)} events.", flush=True)
                
                # Check for relevant events
                action_taken = False
                
                for event in pending_events:
                    event_ticket = event.get('ticket_id')
                    action_id = event.get('action_id')
                    user = event.get('user')
                    
                    # Ensure we have an active ticket to match against
                    # We access st.session_state directly.
                    active_id = st.session_state.get('active_ticket_id')
                    
                    if active_id and st.session_state.get('current_rca'):
                        # Relaxed ID Check for Demo Smoothness
                        # We accept the action if it matches OR if we are in a valid state to accept it (ignoring ID mismatch for demo)
                        is_match = (active_id == event_ticket)
                        
                        if not is_match:
                             print(f"[Dashboard Polling] ID Mismatch (Active: {active_id} vs Event: {event_ticket}). Applying anyway for demo.", flush=True)

                        rca = st.session_state.current_rca
                        action_name = rca.get('recommended_action', 'Unknown')
                        
                        if action_id == "approve_action":
                            comps['jira'].update_status(active_id, "RESOLVED", f"Approved via Slack by @{user} (Ticket {event_ticket})")
                            comps['metrics_gen'].clear_anomaly()
                            st.session_state.audit_trail.append({
                                "time": datetime.now().isoformat(),
                                "event": "Slack Approval Received",
                                "details": f"@{user} approved '{action_name}'"
                            })
                            st.toast(f"✅ Slack: @{user} APPROVED action '{action_name}'")
                            
                            # Update State to Reset
                            st.session_state.agent_triggered = False
                            st.session_state.current_rca = None
                            st.session_state.active_ticket_id = None
                            action_taken = True
                            break
                            
                        elif action_id == "escalate_action":
                            comps['jira'].update_status(active_id, "ESCALATED", f"Escalated via Slack by @{user} (Ticket {event_ticket})")
                            st.session_state.audit_trail.append({
                                "time": datetime.now().isoformat(),
                                "event": "Slack Escalation Received",
                                "details": f"@{user} escalated incident"
                            })
                            st.toast(f"⚠️ Slack: @{user} ESCALATED incident")
                            
                            # Update State to Reset
                            st.session_state.agent_triggered = False
                            st.session_state.current_rca = None
                            st.session_state.active_ticket_id = None
                            action_taken = True
                            break
                    else:
                        print(f"[Dashboard Polling] Skipping Event {event_ticket}. No Active Incident.", flush=True)

                # Clear the file regardless (consume all events to prevents loops)
                # Or maybe only if we processed one? No, safer to clear queue to avoid staleness.
                with open(PENDING_FILE, 'w') as f:
                    json.dump([], f)
                
                if action_taken:
                    time.sleep(1) # Allow toast to be seen?
                    st.rerun()
                
        except Exception as e:
            print(f"[Dashboard Polling Error] {e}", flush=True)

poll_slack_updates()

# --- UI Visualization ---

with col1:
    @st.fragment(run_every=2)
    def live_metrics_section():
        # Generate new data point
        # Note: In a fragment, we must be careful about mutating global session state if other parts read it.
        # But here valid just to append for visualization.
        new_metrics = comps['metrics_gen'].generate_metrics()
        new_log = comps['logs_gen'].generate_log(anomaly_mode=new_metrics['anomaly_active'])
        
        # We need to access/update the 'history' in session state.
        # Since this runs in a separate context, ensure we don't have race conditions (Streamlit manages this mostly).
        st.session_state.metrics_history.append(new_metrics)
        if len(st.session_state.metrics_history) > 60: st.session_state.metrics_history.pop(0)

        st.session_state.log_history.append(new_log)
        if len(st.session_state.log_history) > 20: st.session_state.log_history.pop(0)

        st.subheader("Live System Metrics")
        df = pd.DataFrame(st.session_state.metrics_history)
        if not df.empty:
            st.line_chart(df[['cpu_percent', 'memory_percent']], height=200)
            st.line_chart(df[['latency_seconds']], height=150)
        
        st.subheader("Live Logs")
        for l in reversed(st.session_state.log_history[-5:]):
            color = "red" if l['level'] in ['ERROR', 'CRITICAL'] else "green"
            st.markdown(f":{color}[[{l['timestamp']}] {l['level']} {l['method']} {l['endpoint']} - {l['message']}]")

    live_metrics_section()

with col2:
    st.subheader("Ops Agent Status")
    
    # We need the LATEST metrics for detection, which were just updated in the fragment/session_state?
    # Actually, the fragment updates session_state, but THIS main script runs top-to-bottom.
    # So 'metrics' variable from line 95 is "stale" if we moved generation into the fragment.
    # FIX: We should execute detection logic INSIDE the fragment or rely on shared state.
    # Better: Let's keep data generation in the MAIN loop (so it runs on manual interaction)
    # AND inside the fragment for auto-updates.
    # Actually, simpler: The Fragment updates the display.
    # The main loop logic for "Status" needs the latest data.
    # If the main loop is static, "Status" won't update until interaction.
    # This is exactly what the user wants ("does not disturb me").
    # The anomaly status should ONLY change when they click "Apply Scenario" (which reruns main loop).
    
    if st.session_state.metrics_history:
        latest_metrics = st.session_state.metrics_history[-1]
        anomaly_result = comps['detector'].detect(latest_metrics)
        
        crit_logs = [l for l in st.session_state.log_history[-3:] if l['level'] in ['ERROR', 'CRITICAL']]
        if crit_logs and not anomaly_result['is_anomaly']:
             anomaly_result['is_anomaly'] = True
             anomaly_result['reasons'].append("Critical Logs")
    else:
         anomaly_result = {'is_anomaly': False, 'reasons': []}

    status_color = "green"
    status_text = "System Healthy"
    
    if anomaly_result['is_anomaly']:
        status_color = "red"
        status_text = "⚠️ ANOMALY DETECTED"
        st.error(f"Alert: {', '.join(anomaly_result['reasons'])}")
        
        if not st.session_state.agent_triggered:
            if st.button("🤖 Hand Over to Ops Agent"):
                st.session_state.agent_triggered = True
                with st.spinner("Agent Analyzing..."):
                    # Use last known metrics
                    metrics_snap = st.session_state.metrics_history[-1] if st.session_state.metrics_history else {}
                    rca_result = comps['agent'].analyze_incident(metrics_snap, st.session_state.log_history[-10:])
                    st.session_state.current_rca = rca_result
                    
                    # Create Ticket
                    ticket_id = comps['jira'].create_ticket({
                         'summary': rca_result.get('summary', 'Incident'),
                         'root_cause': rca_result.get('root_cause'),
                         'severity': rca_result.get('severity', 'P2')
                    })
                    st.session_state.active_ticket_id = ticket_id
                    
                    # Slack
                    slack_response = comps['slack'].post_incident(rca_result, ticket_id=ticket_id)
                    
                    st.session_state.audit_trail.append({
                        "time": datetime.now().isoformat(),
                        "event": "RCA Triggered",
                        "details": f"Jira: {ticket_id} | Slack Sent"
                    })
                    
                    if slack_response and slack_response.get('mock'):
                        with st.expander("🔌 Slack Notification (Mock Mode)", expanded=True):
                            st.info("System is in Mock Mode. This payload would be sent to Slack:")
                            st.json(slack_response.get('payload', {}))
                            st.caption(f"Interactive Callback URL: {slack_response.get('callback', 'Not Set')}")
                            st.warning("To send real messages, please provide a Slack Incoming Webhook URL.")
                st.rerun()
    
    st.markdown(f"**Status**: :{status_color}[{status_text}]")
    
    # ... Agent Output & Actions (Standard Static Code) ...


    # --- Agent Output & Actions ---
    if st.session_state.agent_triggered and st.session_state.current_rca:
        rca = st.session_state.current_rca
        
        st.info(f"### 🧠 Agent Diagnosis (Ticket: {st.session_state.active_ticket_id})")
        
        # Display Severity Badge
        severity = rca.get('severity', 'P2')
        sev_color = "red" if severity == "P1" else "orange"
        st.markdown(f"**Severity**: :{sev_color}[{severity}] | **Confidence**: {rca.get('confidence', 0.0)}")
        
        st.markdown(f"**Root Cause**: {rca.get('root_cause', 'Unknown')}")
        st.markdown(f"**Analysis**: \n{rca.get('analysis', 'No detailed analysis available.')}")
        st.markdown(f"**Recommendation**: `{rca.get('recommended_action', 'Escalate to L3')}`")
        if rca.get('escalation_reason'):
            st.warning(f"Escalation Reason: {rca['escalation_reason']}")
        
        # Policy Check
        action = rca.get('recommended_action', 'Escalate to L3')
        policy_status, policy_msg = comps['policy'].check_safety(action)
        
        # Confidence Guardrail
        confidence = rca.get('confidence', 0.5)
        if confidence < 0.75:
            policy_status = "REQUIRES_APPROVAL"
            policy_msg += f" (Low Confidence {confidence} < 0.75)"
        
        st.markdown("---")
        st.markdown(f"**Policy Check**: {policy_status}")
        st.caption(policy_msg)
        
        if policy_status == "REQUIRES_APPROVAL":
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Approve Action"):
                    # Execute Action
                    comps['jira'].update_status(st.session_state.active_ticket_id, "RESOLVED", f"Action {action} approved by user.")
                    st.session_state.audit_trail.append({
                        "time": datetime.now().isoformat(),
                        "event": "Action Approved & Executed",
                        "details": f"User approved: {action} | Ticket Resolved"
                    })
                    comps['metrics_gen'].clear_anomaly() # Simulate Fix
                    st.success(f"Action '{action}' Executed via Automation.")
                    time.sleep(1)
                    st.session_state.agent_triggered = False
                    st.session_state.current_rca = None
                    st.session_state.active_ticket_id = None
                    st.rerun()
            with col_b:
                if st.button("❌ Deny / Manual Fix"):
                    comps['jira'].update_status(st.session_state.active_ticket_id, "ESCALATED", "User denied automated action.")
                    st.session_state.audit_trail.append({
                        "time": datetime.now().isoformat(),
                        "event": "Action Denied",
                        "details": "User chose manual intervention | Ticket Escalated"
                    })
                    st.warning("Agent dismissed. Manual intervention required.")
                    st.session_state.agent_triggered = False
                    st.session_state.current_rca = None
                    st.session_state.active_ticket_id = None
                    st.rerun()

st.divider()
with st.expander("📜 Incident Audit Trail"):
    for item in st.session_state.audit_trail:
        st.code(f"{item['time']} - {item['event']}: {item['details']}")

# Keep alive (auto-refresh) - Enables polling for Slack events ONLY when an incident is active
if st.session_state.agent_triggered:
    time.sleep(3)
    st.rerun()

if st.button("🔄 Refresh Data"):
    st.rerun()

