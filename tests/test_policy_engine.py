"""
Tests for Policy Engine — OpsPilot
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.orchestration.policy_engine import PolicyEngine


@pytest.fixture
def engine():
    return PolicyEngine()


def test_safe_action_allowed(engine):
    """Check Logs is a safe action and should be ALLOWED."""
    status, msg = engine.check_safety("Check Logs")
    assert status == "ALLOWED"
    assert "Safe" in msg


def test_restart_requires_approval(engine):
    """Restart Service requires human approval."""
    status, msg = engine.check_safety("Restart Service")
    assert status == "REQUIRES_APPROVAL"


def test_scale_requires_approval(engine):
    """Scale Resources requires human approval."""
    status, msg = engine.check_safety("Scale Resources")
    assert status == "REQUIRES_APPROVAL"


def test_blocked_action(engine):
    """Delete Database is a blocked dangerous action."""
    status, msg = engine.check_safety("Delete Database")
    assert status == "BLOCKED"


def test_ssh_access_blocked(engine):
    """SSH Access should be blocked."""
    status, msg = engine.check_safety("SSH Access")
    assert status == "BLOCKED"


def test_unknown_action_defaults_to_approval(engine):
    """Unknown actions should default to REQUIRES_APPROVAL (cautious)."""
    status, msg = engine.check_safety("Do Something Unknown")
    assert status == "REQUIRES_APPROVAL"


def test_run_diagnostics_allowed(engine):
    """Run Diagnostics is a safe action."""
    status, msg = engine.check_safety("Run Diagnostics")
    assert status == "ALLOWED"
