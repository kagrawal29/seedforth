# Team Knowledge Base (Flat File Fallback)

When the Asgard Graph MCP tools are available, use those instead — they provide live access to the same knowledge with full topology, demand signals, and cross-person connections. See the `asgard-graph` rule.

This flat file knowledge base at `.claude/knowledge/` is the fallback for when MCP is unavailable.

## How to Search

1. Read `.claude/knowledge/community-map.md` — find the community matching the topic
2. Read the linked entries in that community
3. For keyword lookups, grep `.claude/knowledge/search-index.md`
4. Check "Open Questions" for unresolved items in the same area

## Entry Types

- **[H] Decisions** — settled, do not re-explore
- **Active explorations** — someone is working on this, coordinate before deciding
- **Warnings** — known problems to avoid
- **Procedures** — tested workflows with pitfalls

## Available Skills

- `/architecture-validation` — validate architecture decisions with research agents
- `/fix-workflow` — structured fix workflow (3 tracks, NO-SKIP enforcement, agent review)
- `/spec-to-ship` — feature pipeline (6 phases, phase gates, TDD, 2 human touchpoints)
