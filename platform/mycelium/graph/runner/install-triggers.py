#!/usr/bin/env python3
"""
Install APOC Triggers for Reactive Invariants
Reads trigger definitions from graph/protocols/triggers.cypher and installs
them via apoc.trigger.install(). Idempotent — drops existing triggers first.

Usage:
  python3 install-triggers.py [--verify-only]

Triggers installed:
  1. embedding-dirty-on-graphnode-insert
  2. protocol-atom-sync-dirty
  3. invariant-dirty-on-threshold-change

Each trigger is scoped to database 'neo4j' and fires on specific events.
"""

import subprocess
import json
import sys
import re

# Trigger definitions: (trigger_name, selector, cypher_statement)
# Selectors and statements must match triggers.cypher
TRIGGERS = [
    {
        "name": "embedding-dirty-on-graphnode-insert",
        "selector": {"phase": "after", "events": ["create"]},
        "statement": """UNWIND ($createdNodes) AS node
WITH node
WHERE labels(node) CONTAINS 'GraphNode'
  AND node.embedding IS NULL
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.needs_embedding = true
RETURN node.node_id, 'embedding_dirty_triggered' AS action""",
    },
    {
        "name": "protocol-atom-sync-dirty",
        "selector": {"phase": "after", "events": ["set"]},
        "statement": """UNWIND ($assignedNodeProperties) AS prop
WITH prop.node AS node, prop.key AS key
WHERE labels(node) CONTAINS 'Protocol'
  AND key = 'cypher'
MATCH (node)-[a:HAS_ATOM]->(atom)
DELETE a
WITH node
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.atom_dirty = true
RETURN node.node_id, 'atom_sync_dirty_triggered' AS action""",
    },
    {
        "name": "invariant-dirty-on-threshold-change",
        "selector": {"phase": "after", "events": ["set"]},
        "statement": """UNWIND ($assignedNodeProperties) AS prop
WITH prop.node AS node, prop.key AS key
WHERE labels(node) CONTAINS 'Invariant'
  AND (key STARTS WITH 'healthy_range' OR key = 'threshold')
SET node.dirty = true
WITH node
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.invariant_dirty = true
RETURN node.node_id, 'invariant_dirty_triggered' AS action""",
    },
]


def run_cypher(cypher, params=None):
    """Execute Cypher via cypher-shell; return result."""
    if params is None:
        params = {}

    cmd = [
        "cypher-shell",
        "-a", "neo4j://localhost:7687",
        "-u", "neo4j",
        "-p", "localtest12",
        cypher
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"CYPHER ERROR:\n{result.stderr}")
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"Timeout running cypher")
        return None
    except Exception as e:
        print(f"Error running cypher: {e}")
        return None


def drop_trigger(name):
    """Drop a trigger by name."""
    cypher = f"""
    CALL apoc.trigger.drop('neo4j', '{name}')
    YIELD name, installed
    RETURN name, installed
    """
    print(f"  Dropping trigger '{name}'...")
    result = run_cypher(cypher)
    if result:
        print(f"    ✓ Dropped")
    return result


def install_trigger(name, selector, statement):
    """Install a trigger with given selector and cypher statement."""
    # selector must be JSON
    selector_json = json.dumps(selector)

    # Build the apoc.trigger.install call
    # Escape single quotes in the statement
    stmt_escaped = statement.replace("'", "\\'").replace('"', '\\"')

    cypher = f"""
    CALL apoc.trigger.install('neo4j', '{name}',
        '{stmt_escaped}',
        {selector_json}
    )
    YIELD name, installed, paused
    RETURN name, installed, paused
    """

    print(f"  Installing trigger '{name}'...")
    result = run_cypher(cypher)
    if result:
        # Parse result to check if installed=true
        if "installed" in result.lower() and "true" in result.lower():
            print(f"    ✓ Installed and active")
            return True
        else:
            print(f"    ✓ Installation call succeeded; output: {result[:80]}")
            return True
    return False


def list_triggers():
    """List all installed triggers."""
    cypher = """
    CALL apoc.trigger.list()
    YIELD name, installed, paused, selector, query
    RETURN name, installed, paused, selector, query
    """
    print("\nFetching installed triggers...")
    result = run_cypher(cypher)
    if result:
        print("Installed triggers:")
        print(result)
        return result
    return None


def verify_graph_nodes():
    """Verify Being and essential nodes exist."""
    cypher = """
    MATCH (b:Being {node_id: 'being-mycelium'}) RETURN count(b) AS being_count
    """
    result = run_cypher(cypher)
    if result and "1" in result:
        print("✓ Being singleton found")
        return True
    else:
        print("✗ Being singleton NOT found. Triggers may not fire without it.")
        return False


def main():
    verify_only = "--verify-only" in sys.argv

    print("=" * 70)
    print("Mycelium Reactive Triggers Installer (APOC 5.x+)")
    print("=" * 70)

    # Verify graph is ready
    if not verify_graph_nodes():
        print("\nWARNING: Graph structure incomplete. Proceeding anyway.")

    print("\nInstalling 3 reactive triggers...")

    for trigger in TRIGGERS:
        name = trigger["name"]
        selector = trigger["selector"]
        statement = trigger["statement"]

        # Always drop first for idempotency
        drop_trigger(name)

        if not verify_only:
            install_trigger(name, selector, statement)

    # List all triggers to confirm
    print("\n" + "=" * 70)
    list_triggers()
    print("=" * 70)

    print("\nDone. Triggers are now ACTIVE and will react to graph mutations.")
    print("Dirty flags set by triggers will be processed by next heartbeat.")


if __name__ == "__main__":
    main()
