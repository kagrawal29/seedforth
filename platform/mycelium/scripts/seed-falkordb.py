#!/usr/bin/env python3
"""
Seed FalkorDB directly from graphify-out/graph-v4.json.

No Graphiti, no OpenAI. Loads the existing knowledge graph (105 nodes, 205 edges,
dreamed through 3 rounds) directly into FalkorDB via Cypher.

This is Asgard's first breath — the graph comes alive as a queryable service.

Usage:
    python3 scripts/seed-falkordb.py
    python3 scripts/seed-falkordb.py --graph graphify-out/graph.json
    python3 scripts/seed-falkordb.py --verify   # just check what's in the DB
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    try:
        import redis
        # Fallback: use redis directly with GRAPH commands
        FalkorDB = None
    except ImportError:
        print("ERROR: pip install falkordb  OR  pip install redis")
        sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GRAPH = REPO_ROOT / "graphify-out" / "graph-v4.json"
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"


def get_connection():
    """Connect to FalkorDB."""
    if FalkorDB:
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        return db.select_graph(GRAPH_NAME)
    else:
        # Fallback to raw redis
        import redis
        return redis.Redis(host=FALKORDB_HOST, port=FALKORDB_PORT)


def cypher_escape(s):
    """Escape a string for Cypher."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def seed_graph(graph_path: Path):
    """Load graph JSON into FalkorDB."""
    print(f"Loading graph from {graph_path}")
    data = json.loads(graph_path.read_text())

    nodes = data.get("nodes", [])
    edges = data.get("links", [])
    hyperedges = data.get("graph", {}).get("hyperedges", [])

    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Hyperedges: {len(hyperedges)}")
    print()

    conn = get_connection()
    start = time.time()

    # Create indices
    print("Creating indices...")
    try:
        if FalkorDB:
            conn.query("CREATE INDEX FOR (n:Knowledge) ON (n.node_id)")
            conn.query("CREATE INDEX FOR (n:Knowledge) ON (n.community)")
            conn.query("CREATE INDEX FOR (n:Demand) ON (n.node_id)")
            conn.query("CREATE INDEX FOR (n:Person) ON (n.node_id)")
        else:
            conn.execute_command("GRAPH.QUERY", GRAPH_NAME,
                "CREATE INDEX FOR (n:Knowledge) ON (n.node_id)")
            conn.execute_command("GRAPH.QUERY", GRAPH_NAME,
                "CREATE INDEX FOR (n:Knowledge) ON (n.community)")
    except Exception as e:
        print(f"  Index creation (may already exist): {e}")

    # Seed nodes
    print(f"\nSeeding {len(nodes)} nodes...")
    ok = 0
    for i, node in enumerate(nodes):
        node_id = cypher_escape(node.get("id", f"node_{i}"))
        label = cypher_escape(node.get("label", node_id))
        community = node.get("community", -1)
        source_file = cypher_escape(node.get("source_file", ""))
        file_type = cypher_escape(node.get("file_type", "unknown"))

        # Determine node label based on content
        if "demand" in node_id.lower() or file_type == "demand":
            cypher_label = "Demand"
        elif "person" in file_type.lower():
            cypher_label = "Person"
        else:
            cypher_label = "Knowledge"

        query = (
            f"MERGE (n:{cypher_label} {{node_id: '{node_id}'}}) "
            f"SET n.label = '{label}', "
            f"n.community = {community}, "
            f"n.source_file = '{source_file}', "
            f"n.file_type = '{file_type}'"
        )

        try:
            if FalkorDB:
                conn.query(query)
            else:
                conn.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
            ok += 1
        except Exception as e:
            print(f"  ERROR node {node_id}: {e}")

    print(f"  Nodes: {ok}/{len(nodes)} created")

    # Seed edges
    print(f"\nSeeding {len(edges)} edges...")
    ok = 0
    for edge in edges:
        src = cypher_escape(edge.get("source", edge.get("_src", "")))
        tgt = cypher_escape(edge.get("target", edge.get("_tgt", "")))
        relation = cypher_escape(edge.get("relation", "RELATES_TO")).upper().replace(" ", "_").replace("-", "_")
        confidence = cypher_escape(edge.get("confidence", "INFERRED"))
        score = edge.get("confidence_score", 0.5)
        weight = edge.get("weight", 1.0)

        # Sanitize relation name for Cypher
        relation = "".join(c for c in relation if c.isalnum() or c == "_")
        if not relation:
            relation = "RELATES_TO"

        query = (
            f"MATCH (a {{node_id: '{src}'}}), (b {{node_id: '{tgt}'}}) "
            f"MERGE (a)-[r:{relation}]->(b) "
            f"SET r.confidence = '{confidence}', "
            f"r.confidence_score = {score}, "
            f"r.weight = {weight}"
        )

        try:
            if FalkorDB:
                conn.query(query)
            else:
                conn.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
            ok += 1
        except Exception as e:
            if "no such" not in str(e).lower():
                print(f"  ERROR edge {src}->{tgt}: {e}")

    print(f"  Edges: {ok}/{len(edges)} created")

    elapsed = time.time() - start
    print(f"\nSeeding complete in {elapsed:.1f}s")
    return {"nodes": len(nodes), "edges": len(edges)}


def verify_graph():
    """Query the graph and report statistics."""
    conn = get_connection()
    print("=== Asgard Graph Statistics ===\n")

    queries = {
        "Total nodes": "MATCH (n) RETURN count(n) as c",
        "Knowledge nodes": "MATCH (n:Knowledge) RETURN count(n) as c",
        "Demand nodes": "MATCH (n:Demand) RETURN count(n) as c",
        "Total edges": "MATCH ()-[r]->() RETURN count(r) as c",
        "Communities": "MATCH (n) WHERE n.community IS NOT NULL RETURN count(DISTINCT n.community) as c",
    }

    for label, query in queries.items():
        try:
            if FalkorDB:
                result = conn.query(query)
                val = result.result_set[0][0] if result.result_set else 0
            else:
                result = conn.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
                val = result[1][0][0] if result[1] else 0
            print(f"  {label}: {val}")
        except Exception as e:
            print(f"  {label}: ERROR - {e}")

    # Top 5 most connected nodes
    print("\n  God Nodes (most connected):")
    query = (
        "MATCH (n)-[r]-() "
        "RETURN n.label, count(r) as degree "
        "ORDER BY degree DESC LIMIT 5"
    )
    try:
        if FalkorDB:
            result = conn.query(query)
            for row in result.result_set:
                print(f"    {row[0]}: {row[1]} edges")
        else:
            result = conn.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
            for row in result[1]:
                print(f"    {row[0]}: {row[1]} edges")
    except Exception as e:
        print(f"    ERROR: {e}")

    # Community sizes
    print("\n  Community Sizes:")
    query = (
        "MATCH (n) WHERE n.community IS NOT NULL "
        "RETURN n.community, count(n) as size "
        "ORDER BY size DESC"
    )
    try:
        if FalkorDB:
            result = conn.query(query)
            for row in result.result_set:
                print(f"    Community {row[0]}: {row[1]} nodes")
        else:
            result = conn.execute_command("GRAPH.QUERY", GRAPH_NAME, query)
            for row in result[1]:
                print(f"    Community {row[0]}: {row[1]} nodes")
    except Exception as e:
        print(f"    ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Seed FalkorDB with Asgard knowledge graph")
    parser.add_argument("--graph", default=str(DEFAULT_GRAPH), help="Path to graph JSON")
    parser.add_argument("--verify", action="store_true", help="Just verify current state")
    args = parser.parse_args()

    if args.verify:
        verify_graph()
    else:
        seed_graph(Path(args.graph))
        print()
        verify_graph()


if __name__ == "__main__":
    main()
