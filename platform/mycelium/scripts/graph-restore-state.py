#!/usr/bin/env python3
"""
Restore graph from a Cypher state file (exported by graph-export-state.py).

Clears the current graph and replays all MERGE statements.
This is the graph equivalent of 'git checkout <sha>'.

Usage:
    python3 scripts/graph-restore-state.py graph-state.cypher
    python3 scripts/graph-restore-state.py --verify  # compare current vs file, don't restore
"""

import os
import sys
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def restore(cypher_file: str, verify_only: bool = False):
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = db.select_graph("asgard")

    path = Path(cypher_file)
    if not path.exists():
        print(f"ERROR: {cypher_file} not found")
        sys.exit(1)

    lines = path.read_text().split("\n")
    statements = [l.rstrip(";") for l in lines if l.strip() and not l.startswith("//")]

    if verify_only:
        # Count current graph
        current_nodes = graph.query("MATCH (n) WHERE NOT n:QueryTrace RETURN count(n)").result_set[0][0]
        current_edges = graph.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]

        # Count statements in file
        node_stmts = sum(1 for s in statements if s.startswith("MERGE (n:"))
        edge_stmts = sum(1 for s in statements if s.startswith("MATCH (a"))

        print(f"File: {node_stmts} nodes, {edge_stmts} edges")
        print(f"Live: {current_nodes} nodes, {current_edges} edges")
        print(f"Node diff: {current_nodes - node_stmts}")
        print(f"Edge diff: {current_edges - edge_stmts}")

        if current_nodes == node_stmts and current_edges == edge_stmts:
            print("Status: IN SYNC (counts match)")
        else:
            print("Status: DRIFTED")
        return

    # Confirm before destructive operation
    current_nodes = graph.query("MATCH (n) RETURN count(n)").result_set[0][0]
    print(f"WARNING: This will clear the graph ({current_nodes} nodes) and restore from {path.name}")
    print(f"Statements to replay: {len(statements)}")
    confirm = input("Type 'restore' to proceed: ")
    if confirm != "restore":
        print("Aborted.")
        return

    # Clear graph
    print("[restore] Clearing graph...")
    graph.query("MATCH (n) DETACH DELETE n")

    # Replay statements
    print(f"[restore] Replaying {len(statements)} statements...")
    ok = 0
    errors = 0
    for i, stmt in enumerate(statements):
        try:
            graph.query(stmt)
            ok += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  Error at line {i}: {str(e)[:80]}")

        if (i + 1) % 500 == 0:
            print(f"  {i + 1}/{len(statements)}...")

    # Verify
    restored_nodes = graph.query("MATCH (n) RETURN count(n)").result_set[0][0]
    restored_edges = graph.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]

    print(f"[restore] Done: {ok} ok, {errors} errors")
    print(f"[restore] Restored: {restored_nodes} nodes, {restored_edges} edges")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="graph-state.cypher", help="Cypher state file")
    parser.add_argument("--verify", action="store_true", help="Compare only, don't restore")
    args = parser.parse_args()
    restore(args.file, args.verify)
