"""Tests for the postmortem-backed knowledge base and its build script."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.rag.vector_db import KnowledgeBase
from src.simulation.incident import IncidentType

DATASET = ROOT / "data" / "historical_incidents.json"
TYPES = {t.value for t in IncidentType}

_spec = importlib.util.spec_from_file_location("build_kb", ROOT / "scripts" / "build_kb_from_postmortems.py")
build_kb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_kb)


@pytest.fixture(scope="module")
def items():
    with open(DATASET, encoding="utf-8") as f:
        return json.load(f)


def test_dataset_schema(items):
    assert len(items) >= 100
    required = {"id", "company", "source_url", "category", "summary", "description",
                "root_cause", "resolution", "recommended_action", "severity", "logs_signature"}
    ids = set()
    for it in items:
        assert required <= it.keys(), it.get("id")
        assert it["category"] in TYPES
        assert it["severity"] in ("P1", "P2", "P3")
        assert it["source_url"].startswith("http")
        assert it["id"] not in ids
        ids.add(it["id"])


def test_every_incident_type_has_postmortems(items):
    """Each injectable incident type should retrieve at least one real postmortem."""
    present = {it["category"] for it in items}
    assert TYPES <= present, TYPES - present


def test_build_script_matches_incident_types():
    assert set(build_kb.CATEGORIES) == TYPES


@pytest.fixture(scope="module")
def kb(tmp_path_factory):
    os.environ["CHROMA_PATH"] = str(tmp_path_factory.mktemp("chroma"))
    try:
        kb = KnowledgeBase()
        kb.populate()
        yield kb
    finally:
        os.environ.pop("CHROMA_PATH", None)


def test_category_filtered_search(kb):
    res = kb.search("TLS handshake failed: certificate has expired", n_results=3, category="ssl_expiry")
    metas = res["metadatas"][0]
    assert metas and all(m["category"] == "ssl_expiry" for m in metas)


def test_unfiltered_search_falls_back(kb):
    res = kb.search("DNS SERVFAIL resolution errors", n_results=3, category="not_a_category")
    assert len(res["ids"][0]) == 3


def test_parser_skips_security_incidents():
    md = (
        "## Config Errors\n\n"
        "[ExampleCo](https://example.com/a). A bad config push caused every edge server to crash for 40 minutes.\n\n"
        "[OtherCo](https://example.com/b). Attackers used stolen credentials to exfiltrate customer data from backups.\n\n"
        "## Other lists of postmortems\n\n"
        "[List](https://example.com/c). Another list of postmortems that should not be parsed at all.\n"
    )
    entries = build_kb.parse_entries(md)
    assert [e["company"] for e in entries] == ["ExampleCo"]
    rec = build_kb.rule_extract(entries[0])
    assert rec["category"] in TYPES
    assert rec["duration"] == "40 minutes"
