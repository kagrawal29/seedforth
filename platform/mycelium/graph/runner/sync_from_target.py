#!/usr/bin/env python3
# ============================================================================
# Runner: sync_from_target
# ============================================================================
# Sync nodes from a target database (prod/dev) to local, using MERGE semantics.
# Never deletes. Never overwrites properties except on node_id match.
# Idempotent and additive.
#
# Labels synced: Protocol, CLICommand, Knowledge, OnboardingStep,
# SystemRequirement, FailureMode, Invariant, TestCase
#
# Usage:
#   NEO4J_SOURCE_BOLT=bolt://target:7687 NEO4J_SOURCE_USER=neo4j \
#   NEO4J_SOURCE_PASS=pass python3 sync_from_target.py [--dry-run]
#
# Returns JSON with sync summary:
#   {
#     "status": "success",
#     "synced": {
#       "Protocol": {"new": 5, "updated": 2, "unchanged": 108},
#       "Knowledge": {...},
#       ...
#     },
#     "total_new": 7,
#     "total_updated": 2,
#     "total_unchanged": 108,
#     "dry_run": false
#   }
# ============================================================================
import json
import os
import sys
import urllib.request
import urllib.error
import base64
from typing import Dict, List, Tuple

NEO4J_LOCAL_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_LOCAL_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_LOCAL_PASS = os.environ.get("NEO4J_PASS", "localtest12")

NEO4J_SOURCE_URL = os.environ.get("NEO4J_SOURCE_URL")
NEO4J_SOURCE_USER = os.environ.get("NEO4J_SOURCE_USER", "neo4j")
NEO4J_SOURCE_PASS = os.environ.get("NEO4J_SOURCE_PASS", "localtest12")

LABELS_TO_SYNC = [
    "Protocol",
    "CLICommand",
    "Knowledge",
    "OnboardingStep",
    "SystemRequirement",
    "FailureMode",
    "Invariant",
    "TestCase",
]

DRY_RUN = "--dry-run" in sys.argv


def run_cypher(url, user, password, statement, params=None, timeout=10):
    """Run cypher against a specific Neo4j instance."""
    if not url:
        return []
    body = {"statements": [{"statement": statement, "parameters": params or {}}]}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/db/neo4j/tx/commit",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            result = json.loads(r.read())
            results = result.get("results", [])
            if results:
                return results[0].get("data", [])
            return []
    except urllib.error.URLError as e:
        return []
    except Exception as e:
        return []


def fetch_nodes_from_source(label: str) -> List[Dict]:
    """Fetch all nodes of a given label from source."""
    statement = f"""
    MATCH (n:{label})
    RETURN n.node_id AS node_id, n.cypher AS cypher, n.label AS label,
           properties(n) AS props
    ORDER BY n.node_id
    """
    results = run_cypher(
        NEO4J_SOURCE_URL, NEO4J_SOURCE_USER, NEO4J_SOURCE_PASS, statement
    )
    nodes = []
    for row in results:
        if row.get("row"):
            node_id, cypher, label_val, props = row["row"]
            nodes.append(
                {"node_id": node_id, "cypher": cypher, "label": label_val, "props": props or {}}
            )
    return nodes


def merge_nodes_to_local(label: str, nodes: List[Dict], force: bool = False) -> Tuple[int, int, int, List[str]]:
    """Merge nodes into local database. Returns (new, updated, unchanged, skipped_node_ids)."""
    new_count = 0
    updated_count = 0
    unchanged_count = 0
    skipped_node_ids = []

    for node in nodes:
        node_id = node.get("node_id")
        if not node_id:
            continue

        # Check if node exists locally
        statement = f"""
        MATCH (existing:{label} {{node_id: $node_id}})
        RETURN COUNT(existing) AS cnt, existing._local_edited_at AS edited_at
        """
        result = run_cypher(
            NEO4J_LOCAL_URL,
            NEO4J_LOCAL_USER,
            NEO4J_LOCAL_PASS,
            statement,
            {"node_id": node_id},
        )
        exists = False
        local_edited_at = None
        if result and result[0].get("row"):
            exists = result[0]["row"][0] > 0
            local_edited_at = result[0]["row"][1]

        if not exists:
            # Create new node
            if not DRY_RUN:
                props = node.get("props", {})
                props["node_id"] = node_id
                if node.get("label"):
                    props["label"] = node["label"]
                if node.get("cypher"):
                    props["cypher"] = node["cypher"]
                props["_last_synced_at"] = "datetime()"

                set_clause = ", ".join(
                    f"n.{k} = ${k}" for k in props.keys() if k != "_last_synced_at"
                )
                merge_statement = f"MERGE (n:{label} {{node_id: $node_id}}) SET {set_clause}, n._last_synced_at = datetime()"
                run_cypher(
                    NEO4J_LOCAL_URL,
                    NEO4J_LOCAL_USER,
                    NEO4J_LOCAL_PASS,
                    merge_statement,
                    props,
                )
            new_count += 1
        else:
            # Node exists; check if locally edited and skip if so (unless --force)
            if local_edited_at and not force:
                skipped_node_ids.append(node_id)
                unchanged_count += 1  # Count as unchanged for summary
                continue

            # Node exists and either not edited or --force; check if cypher property changed
            check_stmt = (
                f"MATCH (n:{label} {{node_id: $node_id}}) RETURN n.cypher AS cypher"
            )
            check_result = run_cypher(
                NEO4J_LOCAL_URL,
                NEO4J_LOCAL_USER,
                NEO4J_LOCAL_PASS,
                check_stmt,
                {"node_id": node_id},
            )
            local_cypher = None
            if check_result and check_result[0].get("row"):
                local_cypher = check_result[0]["row"][0]

            source_cypher = node.get("cypher")
            if local_cypher != source_cypher and source_cypher:
                # Update cypher property only
                if not DRY_RUN:
                    update_stmt = f"MATCH (n:{label} {{node_id: $node_id}}) SET n.cypher = $cypher, n._last_synced_at = datetime()"
                    run_cypher(
                        NEO4J_LOCAL_URL,
                        NEO4J_LOCAL_USER,
                        NEO4J_LOCAL_PASS,
                        update_stmt,
                        {"node_id": node_id, "cypher": source_cypher},
                    )
                updated_count += 1
            else:
                if not DRY_RUN:
                    # Update _last_synced_at even if cypher didn't change
                    update_stmt = f"MATCH (n:{label} {{node_id: $node_id}}) SET n._last_synced_at = datetime()"
                    run_cypher(
                        NEO4J_LOCAL_URL,
                        NEO4J_LOCAL_USER,
                        NEO4J_LOCAL_PASS,
                        update_stmt,
                        {"node_id": node_id},
                    )
                unchanged_count += 1

    return new_count, updated_count, unchanged_count, skipped_node_ids


def main():
    if not NEO4J_SOURCE_URL:
        print(
            json.dumps({"status": "error", "message": "NEO4J_SOURCE_URL not set"}),
            file=sys.stdout,
        )
        sys.exit(1)

    force = "--force" in sys.argv

    summary = {
        "status": "success",
        "synced": {},
        "total_new": 0,
        "total_updated": 0,
        "total_unchanged": 0,
        "total_skipped": 0,
        "skipped_node_ids": [],
        "dry_run": DRY_RUN,
    }

    for label in LABELS_TO_SYNC:
        nodes = fetch_nodes_from_source(label)
        new, updated, unchanged, skipped = merge_nodes_to_local(label, nodes, force=force)

        summary["synced"][label] = {
            "new": new,
            "updated": updated,
            "unchanged": unchanged,
            "skipped": len(skipped),
            "total": new + updated + unchanged + len(skipped),
        }
        summary["total_new"] += new
        summary["total_updated"] += updated
        summary["total_unchanged"] += unchanged
        summary["total_skipped"] += len(skipped)
        summary["skipped_node_ids"].extend(skipped)

    print(json.dumps(summary, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
