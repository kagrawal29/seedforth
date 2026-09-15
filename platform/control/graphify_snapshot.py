"""Bounded Graphify source-snapshot adapter.

Graphify output is untrusted extracted content. This adapter records only
provenance and bounded, normalized fact keys in Mycelium; it never lets the
extractor write Cypher or alter authoritative implementation relationships.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from control.graph import Graph

MAX_DOCUMENTS = 100
MAX_CONCEPTS_PER_DOCUMENT = 200
MAX_RELATIONSHIPS_PER_DOCUMENT = 400
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|password|secret|private[_-]?key)")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256(value: Any) -> str:
    material = value if isinstance(value, bytes) else stable_json(value).encode()
    return hashlib.sha256(material).hexdigest()


def _text(value: Any, limit: int) -> str:
    return value[:limit] if isinstance(value, str) else ""


def _safe_source(value: Any) -> str:
    source = _text(value, 500)
    if not source or SECRET_RE.search(source):
        return ""
    return source


def build_snapshot(
    input_path: Path,
    repository: str,
    revision: str,
    extractor_revision: str,
    selected_paths: list[str] | None = None,
    captured_at: str | None = None,
) -> dict[str, Any]:
    raw = input_path.read_bytes()
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("documents"), list):
        raise ValueError("invalid_graphify_output")
    documents = data["documents"]
    if len(documents) > MAX_DOCUMENTS:
        raise ValueError("graphify_document_limit")

    facts: list[dict[str, str]] = []
    failures: list[str] = []
    inspected: list[str] = []
    for document in documents:
        if not isinstance(document, dict):
            failures.append("document_not_object")
            continue
        source = _safe_source(document.get("source"))
        if not source:
            failures.append("document_source_missing_or_sensitive")
            continue
        inspected.append(source)
        concepts = document.get("concepts", [])
        relationships = document.get("relationships", [])
        if not isinstance(concepts, list) or not isinstance(relationships, list):
            failures.append(f"invalid_document_shape:{source}")
            continue
        if len(concepts) > MAX_CONCEPTS_PER_DOCUMENT:
            failures.append(f"concept_limit:{source}")
            concepts = concepts[:MAX_CONCEPTS_PER_DOCUMENT]
        if len(relationships) > MAX_RELATIONSHIPS_PER_DOCUMENT:
            failures.append(f"relationship_limit:{source}")
            relationships = relationships[:MAX_RELATIONSHIPS_PER_DOCUMENT]
        for concept in concepts:
            if not isinstance(concept, dict):
                failures.append(f"concept_not_object:{source}")
                continue
            concept_id = _text(concept.get("id"), 200)
            if not concept_id or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", concept_id):
                failures.append(f"invalid_concept_id:{source}")
                continue
            # Keep identifiers/types only. Summaries are untrusted model text
            # and remain in the external artifact addressed by content_hash.
            facts.append({
                "fact_key": f"{repository}:{revision}:{source}:concept:{concept_id}",
                "kind": "extracted_concept",
                "source_path": source,
                "subject_key": concept_id,
                "relation": "",
                "object_key": "",
            })
        for relationship in relationships:
            if not isinstance(relationship, dict):
                failures.append(f"relationship_not_object:{source}")
                continue
            left = _text(relationship.get("source"), 200)
            right = _text(relationship.get("target"), 200)
            relation = _text(relationship.get("relation"), 80).upper()
            if not (re.fullmatch(r"[a-z0-9][a-z0-9-]*", left or "") and
                    re.fullmatch(r"[a-z0-9][a-z0-9-]*", right or "") and
                    re.fullmatch(r"[A-Z][A-Z0-9_]*", relation or "")):
                failures.append(f"invalid_relationship:{source}")
                continue
            facts.append({
                "fact_key": f"{repository}:{revision}:{source}:relationship:{left}:{relation}:{right}",
                "kind": "inferred_relationship",
                "source_path": source,
                "subject_key": left,
                "relation": relation,
                "object_key": right,
            })

    selected = sorted(set(p for p in (selected_paths or inspected) if isinstance(p, str)))
    metadata = {
        "repository": _text(repository, 300),
        "revision": _text(revision, 200),
        "extractor_revision": _text(extractor_revision, 200),
        "selected_paths": selected[:MAX_DOCUMENTS],
        "coverage": "selected_graphify_documents",
        "captured_at": captured_at or datetime.now(timezone.utc).isoformat(),
        "content_hash": sha256(raw),
        "fact_count": len(facts),
        "failure_count": len(failures),
    }
    if not metadata["repository"] or not metadata["revision"] or not metadata["extractor_revision"]:
        raise ValueError("incomplete_graphify_provenance")
    metadata["snapshot_id"] = sha256(metadata)
    return {"metadata": metadata, "facts": facts, "failures": failures}


def build_collection_failure_snapshot(
    source_path: str,
    repository: str,
    revision: str,
    extractor_revision: str,
    reason: str,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Create an observation when a source artifact cannot be collected."""
    captured = captured_at or datetime.now(timezone.utc).isoformat()
    metadata = {
        "repository": _text(repository, 300),
        "revision": _text(revision, 200),
        "extractor_revision": _text(extractor_revision, 200),
        "selected_paths": [],
        "coverage": "collection_failure",
        "captured_at": captured,
        "content_hash": sha256({"source_path": source_path, "reason": reason}),
        "fact_count": 0,
        "failure_count": 1,
    }
    if not metadata["repository"] or not metadata["revision"] or not metadata["extractor_revision"]:
        raise ValueError("incomplete_graphify_provenance")
    metadata["snapshot_id"] = sha256(metadata)
    return {"metadata": metadata, "facts": [], "failures": [reason]}


def record(graph: Graph, principal: str, scope: str, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = snapshot["metadata"]
    return graph.operation(
        "record-graphify-snapshot", principal, scope,
        snapshot_id=metadata["snapshot_id"], content_hash=metadata["content_hash"],
        repository=metadata["repository"], revision=metadata["revision"],
        extractor_revision=metadata["extractor_revision"],
        captured_at=metadata["captured_at"], coverage=metadata["coverage"],
        selected_paths=metadata["selected_paths"], fact_count=metadata["fact_count"],
        failure_count=metadata["failure_count"], facts=snapshot["facts"],
        failures=snapshot["failures"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(os.environ.get("GRAPHIFY_OUTPUT", "signals/artifacts/graphify-output.json")))
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--extractor-revision", required=True)
    parser.add_argument("--scope", required=True)
    args = parser.parse_args()
    snapshot = build_snapshot(args.input, args.repository, args.revision, args.extractor_revision)
    print(json.dumps({"snapshot_id": snapshot["metadata"]["snapshot_id"], "facts": len(snapshot["facts"]), "failures": len(snapshot["failures"])}))
    record(Graph(), os.environ.get("SEEDFORTH_GRAPHIFY_PRINCIPAL", "principal-graphify-sensor"), args.scope, snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
