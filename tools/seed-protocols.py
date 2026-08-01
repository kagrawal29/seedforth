#!/usr/bin/env python3
"""Seed heartbeat .cypher files into the graph as Protocol + CypherAtom nodes.

The graph becomes the code. Each .cypher file becomes a :Protocol node
referencing :CypherAtom nodes (the actual query text). The graph-runner
executes them by walking the atom chain.

Cadence mapping (from rhythm-and-immune.md):
  heartbeat (30 min): 01-09, 12-14
  dream     (4 hours): 10, 11, 15, 16

Usage: python3 tools/seed-protocols.py [--path deploy/heartbeat]
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q, ql

CADENCE_MAP = {
    "01-wake": "heartbeat",
    "02-connect": "heartbeat",
    "03-converge": "heartbeat",
    "04-decay-confidence": "heartbeat",
    "05-decay-demand": "heartbeat",
    "06-decay-edges": "heartbeat",
    "07-decay-ttl": "heartbeat",
    "08-dedup": "heartbeat",
    "09-heal-orphans": "heartbeat",
    "10-heal-dream": "dream",
    "11-immune": "dream",
    "12-liveness": "heartbeat",
    "13-report": "heartbeat",
    "14-snapshot": "heartbeat",
    "15-health-check": "dream",
    "16-agent-fatal-check": "dream",
}

LABELS = {
    "01-wake": "Wake - check if there is new data",
    "02-connect": "Connect - wire traces to knowledge",
    "03-converge": "Converge - detect agents on same topic",
    "04-decay-confidence": "Decay confidence - demote single-source",
    "05-decay-demand": "Decay demand - flag stale knowledge",
    "06-decay-edges": "Decay edges - prune unused inferred",
    "07-decay-ttl": "Decay TTL - expire transient nodes",
    "08-dedup": "Dedup - remove duplicate edges",
    "09-heal-orphans": "Heal orphans - delete zero-edge noise",
    "10-heal-dream": "Dream round - close triangles",
    "11-immune": "Immune - detect unauthorized changes",
    "12-liveness": "Liveness - is the system alive",
    "13-report": "Report - record system shape",
    "14-snapshot": "Snapshot - capture state",
    "15-health-check": "Health check - load/cpu/mem proposal",
    "16-agent-fatal-check": "Fatal check - fatal agent proposal",
}


def split_statements(text):
    """Split a .cypher file into statements on blank lines / comment sections."""
    # Remove comment lines, split on blank lines
    statements = []
    current = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            if current:
                statements.append("\n".join(current))
                current = []
            continue
        if not stripped:
            if current:
                statements.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        statements.append("\n".join(current))
    return [s.strip() for s in statements if s.strip()]


def seed_file(path, name):
    text = path.read_text()
    cadence = CADENCE_MAP.get(name, "heartbeat")
    label = LABELS.get(name, name.replace("-", " ").title())
    protocol_id = f"protocol-{name}"
    atom_ids = []

    statements = split_statements(text)
    if not statements:
        print(f"  SKIP {name}: no statements")
        return

    # Upsert protocol
    q(
        "MERGE (p:Protocol {node_id:$pid}) "
        "SET p.label=$label, p.cadence=$cadence, p.enabled=true, p.project='system'",
        {"pid": protocol_id, "label": label, "cadence": cadence},
    )

    # Create atoms + chain
    prev_atom = None
    for i, stmt in enumerate(statements):
        atom_id = f"atom-{name}-{i:02d}"
        semantic = f"{label} (part {i+1})"
        q(
            "MERGE (a:CypherAtom {node_id:$aid}) "
            "SET a.cypher=$cypher, a.semantic=$semantic, a.cadence=$cadence, "
            "a.project='system', a.updated_at=datetime()",
            {"aid": atom_id, "cypher": stmt, "semantic": semantic, "cadence": cadence},
        )
        atom_ids.append(atom_id)

        if prev_atom:
            q(
                "MATCH (a1:CypherAtom {node_id:$a1}) "
                "MATCH (a2:CypherAtom {node_id:$a2}) "
                "MERGE (a1)-[:FOLLOWS]->(a2)",
                {"a1": prev_atom, "a2": atom_id},
            )
        prev_atom = atom_id

    # Link protocol -> first atom
    q(
        "MATCH (p:Protocol {node_id:$pid}) "
        "MATCH (a:CypherAtom {node_id:$aid}) "
        "MERGE (p)-[:FIRST_ATOM]->(a)",
        {"pid": protocol_id, "aid": atom_ids[0]},
    )

    print(f"  SEED {name}: {len(statements)} atoms -> {protocol_id} ({cadence})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="deploy/heartbeat",
                        help="Path to .cypher files")
    args = parser.parse_args()

    base = Path(__file__).parent.parent / args.path
    print(f"=== Seeding protocols from {base} ===")
    for f in sorted(base.glob("*.cypher")):
        name = f.stem
        if name in CADENCE_MAP:
            seed_file(f, name)
    print("=== Complete ===")


if __name__ == "__main__":
    main()
