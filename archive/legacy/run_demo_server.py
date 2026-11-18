import os
import sys
import threading
from pyngrok import ngrok
from dotenv import load_dotenv

# Load env vars
load_dotenv()

from src.integration.webhook_server import app

def run_server():
    # Run Flask without reloading to avoid signaling issues in thread
    app.run(port=3000, use_reloader=False)

def main():
    # 1. Open Ngrok Tunnel
    # Set auth token provided by user
    ngrok_token = os.getenv("NGROK_AUTH_TOKEN")
    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)
    else:
        print("⚠️ Warning: NGROK_AUTH_TOKEN not found in .env. Ngrok might fail if not already configured.")
    
    try:
        public_url = ngrok.connect(3000).public_url
        print("="*60)
        print(f"🌍 PUBLIC URL GENERATED: {public_url}/slack/actions")
        print("="*60)
        print("Use this URL in your Slack App Interaction Settings.")
    except Exception as e:
        print(f"Ngrok Error: {e}")
        print("Ensure you have set your authtoken if required: `ngrok config add-authtoken <token>`")
        sys.exit(1)

    # 2. Start Flask Server in background thread (or main thread)
    print("🚀 Starting Webhook Server on port 3000...")
    
    # We run Flask in the main thread for stability, tunnel is already backgrounded by pyngrok
    run_server()

if __name__ == "__main__":
    main()
