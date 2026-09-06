#!/usr/bin/env python3
# ============================================================================
# Runner: ingest_seed_files
# ============================================================================
# Ingest .cypher files from graph/protocols/ that lack @node_id: header
# into the graph as :SeedScript nodes.
#
# These are one-shot seed/migration scripts not tracked by the bootstrap
# system. We store them as SeedScript nodes for visibility and future replay.
#
# Idempotent MERGE on node_id; update cypher/content_hash/ingested_at/line_count
# on match.
#
# Output to stderr: per-file status (ingested/updated/unchanged) + summary.
# ============================================================================
import json
import os
import re
import sys
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")


def run_cypher(statement, params=None, timeout=60):
    """Run a cypher statement and return results."""
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


def has_node_id_header(content):
    """Check if file contains // @node_id: header."""
    return bool(re.search(r'^\s*//\s*@node_id:', content, re.MULTILINE))


def compute_hash(content):
    """Return sha256 hex of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def derive_node_id(filename):
    """Derive node_id from filename (e.g., foo-bar.cypher -> seed-foo-bar)."""
    name = filename.replace(".cypher", "")
    return f"seed-{name}"


def get_cypher_files(protocol_dir):
    """Return list of .cypher files in protocol_dir."""
    path = Path(protocol_dir)
    if not path.exists():
        return []
    return sorted([f for f in path.glob("*.cypher")])


def ingest_seed_script(filename, filepath, cypher_content):
    """
    MERGE a SeedScript node. Returns ('ingested', None), ('updated', None), or ('unchanged', None).
    """
    node_id = derive_node_id(filename)
    content_hash = compute_hash(cypher_content)
    line_count = cypher_content.count('\n')
    ingested_at = datetime.utcnow().isoformat() + 'Z'

    try:
        # Check if it exists and if content changed
        check_cypher = """
            MATCH (s:SeedScript {node_id: $node_id})
            RETURN s.content_hash AS content_hash
        """
        results = run_cypher(check_cypher, {"node_id": node_id})

        if results and results[0].get("data"):
            existing_hash = results[0]["data"][0]["row"][0] if results[0]["data"][0]["row"] else None
            if existing_hash == content_hash:
                return "unchanged", None
            action = "updated"
        else:
            action = "ingested"

        # MERGE the node
        merge_cypher = """
            MERGE (s:SeedScript {node_id: $node_id})
            ON CREATE SET
                s.node_id = $node_id,
                s.filename = $filename,
                s.filepath = $filepath,
                s.cypher = $cypher,
                s.content_hash = $content_hash,
                s.ingested_at = $ingested_at,
                s.line_count = $line_count,
                s.kind = 'seed',
                s.created_at = toString(datetime())
            ON MATCH SET
                s.cypher = $cypher,
                s.content_hash = $content_hash,
                s.ingested_at = $ingested_at,
                s.line_count = $line_count,
                s.updated_at = toString(datetime())
            RETURN s.node_id AS node_id
        """

        run_cypher(merge_cypher, {
            "node_id": node_id,
            "filename": filename,
            "filepath": filepath,
            "cypher": cypher_content,
            "content_hash": content_hash,
            "ingested_at": ingested_at,
            "line_count": line_count,
        })

        return action, None
    except Exception as e:
        return None, str(e)[:150]


def main():
    protocol_dir = Path(__file__).parent.parent / "protocols"

    print(f"[ingest_seed_files] scanning {protocol_dir}", file=sys.stderr)

    cypher_files = get_cypher_files(protocol_dir)
    if not cypher_files:
        print("[ingest_seed_files] no .cypher files found", file=sys.stderr)
        return 0

    ingested_count = 0
    updated_count = 0
    unchanged_count = 0
    error_count = 0
    scanned_count = 0

    for filepath in cypher_files:
        filename = filepath.name
        scanned_count += 1

        try:
            content = filepath.read_text(encoding='utf-8')

            # Skip files with @node_id: header (belong to bootstrap)
            if has_node_id_header(content):
                print(f"  [skip] {filename}: has @node_id: header", file=sys.stderr)
                continue

            # Ingest as seed script
            relative_path = f"graph/protocols/{filename}"
            action, error = ingest_seed_script(filename, relative_path, content)

            if error:
                print(f"  [err] {filename}: {error}", file=sys.stderr)
                error_count += 1
            elif action == "ingested":
                print(f"  [ingested] {filename}", file=sys.stderr)
                ingested_count += 1
            elif action == "updated":
                print(f"  [updated] {filename}", file=sys.stderr)
                updated_count += 1
            elif action == "unchanged":
                print(f"  [unchanged] {filename}", file=sys.stderr)
                unchanged_count += 1
        except Exception as e:
            print(f"  [err] {filename}: {str(e)[:100]}", file=sys.stderr)
            error_count += 1

    print(file=sys.stderr)
    print(f"[ingest_seed_files] {scanned_count} files scanned, {ingested_count} ingested, {updated_count} updated, {unchanged_count} unchanged", file=sys.stderr)

    if error_count > 0:
        print(f"[ingest_seed_files] {error_count} errors encountered", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
