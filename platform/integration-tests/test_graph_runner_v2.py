"""Verify fail-closed execution and evidence boundaries without touching live Neo4j."""
import importlib.util
from pathlib import Path
import pytest


@pytest.fixture
def runner(monkeypatch):
    monkeypatch.setenv("NEO4J_PASSWORD", "fixture-only")
    path = Path(__file__).parents[1] / "delta/tools/graph-runner-v2.py"
    spec = importlib.util.spec_from_file_location("graph_runner_v2_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fail_stops_dependents_and_preserves_error_type(runner, monkeypatch):
    calls, ends, writes = [], [], []
    monkeypatch.setattr(runner, "get_atoms", lambda _: [dict(node_id=n, generation="g") for n in ["a", "b"]])
    monkeypatch.setattr(runner, "start", lambda *a: None)
    monkeypatch.setattr(runner, "write", lambda q, p: writes.append(p))
    monkeypatch.setattr(runner, "finish", lambda *a: ends.append(a))
    def run(atom):
        calls.append(atom["node_id"])
        raise ValueError("private-secret-text")
    monkeypatch.setattr(runner, "run_atom", run)
    assert runner.execute_protocol("p") is False
    assert calls == ["a"]
    assert ends[0][1:] == (0, "failed", "ValueError")
    assert "private-secret-text" not in str(writes)


def test_evidence_required_before_execution(runner, monkeypatch):
    monkeypatch.setattr(runner, "get_atoms", lambda _: [dict(node_id="a", generation="g")])
    def fail(*a):
        raise ConnectionError()
    monkeypatch.setattr(runner, "start", fail)
    monkeypatch.setattr(runner, "run_atom", lambda _: pytest.fail("must not execute"))
    with pytest.raises(ConnectionError):
        runner.execute_protocol("p")


def test_legacy_string_cannot_launch(runner, monkeypatch):
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: pytest.fail("unapproved launch"))
    with pytest.raises(PermissionError):
        runner.run_atom({"node_id": "legacy", "script": "/opt/worker.py --send"})


@pytest.mark.parametrize("successors", [["a"], ["b", "c"]])
def test_cycles_and_branches_rejected(runner, monkeypatch, successors):
    def query(q, p):
        return [["a"]] if "FIRST_ATOM" in q else [["a", "RETURN 1", None, None, None, successors]]
    monkeypatch.setattr(runner, "q_strict", query)
    with pytest.raises(ValueError):
        runner.get_atoms("p")


def test_disabled_protocol_not_executed(runner, monkeypatch):
    seen = []
    monkeypatch.setattr(runner, "q_strict", lambda q, p: seen.append(q) or [])
    assert runner.main(["--protocol", "disabled"]) == 2
    assert "enabled:true" in seen[0]


def test_failed_protocol_has_failed_exit(runner, monkeypatch):
    monkeypatch.setattr(runner, "get_protocols", lambda *a: [["p"]])
    monkeypatch.setattr(runner, "execute_protocol", lambda _: False)
    assert runner.main(["--cadence", "dream"]) == 1


def test_graph_failure_is_not_no_work(runner, monkeypatch):
    def fail(*a):
        raise ConnectionError()
    monkeypatch.setattr(runner, "q_strict", fail)
    assert runner.main(["--cadence", "heartbeat"]) == 1
