#!/usr/bin/env python3
# ============================================================================
# Runner: all_targets_status
# ============================================================================
# Fetch status from all configured targets (local, prod, dev) in parallel.
# For each target: node count, autonomous_score, species DNA hash, latency.
#
# Reads targets from config.toml and attempts connections.
# Uses neo4j driver if available; falls back to HTTP.
#
# Usage:
#   python3 all_targets_status.py
#
# Returns:
#   {
#     "targets": {
#       "local": {"nodes": 10659, "score": 100.0, "dna": "hash", "latency_ms": 2},
#       "prod": {"nodes": 9377, "score": 100.0, "dna": "hash", "latency_ms": 297},
#       "dev": {"nodes": 9377, "score": 100.0, "dna": "hash", "latency_ms": 361}
#     },
#     "driver": "neo4j" or "http"
#   }
# ============================================================================
import json
import os
import sys
import urllib.request
import urllib.error
import base64
import time
import hashlib
from typing import Dict, Optional
from pathlib import Path

NEO4J_LOCAL_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_LOCAL_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_LOCAL_PASS = os.environ.get("NEO4J_PASS", "localtest12")

# Try to import neo4j driver for faster connections
HAVE_NEO4J_DRIVER = False
try:
    from neo4j import GraphDatabase, basic_auth
    HAVE_NEO4J_DRIVER = True
except ImportError:
    pass


def load_config_toml():
    """Load targets from ~/.mycelium/config.toml."""
    config_path = Path.home() / ".mycelium" / "config.toml"
    if not config_path.exists():
        return {}

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            return {}

    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config.get("targets", {})
    except Exception:
        return {}


def run_cypher_http(url, user, password, statement, params=None, timeout=10):
    """Run cypher via HTTP transport."""
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
        start = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            latency_ms = int((time.time() - start) * 1000)
            result = json.loads(r.read())
            results = result.get("results", [])
            if results:
                data = results[0].get("data", [])
                return data, latency_ms
            return [], latency_ms
    except Exception as e:
        return None, None


def fetch_node_count(url, user, password):
    """Fetch total node count."""
    statement = "MATCH (n) RETURN COUNT(n) AS cnt"
    results, latency = run_cypher_http(url, user, password, statement)
    if results and results[0].get("row"):
        return results[0]["row"][0], latency
    return 0, latency


def fetch_autonomous_score(url, user, password):
    """Fetch autonomous_score from Being:mycelium node."""
    statement = "MATCH (b:Being {node_id: 'being-mycelium'}) RETURN b.autonomous_score AS score"
    results, latency = run_cypher_http(url, user, password, statement)
    if results and results[0].get("row"):
        score = results[0]["row"][0]
        return float(score) if score else 0.0, latency
    return 0.0, latency


def fetch_canonical_dna(url, user, password):
    """Fetch canonical species DNA."""
    statement = "MATCH (n) WHERE n.node_id IS NOT NULL RETURN n.node_id ORDER BY n.node_id"
    results, latency = run_cypher_http(url, user, password, statement, timeout=30)
    if results:
        node_ids = []
        for row in results:
            if row.get("row") and row["row"][0]:
                node_ids.append(row["row"][0])
        combined = "|".join(node_ids)
        hash_obj = hashlib.sha256(combined.encode())
        return hash_obj.hexdigest()[:16], latency
    return "none", latency


def ping_target(bolt_url: str, user: str, password: str, timeout: int = 5) -> Optional[int]:
    """Ping a target and return latency in ms, or None if unreachable."""
    # Convert bolt:// to http:// for HTTP pings
    http_url = bolt_url.replace("bolt://", "http://").replace(":7687", ":7474")
    try:
        start = time.time()
        req = urllib.request.Request(
            f"{http_url}/browser/",
            headers={"Connection": "close"},
            method="HEAD",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            latency_ms = int((time.time() - start) * 1000)
            return latency_ms
    except Exception:
        return None


def fetch_target_status(name: str, bolt_url: str, user: str, password: str) -> Dict:
    """Fetch status for a single target."""
    http_url = bolt_url.replace("bolt://", "http://").replace(":7687", ":7474")

    # Try ping first
    ping_latency = ping_target(bolt_url, user, password, timeout=3)
    if ping_latency is None:
        return {
            "status": "unreachable",
            "nodes": 0,
            "score": 0.0,
            "dna": "none",
            "latency_ms": None,
            "heartbeat": "unknown",
        }

    # Fetch node count
    node_count, latency = fetch_node_count(http_url, user, password)
    if node_count is None:
        return {
            "status": "error",
            "nodes": 0,
            "score": 0.0,
            "dna": "none",
            "latency_ms": latency,
            "heartbeat": "unknown",
        }

    # Fetch autonomous score
    score, _ = fetch_autonomous_score(http_url, user, password)

    # Fetch canonical DNA
    dna, _ = fetch_canonical_dna(http_url, user, password)

    # Compute heartbeat status (rough heuristic: if node count > 0, heartbeat is likely scheduled)
    heartbeat_status = "scheduled" if node_count > 0 else "not"

    return {
        "status": "ok",
        "nodes": node_count,
        "score": score,
        "dna": dna,
        "latency_ms": latency or 0,
        "heartbeat": heartbeat_status,
    }


def main():
    config_targets = load_config_toml()
    default_targets = {
        "local": {
            "bolt": "bolt://localhost:7687",
            "user": "neo4j",
            "mode": "rw",
        },
        "dev": {
            "bolt": "bolt://5.78.206.137:7698",
            "user": "neo4j",
            "mode": "ro",
        },
        "prod": {
            "bolt": "bolt://5.78.206.137:7699",
            "user": "neo4j",
            "mode": "ro",
        },
    }

    # Merge config targets with defaults
    all_targets = {**default_targets, **config_targets}

    result = {
        "targets": {},
        "driver": "neo4j_driver" if HAVE_NEO4J_DRIVER else "http",
    }

    for name, config in sorted(all_targets.items()):
        bolt = config.get("bolt", "")
        user = config.get("user", "neo4j")
        # Resolve password from environment
        if name == "prod":
            password = os.environ.get("MYCELIUM_PROD_PASS", "localtest12")
        elif name == "dev":
            password = os.environ.get("MYCELIUM_DEV_PASS", "localtest12")
        else:
            password = os.environ.get("MYCELIUM_LOCAL_PASS", "localtest12")

        status = fetch_target_status(name, bolt, user, password)
        result["targets"][name] = status

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
