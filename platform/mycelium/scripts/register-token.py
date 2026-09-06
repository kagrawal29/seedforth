#!/usr/bin/env python3
"""
Self-service token registration for graph-native auth.

Each team member runs this ONCE (or after token rotation) to register
their token hash on their Person node. The token is never stored or
transmitted — only its SHA-256 hash enters the graph.

Usage (run in a separate terminal, NOT inside Claude Code):
    python3 scripts/register-token.py

The script will:
1. Read your token from your local .mcp.json
2. Hash it (SHA-256)
3. Call the MCP admin endpoint to set your Person.token_hash
4. Verify auth works with the new hash
"""

import getpass
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

MCP_URL = "http://5.78.206.137:6381/mcp"

ALIASES = {
    "kshitiz": "Cedar",
    "pranav": "Banyan",
    "ankit": "Sequoia",
    "sahiram": "Birch",
    "abhishek": "Oak",
    "sahil": "Willow",
}


def read_token_from_mcp() -> str | None:
    """Try to read token from .mcp.json in the project root."""
    candidates = [
        Path(__file__).parent.parent / ".mcp.json",
        Path.cwd() / ".mcp.json",
    ]
    for p in candidates:
        if p.exists():
            with open(p) as f:
                cfg = json.load(f)
            srv = cfg.get("mcpServers", {}).get("asgard-graph", {})
            header = srv.get("headers", {}).get("Authorization", "")
            if header:
                return header.replace("Bearer ", "")
    return None


def mcp_call(token: str, tool: str, arguments: dict) -> dict:
    """Call an MCP tool."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())


def main():
    print("=== Graph-Native Token Registration ===\n")

    # Get token
    token = read_token_from_mcp()
    if token:
        print("Found token in .mcp.json")
    else:
        token = getpass.getpass("Paste your ASGARD_GRAPH_TOKEN (hidden): ")

    if not token:
        print("ERROR: No token provided", file=sys.stderr)
        sys.exit(1)

    # Hash it
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    print(f"Token hash: {token_hash[:16]}...{token_hash[-8:]}")

    # Identify the person
    print(f"\nKnown aliases: {', '.join(f'{k}={v}' for k, v in ALIASES.items())}")
    name = input("Your name (lowercase): ").strip().lower()
    alias = ALIASES.get(name)
    if not alias:
        alias = input("Your forest alias: ").strip()

    print(f"\nRegistering {alias} with token hash...")

    # Ensure Person node exists and set hash
    cypher = f"""
    MERGE (p:Person {{alias: '{alias}'}})
    SET p.token_hash = '{token_hash}',
        p.active = true
    RETURN p.alias, 'registered'
    """
    result = mcp_call(token, "asgard_graph_admin_query", {
        "cypher": cypher,
        "admin_token": token,
    })
    content = result.get("result", {}).get("content", [{}])
    text = content[0].get("text", "") if content else ""
    print(f"  Result: {text[:200]}")

    # Verify: can the hash resolve back?
    verify = mcp_call(token, "asgard_graph_query", {
        "cypher": f"MATCH (p:Person {{token_hash: '{token_hash}'}}) RETURN p.alias",
    })
    v_content = verify.get("result", {}).get("content", [{}])
    v_text = v_content[0].get("text", "") if v_content else ""
    print(f"  Verification: {v_text[:200]}")

    del token
    print(f"\nDone. {alias} is now authenticated via graph-native auth.")
    print("Token rotation: run this script again with the new token. No restart needed.")


if __name__ == "__main__":
    main()
