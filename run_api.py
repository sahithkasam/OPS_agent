"""
run_api.py — Start the OpsPilot FastAPI server
Usage: python run_api.py
API Docs: http://localhost:8000/docs
"""

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  OpsPilot FastAPI Backend")
    print("  Autonomous IT Help Desk & Ticket Resolution")
    print("=" * 60)
    print("  API Docs:  http://localhost:8000/docs")
    print("  Health:    http://localhost:8000/health")
    print("  Agents:    http://localhost:8000/agents/status")
    print("=" * 60)

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
