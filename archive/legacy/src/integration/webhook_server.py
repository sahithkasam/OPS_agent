from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

import requests

app = Flask(__name__)

PENDING_FILE = 'data/pending_actions.json'
API_BASE_URL = os.getenv("OPS_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.route('/slack/actions', methods=['POST'])
def slack_actions():
    """
    Endpoint (Webhook) that Slack calls when a user clicks a button.
    In a real deployment, this would be exposed via ngrok (https://<id>.ngrok-free.app/slack/actions).
    """
    if not request.form.get('payload'):
        return jsonify({"error": "No payload found"}), 400

    payload = json.loads(request.form['payload'])
    user_info = payload.get('user', {})
    user = user_info.get('username') or user_info.get('name') or user_info.get('id') or "unknown"
    action_data = payload['actions'][0]
    action_id = action_data['action_id']
    incident_id = action_data['value']

    print(f"Received Slack Interaction from {user}: {action_id} -> Incident {incident_id}", flush=True)

    if action_id == "approve_action":
        decision = "approve"
        response_text = f"✅ Decision received from @{user}. Approving action for {incident_id}..."
    elif action_id in ("escalate_action", "deny_action"):
        decision = "deny"
        response_text = f"🚨 Decision received from @{user}. Escalating {incident_id} to L3..."
    else:
        return jsonify({
            "replace_original": False,
            "text": f"Unknown Slack action: {action_id}",
            "response_type": "ephemeral"
        })

    api_result = _send_to_fastapi(decision, incident_id)
    if api_result["ok"]:
        return jsonify({
            "replace_original": True,
            "text": response_text,
            "response_type": "in_channel"
        })

    _queue_pending_action(action_id, decision, incident_id, user)
    print(f"FastAPI callback failed; queued pending Slack action: {api_result['error']}", flush=True)

    return jsonify({
        "replace_original": False,
        "text": response_text,
        "response_type": "in_channel"
    })


def _send_to_fastapi(decision: str, incident_id: str) -> dict:
    """Forward Slack clicks to the active React/FastAPI backend."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/incidents/{incident_id}/{decision}",
            timeout=5,
        )
        if response.ok:
            return {"ok": True}
        return {"ok": False, "error": f"{response.status_code}: {response.text}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _queue_pending_action(action_id: str, decision: str, incident_id: str, user: str):
    """Fallback for the older Streamlit dashboard, which polls this JSON file."""
    event_data = {
        "action_id": action_id,
        "action": decision,
        "ticket_id": incident_id,
        "incident_id": incident_id,
        "user": user,
        "timestamp": datetime.utcnow().isoformat()
    }

    existing = []
    try:
        with open(PENDING_FILE, 'r') as f:
            existing = json.load(f)
            if isinstance(existing, dict):
                existing = [existing]
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    existing.append(event_data)

    os.makedirs(os.path.dirname(PENDING_FILE), exist_ok=True)
    with open(PENDING_FILE, 'w') as f:
        json.dump(existing, f)

if __name__ == '__main__':
    print("Starting Slack Webhook Listener on port 3000...")
    app.run(port=3000)
