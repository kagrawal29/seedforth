"""Dependency-light tests for the Delta/Mycelium platform boundary.

These tests intentionally do not write to the live graph. Disposable Neo4j
replay tests belong in the optional integration job; this suite validates the
contracts that job consumes and the deterministic mismatch classifications.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

DELTA_ROOT = Path(__file__).parents[1] / "delta"
sys.path.insert(0, str(DELTA_ROOT))
sys.path.insert(0, str(Path(__file__).parents[2] / "operations"))

from delta.control_envelope import dedupe_key, make_envelope  # noqa: E402
from reconcile import classify_runtime  # noqa: E402

SCHEMA_PATH = Path(__file__).parents[1] / "contracts" / "control-envelope.schema.json"
MODEL_PATH = (
    Path(__file__).parents[1]
    / "mycelium"
    / "graph"
    / "knowledge"
    / "seedforth-control-model-v1.cypher"
)


def _valid_envelope() -> dict:
    return make_envelope(
        kind="progress",
        project="platform",
        source="delta",
        correlation_id="session-1",
        payload={"status": "in_progress"},
        message_id="msg-integration-1",
        occurred_at="2026-09-06T12:00:00+00:00",
    )


def test_python_envelope_matches_json_schema():
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(_valid_envelope()))
    assert errors == []


@pytest.mark.parametrize(
    "change",
    [
        {"project": ""},
        {"kind": "command"},
        {"source": "unknown"},
    ],
)
def test_schema_rejects_unscoped_or_unknown_messages(change):
    envelope = _valid_envelope()
    envelope.update(change)
    schema = json.loads(SCHEMA_PATH.read_text())
    assert list(Draft202012Validator(schema).iter_errors(envelope))


def test_replay_is_idempotent_on_message_id():
    envelope = _valid_envelope()
    durable_events: dict[str, dict] = {}
    for replay in (envelope, dict(envelope)):
        durable_events.setdefault(dedupe_key(replay), replay)
    assert list(durable_events) == ["msg-integration-1"]
    assert durable_events["msg-integration-1"]["payload"]["status"] == "in_progress"


def test_control_model_is_bootstrap_idempotent_by_construction():
    cypher = MODEL_PATH.read_text()
    required_types = {
        "Workstream",
        "WorkItem",
        "ExecutionSession",
        "AgentProcess",
        "Signal",
        "DecisionRequest",
        "ActivityLog",
        "CodeChange",
    }
    assert all(f"(n:{label})" in cypher for label in required_types)
    assert "IF NOT EXISTS" in cypher
    assert "MERGE (s:SchemaContract" in cypher
    assert "MERGE (t:ControlType" in cypher


def test_deliberate_sha_mismatch_is_drifted():
    assert classify_runtime("release-a", "release-b", "running", "active") == "drifted"


def test_deliberate_process_graph_mismatch_is_conflicting():
    assert classify_runtime("release-a", "release-a", "running", "stopped") == "conflicting"


def test_matching_runtime_is_healthy():
    assert classify_runtime("release-a", "release-a", "running", "active") == "healthy"
