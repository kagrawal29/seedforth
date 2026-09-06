---
id: tool-config-hooks-data-capture
category: tool-configs
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: maverick-market-research .claude/settings.json — PostToolUse hook auto-saves Xpoz responses
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 6
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.00
  last_scored: 2026-04-09
tags: [hooks, post-tool-use, xpoz, mcp, data-capture, raw-data, audit-trail, python]
relevant-when: setting up data collection hooks, auto-saving API responses, building audit trails for MCP tools
related: [tool-config-auto-sync-hooks]
---

# Claude Code Hooks for Automatic Data Capture

## What
PostToolUse hook that auto-saves all MCP tool responses to disk, creating a complete audit trail before any LLM processing.

## Why
Decouples data collection from analysis. Prevents data loss from session crashes or context compaction. Raw data always available for reprocessing.

## Procedure
1. Create the hook script at `.claude/hooks/save-xpoz-response.py`:
   - Read stdin as JSON (contains `tool_name`, `tool_input`, `tool_output`)
   - Extract the response payload from `tool_output`
   - Build metadata dict: timestamp, tool name, input parameters
   - Save to `data/raw/xpoz_dumps/{YYYY-MM-DD}/{timestamp}_{tool_name}.json`
   - Ensure the script completes in <1s and is idempotent
2. Create the output directory: `mkdir -p data/raw/xpoz_dumps`
3. Add the hook to `.claude/settings.json`:
   ```json
   {
     "hooks": {
       "PostToolUse": [
         {
           "matcher": "mcp__xpoz-mcp__.*",
           "hooks": [
             {
               "type": "command",
               "command": "python3 .claude/hooks/save-xpoz-response.py"
             }
           ]
         }
       ]
     }
   }
   ```
4. Test: invoke any Xpoz MCP tool and check `data/raw/xpoz_dumps/` for the saved file
5. Adapt matcher regex for other MCP tools (e.g., `mcp__other-tool__.*`)

## Pitfalls
- What breaks: Matcher too broad (e.g., `.*`) captures non-MCP tools. Detection: unexpected files in dump dir. Fix: use specific regex like `mcp__xpoz-mcp__.*`.
- What breaks: Hook script crashes on malformed stdin. Detection: no files saved after tool calls. Fix: wrap JSON parsing in try/except, log errors to stderr.
- What breaks: Slow hook script blocks Claude Code. Detection: noticeable delay after every tool call. Fix: keep script under 1s; offload heavy work to async process.

## Verification
- [ ] After an MCP tool call, a new JSON file exists in `data/raw/xpoz_dumps/{today}/`
- [ ] File contains both raw response and metadata (timestamp, tool name, params)
- [ ] Non-matching tool calls (e.g., Bash, Read) do NOT trigger the hook

## Evidence
- 180 xpoz_dumps folders in maverick-market-research — every API call captured
- Custom `/coverage` command built on top of this captured data
