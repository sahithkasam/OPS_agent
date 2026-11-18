"""One incident must produce exactly one Slack alert and one Jira ticket."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent.llm_client import LLMClient
from src.agent.message_bus import MessageBus
from src.agent.orchestrator import OrchestratorAgent
from src.simulation.engine import SimulationEngine


class FakeSlack:
    def __init__(self):
        self.posts = []

    def post_incident(self, data, ticket_id=None):
        self.posts.append(ticket_id)
        return {"ok": True}


class FakeJira:
    mock = True

    def __init__(self):
        self.created = []

    def create_ticket(self, data):
        key = f"KAN-{len(self.created) + 1}"
        self.created.append(key)
        return key

    def get_ticket_status(self, key):
        return "To Do"

    def update_status(self, key, status, comment=None):
        return True


@pytest.fixture
def engine(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.chdir(tmp_path)          # tick() appends to data/app_logs.log
    (tmp_path / "data").mkdir()
    eng = SimulationEngine()
    eng.slack_notifier, eng.jira_connector = FakeSlack(), FakeJira()
    eng.orchestrator = OrchestratorAgent(bus=MessageBus(), slack_notifier=eng.slack_notifier,
                                         jira_connector=eng.jira_connector, llm_client=LLMClient())
    return eng


def test_single_slack_and_jira_per_incident(engine):
    inc = engine.inject_incident("dns_failure")
    engine.tick()
    assert inc.analysis is not None
    assert engine.slack_notifier.posts == [inc.id]
    assert engine.jira_connector.created == ["KAN-1"]
    assert inc.slack_sent and inc.jira_ticket_key == "KAN-1"

    # Re-analysis (e.g. after new logs) must not notify again.
    engine.trigger_reanalysis()
    engine.tick()
    assert engine.slack_notifier.posts == [inc.id]
    assert engine.jira_connector.created == ["KAN-1"]


def test_logging_keeps_integrations(engine):
    """engine.log() used to reset log_source/slack/jira to None on every call."""
    slack, jira = engine.slack_notifier, engine.jira_connector
    engine.log_source = FakeLogSource([])
    engine.log("hello")
    assert engine.slack_notifier is slack and engine.jira_connector is jira
    assert engine.log_source is not None


class FakeLogSource:
    def __init__(self, batches):
        self.batches = list(batches)

    def fetch_new_logs(self):
        return self.batches.pop(0) if self.batches else []


ERR = "2026 ERROR [Backend] GET /x 500 - boom"
OK = "2026 INFO [Backend] GET /x 200 - ok"


def test_single_noise_error_does_not_open_incident(engine):
    engine.log_source = FakeLogSource([[OK, ERR, OK]])
    engine.tick()
    assert engine.state_tracker.get_active() == []


def test_error_burst_opens_service_down(engine):
    engine.log_source = FakeLogSource([[ERR, ERR, ERR]])
    engine.tick()
    assert [i.type.value for i in engine.state_tracker.get_active()] == ["service_down"]


def test_old_errors_in_window_do_not_retrigger(engine):
    engine.log_source = FakeLogSource([[ERR, ERR, ERR], [OK], [OK]])
    engine.tick()
    inc = engine.state_tracker.get_active()[0]
    engine.approve_action(inc.id)
    engine.cooldown_until = 0          # cooldown over; the errors are still in the window
    engine.tick()
    engine.tick()
    assert engine.state_tracker.get_active() == []
