from flask import Flask, request, jsonify
import json

app = Flask(__name__)

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
    user = payload['user']['username']
    action_data = payload['actions'][0]
    action_id = action_data['action_id']
    value = action_data['value']

    print(f"Received Slack Interaction from {user}: {action_id} -> Ticket {value}", flush=True)

    # Logic to handle the action (e.g., call PolicyEngine, execute action)
    # Write to a shared file that the Dashboard polls
    event_data = {
        "action_id": action_id,
        "ticket_id": value,
        "user": user,
        "timestamp": 1234567890 # placeholder, real time in dashboard
    }
    
    # Append to pending actions file
    PENDING_FILE = 'data/pending_actions.json'
    existing = []
    try:
        with open(PENDING_FILE, 'r') as f:
            existing = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
        
    existing.append(event_data)
    
    with open(PENDING_FILE, 'w') as f:
        json.dump(existing, f)
    
    response_text = ""
    if action_id == "approve_action":
         response_text = f"✅ Decision received from @{user}. Approving action for {value}..."
    elif action_id == "escalate_action":
         response_text = f"🚨 Decision received from @{user}. Escalating {value} to L3..."

    # Return new message to replace the original one (or just an ack)
    return jsonify({
        "replace_original": False,
        "text": response_text,
        "response_type": "in_channel"
    })

if __name__ == '__main__':
    print("Starting Slack Webhook Listener on port 3000...")
    app.run(port=3000)
