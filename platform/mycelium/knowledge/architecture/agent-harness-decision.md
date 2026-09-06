---
id: architecture-agent-harness-decision
category: architecture
type: knowledge
discovered: 2026-04-09
last-validated: 2026-04-11
confidence: high
source: Sahil LangSmith traces 2026-04-09 — Grand Debate session (67 turns, 44M tokens); doc at docs/architecture/agent-harness-decisions.md; 2026-04-10 Sahil 5-agent CASDK vs custom harness research (traces 15:20–17:45); v3 architecture doc docs/architecture/agent-harness-understanding-v3.md
tags: [agent-harness, vercel-ai-sdk, trigger-dev, mastra, copilotkit, ai-runtime, grand-debate, architecture, casdk, claude-agent-sdk, plugin-format]
relevant-when: building AI agent features, choosing agent framework, implementing chat/streaming, designing tool execution, working on background AI tasks, evaluating CASDK adoption
related: [architecture-tech-stack-completed, architecture-phase1-decisions-settled, architecture-memory-layer-decisions, patterns-expert-panel-validation]
distributed-to: [VC-AI-Assoicate, maverick-market-research]
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Agent Harness Decision — Vercel AI SDK + Trigger.dev (SETTLED)

## What
The AI agent runtime framework is decided: **Vercel AI SDK + Trigger.dev v4 (Option A)**, not Mastra. Sahil ran a "Grand Debate" with 8 specialist agents who each evaluated the decision from their domain. All 8 converged on Option A. 11 sub-decisions made. This resolves the "AI runtime" item previously deferred in Phase 1 decisions.

## Why
Three killing arguments against Mastra:

| Issue | Detail |
|-------|--------|
| **Prompt caching** | Mastra breaks Anthropic's prompt caching — its `AbstractAgent` wraps messages in a way that invalidates cache. Vercel AI SDK preserves cache natively. At scale this is 50-90% cost difference. |
| **No Trigger.dev integration** | Mastra has its own workflow engine that competes with Trigger.dev (already settled in stack). Running both creates operational overhead and split debugging. |
| **React hooks don't work** | Mastra's `useChat` hooks don't integrate cleanly with the existing CopilotKit transport layer or the 25+ custom message types in the frontend. |

Additional factors:
- CopilotKit is installed but effectively unused — zero migration pain either way
- Vercel AI SDK adapter pattern (not direct AbstractAgent) fits existing architecture
- Infrastructure fits on a Hetzner CAX31 (~$14/mo)

## How to Apply
1. **AI agent features** use Vercel AI SDK for streaming, tool calling, and message management
2. **Three execution modes** — design all AI tools into one of:
   - **Inline** (<100ms): DB queries, lookups — run in API route
   - **Durable** (long-running): web research, enrichment — run as Trigger.dev `schemaTask`
   - **MCP** (external): third-party tools via Nango proxy
3. **CopilotKit**: use for transport layer only. Build own chat renderer for custom message types.
4. **Do not introduce Mastra** — the evaluation is complete and documented

## CASDK vs Custom Harness — Follow-up Research (2026-04-10)

Sahil ran 5 research agents to compare Maverick's custom harness against the Claude Agent SDK (CASDK). Key findings:

| Finding | Detail |
|---|---|
| **CASDK subprocess can't run in Next.js** | Vercel's own KB explicitly says don't run CASDK in API routes — it spawns subprocesses, which Vercel's Edge Runtime doesn't support. This kills the "adopt CASDK wholesale" option. |
| **CASDK + Trigger.dev IS officially supported** | Trigger.dev ships a working reference implementation. The composition works — it's not a blocker. |
| **Plugin model fit: ~50%** | 3/13 Maverick hook events have native CASDK equivalents; 6/13 partial; 4/13 missing entirely. Copying CASDK's plugin *format* (`.claude-plugin/`, SKILL.md, hooks/, commands/, agents/, .mcp.json) is worthwhile; replacing the runtime is not. |
| **`@ag-ui/claude-agent-sdk` adapter** | Shipped ~1 month ago — frontend CopilotKit/AG-UI integration with CASDK is no longer a blocker if needed later. |
| **v3 architecture** | Maverick v3 copies CASDK plugin *format* verbatim (`maverick:` namespace extensions) but uses Vercel AI SDK as the runtime. "A+ architecture" — gets the composability model without the subprocess constraint. |

**The v3 decision stands: Vercel AI SDK + Trigger.dev as runtime, CASDK plugin format for plugin interface design.**

## Evidence
- Sahil + Claude Code Grand Debate, 2026-04-09 (67 turns, 44M tokens)
- 8 specialist agents: LLM Engineer, Frontend Engineer, Tool Systems Engineer, Infrastructure Engineer, and 4 others
- All 8 converged on Option A with concrete technical evidence
- Decision doc: `docs/architecture/agent-harness-decisions.md` (VC-AI-Assoicate, branch `dev/claude/agent-harness-research`)
- Commit: pushed 2026-04-09T12:26
- CASDK research: Sahil 5-agent parallel research session, 2026-04-10T15:20–17:45 LangSmith traces
- v3 architecture doc: `docs/architecture/agent-harness-understanding-v3.md` committed 2026-04-10T17:45
