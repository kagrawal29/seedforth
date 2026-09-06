#!/usr/bin/env python3
"""
Export full graph state as deterministic Cypher MERGE statements.

Output is a .cypher file that, when executed against an empty graph,
reproduces the exact graph state. Committed to git = versioned.

Nodes sorted by node_id, edges sorted by src:type:dst.
Deterministic output = git only stores the diff.

Usage:
    python3 scripts/graph-export-state.py                    # writes graph-state.cypher
    python3 scripts/graph-export-state.py --output /tmp/x.cypher
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "graph-state.cypher"


def esc(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


def export_graph(output_path: str = None):
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = db.select_graph("asgard")
    output = Path(output_path) if output_path else DEFAULT_OUTPUT

    ts = datetime.now(timezone.utc).isoformat()
    lines = []
    lines.append(f"// Graph state export — {ts}")
    lines.append(f"// Deterministic: sorted by node_id, then edges by src:type:dst")
    lines.append(f"// Execute against empty 'asgard' graph to restore")
    lines.append("")

    # Export nodes — sorted by label then node_id for deterministic output
    # Exclude QueryTrace (ephemeral, high volume)
    lines.append("// === NODES ===")
    r = graph.query(
        "MATCH (n) WHERE NOT n:QueryTrace "
        "RETURN labels(n)[0] AS type, n "
        "ORDER BY labels(n)[0], n.node_id"
    )

    node_count = 0
    for row in r.result_set:
        label = row[0]
        node = row[1]
        props = node.properties

        node_id = props.get("node_id", "")
        if not node_id:
            continue

        prop_sets = []
        for k in sorted(props.keys()):
            v = props[k]
            if v is None:
                continue
            if isinstance(v, bool):
                prop_sets.append(f"n.{k} = {str(v).lower()}")
            elif isinstance(v, (int, float)):
                prop_sets.append(f"n.{k} = {v}")
            elif isinstance(v, list):
                items = ", ".join(f"'{esc(str(i))}'" for i in v)
                prop_sets.append(f"n.{k} = [{items}]")
            else:
                prop_sets.append(f"n.{k} = '{esc(str(v))}'")

        set_clause = ", ".join(prop_sets)
        lines.append(f"MERGE (n:{label} {{node_id: '{esc(node_id)}'}}) SET {set_clause};")
        node_count += 1

    lines.append("")
    lines.append("// === EDGES ===")

    # Export edges — sorted for deterministic output
    # Exclude edges involving QueryTrace
    r = graph.query(
        "MATCH (a)-[r]->(b) "
        "WHERE NOT a:QueryTrace AND NOT b:QueryTrace "
        "AND a.node_id IS NOT NULL AND b.node_id IS NOT NULL "
        "RETURN a.node_id, type(r), b.node_id, r "
        "ORDER BY a.node_id, type(r), b.node_id"
    )

    edge_count = 0
    for row in r.result_set:
        src_id, edge_type, dst_id = row[0], row[1], row[2]
        edge = row[3]

        # Edge properties (if any, excluding internal)
        edge_props = edge.properties if hasattr(edge, 'properties') else {}
        if edge_props:
            prop_sets = []
            for k in sorted(edge_props.keys()):
                v = edge_props[k]
                if v is None:
                    continue
                if isinstance(v, bool):
                    prop_sets.append(f"r.{k} = {str(v).lower()}")
                elif isinstance(v, (int, float)):
                    prop_sets.append(f"r.{k} = {v}")
                else:
                    prop_sets.append(f"r.{k} = '{esc(str(v))}'")
            set_clause = f" SET {', '.join(prop_sets)}" if prop_sets else ""
        else:
            set_clause = ""

        lines.append(
            f"MATCH (a {{node_id: '{esc(src_id)}'}}), (b {{node_id: '{esc(dst_id)}'}}) "
            f"MERGE (a)-[r:{edge_type}]->(b){set_clause};"
        )
        edge_count += 1

    # Footer
    lines.append("")
    lines.append(f"// Exported: {node_count} nodes, {edge_count} edges")
    lines.append(f"// Timestamp: {ts}")

    output.write_text("\n".join(lines))
    print(f"[export] {node_count} nodes, {edge_count} edges → {output}")
    print(f"[export] Size: {round(output.stat().st_size / 1024)}KB")
    return node_count, edge_count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()
    export_graph(args.output)
