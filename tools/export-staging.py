#!/usr/bin/env python3
"""Nightly export: reads promoted=false Knowledge nodes from local Neo4j
and generates mycelium-compatible .cypher files.

Usage:
    python3 export-staging.py --output /opt/mycelium/graph/knowledge/agent-facts.cypher
    python3 export-staging.py --output /opt/mycelium/graph/knowledge/ --split-by-project

Requires LOCAL_NEO4J_USER and LOCAL_NEO4J_PASSWORD environment variables.
Connects to bolt://localhost:7687 (write-enabled local staging instance).
"""

import argparse
import json
import os
import sys
from pathlib import Path


def _connect():
    from neo4j import GraphDatabase

    uri = os.environ.get("LOCAL_NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("LOCAL_NEO4J_USER")
    password = os.environ.get("LOCAL_NEO4J_PASSWORD")
    if not user or not password:
        print(json.dumps({
            "error": "LOCAL_NEO4J_USER and LOCAL_NEO4J_PASSWORD must be set"
        }), flush=True)
        sys.exit(1)

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(json.dumps({
            "error": f"Failed to connect to Neo4j at {uri}: {str(e)}"
        }), flush=True)
        sys.exit(1)


def _fetch_pending(driver):
    query = """
        MATCH (k:Knowledge)
        WHERE k.promoted = false
        RETURN k
        ORDER BY k.project, k.compacted_at
    """
    with driver.session() as session:
        result = session.run(query)
        records = [record["k"] for record in result]
        return records


def _escape_value(val):
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    escaped = str(val).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _build_merge_statement(node):
    node_id = node.get("node_id", "")
    props = dict(node.items())

    prop_lines = []
    if "node_id" in props:
        prop_lines.append(f'  k.node_id = {_escape_value(props.pop("node_id"))}')

    skip_set_keys = {"node_id", "promoted"}
    for key, val in sorted(props.items()):
        if key in skip_set_keys:
            continue
        prop_lines.append(f'  k.{key} = {_escape_value(val)}')

    prop_lines.append(f'  k.promoted = true')

    lines = []
    lines.append(f"// @node_id: {node_id}")
    lines.append("// @label: Knowledge")
    lines.append(f"MERGE (k:Knowledge {{node_id: {_escape_value(node_id)}}})")
    lines.append("ON CREATE SET")
    lines.extend(prop_lines)
    lines.append("ON MATCH SET")
    lines.append(f'  k.promoted = true')
    lines.append(";")

    return "\n".join(lines)


def _group_by_project(records):
    groups = {}
    for node in records:
        project = node.get("project", "unknown")
        groups.setdefault(project, []).append(node)
    return groups


def _write_file(filepath, records, header_comment=None):
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines_written = 0
    with open(path, "w") as f:
        if header_comment:
            f.write(f"// {header_comment}\n\n")
        for i, node in enumerate(records):
            if i > 0:
                f.write("\n")
            stmt = _build_merge_statement(node)
            f.write(stmt)
            f.write("\n")
            lines_written += 1

    return path, lines_written


def export_staging(output_path, split_by_project=False):
    driver = _connect()

    try:
        records = _fetch_pending(driver)
    except Exception as e:
        print(json.dumps({
            "error": f"Read failed: {str(e)}"
        }), flush=True)
        sys.exit(1)
    finally:
        driver.close()

    total = len(records)
    if total == 0:
        print(json.dumps({
            "exported": 0,
            "files": [],
            "message": "No pending facts to export"
        }), flush=True)
        return

    output_path = Path(output_path)
    files_written = []

    if split_by_project:
        groups = _group_by_project(records)
        for project, group_records in sorted(groups.items()):
            safe_name = project.replace("/", "-").replace(" ", "_")
            if output_path.suffix == ".cypher":
                base = output_path.parent
                filepath = base / f"{output_path.stem}-{safe_name}.cypher"
            else:
                filepath = output_path / f"{safe_name}.cypher"
            path, count = _write_file(
                filepath, group_records,
                header_comment=f"Agent facts for project: {project}"
            )
            files_written.append({"path": str(path), "count": count})
    else:
        path, count = _write_file(
            output_path, records,
            header_comment=f"Agent facts export — {total} pending nodes"
        )
        files_written.append({"path": str(path), "count": count})

    print(json.dumps({
        "exported": total,
        "files": files_written
    }), flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Export pending Knowledge facts from local Neo4j staging as mycelium-compatible Cypher"
    )
    parser.add_argument(
        "--output", required=True,
        help="Output .cypher file path (or directory with --split-by-project)"
    )
    parser.add_argument(
        "--split-by-project", action="store_true",
        help="Group facts by project and write to separate .cypher files"
    )
    args = parser.parse_args()

    export_staging(
        output_path=args.output,
        split_by_project=args.split_by_project,
    )


if __name__ == "__main__":
    main()
