---
id: pattern-graph-native-identity
category: patterns
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: medium
source: commit 0101de17 (CLAUDE.md becomes a thin bootstrap pointer to the graph — kagrawal29); issue #58 open (Identity as graph: CLAUDE.md and rules become thin pointers to graph topology); maverick-meta CLAUDE.md rewrite
tags: [graph-native, identity, claude-md, bootstrap, configuration, invariants, self-referential, mycelium]
relevant-when: updating CLAUDE.md or rules files, adding new invariants, designing system identity, onboarding to maverick-meta, debugging session context issues
related: [architecture-mcp-streamable-http-auth, architecture-cypher-native-pipeline]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Graph-Native Identity — Files Are Bootstrap Pointers, Graph Is the System

## What
The system's identity (who it is), operating rules (invariants), tests (TestCase nodes), and development plan (WorkItem nodes) live in the graph — not in files. Files like CLAUDE.md and `.claude/rules/*.md` are **thin bootstrap pointers** that tell the system how to connect to the graph and query itself.

This is the pattern established in commit 0101de17 and being evolved in open issue #58.

## Why
Files go stale. A CLAUDE.md written 3 weeks ago contains context that was accurate then. The graph is continuously updated by the heartbeat, dream round, and ingestion pipeline. By the time a new Claude session starts, the graph reflects the current system state — files don't.

Concrete problem this solves: Without graph-native identity, every session needs a long CLAUDE.md describing the current state. With graph-native identity, CLAUDE.md shrinks to: "You are Mycelium. Connect to the graph. Query yourself first." The graph holds everything else.

## The Bootstrap Sequence
1. Claude session starts, reads CLAUDE.md
2. CLAUDE.md tells Claude to connect via Asgard Graph MCP tools
3. Claude runs Session Start Protocol queries (ContextPointer, HealthCheck, TestCase, WorkItem, Invariant, Principle nodes)
4. Claude now has live, current system state — not a stale file snapshot
5. All subsequent work is grounded in graph topology, not file content

## What Lives Where

| Lives in graph | Lives in files (bootstrap only) |
|---|---|
| Invariants (enforced, numbered) | CLAUDE.md (connect + query instructions) |
| TestCase nodes (pass/fail state) | `.claude/rules/*.md` (operational patterns) |
| WorkItem nodes (dev plan, status) | `.mcp.json` (MCP server config) |
| Principle nodes (design philosophy) | `scripts/` (I/O glue, Python) |
| Person nodes (team, UUIDs) | `agents/` (SDK scripts) |
| ContextPointer (what's next) | — |

## Current State (as of 2026-04-11)
Issue #58 is open — full graph-native identity not yet complete. The CLAUDE.md was rewritten to be a thin pointer, but rules files still carry substantive content. The direction is toward all operational guidance living as graph nodes (Cypher queries as edge properties — issue #59), with files reduced to pure bootstrapping.

## Implications for Development
- When adding a new invariant: create an `Invariant` node in the graph, don't add it to CLAUDE.md
- When updating operating rules: consider whether this belongs in a graph node or a rule file
- Rule files are appropriate for patterns that must load before MCP connection is available (true bootstrap); everything else belongs in the graph
