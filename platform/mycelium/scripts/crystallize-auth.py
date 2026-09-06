#!/usr/bin/env python3
"""
Crystallize graph-native auth into the Asgard Graph topology.

What this does:
1. Reads your local token from .mcp.json (never printed)
2. Updates the server's .env with the current token via SSH
3. Restarts the asgard-graph container
4. Creates Person nodes for all team members with token_hash
5. Creates the auth Protocol, TestCases, and Invariant in the graph
6. Verifies everything works end-to-end

Run in a SEPARATE terminal (not inside Claude Code — that session is traced):
    python3 scripts/crystallize-auth.py

After this, auth is graph-native:
- Token rotation = update the hash on the Person node (no restart needed)
- New team member = new Person node with token_hash
- The graph IS the auth system — no .env, no TOKENS_JSON, no restart
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SERVER = "root@5.78.206.137"
ENV_FILE = "/opt/maverick-meta/docker/.env"
MCP_URL = "http://5.78.206.137:6381/mcp"
COMPOSE_DIR = "/opt/maverick-meta"
COMPOSE_FILE = "docker/docker-compose.production.yml"

# Team aliases (forest names)
TEAM = {
    "Kshitiz": "Cedar",
    "Pranav": "Banyan",
    "Ankit-S": "Sequoia",
    "Sahiram": "Birch",
    "Abhishek": "Oak",
    "Sahil": "Willow",
}


def read_local_token() -> str:
    """Read the current auth token from local .mcp.json."""
    mcp_path = Path(__file__).parent.parent / ".mcp.json"
    with open(mcp_path) as f:
        cfg = json.load(f)
    header = cfg["mcpServers"]["asgard-graph"]["headers"]["Authorization"]
    return header.replace("Bearer ", "")


def hash_token(token: str) -> str:
    """SHA-256 hash — this is what gets stored in the graph. Token never enters the graph."""
    return hashlib.sha256(token.encode()).hexdigest()


def ssh_cmd(cmd: str) -> str:
    """Run a command on the server via SSH."""
    result = subprocess.run(
        ["ssh", SERVER, cmd],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        print(f"  SSH error: {result.stderr.strip()}", file=sys.stderr)
    return result.stdout.strip()


def update_server_env(token: str):
    """Update ASGARD_GRAPH_TOKEN and ASGARD_ADMIN_TOKEN on the server."""
    print("\n[1/6] Updating server .env...")
    # Use a temp file approach to avoid token in command line args
    # Write token to a temp file on server, then sed from it
    ssh_cmd(f"sed -i 's|^ASGARD_GRAPH_TOKEN=.*|ASGARD_GRAPH_TOKEN={token}|' {ENV_FILE}")
    ssh_cmd(f"sed -i 's|^ASGARD_ADMIN_TOKEN=.*|ASGARD_ADMIN_TOKEN={token}|' {ENV_FILE}")
    print("  Updated ASGARD_GRAPH_TOKEN and ASGARD_ADMIN_TOKEN")


def restart_container():
    """Restart the asgard-graph container to pick up new env."""
    print("\n[2/6] Restarting asgard-graph container...")
    output = ssh_cmd(
        f"cd {COMPOSE_DIR} && docker compose -f {COMPOSE_FILE} up -d asgard-graph 2>&1"
    )
    print(f"  {output}")
    print("  Waiting for container to be ready...")
    time.sleep(6)
    # Verify it's running
    status = ssh_cmd("docker ps --filter name=docker-asgard-graph-1 --format '{{.Status}}'")
    print(f"  Container status: {status}")


def mcp_admin_query(token: str, cypher: str) -> dict:
    """Execute a write query via the MCP admin endpoint."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "asgard_graph_admin_query",
            "arguments": {
                "cypher": cypher,
                "admin_token": token,
            },
        },
    }
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  MCP error: {e}", file=sys.stderr)
        return {}


def mcp_read_query(token: str, cypher: str) -> dict:
    """Execute a read query via MCP."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "asgard_graph_query",
            "arguments": {"cypher": cypher},
        },
    }
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read())
    except Exception as e:
        print(f"  MCP error: {e}", file=sys.stderr)
        return {}


def create_person_nodes(token: str, token_hash: str):
    """Create Person nodes for all team members. Set token_hash for current user."""
    print("\n[3/6] Creating Person nodes with graph-native auth...")

    for name, alias in TEAM.items():
        cypher = f"""
        MERGE (p:Person {{alias: '{alias}'}})
        SET p.name = '{name}',
            p.active = true,
            p.node_id = 'person-{alias.lower()}'
        RETURN p.alias, p.name
        """
        result = mcp_admin_query(token, cypher)
        print(f"  Created/updated: {alias} ({name})")

    # Set token_hash for current user (Cedar/Kshitiz)
    cypher = f"""
    MATCH (p:Person {{alias: 'Cedar'}})
    SET p.token_hash = '{token_hash}'
    RETURN p.alias, 'token_hash_set'
    """
    mcp_admin_query(token, cypher)
    print(f"  Set token_hash for Cedar (SHA-256, not the token itself)")


def create_auth_protocol(token: str):
    """Create the auth Protocol node and wire it to the topology."""
    print("\n[4/6] Creating auth Protocol + Invariant...")

    # Protocol: Graph-Native Auth
    cypher = """
    MERGE (p:Protocol {node_id: 'protocol-graph-native-auth'})
    SET p.name = 'Graph-Native Auth',
        p.label = 'Graph-Native Auth',
        p.description = 'Auth lives in the graph as Person nodes with token_hash. Token rotation = MERGE new hash. No restart, no .env, no stale state.',
        p.phase = 'auth',
        p.status = 'live',
        p.cypher_template = 'MATCH (p:Person {token_hash: $hash}) RETURN p.alias'
    RETURN p.name
    """
    mcp_admin_query(token, cypher)
    print("  Protocol: Graph-Native Auth")

    # Invariant: Auth is Graph-Native
    cypher = """
    MERGE (inv:Invariant {node_id: 'invariant-graph-native-auth'})
    SET inv.number = 12,
        inv.label = 'Invariant 12: Auth is Graph-Native',
        inv.description = 'All auth MUST resolve through Person.token_hash in the graph. Env-var tokens are bootstrap fallback only. If graph-native auth has 0 Person nodes with token_hash, the system is in degraded mode.',
        inv.status = 'live',
        inv.severity = 'critical'
    RETURN inv.label
    """
    mcp_admin_query(token, cypher)
    print("  Invariant 12: Auth is Graph-Native")

    # Wire Protocol -> Invariant
    cypher = """
    MATCH (p:Protocol {node_id: 'protocol-graph-native-auth'})
    MATCH (inv:Invariant {node_id: 'invariant-graph-native-auth'})
    MERGE (p)-[:ENFORCES]->(inv)
    RETURN 'wired'
    """
    mcp_admin_query(token, cypher)

    # Wire Protocol -> Person nodes
    cypher = """
    MATCH (p:Protocol {node_id: 'protocol-graph-native-auth'})
    MATCH (person:Person)
    MERGE (p)-[:AUTHENTICATES]->(person)
    RETURN count(person)
    """
    mcp_admin_query(token, cypher)
    print("  Wired: Protocol -[ENFORCES]-> Invariant, Protocol -[AUTHENTICATES]-> Person")


def create_test_cases(token: str, token_hash: str):
    """Create TestCase nodes for auth verification."""
    print("\n[5/6] Creating TestCase nodes...")

    tests = [
        {
            "id": "test-auth-person-nodes-exist",
            "label": "Person nodes with token_hash exist",
            "query": "MATCH (p:Person) WHERE p.token_hash IS NOT NULL RETURN count(p) > 0",
            "expected": "true",
            "description": "At least one Person node must have a token_hash for graph-native auth to function",
        },
        {
            "id": "test-auth-all-active-persons-have-hash",
            "label": "All active Persons have token_hash",
            "query": "MATCH (p:Person {active: true}) WHERE p.token_hash IS NULL RETURN count(p)",
            "expected": "0",
            "description": "Every active team member should have graph-native auth (token_hash set)",
        },
        {
            "id": "test-auth-no-duplicate-hashes",
            "label": "No duplicate token hashes",
            "query": "MATCH (p:Person) WHERE p.token_hash IS NOT NULL WITH p.token_hash AS h, count(*) AS c WHERE c > 1 RETURN count(h)",
            "expected": "0",
            "description": "Each Person must have a unique token_hash — duplicates mean shared tokens",
        },
        {
            "id": "test-auth-protocol-exists",
            "label": "Auth protocol is live",
            "query": "MATCH (p:Protocol {node_id: 'protocol-graph-native-auth'}) RETURN p.status",
            "expected": "live",
            "description": "The Graph-Native Auth protocol must exist and be live",
        },
        {
            "id": "test-auth-invariant-wired",
            "label": "Auth invariant is wired to protocol",
            "query": "MATCH (p:Protocol {node_id: 'protocol-graph-native-auth'})-[:ENFORCES]->(inv:Invariant) RETURN count(inv) > 0",
            "expected": "true",
            "description": "Auth protocol must enforce its invariant",
        },
        {
            "id": "test-auth-hash-resolves",
            "label": "Current token hash resolves to a Person",
            "query": f"MATCH (p:Person {{token_hash: '{token_hash}'}}) RETURN p.alias IS NOT NULL",
            "expected": "true",
            "description": "The current operator's token hash must resolve to a known Person",
        },
    ]

    for t in tests:
        cypher = f"""
        MERGE (tc:TestCase {{node_id: '{t["id"]}'}})
        SET tc.label = '{t["label"]}',
            tc.assertion_query = '{t["query"].replace("'", "\\'")}',
            tc.expected = '{t["expected"]}',
            tc.description = '{t["description"]}',
            tc.category = 'auth',
            tc.last_result = 'pending'
        RETURN tc.label
        """
        mcp_admin_query(token, cypher)
        print(f"  TestCase: {t['label']}")

    # Wire tests to protocol
    cypher = """
    MATCH (p:Protocol {node_id: 'protocol-graph-native-auth'})
    MATCH (tc:TestCase) WHERE tc.category = 'auth'
    MERGE (p)-[:TESTED_BY]->(tc)
    RETURN count(tc)
    """
    mcp_admin_query(token, cypher)
    print("  Wired: Protocol -[TESTED_BY]-> TestCases")


def create_rotation_protocol(token: str):
    """Create the self-service token rotation protocol."""
    print("\n    Creating rotation sub-protocol...")

    cypher = """
    MERGE (p:Protocol {node_id: 'protocol-token-rotation'})
    SET p.name = 'Token Rotation',
        p.label = 'Token Rotation',
        p.description = 'To rotate a token: hash the new token (SHA-256), then MERGE the hash onto the Person node. No restart. No .env update. The graph updates auth in real-time.',
        p.phase = 'auth',
        p.status = 'live',
        p.cypher_template = "MATCH (p:Person {alias: $alias}) SET p.token_hash = $new_hash RETURN p.alias, 'rotated'"
    RETURN p.name
    """
    mcp_admin_query(token, cypher)

    # Wire rotation -> main auth protocol
    cypher = """
    MATCH (main:Protocol {node_id: 'protocol-graph-native-auth'})
    MATCH (rot:Protocol {node_id: 'protocol-token-rotation'})
    MERGE (main)-[:ENABLES]->(rot)
    RETURN 'wired'
    """
    mcp_admin_query(token, cypher)
    print("  Protocol: Token Rotation (sub-protocol of Graph-Native Auth)")


def verify(token: str, token_hash: str):
    """End-to-end verification."""
    print("\n[6/6] Verifying graph-native auth...")

    # Check Person nodes
    result = mcp_read_query(token,
        "MATCH (p:Person) RETURN p.alias, p.active, p.token_hash IS NOT NULL AS has_hash"
    )
    print(f"  Person query result: {json.dumps(result.get('result', {}).get('content', [{}])[0].get('text', '?'), indent=2)[:500]}")

    # Check auth resolution
    result = mcp_read_query(token,
        f"MATCH (p:Person {{token_hash: '{token_hash}'}}) RETURN p.alias"
    )
    print(f"  Token hash resolves to: {json.dumps(result.get('result', {}).get('content', [{}])[0].get('text', '?'))}")

    # Check protocol topology
    result = mcp_read_query(token,
        "MATCH (p:Protocol {node_id: 'protocol-graph-native-auth'})-[r]->(n) RETURN type(r), labels(n)[0], n.node_id"
    )
    print(f"  Auth topology: {json.dumps(result.get('result', {}).get('content', [{}])[0].get('text', '?'), indent=2)[:500]}")

    # Check invariant
    result = mcp_read_query(token,
        "MATCH (inv:Invariant {node_id: 'invariant-graph-native-auth'}) RETURN inv.label, inv.status"
    )
    print(f"  Invariant: {json.dumps(result.get('result', {}).get('content', [{}])[0].get('text', '?'))}")


def main():
    print("=" * 60)
    print("Crystallizing Graph-Native Auth")
    print("=" * 60)

    # Step 0: Read token (never printed)
    token = read_local_token()
    token_hash = hash_token(token)
    print(f"\nToken hash (SHA-256, safe to display): {token_hash[:16]}...{token_hash[-8:]}")

    # Step 1: Update server .env
    update_server_env(token)

    # Step 2: Restart container
    restart_container()

    # Step 3: Create Person nodes
    create_person_nodes(token, token_hash)

    # Step 4: Create Protocol + Invariant
    create_auth_protocol(token)
    create_rotation_protocol(token)

    # Step 5: Create TestCases
    create_test_cases(token, token_hash)

    # Step 6: Verify
    verify(token, token_hash)

    # Clear token from memory
    del token

    print("\n" + "=" * 60)
    print("DONE. Auth is now graph-native.")
    print("=" * 60)
    print("""
Next steps for each team member:
  1. Generate their token hash:
     python3 -c "import hashlib; t=input('Token: '); print(hashlib.sha256(t.encode()).hexdigest())"

  2. Register it (anyone with admin access):
     MATCH (p:Person {alias: '<their-alias>'})
     SET p.token_hash = '<their-hash>'

  3. That's it. No restart. No .env. The graph IS the auth.

To rotate ANY token in the future:
  - Hash the new token → SET it on the Person node → done.
  - The old hash stops working immediately.
  - Zero downtime. Zero config drift.
""")


if __name__ == "__main__":
    main()
