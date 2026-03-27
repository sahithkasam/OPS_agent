"""
run.py — Single entry point to start the entire OPS Agent system.

Starts:
  1. Webhook Server (Flask) + Ngrok tunnel  → port 3000
  2. FastAPI Backend                         → port 8000
  3. Streamlit Dashboard                     → port 8501

Usage:
  python run.py
"""

import os
import sys
import time
import threading
import subprocess
import signal
from dotenv import load_dotenv

load_dotenv()

# ── Track subprocesses for clean shutdown ─────────────────────────
processes = []


def cleanup(signum=None, frame=None):
    print("\n\n🛑 Shutting down all services...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


# ── 1. Webhook Server + Ngrok ─────────────────────────────────────
def start_webhook():
    from pyngrok import ngrok
    from src.integration.webhook_server import app

    ngrok_token = os.getenv("NGROK_AUTH_TOKEN")
    if ngrok_token:
        ngrok.set_auth_token(ngrok_token)
    else:
        print("⚠️  NGROK_AUTH_TOKEN not set — ngrok may fail.")

    try:
        public_url = ngrok.connect(3000).public_url
        print("=" * 60)
        print(f"🌍 Ngrok Public URL : {public_url}/slack/actions")
        print("   → Paste this into your Slack App > Interactivity settings")
        print("=" * 60)
    except Exception as e:
        print(f"❌ Ngrok error: {e}")

    print("🚀 Webhook server starting on http://localhost:3000 ...")
    app.run(port=3000, use_reloader=False)


# ── 2. FastAPI Backend ────────────────────────────────────────────
def start_api():
    import uvicorn
    print("🚀 FastAPI backend starting on http://localhost:8000 ...")
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
    )


# ── 3. Streamlit Dashboard ────────────────────────────────────────
def start_dashboard():
    print("🚀 Streamlit dashboard starting on http://localhost:8501 ...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
         "--server.headless", "true"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    processes.append(proc)
    proc.wait()


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  🤖  OPS Agent — Full System Startup")
    print("=" * 60)
    print("  Webhook  → http://localhost:3000")
    print("  API      → http://localhost:8000/docs")
    print("  Dashboard→ http://localhost:8501")
    print("=" * 60)
    print("  Press Ctrl+C to stop all services\n")

    # Start webhook + API in background threads
    t_webhook = threading.Thread(target=start_webhook, daemon=True)
    t_api = threading.Thread(target=start_api, daemon=True)

    t_webhook.start()
    time.sleep(2)   # let ngrok connect first
    t_api.start()
    time.sleep(1)

    # Streamlit runs in the foreground (blocks until Ctrl+C)
    start_dashboard()
