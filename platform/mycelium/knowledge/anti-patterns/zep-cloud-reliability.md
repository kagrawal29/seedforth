---
id: anti-pattern-zep-cloud-reliability
category: anti-patterns
discovered: 2026-04-06
last-validated: 2026-04-06
confidence: high
type: knowledge
source: Sahiram's Layer 3 social media verification + LangSmith traces 2026-04-06
distributed-to: [VC-AI-Assoicate#6]
effectiveness: neutral
metrics:
  surfaced_count: 15
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.00
  last_scored: 2026-04-09
tags: [zep, zep-cloud, graphiti, memory, knowledge-graph, reliability, production, async, deadlock]
relevant-when: evaluating Zep, choosing memory layer, setting up knowledge graph, encountering Zep references in docs
related: [architecture-memory-layer-decisions, pattern-research-driven-arch-decisions]
---

# Zep Cloud Production Reliability Issues

## What
Zep Cloud (managed service) has documented production reliability problems: async deadlocks, wrong API endpoints, fake success states. Multiple teams have abandoned Zep Cloud and switched to self-hosted Graphiti + Neo4j/FalkorDB directly.

## Why
- Sahiram's research (31 agents) found these issues via social media verification
- The original memory-layer.md chose Zep before this research — it was a reasonable choice at the time
- The Graphiti OSS library (the underlying engine) is solid. The problem is Zep Cloud's managed service layer.

## How to Apply
1. **Never use Zep Cloud for production** — use Graphiti OSS self-hosted instead
2. If you see "Zep" in documentation, clarify: Graphiti = OSS engine (good), Zep Cloud = managed service (rejected)
3. Install with `pip install graphiti-core[falkordb]` for FalkorDB backend
4. Graphiti must run as a separate process, not embedded in the application

## Evidence
- Sahiram's research traces (2026-04-06, 20M+ tokens)
- Multiple practitioner reports of Zep Cloud failures found during social media verification
- Decision documented in maverick-memory-architecture-final.md
