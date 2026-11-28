"""Cold-start behaviour: nothing slow or networked happens until it's needed."""
import sys
import threading
import types
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.detection.anomaly_model import AnomalyDetector
from src.integration.jira_client import JiraConnector


def test_detector_works_untrained_and_trains_on_demand():
    det = AnomalyDetector()
    assert det.model is None
    res = det.detect({"cpu_percent": 95, "memory_percent": 40, "latency_seconds": 0.05})
    assert res["is_anomaly"] and res["ml_score"] == 0.0
    det.train_initial([[30 + i % 5, 40, 0.05] for i in range(20)])
    assert det.is_fitted and det.model is not None


def test_jira_does_not_connect_at_startup(monkeypatch):
    calls = []
    fake = types.ModuleType("jira")

    class FakeJIRA:
        def __init__(self, server, basic_auth):
            calls.append(server)
            raise ConnectionError("unreachable")

    fake.JIRA = FakeJIRA
    monkeypatch.setitem(sys.modules, "jira", fake)

    jira = JiraConnector(url="https://example.atlassian.net", username="u", token="t", mock=False)
    assert calls == [] and not jira.mock          # nothing happened yet
    key = jira.create_ticket({"summary": "s", "root_cause": "r"})
    assert calls == ["https://example.atlassian.net"]  # connected on first use
    assert jira.mock and key.startswith("OPS-")    # failed -> mock fallback
    jira.create_ticket({"summary": "s2", "root_cause": "r"})
    assert len(calls) == 1                          # never retries per call


def test_unconfigured_jira_is_mock():
    assert JiraConnector(url=None, username=None, token=None, mock=False).mock


def test_kb_endpoint_returns_503_while_loading(monkeypatch):
    import api.server as server
    rca = types.SimpleNamespace(kb_ready=False, _kb_ready=threading.Event(), _kb_error=None)
    fake_runtime = types.SimpleNamespace(engine=types.SimpleNamespace(
        orchestrator=types.SimpleNamespace(rca=rca)))
    monkeypatch.setattr(server, "runtime", fake_runtime)
    with pytest.raises(HTTPException) as exc:
        server._kb()
    assert exc.value.status_code == 503
    assert server.health() == {"ok": True, "kb_ready": False}
