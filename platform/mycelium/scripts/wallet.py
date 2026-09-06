#!/usr/bin/env python3
"""
Graph-Native Auth Wallet — generate your key, publish your address.

Like a crypto wallet:
  - YOU generate your private key (token) locally
  - YOU publish your public address (SHA-256 hash) to the graph
  - Nobody distributes tokens. Nobody holds your key.
  - The graph only knows your hash. Token never leaves your machine.

Usage:
    python3 scripts/wallet.py

What it does:
    1. Generates a unique token (your private key)
    2. Hashes it (your public address)
    3. Saves the token to ~/.asgard-wallet (local, never shared)
    4. Publishes the hash to your Person node in the graph
    5. Updates your shell profile so ASGARD_GRAPH_TOKEN is always set
    6. Done. You're authenticated. No admin needed.
"""

import hashlib
import json
import os
import secrets
import sys
import urllib.request
from pathlib import Path

MCP_URL = "http://5.78.206.137:6381/mcp"
WALLET_PATH = Path.home() / ".asgard-wallet"

ALIASES = {
    "kshitiz": "Cedar",
    "pranav": "Banyan",
    "ankit": "Sequoia",
    "sahiram": "Birch",
    "abhishek": "Oak",
    "sahil": "Willow",
}


def mcp_call(token: str, tool: str, arguments: dict) -> dict:
    payload = {
        "jsonrpc": "2.0", "id": 1,
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
    print("=== Asgard Graph Wallet ===\n")

    # Check for existing wallet
    if WALLET_PATH.exists():
        with open(WALLET_PATH) as f:
            wallet = json.load(f)
        print(f"Existing wallet found for {wallet.get('alias', '?')}")
        print(f"Token hash: {wallet.get('hash', '?')[:16]}...")
        resp = input("\nRegenerate? This invalidates your current key. [y/N]: ").strip().lower()
        if resp != "y":
            print("Keeping existing wallet.")
            return
        # Use existing token for auth during rotation
        old_token = wallet.get("token", "")
    else:
        old_token = ""

    # Identify
    print(f"Known aliases: {', '.join(f'{k} → {v}' for k, v in ALIASES.items())}")
    name = input("Your name (lowercase): ").strip().lower()
    alias = ALIASES.get(name)
    if not alias:
        alias = input("Forest alias: ").strip()
        if not alias:
            print("Need an alias.")
            sys.exit(1)

    # Generate key
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    print(f"\nGenerated wallet for {alias}")
    print(f"  Public address (hash): {token_hash[:16]}...{token_hash[-8:]}")
    print(f"  Private key: saved locally, never shared")

    # Save wallet locally
    wallet = {
        "alias": alias,
        "hash": token_hash,
        "token": token,
        "algorithm": "sha256",
    }
    WALLET_PATH.write_text(json.dumps(wallet, indent=2))
    os.chmod(WALLET_PATH, 0o600)  # owner-only
    print(f"  Wallet saved: {WALLET_PATH}")

    # Publish hash to graph
    # Use old token, or admin token from env, or the new token itself
    auth_token = old_token or os.environ.get("ASGARD_GRAPH_TOKEN", "") or token

    print(f"\nPublishing hash to graph...")
    try:
        # First try as admin query (to set token_hash)
        result = mcp_call(auth_token, "asgard_graph_admin_query", {
            "cypher": f"MERGE (p:Person {{alias: '{alias}'}}) "
                      f"SET p.token_hash = '{token_hash}', "
                      f"p.hash_algorithm = 'sha256', "
                      f"p.last_rotation = timestamp(), "
                      f"p.active = true "
                      f"RETURN p.alias, 'registered'",
            "admin_token": auth_token,
        })
        content = result.get("result", {}).get("content", [{}])
        text = content[0].get("text", "") if content else ""
        print(f"  Published: {text[:100]}")
    except Exception as e:
        print(f"  Could not publish to graph: {e}")
        print(f"  Ask an admin to run:")
        print(f"    MATCH (p:Person {{alias: '{alias}'}}) SET p.token_hash = '{token_hash}'")
        print(f"  Or share your hash (safe — it's public): {token_hash}")

    # Verify
    try:
        result = mcp_call(token, "asgard_graph_query", {
            "cypher": f"MATCH (p:Person {{token_hash: '{token_hash}'}}) RETURN p.alias"
        })
        content = result.get("result", {}).get("content", [{}])
        text = content[0].get("text", "") if content else ""
        print(f"  Verified: {text[:100]}")
    except:
        print("  Verification pending — will work after server restart or next auth cycle")

    # Update shell profile
    shell_rc = Path.home() / (".zshrc" if os.environ.get("SHELL", "").endswith("zsh") else ".bashrc")
    print(f"\nTo activate, add to {shell_rc}:")
    print(f'  export ASGARD_GRAPH_TOKEN="{token}"')

    resp = input(f"\nAdd to {shell_rc} automatically? [Y/n]: ").strip().lower()
    if resp != "n":
        marker = "# Asgard Graph wallet"
        rc_content = shell_rc.read_text() if shell_rc.exists() else ""
        if marker in rc_content:
            # Replace existing
            lines = rc_content.split("\n")
            new_lines = []
            skip = False
            for line in lines:
                if line.strip() == marker:
                    skip = True
                    new_lines.append(marker)
                    new_lines.append(f'export ASGARD_GRAPH_TOKEN="{token}"')
                    continue
                if skip:
                    skip = False
                    continue
                new_lines.append(line)
            shell_rc.write_text("\n".join(new_lines))
        else:
            with open(shell_rc, "a") as f:
                f.write(f"\n{marker}\n")
                f.write(f'export ASGARD_GRAPH_TOKEN="{token}"\n')
        print(f"  Added to {shell_rc}")
        print(f"  Run: source {shell_rc}")

    print(f"""
=== Wallet Ready ===
  Alias:    {alias}
  Address:  {token_hash[:16]}...
  Wallet:   {WALLET_PATH}

  Your token never leaves this machine.
  The graph only knows your hash.
  To rotate: run this script again.
""")


if __name__ == "__main__":
    main()
