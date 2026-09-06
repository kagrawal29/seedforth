---
id: rule-hook-pattern-matching
category: tool-configs
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: low
source: Sahil LangSmith trace 2026-04-10T21:17 — block-playwright.sh blocking claude-in-chrome unexpectedly
tags: [hooks, playwright, browser, pattern-matching, block-playwright, claude-code]
relevant-when: writing Claude Code hook scripts that match on tool names, debugging hooks that block unexpected tools
related: [tool-config-auto-sync-hooks, tool-config-hooks-data-capture]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Write Hook Matchers Precisely to Avoid Blocking Adjacent Tools

## What
Claude Code hook scripts that match on partial strings (e.g., "playwright") will also block other tools whose names contain that substring. A `block-playwright.sh` hook intended for Playwright test runs also blocks `claude-in-chrome` because the matching logic captures "chrome" as browser-related.

## Why This Matters
Hook mismatch silently blocks tool calls — the user sees a refusal without understanding why. In enrichment workflows where the hook is designed for one specific tool type, an overly broad match creates debugging confusion.

## How to Write Precise Hooks
1. **Match on exact tool names**, not partial strings: `[[ "$tool" == "playwright" ]]` not `[[ "$tool" == *"playwright"* ]]`
2. **Log what the hook is blocking** — write to stderr so the user can see what triggered the block
3. **Scope hooks narrowly**: if blocking browser automation, name specific tools rather than matching on "browser" or "chrome"
4. **Use the `!` prefix** in Claude Code to bypass hooks for legitimate browser use in development sessions

## Workaround
```bash
# User can bypass any hook by prefixing the command with !
!open maverick-competitive-graph.html
```
