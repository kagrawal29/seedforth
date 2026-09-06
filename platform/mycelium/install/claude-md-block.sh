#!/usr/bin/env bash
# claude-md-block.sh — CLAUDE.md directives for maverick CLI integration
# This block teaches teammate Claude Code sessions when + how to reach for the maverick CLI.
# Sourced by install.sh to inject into ~/.claude/CLAUDE.md (idempotent via markers).

cat <<'BLOCK'
<!-- MAVERICK_BLOCK_START -->
# Maverick — Graph-Native Reasoning

You have access to the team's living knowledge graph via the `maverick` CLI. Use it for queries, not external research.

## When to invoke

| Trigger | Cue | Action |
|---------|-----|--------|
| "Did the team decide on X?" | decision / precedent / rule | `maverick ask "has the team decided on X"` |
| "What's the pattern for Y?" | idiom / convention / design | `maverick ask "pattern for Y"` |
| "Who owns Z?" | ownership / responsibility | `maverick ask "who owns Z"` |
| "Is X blocked?" | dependencies / blockers | `maverick ask "is X blocked"` |
| "How do I contribute?" | contributor onboarding | `maverick ask "how do I contribute"` |
| Verifying code against team norms | compliance / invariants | `maverick --target maverick-dev shell "MATCH (inv:Invariant) WHERE inv.topic = 'code-style' RETURN inv.rule"` |

## Portal to the graph

**Read-only by default.** The CLI is pre-approved for `ask` and `shell MATCH/RETURN` queries. No setup needed — it works in your session immediately after `install.sh`.

```bash
# Fastest: semantic search
maverick ask "has the team decided on Cypher patterns"

# Explicit: raw Cypher (read-only)
maverick --target maverick-dev shell "MATCH (p:Protocol) RETURN p.title LIMIT 5"

# List targets
maverick targets

# Check status
maverick status
```

## Hard rule: no direct writes

Never write to the graph directly. All mutations flow through:
1. Edit a `.cypher` file under `graph/protocols/` or `graph/knowledge/`
2. PR it to the repo
3. Merge triggers autodeploy → graph updated

If you see a `:DriftEvent` node (someone wrote directly), report it immediately. The graph heals on the next cycle, but the pattern must stop.

## No setup required

`install.sh` configures targets for you:
- `maverick-dev` — team sandbox, always live
- `maverick-prod` — canonical state
- `maverick-local` — your laptop (if you `maverick local bootstrap`)

Just run it. No `GRAPHQL_URL`, no API keys, no manual Neo4j install.
<!-- MAVERICK_BLOCK_END -->
BLOCK
