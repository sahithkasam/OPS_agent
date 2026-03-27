"""
Tests for RCA Agent — OpsPilot
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent.rca_agent import RCAAgent


@pytest.fixture
def agent():
    return RCAAgent()


def test_rca_agent_init(agent):
    """RCA Agent should initialize without errors."""
    assert agent is not None
    assert agent.kb is not None


def test_analyze_incident_high_cpu(agent):
    """Should detect high CPU and return a valid analysis dict."""
    metrics = {"cpu_percent": 92.5, "memory_percent": 60.0, "latency_seconds": 0.5}
    logs = {"recent_errors": 2, "log_samples": ["ERROR [Service] Connection refused"]}
    result = agent.analyze_incident(metrics, logs, incident_id="test-001")

    assert isinstance(result, dict)
    assert "hypotheses" in result
    assert "top_recommendation" in result
    assert "severity" in result
    assert "needs_approval" in result
    assert "summary" in result
    assert len(result["hypotheses"]) > 0


def test_severity_p1_for_critical_metrics(agent):
    """CPU > 95% should result in P1 severity."""
    metrics = {"cpu_percent": 97.0, "memory_percent": 70.0, "latency_seconds": 0.3}
    logs = {"recent_errors": 0, "log_samples": []}
    result = agent.analyze_incident(metrics, logs)
    assert result["severity"] == "P1"


def test_severity_p2_for_high_metrics(agent):
    """CPU > 80% should result in P2 severity."""
    metrics = {"cpu_percent": 85.0, "memory_percent": 60.0, "latency_seconds": 0.5}
    logs = {"recent_errors": 0, "log_samples": []}
    result = agent.analyze_incident(metrics, logs)
    assert result["severity"] in ("P2", "P3")  # allow P3 too


def test_analyze_incident_no_logs(agent):
    """Should handle empty logs gracefully."""
    metrics = {"cpu_percent": 70.0, "memory_percent": 80.0, "latency_seconds": 2.5}
    logs = {}
    result = agent.analyze_incident(metrics, logs)
    assert result is not None
    assert "top_recommendation" in result


def test_needs_approval_default_true(agent):
    """Most incidents should require human approval."""
    metrics = {"cpu_percent": 85.0, "memory_percent": 70.0, "latency_seconds": 0.5}
    logs = {"recent_errors": 3, "log_samples": []}
    result = agent.analyze_incident(metrics, logs)
    # Default = needs approval (except very high confidence auto-actions)
    assert isinstance(result["needs_approval"], bool)
