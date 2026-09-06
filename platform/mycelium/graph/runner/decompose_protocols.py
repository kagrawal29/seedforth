#!/usr/bin/env python3
# ============================================================================
# Runner: decompose_protocols
# ============================================================================
# Splits each Protocol.cypher blob into CypherAtom nodes linked via HAS_ATOM.
#
# Part of wi-v2-03-atom-decomposition. Reads every Protocol with non-empty
# .cypher, parses statements (comment-aware), MERGE each statement as a
# CypherAtom {atom_id, cypher, order, protocol_id}, link via HAS_ATOM edge.
#
# Idempotent: updates order + cypher on existing atoms, removes stale ones.
#
# Comment-aware splitting:
#   - Ignore `;` inside `// line comments` (treat as literal char)
#   - Ignore `;` inside `/* block comments */` (ditto)
#   - Ignore `;` inside single-quoted strings '...'
#   - Only split on `;` that's outside all of the above
#
# This enables protocols to use bare cypher like:
#   // SELECT FROM somewhere; weird thing
#   MATCH (x) RETURN x;  // end of atom 1
#   MATCH (y) RETURN y;  // end of atom 2
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


def split_on_semicolons(cypher_text):
    """
    Split cypher text on `;` but ignore semicolons inside:
      - `// line comments`
      - `/* block comments */`
      - 'single quoted strings'

    Returns a list of statement strings (trimmed, non-empty).
    """
    statements = []
    current = []
    i = 0
    length = len(cypher_text)

    while i < length:
        char = cypher_text[i]

        # Check for line comment
        if char == '/' and i + 1 < length and cypher_text[i + 1] == '/':
            # Consume until end of line, including the comment
            eol = cypher_text.find('\n', i)
            if eol == -1:
                # Comment goes to end of file
                current.append(cypher_text[i:])
                i = length
            else:
                # Include everything up to and including the newline
                current.append(cypher_text[i:eol + 1])
                i = eol + 1
            continue

        # Check for block comment
        if char == '/' and i + 1 < length and cypher_text[i + 1] == '*':
            # Consume until `*/`
            end = cypher_text.find('*/', i + 2)
            if end == -1:
                # Unclosed block comment — consume to end
                current.append(cypher_text[i:])
                i = length
            else:
                # Include everything up to and including the `*/`
                current.append(cypher_text[i:end + 2])
                i = end + 2
            continue

        # Check for single-quoted string
        if char == "'":
            # Consume until closing quote (handle escapes)
            current.append(char)
            i += 1
            while i < length:
                char = cypher_text[i]
                current.append(char)
                if char == "'":
                    i += 1
                    break
                elif char == '\\' and i + 1 < length:
                    # Escaped character
                    i += 1
                    current.append(cypher_text[i])
                i += 1
            continue

        # Check for statement separator
        if char == ';':
            # This semicolon is NOT inside a comment or string
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
            i += 1
            continue

        # Regular character
        current.append(char)
        i += 1

    # Flush remaining
    stmt = ''.join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements


def get_all_protocols_with_cypher():
    """Fetch all Protocol nodes that have non-empty .cypher property."""
    cypher = """
        MATCH (p:Protocol)
        WHERE p.cypher IS NOT NULL AND p.cypher <> ''
        RETURN p.node_id AS node_id, p.cypher AS cypher
        ORDER BY p.node_id
    """
    results = run_cypher(cypher)
    if not results or not results[0].get("data"):
        return []

    protocols = []
    for row in results[0]["data"]:
        protocols.append({
            "node_id": row["row"][0],
            "cypher": row["row"][1],
        })
    return protocols


def decompose_protocol(protocol_id, cypher_text):
    """
    Split cypher_text into statements and MERGE CypherAtom nodes.

    Returns: (atom_count, failed_statements)
    """
    statements = split_on_semicolons(cypher_text)
    if not statements:
        return 0, []

    atom_count = 0
    failed = []

    for order, stmt in enumerate(statements):
        if not stmt.strip():
            continue

        # Create atom_id: protocol-node_id + order
        atom_id = f"{protocol_id}-atom-{order}"

        try:
            # MERGE CypherAtom node, link to Protocol
            cypher = """
                MATCH (p:Protocol {node_id: $protocol_id})
                WITH p
                MERGE (a:CypherAtom {atom_id: $atom_id})
                  ON CREATE SET
                    a.atom_id = $atom_id,
                    a.protocol_id = $protocol_id,
                    a.cypher = $cypher_text,
                    a.order = $order,
                    a.created_at = toString(datetime())
                  ON MATCH SET
                    a.cypher = $cypher_text,
                    a.order = $order,
                    a.updated_at = toString(datetime())
                MERGE (p)-[rel:HAS_ATOM]->(a)
                  ON CREATE SET rel.order = $order
                  ON MATCH SET rel.order = $order
                RETURN a.atom_id AS atom_id
            """
            results = run_cypher(cypher, {
                "protocol_id": protocol_id,
                "atom_id": atom_id,
                "cypher_text": stmt.strip(),
                "order": order,
            })
            if results and results[0].get("data"):
                atom_count += 1
        except Exception as e:
            failed.append((order, str(e)[:100]))

    # Remove stale atoms (order >= atom_count)
    try:
        cypher = """
            MATCH (p:Protocol {node_id: $protocol_id})-[:HAS_ATOM]->(a:CypherAtom)
            WHERE a.order >= $max_order
            DETACH DELETE a
            RETURN count(*) AS deleted
        """
        run_cypher(cypher, {
            "protocol_id": protocol_id,
            "max_order": atom_count,
        })
    except Exception as e:
        print(f"  [warn] failed to clean stale atoms for {protocol_id}: {e}", file=sys.stderr)

    return atom_count, failed


def main():
    print("[decompose_protocols] fetching all Protocols with cypher...", file=sys.stderr)

    protocols = get_all_protocols_with_cypher()
    if not protocols:
        print("[decompose_protocols] no Protocols with cypher found", file=sys.stderr)
        return 0

    print(f"[decompose_protocols] decomposing {len(protocols)} Protocols", file=sys.stderr)

    total_atoms = 0
    total_protocols = 0
    failed_protocols = []

    for proto in protocols:
        node_id = proto["node_id"]
        cypher_text = proto["cypher"]

        try:
            atom_count, failed_stmts = decompose_protocol(node_id, cypher_text)
            total_atoms += atom_count
            total_protocols += 1

            if failed_stmts:
                print(f"  [partial] {node_id}: {atom_count} atoms created, {len(failed_stmts)} failed", file=sys.stderr)
                for order, err in failed_stmts:
                    print(f"    [fail] atom {order}: {err}", file=sys.stderr)
                failed_protocols.append((node_id, len(failed_stmts)))
            else:
                print(f"  [ok] {node_id}: {atom_count} atoms", file=sys.stderr)
        except Exception as e:
            print(f"  [err] {node_id}: {str(e)[:150]}", file=sys.stderr)
            failed_protocols.append((node_id, -1))
            continue

    print(file=sys.stderr)
    print(f"[decompose_protocols] done: {total_protocols} protocols → {total_atoms} atoms", file=sys.stderr)

    if failed_protocols:
        print(f"[decompose_protocols] {len(failed_protocols)} protocols had issues", file=sys.stderr)
        for pname, fail_count in failed_protocols:
            print(f"  {pname}: {fail_count if fail_count > 0 else 'total'} failures", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
