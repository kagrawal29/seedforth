#!/usr/bin/env python3
"""
atomize-protocol — parse a .cypher file into :CypherAtom nodes.

Decomposition strategy (coarse, statement-level):

  - Comments (lines starting with //) are collected as the semantic hint
    for the NEXT atom until a non-comment line is seen.
  - Blank lines are separators but don't split atoms.
  - Everything else is concatenated until we hit a trailing semicolon;
    that accumulated text becomes one :CypherAtom.

Each atom is written as:

  MERGE (a:CypherAtom {node_id: 'atom-<protocol-slug>-<i>'})
  SET a.cypher = <statement>,
      a.semantic = <preceding-comment-block>,
      a.atom_order = <i>,
      a.source_protocol = <protocol_node_id>,
      a.category = 'auto-statement',
      a.fire_count = 0,
      a.file_type = 'cypher-atom'

And :FOLLOWS edges wire atom_i to atom_{i+1}. The Protocol gets a
:FIRST_ATOM edge to atom_1.

Usage:
  atomize-protocol.py <protocol_node_id> <cypher_file>

Example:
  atomize-protocol.py protocol-merkle-properties graph/protocols/merkle-properties.cypher
"""

import os
import re
import sys
from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")


def parse_statements(text):
    """Yield (semantic_comment, cypher_statement) tuples from a cypher file."""
    lines = text.splitlines()
    pending_comment = []
    pending_cypher = []

    for raw in lines:
        line = raw.rstrip()
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("--"):
            comment_text = stripped.lstrip("/-").strip()
            if not pending_cypher:
                pending_comment.append(comment_text)
            continue
        if not stripped:
            continue

        pending_cypher.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(pending_cypher).rstrip(";").strip()
            semantic = "\n".join(pending_comment).strip()
            yield semantic, statement
            pending_cypher = []
            pending_comment = []

    # Trailing cypher without a semicolon (e.g. bare RETURN)
    if pending_cypher:
        statement = "\n".join(pending_cypher).rstrip(";").strip()
        semantic = "\n".join(pending_comment).strip()
        yield semantic, statement


def slugify(protocol_id):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", protocol_id.replace("protocol-", ""))
    return slug.strip("-").lower()


def main():
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <protocol_node_id> <cypher_file>", file=sys.stderr)
        return 2

    protocol_id, cypher_file = sys.argv[1], sys.argv[2]
    if not os.path.isfile(cypher_file):
        print(f"file not found: {cypher_file}", file=sys.stderr)
        return 2

    with open(cypher_file, "r", encoding="utf-8") as f:
        text = f.read()

    statements = list(parse_statements(text))
    if not statements:
        print(f"no statements parsed from {cypher_file}", file=sys.stderr)
        return 1

    slug = slugify(protocol_id)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        # First drop any previously-auto-generated atoms for this protocol so
        # re-running produces a clean graph (avoid duplicating atoms with
        # slightly different atom_order on edits).
        session.run(
            "MATCH (a:CypherAtom {source_protocol: $p, category: 'auto-statement'}) "
            "DETACH DELETE a",
            p=protocol_id,
        )

        prev_atom_id = None
        for idx, (semantic, statement) in enumerate(statements, start=1):
            atom_id = f"atom-{slug}-{idx:02d}"
            session.run(
                """
                MERGE (a:CypherAtom {node_id: $atom_id})
                SET a.cypher = $cypher,
                    a.semantic = $semantic,
                    a.atom_order = $order,
                    a.source_protocol = $protocol_id,
                    a.category = 'auto-statement',
                    a.fire_count = 0,
                    a.file_type = 'cypher-atom',
                    a.first_seen = toString(datetime())
                """,
                atom_id=atom_id,
                cypher=statement,
                semantic=semantic or "(no description)",
                order=idx,
                protocol_id=protocol_id,
            )
            if prev_atom_id is not None:
                session.run(
                    """
                    MATCH (a1:CypherAtom {node_id: $prev})
                    MATCH (a2:CypherAtom {node_id: $curr})
                    MERGE (a1)-[:FOLLOWS]->(a2)
                    """,
                    prev=prev_atom_id,
                    curr=atom_id,
                )
            prev_atom_id = atom_id

        # Wire the protocol to its first atom
        first_atom_id = f"atom-{slug}-01"
        session.run(
            """
            MATCH (p:Protocol {node_id: $p})
            MATCH (first:CypherAtom {node_id: $first})
            MERGE (p)-[:FIRST_ATOM]->(first)
            """,
            p=protocol_id,
            first=first_atom_id,
        )

    driver.close()
    print(f"{protocol_id}: {len(statements)} atoms wired ({first_atom_id} ... atom-{slug}-{len(statements):02d})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
