#!/usr/bin/env python3
"""Store a fact in the local Neo4j knowledge graph staging area.

Writes are promoted to the shared mycelium graph during nightly promotion.

Usage:
    python3 store-fact.py \
        --type decision|learning|pattern|workitem \
        --label "..." \
        --content '{"key":"value"}' \
        --scope "org-name" \
        --visibility fleet|org|private \
        --project "project-name" \
        --agent "agent-id"

Requires LOCAL_NEO4J_USER and LOCAL_NEO4J_PASSWORD environment variables.
Connects to bolt://localhost:7687 (write-enabled local staging instance).
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone


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


def _generate_node_id(fact_type, label, project, agent):
    ts = datetime.now(timezone.utc).isoformat()
    raw = f"{fact_type}|{label}|{project}|{agent}|{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _parse_content(raw):
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({
            "error": f"Invalid JSON in --content: {str(e)}"
        }), flush=True)
        sys.exit(1)


def store_fact(fact_type, label, content, scope, visibility, project, agent):
    driver = _connect()
    node_id = _generate_node_id(fact_type, label, project, agent)
    content_json = _parse_content(content)
    compacted_at = datetime.now(timezone.utc).isoformat()

    query = """
        MERGE (k:Knowledge {node_id: $node_id})
        SET k.file_type = $file_type,
            k.label = $label,
            k.content = $content,
            k.scope = $scope,
            k.visibility = $visibility,
            k.project = $project,
            k.agent = $agent,
            k.promoted = false,
            k.decay_protected = true,
            k.compaction_retention_days = 90,
            k.compacted_at = $compacted_at,
            k.created_by = $agent
        RETURN k.node_id AS node_id
    """

    try:
        with driver.session() as session:
            result = session.run(query, {
                "node_id": node_id,
                "file_type": fact_type,
                "label": label,
                "content": json.dumps(content_json),
                "scope": scope,
                "visibility": visibility,
                "project": project,
                "agent": agent,
                "compacted_at": compacted_at,
            })
            record = result.single()
            if record:
                print(record["node_id"], flush=True)
            else:
                print(json.dumps({
                    "error": "MERGE returned no result"
                }), flush=True)
                sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "error": f"Write failed: {str(e)}"
        }), flush=True)
        sys.exit(1)
    finally:
        driver.close()


def main():
    parser = argparse.ArgumentParser(
        description="Store a fact in local Neo4j staging for nightly promotion"
    )
    parser.add_argument(
        "--type", dest="fact_type", required=True,
        choices=["decision", "learning", "pattern", "workitem"],
        help="Fact type"
    )
    parser.add_argument(
        "--label", required=True,
        help="Human-readable label"
    )
    parser.add_argument(
        "--content", required=True,
        help="Structured fact data (JSON string or literal)"
    )
    parser.add_argument(
        "--scope", required=True,
        help="Owning organization (e.g. seedforth, solveos)"
    )
    parser.add_argument(
        "--visibility", required=True,
        choices=["fleet", "org", "private"],
        help="Visibility: fleet=all, org=same org, private=this agent"
    )
    parser.add_argument(
        "--project", required=True,
        help="Source project name"
    )
    parser.add_argument(
        "--agent", required=True,
        help="Source agent identifier"
    )
    args = parser.parse_args()

    store_fact(
        fact_type=args.fact_type,
        label=args.label,
        content=args.content,
        scope=args.scope,
        visibility=args.visibility,
        project=args.project,
        agent=args.agent,
    )


if __name__ == "__main__":
    main()
