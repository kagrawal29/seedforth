#!/usr/bin/env python3
# ============================================================================
# Runner: drift_from_target
# ============================================================================
# Compute symmetric difference between local and target databases.
# Report only-local, only-target, and in-both node counts per label.
#
# Exit codes:
#   0: no drift (local has everything target has, or more)
#   1: local is stale (target has nodes that local doesn't)
#
# Usage:
#   NEO4J_SOURCE_BOLT=bolt://target:7687 NEO4J_SOURCE_USER=neo4j \
#   NEO4J_SOURCE_PASS=pass python3 drift_from_target.py
#
# Returns JSON with drift report:
#   {
#     "status": "success" or "drift_detected",
#     "drift": {
#       "Protocol": {"only_local": 3, "only_target": 0, "in_both": 108},
#       ...
#     },
#     "total_local": 1234,
#     "total_target": 1200,
#     "only_target_count": 5,
#     "canonical_species_dna": {"local": "hash", "target": "hash"},
#     "last_heartbeat_at": {"local": "ts", "target": "ts"}
#   }
# ============================================================================
import json
import os
import sys
import urllib.request
import urllib.error
import base64
import hashlib
from typing import Dict, Set, Tuple

NEO4J_LOCAL_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_LOCAL_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_LOCAL_PASS = os.environ.get("NEO4J_PASS", "localtest12")

NEO4J_SOURCE_URL = os.environ.get("NEO4J_SOURCE_URL")
NEO4J_SOURCE_USER = os.environ.get("NEO4J_SOURCE_USER", "neo4j")
NEO4J_SOURCE_PASS = os.environ.get("NEO4J_SOURCE_PASS", "localtest12")

LABELS_TO_CHECK = [
    "Protocol",
    "CLICommand",
    "Knowledge",
    "OnboardingStep",
    "SystemRequirement",
    "FailureMode",
    "Invariant",
    "TestCase",
]


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
    except urllib.error.URLError:
        return []
    except Exception:
        return []


def fetch_node_ids(url, user, password, label: str) -> Set[str]:
    """Fetch all node_ids for a label from a database."""
    statement = f"MATCH (n:{label}) RETURN n.node_id ORDER BY n.node_id"
    results = run_cypher(url, user, password, statement)
    node_ids = set()
    for row in results:
        if row.get("row") and row["row"][0]:
            node_ids.add(row["row"][0])
    return node_ids


def compute_drift(local_ids: Set[str], target_ids: Set[str]) -> Tuple[int, int, int]:
    """Compute only_local, only_target, in_both counts."""
    only_local = len(local_ids - target_ids)
    only_target = len(target_ids - local_ids)
    in_both = len(local_ids & target_ids)
    return only_local, only_target, in_both


def fetch_canonical_species_dna(url, user, password) -> str:
    """Fetch canonical species DNA (hash of all node_ids)."""
    statement = "MATCH (n) WHERE n.node_id IS NOT NULL RETURN n.node_id ORDER BY n.node_id"
    results = run_cypher(url, user, password, statement)
    node_ids = []
    for row in results:
        if row.get("row") and row["row"][0]:
            node_ids.append(row["row"][0])

    combined = "|".join(node_ids)
    hash_obj = hashlib.sha256(combined.encode())
    return hash_obj.hexdigest()[:16]


def fetch_last_heartbeat(url, user, password) -> str:
    """Fetch the last heartbeat timestamp."""
    statement = "MATCH (hb:HeartbeatEvent) RETURN hb.fired_at ORDER BY hb.fired_at DESC LIMIT 1"
    results = run_cypher(url, user, password, statement)
    if results and results[0].get("row"):
        return results[0]["row"][0] or "never"
    return "never"


def main():
    if not NEO4J_SOURCE_URL:
        print(
            json.dumps({"status": "error", "message": "NEO4J_SOURCE_URL not set"}),
            file=sys.stdout,
        )
        sys.exit(1)

    drift = {}
    total_local = 0
    total_target = 0
    only_target_count = 0

    for label in LABELS_TO_CHECK:
        local_ids = fetch_node_ids(
            NEO4J_LOCAL_URL, NEO4J_LOCAL_USER, NEO4J_LOCAL_PASS, label
        )
        target_ids = fetch_node_ids(
            NEO4J_SOURCE_URL, NEO4J_SOURCE_USER, NEO4J_SOURCE_PASS, label
        )

        only_local, only_target, in_both = compute_drift(local_ids, target_ids)
        drift[label] = {
            "only_local": only_local,
            "only_target": only_target,
            "in_both": in_both,
        }

        total_local += only_local + in_both
        total_target += only_target + in_both
        only_target_count += only_target

    local_dna = fetch_canonical_species_dna(
        NEO4J_LOCAL_URL, NEO4J_LOCAL_USER, NEO4J_LOCAL_PASS
    )
    target_dna = fetch_canonical_species_dna(
        NEO4J_SOURCE_URL, NEO4J_SOURCE_USER, NEO4J_SOURCE_PASS
    )

    local_hb = fetch_last_heartbeat(NEO4J_LOCAL_URL, NEO4J_LOCAL_USER, NEO4J_LOCAL_PASS)
    target_hb = fetch_last_heartbeat(
        NEO4J_SOURCE_URL, NEO4J_SOURCE_USER, NEO4J_SOURCE_PASS
    )

    summary = {
        "status": "drift_detected" if only_target_count > 0 else "healthy",
        "drift": drift,
        "total_local": total_local,
        "total_target": total_target,
        "only_target_count": only_target_count,
        "canonical_species_dna": {
            "local": local_dna,
            "target": target_dna,
            "match": local_dna == target_dna,
        },
        "last_heartbeat_at": {"local": local_hb, "target": target_hb},
    }

    print(json.dumps(summary, indent=2))
    sys.exit(1 if only_target_count > 0 else 0)


if __name__ == "__main__":
    main()
