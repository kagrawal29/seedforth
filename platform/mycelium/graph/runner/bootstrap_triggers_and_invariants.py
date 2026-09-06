#!/usr/bin/env python3
"""
Bootstrap Triggers and Invariants from Cypher Files

Scans graph/triggers/ and graph/invariants/ directories for .cypher files
with // @node_id: headers, loads them into the graph as Trigger and Invariant
nodes, then executes the cypher to create/update the nodes.

This is part of the bootstrap pipeline. Runs after Protocols are loaded.

Usage:
  python3 bootstrap_triggers_and_invariants.py

Exit codes:
  0 — success
  1 — Neo4j connection error
  2 — file read/parse error
"""

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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("errors"):
            raise RuntimeError(f"Neo4j errors: {result['errors']}")
        return result.get("results", [])
    except urllib.error.URLError as e:
        raise RuntimeError(f"Connection error: {e}")


def extract_header_value(cypher_text, header_name):
    """Extract value from // @header_name: value comment line."""
    pattern = rf'//\s*@{header_name}:\s*(.+)'
    match = re.search(pattern, cypher_text, re.MULTILINE)
    return match.group(1).strip() if match else None


def load_cypher_files(directory):
    """
    Scan directory for *.cypher files.
    Return list of (file_path, file_content, node_id, label) tuples.
    """
    items = []
    dir_path = Path(directory)
    if not dir_path.exists():
        return items

    for cypher_file in sorted(dir_path.glob("*.cypher")):
        try:
            with open(cypher_file, "r") as f:
                content = f.read()
            node_id = extract_header_value(content, "node_id")
            label = extract_header_value(content, "label")
            if node_id:
                items.append({
                    "file_path": str(cypher_file),
                    "content": content,
                    "node_id": node_id,
                    "label": label or node_id,
                })
        except Exception as e:
            print(f"  [error] failed to read {cypher_file}: {e}", file=sys.stderr)
            return None  # Signal error to caller
    return items


def load_triggers(trigger_files):
    """Load Trigger nodes (reference, not executable)."""
    count = 0
    for item in trigger_files:
        try:
            cypher = f"""
                MERGE (t:Trigger {{node_id: $node_id}})
                SET t.label = $label,
                    t.cypher = $cypher,
                    t.loaded_at = toString(datetime()),
                    t.file_path = $file_path
                RETURN t.node_id AS node_id
            """
            result = run_cypher(cypher, {
                "node_id": item["node_id"],
                "label": item["label"],
                "cypher": item["content"],
                "file_path": item["file_path"],
            })
            if result:
                count += 1
                print(f"  ✓ {item['node_id']}", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ {item['node_id']}: {e}", file=sys.stderr)
    return count


def load_invariants(invariant_files):
    """Load Invariant nodes by executing their cypher files.

    Splits multi-statement files by semicolon and executes each statement
    separately since the Neo4j HTTP API expects one statement per request.
    Skips comment-only lines to avoid syntax errors.
    """
    count = 0
    for item in invariant_files:
        try:
            # Remove comment lines (but keep comment content that's part of string literals)
            lines = item["content"].split("\n")
            non_comment_lines = []
            for line in lines:
                stripped = line.strip()
                # Skip lines that are purely comments
                if not stripped.startswith("//") and stripped:
                    non_comment_lines.append(line)

            content_without_comments = "\n".join(non_comment_lines)

            # Split by semicolon to get individual statements
            statements = [s.strip() for s in content_without_comments.split(";")]
            statements = [s for s in statements if s]  # Remove empty statements

            # Execute each statement
            for stmt in statements:
                results = run_cypher(stmt)

            # If we got here without exception, count as success
            count += 1
            print(f"  ✓ {item['node_id']}", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ {item['node_id']}: {e}", file=sys.stderr)
    return count



def main():
    print("[bootstrap_triggers_and_invariants] starting", file=sys.stderr)

    # Load triggers
    print("[bootstrap_triggers_and_invariants] loading triggers...", file=sys.stderr)
    trigger_files = load_cypher_files("graph/triggers")
    if trigger_files is None:
        return 1
    trigger_count = load_triggers(trigger_files)
    print(f"[bootstrap_triggers_and_invariants] {trigger_count}/{len(trigger_files)} triggers loaded", file=sys.stderr)

    # Load invariants
    print("[bootstrap_triggers_and_invariants] loading invariants...", file=sys.stderr)
    invariant_files = load_cypher_files("graph/invariants")
    if invariant_files is None:
        return 1
    invariant_count = load_invariants(invariant_files)
    print(f"[bootstrap_triggers_and_invariants] {invariant_count}/{len(invariant_files)} invariants loaded", file=sys.stderr)

    print("[bootstrap_triggers_and_invariants] done", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
