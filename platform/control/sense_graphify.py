"""Record bounded Graphify observations for registered source streams.

This collector does not run extraction or infer facts. A Graphify producer must
create the approved JSON artifact; until then the stream gets a durable failure
observation rather than a misleading empty snapshot.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from control.graph import Graph
from control.graphify_snapshot import build_collection_failure_snapshot, build_snapshot, record

ADAPTER_REVISION = "graphify-sensor-v1"
ARTIFACTS = {
    "seedforth-platform": "/opt/seedforth/current/platform/mycelium/signals/artifacts/graphify-output.json",
    "flowing-indian": "/var/lib/seedforth-graphify-proj-flowing-indian/output.json",
    "cajon-sensei": "/var/lib/seedforth-graphify-proj-cajon-sensei/output.json",
}
REPOSITORIES = {
    "seedforth-platform": "kagrawal29/seedforth",
    "flowing-indian": "kartiksahu/flowing-indian-website",
    "cajon-sensei": "seedforth/cajon-sensei",
}


def collect(graph: Graph, revision: str):
    sources = graph.query(
        "MATCH (s:SourceStream {adapter:'graphify-snapshot-v1',enabled:true}) "
        "RETURN s.scope_id AS scope"
    )
    outcomes = []
    for source in sources:
        scope = source["scope"]
        if scope not in ARTIFACTS or scope not in REPOSITORIES:
            raise ValueError("unapproved_graphify_source")
        path = Path(ARTIFACTS[scope])
        captured = datetime.now(timezone.utc).isoformat()
        try:
            if not path.is_file() or path.is_symlink():
                raise FileNotFoundError(str(path))
            envelope = json.loads(path.read_text(encoding="utf-8"))
            repository = envelope.get("repository", REPOSITORIES[scope])
            source_revision = envelope.get("revision", revision)
            extractor_revision = envelope.get("extractor_revision", ADAPTER_REVISION)
            if repository != REPOSITORIES[scope] or not isinstance(source_revision, str):
                raise ValueError("artifact_provenance_mismatch")
            snapshot = build_snapshot(path, repository, source_revision, extractor_revision,
                                      captured_at=captured)
            status = "collected" if not snapshot["failures"] else "partial"
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            snapshot = build_collection_failure_snapshot(
                str(path), REPOSITORIES[scope], revision, ADAPTER_REVISION,
                "artifact_collection_failed:" + type(exc).__name__, captured)
            status = "collection_failed"
        rows = record(graph, "principal-graphify-sensor", scope, snapshot)
        if len(rows) != 1:
            raise RuntimeError("observation_not_persisted")
        outcomes.append({"scope": scope, "status": status,
                         "facts": snapshot["metadata"]["fact_count"],
                         "failures": snapshot["metadata"]["failure_count"]})
    if not sources:
        raise RuntimeError("no_registered_sources")
    return outcomes


if __name__ == "__main__":
    print(json.dumps(collect(Graph(), os.environ["SEEDFORTH_RELEASE_SHA"])))
