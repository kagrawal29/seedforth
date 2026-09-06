---
paths:
  - "**/*"
---

# Context for Sahil — 2026-04-10

## Decisions that affect your current work

- **Memory architecture is settled**: Graphiti OSS + FalkorDB + pgvector hybrid — settled by Sahiram Apr 6. The continuity model you implemented (work-unit + members) runs on top of this stack. Specifically: Graphiti runs as a separate process (not embedded), pgvector handles semantic search, FalkorDB is the graph DB. Ensure `continuity_contexts` schema aligns with Graphiti's episode model — Graphiti expects episodes as discrete temporal units.

- **Agent harness is settled (your own decision)**: Vercel AI SDK + Trigger.dev v4, Mastra rejected. Key operational point: CopilotKit is transport layer only — build own chat renderer for custom message types. The 25+ custom message types in the frontend are not compatible with Mastra's `useChat` hooks.

- **Cross-channel continuity model is settled (your own work)**: Work-unit + members model, NOT single-anchor. Critical index fix applied: `idx_unique_deal_context` now scoped to `(fund_id, deal_id, context_type, status)` — not just `(fund_id, context_type, status)`. Authorization boundary is per-member, not per-context.

## Cross-team connections

- Your concern about AI-generated doc quality (Apr 7: "most of it is just done by AI") is being addressed by Ankit-S building reading guides into the spec-to-ship playbook v7 (Apr 10). The reading guide requirement makes every AI-generated spec self-verifiable — each technical field maps explicitly to its product meaning. This is a direct response to the class of problem you identified.

- Ankit-S is also using spec-to-ship for feature implementation (channel preferences). You're both encountering the playbook's limits in different ways — Ankit-S on spec reviewability, you on AI doc trust. Both inform playbook v7+.

## Expanding your questions

- Your question about AI-generated documentation trustworthiness has no settled answer in the knowledge base. The `claude-code-agent-as-primary-builder` entry covers Claude as builder but doesn't address when to trust vs. verify AI-produced architectural documentation. This is the one undocumented gap in your demand profile — worth a report if you reach a conclusion.

- The Reddit practitioner research you did on agent harnesses (open-source vs. custom) is not in the knowledge base. The Grand Debate outcome is documented but your community research findings are not — if there were notable practitioner perspectives, capturing them strengthens the decision's evidence base.
