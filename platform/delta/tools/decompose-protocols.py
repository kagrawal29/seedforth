#!/usr/bin/env python3
"""Decompose fat heartbeat protocol atoms into fine-grained semantic chains.

Mycelium's design: a protocol is a WALK through fine-grained CypherAtoms
connected by FOLLOWS edges. Each atom is one logical step with a semantic
description. The graph can then explain its own reasoning.

Current state: protocols are single fat atoms. This tool decomposes them.

Approach: for each protocol's current atom, use a rule-based splitter:
- Split multi-statement cypher (WITH/MATCH/MERGE/SET/RETURN as boundaries)
- Give each fragment a semantic label
- Re-link Protocol -> FIRST_ATOM -> FOLLOWS* chain

Usage: python3 decompose-protocols.py [--protocol protocol-02-connect]
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q, ql


def split_cypher_steps(cypher):
    """Split a cypher statement into logical steps at WITH/MATCH boundaries.

    Returns list of {cypher, semantic} steps.
    """
    # Split on lines that start a new clause: WITH, MATCH, OPTIONAL MATCH, MERGE
    clauses = re.split(r'\n(?=(?:OPTIONAL\s+)?(?:MATCH|WITH|MERGE|CREATE|RETURN|UNWIND|SET|DELETE|REMOVE|CALL|WHERE)\b)', cypher.strip())
    steps = []
    for c in clauses:
        c = c.strip()
        if not c:
            continue
        # Determine semantic from first keyword
        kw = re.match(r'^([A-Z\s]+)\b', c)
        keyword = kw.group(1).strip() if kw else "STEP"
        semantic = keyword.lower()
        steps.append({"cypher": c, "semantic": semantic})
    return steps


def decompose(protocol_id):
    """Decompose a protocol's fat atom into a chain of fine atoms."""
    # Get current first atom
    rows = ql(
        "MATCH (p:Protocol {node_id:$pid})-[:FIRST_ATOM]->(a:CypherAtom) "
        "RETURN a.node_id, a.cypher, a.semantic",
        {"pid": protocol_id},
    )
    if not rows:
        print(f"  {protocol_id}: no atom")
        return False

    fat_atom_id, fat_cypher, _ = rows[0]
    steps = split_cypher_steps(fat_cypher)
    if len(steps) <= 1:
        print(f"  {protocol_id}: single step ({len(fat_cypher)} chars), leave as-is")
        # Still add a semantic if missing
        return False

    print(f"  {protocol_id}: splitting into {len(steps)} atoms")

    # Create fine atoms
    atom_ids = []
    for i, step in enumerate(steps):
        atom_id = f"{fat_atom_id}-step{i}"
        q(
            "MERGE (a:CypherAtom {node_id:$aid}) "
            "SET a.cypher=$c, a.semantic=$sem, a.project='system', a.updated_at=datetime()",
            {"aid": atom_id, "c": step["cypher"], "sem": step["semantic"]},
        )
        atom_ids.append(atom_id)

    # Link chain: step0 -> step1 -> step2
    for i in range(len(atom_ids) - 1):
        q(
            "MATCH (a1:CypherAtom {node_id:$a1}) "
            "MATCH (a2:CypherAtom {node_id:$a2}) "
            "MERGE (a1)-[:FOLLOWS {decay_protected:true}]->(a2)",
            {"a1": atom_ids[i], "a2": atom_ids[i + 1]},
        )

    # Repoint protocol: remove old FIRST_ATOM, link to step0
    q(
        "MATCH (p:Protocol {node_id:$pid})-[r:FIRST_ATOM]->(old) "
        "MATCH (s0:CypherAtom {node_id:$s0}) "
        "DELETE r "
        "MERGE (p)-[:FIRST_ATOM {decay_protected:true}]->(s0)",
        {"pid": protocol_id, "s0": atom_ids[0]},
    )

    return True


def main():
    protocols = sys.argv[1:] or [
        p[0] for p in ql(
            "MATCH (p:Protocol) WHERE p.enabled=true RETURN p.node_id ORDER BY p.node_id"
        )
    ]
    print(f"=== Decomposing {len(protocols)} protocols ===")
    for pid in protocols:
        if not pid.startswith("protocol-"):
            pid = f"protocol-{pid}"
        decompose(pid)
    print("=== Complete ===")


if __name__ == "__main__":
    main()
