import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control import ingest_delta_events as ingest


class FakeGraph:
    def __init__(self):
        self.calls = []
        self.fail = False

    def operation(self, name, actor, scope, **params):
        if self.fail:
            raise RuntimeError("graph_unavailable")
        self.calls.append((name, actor, scope, params))
        return [{"id": params["event_id"]}]


def source(path):
    return ingest.EventSource(path, "flowing-indian", "source-delta-project-events-flowing-indian", ingest.PROJECT_STREAM_ID)


def record(event_type="session_trace"):
    return {
        "project": "flowing-indian",
        "event_type": event_type,
        "ts": "2026-09-07T10:00:00+00:00",
        "payload": {"msg_id": "m-1", "user": "owner", "text_preview": "hello"},
    }


def test_ingest_is_idempotent_at_cursor_and_quarantines_bad_lines(tmp_path):
    stream = tmp_path / "graph-events.jsonl"
    stream.write_text(json.dumps(record()) + "\nnot-json\n" + json.dumps(record("unknown")) + "\n")
    state = tmp_path / "state.json"
    graph = FakeGraph()

    stats = ingest.collect_and_dispatch(graph, sources=[source(stream)], state_file=state)

    assert stats == {"files": 1, "lines": 3, "events": 1, "dispatched": 1, "skipped": 0, "failed": 2}
    assert len(graph.calls) == 1
    quarantine = stream.with_name("graph-events.jsonl.quarantine.jsonl")
    entries = [json.loads(line) for line in quarantine.read_text().splitlines()]
    assert [entry["reason"] for entry in entries] == ["Expecting value: line 1 column 1 (char 0)", "unsupported_event_type"]

    # A second run sees the durable cursor and cannot duplicate the event.
    assert ingest.collect_and_dispatch(graph, sources=[source(stream)], state_file=state)["events"] == 0
    assert len(graph.calls) == 1


def test_partial_final_record_is_retried_after_writer_finishes(tmp_path):
    stream = tmp_path / "graph-events.jsonl"
    stream.write_text(json.dumps(record()))
    state = tmp_path / "state.json"
    graph = FakeGraph()

    first = ingest.collect_and_dispatch(graph, sources=[source(stream)], state_file=state)
    assert first["lines"] == 0 and not graph.calls
    assert json.loads(state.read_text())["sources"][str(stream)]["cursor"] == 0

    with stream.open("a") as handle:
        handle.write("\n")
    second = ingest.collect_and_dispatch(graph, sources=[source(stream)], state_file=state)
    assert second["events"] == 1 and len(graph.calls) == 1


def test_graph_failure_does_not_advance_cursor(tmp_path):
    stream = tmp_path / "graph-events.jsonl"
    stream.write_text(json.dumps(record()) + "\n")
    state = tmp_path / "state.json"
    graph = FakeGraph()
    graph.fail = True

    with pytest.raises(RuntimeError, match="graph_unavailable"):
        ingest.collect_and_dispatch(graph, sources=[source(stream)], state_file=state)
    assert not state.exists()

    graph.fail = False
    assert ingest.collect_and_dispatch(graph, sources=[source(stream)], state_file=state)["events"] == 1


def test_explicit_event_id_is_stable_across_offset_changes():
    first = record()
    first["event_id"] = "external-1"
    assert ingest._event_id("source", "scope", 1, first, ingest._normalize_ts(first["ts"])) == ingest._event_id(
        "source", "scope", 2, first, ingest._normalize_ts(first["ts"])
    )
