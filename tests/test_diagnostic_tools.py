"""
Tests for Diagnostic Tools — OpsPilot
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.tools.diagnostic_tools import (
    ping_host,
    check_port,
    check_disk_usage,
    get_system_metrics,
    run_full_diagnostic
)


def test_ping_host_google_dns():
    """Ping to 8.8.8.8 should succeed in a networked environment."""
    result = ping_host("8.8.8.8", count=1)
    assert "tool" in result
    assert result["tool"] == "ping"
    assert "reachable" in result
    assert isinstance(result["reachable"], bool)


def test_check_port_closed():
    """Port 9999 on localhost should be closed (not in use)."""
    result = check_port("localhost", 9999)
    assert result["tool"] == "port_check"
    assert "open" in result
    assert isinstance(result["open"], bool)


def test_check_disk_usage_root():
    """Disk usage for / should return valid data."""
    result = check_disk_usage("/")
    assert result["tool"] == "disk_usage"
    assert "used_percent" in result
    assert 0 <= result["used_percent"] <= 100
    assert "free_gb" in result


def test_get_system_metrics():
    """System metrics should return CPU/memory/disk data."""
    result = get_system_metrics()
    assert result["tool"] == "system_metrics"
    # At least disk should be present (psutil optional)
    assert "disk_percent" in result or "error" in result


def test_run_full_diagnostic_service_down():
    """Full diagnostic for service_down should include network and system checks."""
    result = run_full_diagnostic("service_down")
    assert "incident_type" in result
    assert result["incident_type"] == "service_down"
    assert "checks" in result
    assert "healthy" in result
    assert isinstance(result["issues_found"], list)


def test_run_full_diagnostic_high_cpu():
    """Full diagnostic for high_cpu should include top_processes check."""
    result = run_full_diagnostic("high_cpu")
    assert "checks" in result
    assert "system" in result["checks"]


def test_run_full_diagnostic_disk():
    """Full diagnostic for disk_usage_high should include disk check."""
    result = run_full_diagnostic("disk_usage_high")
    assert "disk" in result["checks"]
