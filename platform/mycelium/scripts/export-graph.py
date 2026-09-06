#!/usr/bin/env python3
"""
Export FalkorDB graph to graph-v4.json format for dream-analysis.py.

Queries the live Asgard graph and writes a JSON file compatible with
the static graph format that dream-analysis.py and integrity-rules.py expect.

Usage:
    python3 scripts/export-graph.py                  # writes graphify-out/graph-v4.json
    python3 scripts/export-graph.py --output /tmp/g.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "graphify-out" / "graph-v4.json"

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(GRAPH_NAME)


def export_graph(output_path: Path):
    try:
        graph = get_graph()
    except Exception as e:
        print(f"[export-graph] FalkorDB unavailable: {e}")
        sys.exit(1)

    # Export all nodes (Knowledge + Demand)
    result = graph.query(
        "MATCH (n) RETURN n.node_id, n.label, n.community, n.source_file, "
        "n.file_type, n.category, n.confidence, labels(n) AS node_labels"
    )

    nodes = []
    node_ids = set()
    for row in result.result_set:
        node_id = row[0] or ""
        if not node_id or node_id in node_ids:
            continue
        node_ids.add(node_id)
        node_labels = row[7] if row[7] else []
        nodes.append({
            "id": node_id,
            "label": row[1] or node_id,
            "community": row[2] if row[2] is not None else -1,
            "source_file": row[3] or "",
            "file_type": row[4] or (
                "demand" if "Demand" in node_labels else "knowledge"
            ),
            "category": row[5] or "",
            "confidence": row[6] or "",
        })

    # Export all edges
    result = graph.query(
        "MATCH (a)-[r]->(b) RETURN a.node_id, b.node_id, type(r), "
        "r.confidence, r.confidence_score"
    )

    links = []
    for row in result.result_set:
        src = row[0] or ""
        tgt = row[1] or ""
        if not src or not tgt or src not in node_ids or tgt not in node_ids:
            continue
        links.append({
            "source": src,
            "target": tgt,
            "relation": row[2] or "",
            "confidence": row[3] or "INFERRED",
            "confidence_score": float(row[4]) if row[4] else 0.5,
        })

    data = {
        "nodes": nodes,
        "links": links,
        "graph": {
            "hyperedges": [],
            "exported_from": "falkordb",
            "node_count": len(nodes),
            "edge_count": len(links),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2))
    print(f"[export-graph] Exported {len(nodes)} nodes, {len(links)} edges to {output_path}")
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    export_graph(Path(args.output))


if __name__ == "__main__":
    main()
