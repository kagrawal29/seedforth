---
id: architecture-mcp-streamable-http-auth
category: architecture
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: high
source: commits aa9d42df, e69e2888, 25590586 (maverick-meta + VC-AI-Assoicate + maverick-market-research 2026-04-11); issues #9, #15 closed
tags: [mcp, asgard-graph, security, auth, streamable-http, sse, headers, falkordb]
relevant-when: configuring MCP servers, connecting to Asgard Graph, setting up .mcp.json, securing API tokens
related: [architecture-tech-stack-completed, tool-config-auto-sync-hooks]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# MCP Config: Streamable HTTP Transport + Header Auth (SETTLED)

## What
The Asgard Graph MCP server connection uses **Streamable HTTP transport** with the auth token passed via `Authorization` header — NOT via URL query parameters and NOT via SSE transport. This configuration is deployed and working across all three repos.

## Why
Two bugs forced this evolution:

| Bug | Problem | Fix |
|-----|---------|-----|
| SSE transport + `headers` field | `.mcp.json` schema validation rejected `headers` field (Claude Code issue #9, #15) | Switched to Streamable HTTP transport which supports header auth natively |
| Token in URL | Token visible in server logs, LangSmith traces, and any proxy — secrets exposure (issue #48) | Move token to `Authorization` header — redacted at transport layer |

The fix required two commits per repo: initial add with SSE (rejected), then fix to Streamable HTTP.

## How to Configure
```json
{
  "mcpServers": {
    "asgard-graph": {
      "type": "http",
      "url": "http://5.78.206.137:3001/mcp",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

**Do NOT use:** `type: "sse"` — schema validation fails. Do NOT put token in URL.

## Applied To
- VC-AI-Assoicate (Kshitiz, commit e69e2888)
- maverick-market-research (Kshitiz, commit 25590586)
- maverick-meta (commit aa9d42df — moved from URL to header)
