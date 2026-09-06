#!/usr/bin/env python3
# ============================================================================
# Runner: materialize_calls
# ============================================================================
# Extracts protocol-to-protocol calls from CypherAtom bodies where atoms
# invoke other protocols via apoc.cypher.run/runMany/runTimeboxed, then
# materializes them as `:CALLS` edges in the graph.
#
# Part of wi-v2-03-atom-decomposition. Reads CypherAtom nodes whose .cypher
# contains apoc.cypher.run* calls, parses out referenced Protocol.node_id
# values, and either reports (dry-run, default) or MERGE (--apply) edges.
#
# Idempotent via MERGE: safe to run multiple times.
#
# Parsing strategy:
#   - Regex: apoc.cypher.run[a-zA-Z]*\s*\(\s*([^,]+) (captures first arg)
#   - Extract node_id patterns: "protocol-\w+" in strings or MATCH bindings
#   - Handle both quoted strings and variable references (MATCH (p:Protocol...))
#   - Fall back to any node_id literal in the same atom if variable is unresolved
# ============================================================================
import json
import os
import re
import sys
import urllib.request
import urllib.error
import argparse


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


def extract_protocol_ids(cypher_text):
    """
    Extract protocol node IDs from cypher text using a simple, exhaustive pattern.

    Returns: list of protocol node_id strings found.

    Strategy:
      - Find every substring matching the pattern `protocol-[a-zA-Z0-9_-]+`
      - These are the only "protocol" references the atom knows about
      - Skip Invariant references (inv-*) which are not Protocol calls
    """
    # Find all protocol-* references in the atom
    all_matches = re.findall(r"protocol-[a-zA-Z0-9_-]+", cypher_text)
    return sorted(list(set(all_matches)))


def get_atoms_with_apoc_calls():
    """Fetch all CypherAtom nodes whose cypher property contains apoc.cypher.run*."""
    cypher = """
        MATCH (a:CypherAtom)
        WHERE a.cypher CONTAINS 'apoc.cypher.run'
        RETURN a.atom_id AS atom_id, a.protocol_id AS protocol_id, a.cypher AS cypher
        ORDER BY a.atom_id
    """
    results = run_cypher(cypher)
    if not results or not results[0].get("data"):
        return []

    atoms = []
    for row in results[0]["data"]:
        atoms.append({
            "atom_id": row["row"][0],
            "protocol_id": row["row"][1],
            "cypher": row["row"][2],
        })
    return atoms


def get_existing_protocol_ids():
    """Fetch all Protocol node_ids that exist in the graph."""
    cypher = """
        MATCH (p:Protocol)
        RETURN p.node_id AS node_id
    """
    results = run_cypher(cypher)
    if not results or not results[0].get("data"):
        return set()

    protocol_ids = set()
    for row in results[0]["data"]:
        node_id = row["row"][0]
        if node_id:
            protocol_ids.add(node_id)
    return protocol_ids


def parse_atom_calls(atom_id, protocol_id, cypher_text):
    """
    Parse a CypherAtom to extract caller→callee pairs.

    Returns: list of (caller_protocol_id, callee_protocol_id) tuples.
    """
    callees = extract_protocol_ids(cypher_text)
    pairs = []

    for callee_id in callees:
        # Skip self-loops
        if callee_id != protocol_id:
            pairs.append((protocol_id, callee_id))

    return pairs


def materialize_edges(pairs, dry_run=True):
    """
    Materialize `:CALLS` edges for each (caller, callee) pair.

    Returns: count of edges written (or would be written in dry-run mode).
    """
    count = 0
    failed = []

    for caller_id, callee_id in pairs:
        if dry_run:
            count += 1
            continue

        try:
            cypher = """
                MATCH (caller:Protocol {node_id: $caller}), (callee:Protocol {node_id: $callee})
                MERGE (caller)-[:CALLS]->(callee)
                RETURN caller.node_id AS caller_id, callee.node_id AS callee_id
            """
            results = run_cypher(cypher, {
                "caller": caller_id,
                "callee": callee_id,
            })
            if results and results[0].get("data"):
                count += 1
        except Exception as e:
            failed.append((caller_id, callee_id, str(e)[:100]))

    return count, failed


def main():
    parser = argparse.ArgumentParser(
        description="Extract and materialize protocol-to-protocol CALLS edges from CypherAtom bodies."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (MERGE edges). Default is dry-run (report only).",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    mode = "dry-run" if dry_run else "apply"
    print(f"[materialize_calls] starting {mode}...", file=sys.stderr)

    atoms = get_atoms_with_apoc_calls()
    if not atoms:
        print("[materialize_calls] no CypherAtoms with apoc.cypher.run* found", file=sys.stderr)
        return 0

    print(f"[materialize_calls] scanning {len(atoms)} atoms for calls", file=sys.stderr)

    # Fetch all existing Protocol IDs for validation
    existing_protocols = get_existing_protocol_ids()
    print(f"[materialize_calls] loaded {len(existing_protocols)} existing Protocol IDs", file=sys.stderr)

    total_pairs = set()
    atoms_scanned = 0
    atoms_with_calls = 0
    failed_atoms = []
    skipped_callees = 0

    for atom in atoms:
        atom_id = atom["atom_id"]
        protocol_id = atom["protocol_id"]
        cypher_text = atom["cypher"]

        try:
            # Extract all protocol-* references in the atom
            callees = extract_protocol_ids(cypher_text)
            pairs = []

            for callee_id in callees:
                # Skip self-loops
                if callee_id == protocol_id:
                    continue
                # Only emit if the callee actually exists as a Protocol node
                if callee_id not in existing_protocols:
                    skipped_callees += 1
                    continue
                pairs.append((protocol_id, callee_id))

            if pairs:
                atoms_with_calls += 1
                for caller, callee in pairs:
                    total_pairs.add((caller, callee))
                    # Print each call in dry-run for visibility
                    if dry_run:
                        print(f"  {caller} → {callee}", file=sys.stderr)
        except Exception as e:
            print(f"  [err] {atom_id}: {str(e)[:100]}", file=sys.stderr)
            failed_atoms.append((atom_id, str(e)[:100]))
            continue

        atoms_scanned += 1

    print(file=sys.stderr)
    print(f"[materialize_calls] scanned {atoms_scanned} atoms, {atoms_with_calls} have calls", file=sys.stderr)
    print(f"[materialize_calls] found {len(total_pairs)} unique caller→callee pairs", file=sys.stderr)
    if skipped_callees > 0:
        print(f"[materialize_calls] skipped {skipped_callees} callee refs (Protocol doesn't exist)", file=sys.stderr)

    if not dry_run:
        count, failed = materialize_edges(list(total_pairs), dry_run=False)
        print(f"[materialize_calls] materialized {count} :CALLS edges", file=sys.stderr)
        if failed:
            print(f"[materialize_calls] {len(failed)} edges failed to materialize", file=sys.stderr)
            for caller, callee, err in failed[:5]:
                print(f"  {caller} → {callee}: {err}", file=sys.stderr)

    if failed_atoms:
        print(f"[materialize_calls] {len(failed_atoms)} atoms failed to parse", file=sys.stderr)
        for atom_id, err in failed_atoms[:5]:
            print(f"  {atom_id}: {err}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
