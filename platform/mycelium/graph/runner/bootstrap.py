#!/usr/bin/env python3
# ============================================================================
# Runner: bootstrap
# ============================================================================
# Loads graph/protocols/*.cypher files into Neo4j as Protocol nodes.
# Each file must start with `// @node_id: <id>` header. Optional `// @label: "..."`.
# MERGE Protocol {node_id}, set cypher + source_file + loaded_at.
# Idempotent: rerun after edits — nodes get updated, unchanged files reported.
# ============================================================================
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path


NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")


def run_cypher(statement, params=None, timeout=30):
    body = {"statements": [{"statement": statement, "parameters": params or {}}]}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    import base64
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("errors"):
        raise RuntimeError(f"Neo4j errors: {result['errors']}")
    return result.get("results", [])


HEADER_NODE_ID = re.compile(r"^//\s*@node_id:\s*(\S+)", re.MULTILINE)
HEADER_LABEL = re.compile(r'^//\s*@label:\s*"?([^"\n]+?)"?\s*$', re.MULTILINE)
HEADER_LINE = re.compile(r"^//\s*@(node_id|label):.*$", re.MULTILINE)


def parse_headers(content):
    nid_match = HEADER_NODE_ID.search(content)
    lbl_match = HEADER_LABEL.search(content)
    return (
        nid_match.group(1).strip() if nid_match else None,
        lbl_match.group(1).strip() if lbl_match else None,
    )


def strip_headers_and_clean(content):
    # Remove our magic header lines — apoc.cypher.runMany can't parse them
    # as standalone statements. Also trim trailing whitespace + empty statements
    # that result from trailing `;` (runMany would try to parse the empty tail).
    cleaned = HEADER_LINE.sub("", content)
    # Drop trailing semicolons + whitespace so runMany doesn't see an empty stmt
    cleaned = cleaned.rstrip()
    while cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    return cleaned + "\n"


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    proto_dir = repo_root / "graph" / "protocols"

    if not proto_dir.exists():
        print(f"[bootstrap] ERROR: {proto_dir} not found", file=sys.stderr)
        sys.exit(1)

    files = sorted(proto_dir.glob("*.cypher"))
    print(f"[bootstrap] scanning {len(files)} .cypher files in {proto_dir}")

    loaded = 0
    updated = 0
    unchanged = 0
    skipped = 0

    for f in files:
        content = f.read_text()
        node_id, label = parse_headers(content)
        rel_path = str(f.relative_to(repo_root))

        if not node_id:
            print(f"  [skip] {f.name} — missing // @node_id: header")
            skipped += 1
            continue

        params = {
            "node_id": node_id,
            "cypher": strip_headers_and_clean(content),
            "source_file": rel_path,
            "label": label or node_id,
        }

        cypher = """
            MERGE (p:Protocol {node_id: $node_id})
            WITH p, p.cypher AS prev_cypher, coalesce(p.loaded_at, '') AS prev_loaded
            SET p.cypher = $cypher,
                p.source_file = $source_file,
                p.label = coalesce(p.label, $label),
                p.loaded_at = toString(datetime())
            RETURN
              CASE
                WHEN prev_cypher IS NULL THEN 'loaded'
                WHEN prev_cypher <> $cypher THEN 'updated'
                ELSE 'unchanged'
              END AS state
        """
        try:
            results = run_cypher(cypher, params)
            state = results[0]["data"][0]["row"][0]
        except Exception as e:
            print(f"  [err] {f.name} — {e}", file=sys.stderr)
            skipped += 1
            continue

        if state == "loaded":
            loaded += 1
            print(f"  [new] {node_id} ← {f.name}")
        elif state == "updated":
            updated += 1
            print(f"  [upd] {node_id} ← {f.name}")
        else:
            unchanged += 1

    print()
    print(f"[bootstrap] loaded={loaded} updated={updated} unchanged={unchanged} skipped={skipped}")
    sys.exit(0 if skipped == 0 else 1)


if __name__ == "__main__":
    main()
