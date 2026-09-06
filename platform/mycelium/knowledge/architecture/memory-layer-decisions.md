---
id: architecture-memory-layer-decisions
category: architecture
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: Sahiram LangSmith traces 2026-04-06 — 20M+ token architecture session with 31 research agents
distributed-to: [VC-AI-Assoicate#6]
effectiveness: neutral
metrics:
  surfaced_count: 19
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.00
  last_scored: 2026-04-12
tags: [graphiti, falkordb, neo4j, pgvector, trigger-dev, queue, embedding, bge, digital-ocean, postgres, rls, fund-id, tenant-isolation, memory-layer, knowledge-graph]
relevant-when: choosing a database, setting up backend, evaluating graph databases, picking a queue system, designing tenant isolation, working with embeddings, configuring Graphiti
related: [anti-pattern-zep-cloud-reliability, architecture-production-readiness-gap, architecture-fixture-first-development, workflow-architecture-validation-research, architecture-trigger-dev-vs-temporal, architecture-cross-channel-continuity-model]
---

# Memory Layer Architecture Decisions

## What
Sahiram finalized the AI memory/retrieval architecture through a massive research session (31 agents, 20M+ tokens). Key decisions:

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Knowledge graph engine | **Graphiti OSS** (self-hosted) | 94.8% DMR accuracy; Zep Cloud rejected (async deadlocks, wrong endpoints, fake success states) |
| Graph database | **FalkorDB over Neo4j** | 7x less memory, 500x faster P99, native Graphiti support (`pip install graphiti-core[falkordb]`) |
| Queue system | **Trigger.dev v4** | v3 shut down April 1 2026; v4 GA with checkpointing + Bun runtime |
| Main database | **Digital Ocean PostgreSQL** | Hosted, managed |
| AI retrieval | **Graphiti + pgvector hybrid** | Knowledge graph for relationships, pgvector for semantic search |
| User search Phase 1 | **Keyword only** (Postgres FTS + pg_trgm) | PRD constraint |
| Tenant isolation | **RLS on fund_id** | Multi-fund orgs; user_fund_access junction table controls per-fund access |
| Embedding models | **Self-hosted viable** | BGE-small (256MB RAM, ~12ms/query CPU), BGE-large (1.5GB, ~50ms) |

## Why
- Zep Cloud has documented production reliability issues — multiple teams abandoned it
- FalkorDB is a drop-in replacement for Neo4j with dramatically better resource usage
- Trigger.dev v3 literally shut down — this was a forced migration
- Three-layer split (Truth: Postgres, Knowledge: Graphiti/FalkorDB, Evidence: pgvector) keeps concerns clean

## How to Apply
1. **Backend team:** Use these decisions as settled — don't re-research graph DB or queue choices
2. **FalkorDB is the graph DB**, not Neo4j — any docs referencing Neo4j need updating
3. **Zep Cloud is rejected** — any references to "Zep" should be "Graphiti" (the OSS component)
4. RLS design: every table gets `fund_id`, access controlled via `user_fund_access(user_id, fund_id, role)`
5. Stealth deals add second layer: `deal_access(deal_id, user_id)` for restricted deals within a fund

## Evidence
- Sahiram's LangSmith traces 2026-04-06 (10 turns, 20.3M tokens)
- 31 research agents deployed for validation
- Architecture doc: `docs/research/maverick-memory-architecture-final.md` in Sahiram's repo
- Graphiti architectural issue flagged: must run as separate process, not embedded
