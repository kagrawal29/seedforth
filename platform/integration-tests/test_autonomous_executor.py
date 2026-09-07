import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control import autonomous_executor


class Graph:
    def __init__(self, candidates=None):
        self.candidates = candidates or []
        self.calls = []

    def operation(self, name, actor, scope, **params):
        self.calls.append((name, actor, scope, params))
        return self.candidates


class Worker:
    def __init__(self):
        self.calls = []

    def request(self, name, **params):
        self.calls.append((name, params))
        return {
            "read-attempt": [],
            "read-work": [{"id": "work-1", "status": "ready", "hold": False, "version": 4}],
            "claim-work": [{"fence": 2}],
            "read-execution-spec": [{"capability": "cap", "arguments_json": "{}"}],
            "invoke": [{"status": "succeeded"}],
            "complete-invocation-work": [{"status": "review", "receipt": "receipt-1"}],
        }[name]


def test_idle_selector_has_no_worker_side_effect():
    graph = Graph()
    worker = Worker()
    assert autonomous_executor.run_once(graph, worker, "principal", "flowing-indian") == {
        "status": "idle", "scope": "flowing-indian"
    }
    assert not worker.calls


def test_selected_work_runs_one_bounded_cycle_and_stops_at_review():
    graph = Graph([{"id": "work-1", "version": 4, "title": "fixture"}])
    worker = Worker()
    result = autonomous_executor.run_once(graph, worker, "principal", "flowing-indian")
    assert result["status"] == "review"
    assert result["accepted"] is False
    assert [name for name, _ in worker.calls] == [
        "read-attempt", "read-work", "claim-work", "read-execution-spec", "invoke", "complete-invocation-work"
    ]
    assert graph.calls[0][0] == "select-ready-work"


def test_malformed_selector_result_fails_before_worker_contact():
    graph = Graph([{"id": "work-1", "version": "not-an-int"}])
    worker = Worker()
    with pytest.raises(RuntimeError, match="invalid_selected_work"):
        autonomous_executor.run_once(graph, worker, "principal", "flowing-indian")
    assert not worker.calls
