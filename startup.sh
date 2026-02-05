#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Shutting down..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT SIGTERM

echo "🚀 Starting Ops Agent System..."

# 1. Start Webhook Server & Ngrok (runs in background)
echo "Starting Webhook Server..."
python3 run_demo_server.py > webhook.log 2>&1 &

# Wait for it to initialize
echo "Waiting for ngrok tunnel..."
sleep 5

# 2. Check if it's running
if ps aux | grep -v grep | grep "run_demo_server.py" > /dev/null; then
    echo "✅ Webhook Server is running."
else
    echo "❌ Failed to start Webhook Server. Check webhook.log"
    exit 1
fi

# 3. Start Streamlit Dashboard
echo "Starting Dashboard..."
streamlit run dashboard/app.py

# When Streamlit exits, the trap will kill the webhook server
