#!/usr/bin/env python3
"""
Patch .mcp.json to add the Asgard Graph MCP server.

Reads existing .mcp.json from stdin, adds/updates the asgard-graph
server entry, preserves all other MCP servers. Outputs merged JSON.

Per-person auth:
    Each team member should have their own token (generated via
    `python3 scripts/asgard-mcp-server.py --generate-tokens /app/tokens.yaml`).
    Set ASGARD_GRAPH_TOKEN to the person's individual token, or
    use ASGARD_PERSON_TOKEN if both admin and person tokens are set.

Usage:
    echo '{}' | python3 scripts/patch-mcp-config.py
    cat .mcp.json | python3 scripts/patch-mcp-config.py
    echo '{"mcpServers": {"other": {...}}}' | python3 scripts/patch-mcp-config.py

    # With per-person token:
    ASGARD_PERSON_TOKEN=<your-token> cat .mcp.json | python3 scripts/patch-mcp-config.py
"""

import json
import os
import sys

# Read config from environment or defaults
ASGARD_GRAPH_HOST = os.environ.get("ASGARD_MCP_HOST", "5.78.206.137")
ASGARD_GRAPH_PORT = os.environ.get("ASGARD_MCP_PORT", "6381")
ASGARD_GRAPH_URL = os.environ.get(
    "ASGARD_GRAPH_URL", f"http://{ASGARD_GRAPH_HOST}:{ASGARD_GRAPH_PORT}/mcp"
)
# Per-person token takes priority over admin token
ASGARD_GRAPH_TOKEN = os.environ.get("ASGARD_PERSON_TOKEN", "") or os.environ.get("ASGARD_GRAPH_TOKEN", "")

# Read existing config from stdin
try:
    content = sys.stdin.read().strip()
    if not content:
        existing = {}
    else:
        existing = json.loads(content)
except (json.JSONDecodeError, Exception):
    existing = {}

# Ensure mcpServers key exists
if "mcpServers" not in existing:
    existing["mcpServers"] = {}

# Add/update asgard-graph entry
# Token embedded in URL as query param — Claude Code .mcp.json schema
# doesn't support headers on SSE servers (see VC-AI-Assoicate#9)
url = ASGARD_GRAPH_URL
if ASGARD_GRAPH_TOKEN:
    url = f"{ASGARD_GRAPH_URL}?token={ASGARD_GRAPH_TOKEN}"

asgard_config = {
    "type": "http",
    "url": url,
}

existing["mcpServers"]["asgard-graph"] = asgard_config

# Remove old "asgard" entry if it exists (renamed to asgard-graph)
existing["mcpServers"].pop("asgard", None)

# Output merged config
print(json.dumps(existing, indent=2))
