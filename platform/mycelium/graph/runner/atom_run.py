#!/usr/bin/env python3
# ============================================================================
# Runner: atom_run
# ============================================================================
# Executes a Protocol by walking its CypherAtom chain in order.
#
# Part of wi-v2-03-atom-decomposition. Given a protocol_id, walks the
# HAS_ATOM chain ordered by atom.order, executes each atom via
# apoc.cypher.runMany, captures duration_ms into a QueryTrace per atom,
# and aggregates into a per-protocol QueryTrace for backward compatibility.
#
# Each atom's execution is timed:
#   - start_ms: timestamp() before apoc.cypher.runMany
#   - end_ms: timestamp() after
#   - duration_ms: difference
#   - Persisted to QueryTrace node with timing metadata
#
# Returns: exit code 0 on success, 1 on failure. Outputs JSON to stdout
# with atom_count, total_duration_ms, atoms_executed, any failures.
#
# Usage:
#   python3 atom_run.py <protocol_id>
#
# Example:
#   python3 atom_run.py protocol-immune-cycle
# ============================================================================
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_BOLT = os.environ.get("NEO4J_BOLT", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")

# Use Bolt when NEO4J_BOLT is remote — dev/prod targets go through pulse's
# bolt-proxy on 7698/7699, which does not expose HTTP. The CLI sets NEO4J_BOLT
# via load_target_config; atom_run picks up the transport transparently.
_USE_BOLT = os.environ.get("MYCELIUM_FORCE_BOLT", "").lower() in ("1", "true", "yes")
if NEO4J_BOLT and not (
    NEO4J_BOLT.startswith("bolt://localhost")
    or NEO4J_BOLT.startswith("bolt://127.0.0.1:7687")
):
    _USE_BOLT = True

# Read-only targets (dev / prod via bolt-proxy) reject any write. The trace
# emission that atom_run normally does after each atom (CREATE :QueryTrace)
# would be rejected and poison the bolt session for subsequent reads. Skip
# traces entirely on read-only targets.
_READ_ONLY_TARGET = os.environ.get("NEO4J_TARGET_MODE", "rw").lower() == "ro"


def run_cypher(statement, params=None, timeout=60):
    """Run a cypher statement and return results in the legacy HTTP-tx shape."""
    if _USE_BOLT:
        return _run_cypher_bolt(statement, params, timeout)
    return _run_cypher_http(statement, params, timeout)


def _run_cypher_bolt(statement, params=None, timeout=60):
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_BOLT, auth=(NEO4J_USER, NEO4J_PASS))
    try:
        with driver.session() as s:
            res = s.run(statement, params or {})
            cols = list(res.keys())
            rows = [{"row": [r[k] for k in cols], "meta": []} for r in res]
        return [{"columns": cols, "data": rows}]
    finally:
        driver.close()


def _run_cypher_http(statement, params=None, timeout=60):
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


def get_atom_chain(protocol_id):
    """Fetch the atom chain for a protocol, ordered by atom.order."""
    cypher = """
        MATCH (p:Protocol {node_id: $protocol_id})-[:HAS_ATOM]->(a:CypherAtom)
        WHERE a.cypher IS NOT NULL
        RETURN a.atom_id AS atom_id, a.cypher AS cypher, a.order AS order
        ORDER BY a.order ASC
    """
    results = run_cypher(cypher, {"protocol_id": protocol_id})
    if not results or not results[0].get("data"):
        return []

    atoms = []
    for row in results[0]["data"]:
        atoms.append({
            "atom_id": row["row"][0],
            "cypher": row["row"][1],
            "order": row["row"][2],
        })
    return atoms


def execute_atom(protocol_id, atom_id, atom_cypher):
    """
    Execute a single atom directly. Captures timing around execution.

    Returns: (duration_ms, error_msg or None, result_rows list)
    """
    import time

    try:
        # Execute the atom cypher directly, timing it from Python
        start_ms = int(time.time() * 1000)

        results = run_cypher(atom_cypher, {})

        end_ms = int(time.time() * 1000)
        duration_ms = end_ms - start_ms

        # Extract result rows from first result set
        result_rows = []
        if results and len(results) > 0 and results[0].get("data"):
            for row_data in results[0]["data"]:
                # row_data is {"row": [val1, val2, ...], "meta": [...]}
                if "row" in row_data:
                    result_rows.append(row_data["row"])

        # Create QueryTrace for this atom execution. Skip on read-only targets:
        # the CREATE would be rejected by bolt-proxy and poison the session.
        if not _READ_ONLY_TARGET:
            trace_cypher = """
                CREATE (qt:QueryTrace {
                    node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
                    protocol_id: $protocol_id,
                    atom_id: $atom_id,
                    duration_ms: $duration_ms,
                    fired_at: toString(datetime()),
                    invoked_epoch_ms: timestamp(),
                    cypher_summary: 'Atom execution: ' + substring($atom_id, 0, 40),
                    file_type: 'query-trace',
                    phase: 'atom-execution'
                })
                MATCH (p:Protocol {node_id: $protocol_id})
                MERGE (qt)-[:FIRED_BY]->(p)
                RETURN qt.node_id
            """

            run_cypher(trace_cypher, {
                "protocol_id": protocol_id,
                "atom_id": atom_id,
                "duration_ms": duration_ms,
            })

        return duration_ms, None, result_rows
    except Exception as e:
        return 0, str(e)[:200], []


def get_protocol_cypher(protocol_id):
    """Fetch the .cypher property from a Protocol node."""
    cypher = """
        MATCH (p:Protocol {node_id: $protocol_id})
        RETURN p.cypher AS cypher
    """
    results = run_cypher(cypher, {"protocol_id": protocol_id})
    if not results or not results[0].get("data"):
        return None

    rows = results[0].get("data", [])
    if rows and len(rows[0]["row"]) > 0:
        return rows[0]["row"][0]
    return None


def execute_protocol(protocol_id):
    """
    Execute all atoms in a protocol in order.
    If no atoms exist, execute the protocol's .cypher directly (for single-statement protocols).

    Returns: (total_duration_ms, atom_count, failures, all_result_rows)
    """
    atoms = get_atom_chain(protocol_id)

    # Fallback: if no atoms, try to run the protocol's .cypher directly
    if not atoms:
        protocol_cypher = get_protocol_cypher(protocol_id)
        if protocol_cypher:
            print(f"[atom_run] {protocol_id}: no atoms, executing protocol.cypher directly", file=sys.stderr)
            duration_ms, error, result_rows = execute_atom(protocol_id, f"{protocol_id}-direct", protocol_cypher)
            if error:
                return 0, 0, [{"order": 0, "atom_id": f"{protocol_id}-direct", "error": error}], []
            else:
                return duration_ms, 1, [], result_rows
        return 0, 0, [], []

    total_duration = 0
    failures = []
    all_result_rows = []

    for atom in atoms:
        atom_id = atom["atom_id"]
        atom_cypher = atom["cypher"]
        order = atom["order"]

        duration_ms, error, result_rows = execute_atom(protocol_id, atom_id, atom_cypher)
        total_duration += duration_ms
        all_result_rows.extend(result_rows)

        if error:
            failures.append({
                "order": order,
                "atom_id": atom_id,
                "error": error,
            })
            print(f"  [atom {order}] {atom_id}: FAILED — {error}", file=sys.stderr)
        else:
            print(f"  [atom {order}] {atom_id}: {duration_ms}ms", file=sys.stderr)

    # Create per-protocol QueryTrace for backward compatibility. Same as
    # atom-level trace: skip on read-only targets so bolt-proxy doesn't reject.
    if not _READ_ONLY_TARGET:
        try:
            run_cypher("""
                MATCH (p:Protocol {node_id: $protocol_id})
                CREATE (qt:QueryTrace {
                    node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
                    protocol_id: $protocol_id,
                    duration_ms: $total_duration_ms,
                    fired_at: toString(datetime()),
                    invoked_epoch_ms: timestamp(),
                    cypher_summary: 'Protocol atom chain execution',
                    file_type: 'query-trace',
                    phase: 'protocol-execution',
                    atom_count: $atom_count,
                    failures: $failure_count
                })
                MERGE (qt)-[:FIRED_BY]->(p)
                RETURN qt.node_id
            """, {
                "protocol_id": protocol_id,
                "total_duration_ms": total_duration,
                "atom_count": len(atoms),
                "failure_count": len(failures),
            })
        except Exception as e:
            print(f"  [warn] failed to create protocol-level trace: {e}", file=sys.stderr)

    return total_duration, len(atoms), failures, all_result_rows


def main():
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <protocol_id>", file=sys.stderr)
        sys.exit(1)

    protocol_id = sys.argv[1]

    print(f"[atom_run] executing {protocol_id}", file=sys.stderr)

    try:
        total_duration, atom_count, failures, result_rows = execute_protocol(protocol_id)

        result = {
            "status": "success" if not failures else "partial",
            "protocol_id": protocol_id,
            "atom_count": atom_count,
            "total_duration_ms": total_duration,
            "atoms_executed": atom_count - len(failures),
            "failures": failures,
            "results": result_rows,
        }

        print(json.dumps(result, indent=2))

        if failures:
            print(f"[atom_run] {protocol_id}: {len(failures)} atoms failed", file=sys.stderr)
            return 1

        print(f"[atom_run] {protocol_id}: all {atom_count} atoms executed in {total_duration}ms", file=sys.stderr)
        return 0

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "protocol_id": protocol_id,
            "error": str(e),
        }, indent=2))
        print(f"[atom_run] {protocol_id}: ERROR — {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
