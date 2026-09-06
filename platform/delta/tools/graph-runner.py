#!/usr/bin/env python3
"""Graph-native execution runner.

Protocols live IN the graph as :Protocol nodes. Each protocol references
Cypher atoms (:CypherAtom nodes with the actual query text). The runner is a
thin shell: it reads protocol nodes, walks their atom chains, executes each
atom against Neo4j, records the run. No .cypher files — the graph is the code.

Schema:
  (:Protocol {node_id, label, cadence, enabled})
    -[:FIRST_ATOM]-> (:CypherAtom {node_id, cypher, semantic})  -- graph behavior
    -[:FIRST_ATOM]-> (:ExternalAtom {node_id, script, semantic}) -- Python I/O
    -[:NEXT_ATOM]-> ...   (via :FOLLOWS edges between atoms)

Usage:
  python3 graph-runner.py --cadence heartbeat
  python3 graph-runner.py --cadence dream
  python3 graph-runner.py --cadence deep
  python3 graph-runner.py --all
"""
import argparse
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from neo4j_helper import q, ql, q_strict


def get_protocols(cadence=None):
    """Fetch protocol nodes, optionally filtered by cadence."""
    if cadence:
        rows = ql(
            "MATCH (p:Protocol {cadence:$cadence, enabled:true}) "
            "RETURN p.node_id, p.label ORDER BY p.node_id",
            {"cadence": cadence},
        )
    else:
        rows = ql(
            "MATCH (p:Protocol {enabled:true}) "
            "RETURN p.node_id, p.label ORDER BY p.node_id"
        )
    return [{"node_id": r[0], "label": r[1] or r[0]} for r in rows]


def get_atoms_for_protocol(protocol_id):
    """Fetch the ordered atom chain for a protocol via FIRST_ATOM + FOLLOWS.

    Atoms may be :CypherAtom (graph behavior) or :ExternalAtom (Python
    script reference). Order follows the FOLLOWS chain depth from FIRST_ATOM.
    """
    rows = ql(
        "MATCH (p:Protocol {node_id:$pid})-[:FIRST_ATOM]->(first) "
        "MATCH path=(first)-[:FOLLOWS*0..]->(atom) "
        "RETURN atom.node_id, atom.cypher, atom.semantic, atom.script, length(path) AS depth "
        "ORDER BY depth",
        {"pid": protocol_id},
    )
    return [
        {"node_id": r[0], "cypher": r[1], "semantic": r[2] or r[0], "script": r[3]}
        for r in rows
    ]


def run_atom(atom, protocol_id):
    """Execute one atom. Returns (success, output).

    CypherAtom -> run the cypher text. ExternalAtom -> run the referenced
    Python script (system-state I/O the graph cannot express).
    """
    if atom.get("script"):
        try:
            res = subprocess.run(
                ["python3", atom["script"]],
                capture_output=True,
                text=True,
                timeout=120,
            )
            out = (res.stdout or res.stderr).strip()[-500:]
            return res.returncode == 0, out
        except Exception as e:
            return False, str(e)
    try:
        rows = q_strict(atom["cypher"])
        return True, rows
    except Exception as e:
        return False, str(e)


def compose_chain(atoms):
    """Compose a chain of atoms into ONE Cypher query.

    Fine-grained atoms need variable passing between steps. Joining with
    WITH * carries all bound variables forward, so a later atom's WHERE or
    MATCH sees the earlier atom's bindings. This is mycelium's CypherAtom
    walk, executed as a single composed statement.

    Returns a single cypher string, or None if the chain has external atoms.
    """
    if not atoms:
        return None
    parts = []
    for i, atom in enumerate(atoms):
        if atom.get("script"):
            return None  # can't compose external atoms
        cypher = (atom.get("cypher") or "").strip().rstrip(";").strip()
        if not cypher:
            continue
        parts.append(cypher)
        # Insert WITH * between steps so variables carry forward
        # (skip after the last atom)
        if i < len(atoms) - 1:
            parts.append("WITH *")
    return "\n".join(parts)


def run_protocol_chain(protocol_id, atoms):
    """Run a protocol's atom chain as one composed query when possible."""
    composed = compose_chain(atoms)
    if composed is None:
        return None  # fall back to per-atom execution
    try:
        rows = q_strict(composed)
        return True, rows
    except Exception as e:
        return False, str(e)


def record_run(protocol_id, results, run_id):
    """Write a ProtocolRun node + per-atom results + :RAN edge to the protocol."""
    ok = sum(1 for r in results if r[0])
    q(
        "MATCH (p:Protocol {node_id:$pid}) "
        "CREATE (pr:ProtocolRun {node_id:$rid, protocol:$pid, timestamp:datetime(), "
        "atoms_total:$total, atoms_ok:$ok, project:'system'}) "
        "MERGE (p)<-[:RAN {decay_protected:true}]-(pr)",
        {"rid": run_id, "pid": protocol_id, "total": len(results), "ok": ok},
    )


def main():
    parser = argparse.ArgumentParser(description="Graph-native protocol runner")
    parser.add_argument("--cadence", choices=["heartbeat", "dream", "deep", "fast", "weekly"],
                        help="Run protocols with this cadence")
    parser.add_argument("--all", action="store_true", help="Run all enabled protocols")
    parser.add_argument("--protocol", help="Run a single protocol by node_id")
    args = parser.parse_args()

    if args.protocol:
        protocols = [{"node_id": args.protocol, "label": args.protocol}]
    elif args.all:
        protocols = get_protocols()
    elif args.cadence:
        protocols = get_protocols(args.cadence)
    else:
        print("Specify --cadence, --all, or --protocol")
        sys.exit(1)

    if not protocols:
        print(f"No protocols found" + (f" for cadence={args.cadence}" if args.cadence else ""))
        return

    print(f"=== GRAPH RUNNER ({time.strftime('%H:%M:%S')}) ===")
    print(f"Running {len(protocols)} protocols\n")

    for proto in protocols:
        print(f"[{proto['label']}]")
        atoms = get_atoms_for_protocol(proto["node_id"])
        if not atoms:
            print(f"  (no atoms defined)")
            continue
        run_id = f"prun-{proto['node_id']}-{int(time.time())}"

        # Execute atoms SEQUENTIALLY as separate transactions.
        # Effects persist in the graph between atoms (the graph is the shared
        # state). Each atom is independently valid — no WITH-composition,
        # which is fragile and loses effects. This is mycelium's atom-walk:
        # atoms fire in order, each reading/writing graph state.
        results = []
        for atom in atoms:
            ok, output = run_atom(atom, proto["node_id"])
            status = "OK" if ok else "ERR"
            print(f"  {status} {atom['node_id']}: {atom['semantic'][:50]}")
            if not ok:
                print(f"      {str(output)[:150]}")
            results.append((ok, output))
        record_run(proto["node_id"], results, run_id)

    print("\n=== COMPLETE ===")


if __name__ == "__main__":
    main()
