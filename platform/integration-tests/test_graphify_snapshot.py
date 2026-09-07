import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control import graphify_snapshot


def output(tmp_path, *, sensitive=False):
    source = "docs/plan.md" if not sensitive else "docs/api-key.md"
    data = {"documents": [{
        "source": source,
        "concepts": [{"id": "truthful-state", "label": "Truthful state", "summary": "untrusted"}],
        "relationships": [{"source": "truthful-state", "target": "bounded-work", "relation": "CONSTRAINS"}],
    }]}
    path = tmp_path / "graphify-output.json"
    path.write_text(json.dumps(data))
    return path


def test_snapshot_is_provenanced_and_normalizes_untrusted_text(tmp_path):
    snapshot = graphify_snapshot.build_snapshot(output(tmp_path), "org/repo", "abc123", "graphify-fixture-v1")
    metadata = snapshot["metadata"]
    assert len(metadata["content_hash"]) == 64
    assert metadata["repository"] == "org/repo"
    assert metadata["fact_count"] == 2
    assert {fact["kind"] for fact in snapshot["facts"]} == {"extracted_concept", "inferred_relationship"}
    assert all("summary" not in fact for fact in snapshot["facts"])
    assert len(metadata["snapshot_id"]) == 64


def test_sensitive_source_is_not_admitted(tmp_path):
    snapshot = graphify_snapshot.build_snapshot(output(tmp_path, sensitive=True), "org/repo", "abc123", "fixture-v1")
    assert snapshot["metadata"]["fact_count"] == 0
    assert "document_source_missing_or_sensitive" in snapshot["failures"]


def test_provenance_is_required_and_limits_are_bounded(tmp_path):
    with pytest.raises(ValueError, match="incomplete_graphify_provenance"):
        graphify_snapshot.build_snapshot(output(tmp_path), "", "abc123", "fixture-v1")
    data = {"documents": [{"source": "docs/plan.md", "concepts": [], "relationships": []}] * 101}
    path = tmp_path / "too-many.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="graphify_document_limit"):
        graphify_snapshot.build_snapshot(path, "org/repo", "abc123", "fixture-v1")


def test_graph_record_contains_only_snapshot_contract():
    class Graph:
        def operation(self, name, actor, scope, **params):
            assert name == "record-graphify-snapshot"
            assert params["facts"][0]["kind"] == "extracted_concept"
            assert "summary" not in params["facts"][0]
            return [{"id": params["snapshot_id"]}]

    snapshot = {
        "metadata": {"snapshot_id": "a" * 64, "content_hash": "b" * 64,
                     "repository": "org/repo", "revision": "r", "extractor_revision": "e",
                     "captured_at": "2026-09-07T10:00:00+00:00", "coverage": "selected",
                     "selected_paths": [], "fact_count": 1, "failure_count": 0},
        "facts": [{"fact_key": "f", "kind": "extracted_concept", "source_path": "x",
                   "subject_key": "x", "relation": "", "object_key": ""}],
        "failures": [],
    }
    assert graphify_snapshot.record(Graph(), "principal", "flowing-indian", snapshot)


def test_empty_extraction_is_still_a_recorded_observation(tmp_path):
    class Graph:
        def operation(self, name, actor, scope, **params):
            assert params["fact_count"] == 0
            assert params["failure_count"] == 0
            return [{"id": params["snapshot_id"]}]

    path = output(tmp_path)
    path.write_text(json.dumps({"documents": []}))
    snapshot = graphify_snapshot.build_snapshot(path, "org/repo", "empty", "fixture-v1")
    assert snapshot["metadata"]["fact_count"] == 0
    assert graphify_snapshot.record(Graph(), "principal", "seedforth-platform", snapshot)
