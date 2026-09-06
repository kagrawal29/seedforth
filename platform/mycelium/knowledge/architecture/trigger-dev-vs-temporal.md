---
id: architecture-trigger-dev-vs-temporal
category: architecture
type: knowledge
discovered: 2026-04-07
last-validated: 2026-04-07
confidence: high
source: Abhishek LangSmith traces 2026-04-07 (3.8M tokens deep comparison) + Sahiram Apr 6 decision
tags: [trigger-dev, temporal, queue, workflow, job, orchestration, workers, self-hosting, migration]
relevant-when: choosing a workflow/job queue system, evaluating Trigger.dev vs Temporal, designing background job processing
related: [architecture-memory-layer-decisions]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Trigger.dev v4 Chosen Over Temporal

## What
Trigger.dev v4 was chosen as the workflow/job queue system after Sahiram's initial decision (Apr 6) and Abhishek's deep comparative evaluation (Apr 7, 3.8M tokens across multiple turns). Temporal documented as the evaluated alternative with a clear migration path.

## Why

### Why Trigger.dev v4
- v3 shut down April 1, 2026 — forced migration to v4
- v4 GA with checkpointing + Bun runtime
- No worker management needed — Trigger.dev handles workers as managed Docker containers
- Simpler for current team size and scale (design partners, not enterprise yet)
- Dashboard shows parent-child tasks as unified traces (OpenTelemetry)
- Warm starts: 100-300ms (confirmed from social media research)

### Why Not Temporal (for now)
- Requires managing your own workers (more DevOps burden)
- More complex SDK (temporal-io/sdk-typescript)
- Better suited for enterprise scale with dedicated DevOps team
- More expensive self-hosting (needs Cassandra or MySQL as persistence)
- Overkill for current 2-3 design partner stage

### When to Reconsider Temporal
- At 20+ customers with complex, long-running workflows
- If Trigger.dev v4 hits scaling limits
- If need for truly durable, multi-day workflows (Temporal's sweet spot)
- Migration effort: moderate — workflow definitions rewrite, new persistence layer, but DB tables (email sequences, etc.) stay the same

## Evidence
- Sahiram's decision: Apr 6, found v3 shutdown, chose v4 (LangSmith traces)
- Abhishek's evaluation: Apr 7, compared worker management, migration path, self-hosting cost, email sequence example (3.8M tokens, multiple turns)
- Social media verification: @triggerdotdev confirmed v4 100-300ms warm starts
