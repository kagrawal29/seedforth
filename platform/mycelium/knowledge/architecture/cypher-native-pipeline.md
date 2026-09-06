---
id: architecture-cypher-native-pipeline
category: architecture
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: high
source: Kshitiz LangSmith traces 2026-04-11 (commits 4186bc15, fc7bc74a, d73296af); issues #44 closed, #59 open, Invariant 6
tags: [cypher, graph, pipeline, falkordb, zero-cost, pipelinestage, flows-to, invariant, meta-intelligence]
relevant-when: building meta-intelligence pipeline, adding new pipeline stages, querying system state, deciding where logic lives (Python vs graph)
related: [architecture-tech-stack-completed, architecture-memory-layer-decisions]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Cypher-Native Pipeline — Intelligence Lives in the Graph (Invariant 6)

## What
The meta-intelligence pipeline is not a Python script. It is a **graph topology**: `PipelineStage` nodes hold their own Cypher queries as properties; `FLOWS_TO` edges define execution order. This is Invariant 6: "Cypher-native — all planning intelligence is graph traversal, not Python logic."

19 stages, 18 FLOWS_TO edges. Zero LLM cost. Each stage self-describes in the graph.

## Why
Python files that define pipeline structure are the same bypass that Invariant 6 prohibits:
- A Python file can go stale; the graph is the single source of truth
- Reading a file is a bypass — the system should ingest, not read
- LLM cost per pipeline run is not acceptable for an always-on nervous system
- Graph topology is inspectable, queryable, and debuggable via Cypher

**The principle**: "The system does not read. It ingests."

## Graph Schema
```cypher
-- Stage nodes hold their own execution logic
(:PipelineStage {
  node_id: "stage-ingest-traces",
  label: "Ingest LangSmith Traces",
  cypher_query: "MATCH (p:Person) ...",  -- the actual logic
  stage_order: 1
})

-- Edges define the flow
(:PipelineStage)-[:FLOWS_TO]->(:PipelineStage)
```

## What Was Migrated
- Integrity rules (previously in `scripts/integrity-rules.py`) → now encoded as Cypher in graph nodes
- Phase detection logic → graph traversal
- Operating model → `scripts/heartbeat.py` now reads from graph, executes graph queries

## Applied Context
- Kshitiz built this in one session (2026-04-11 09:16–09:31)
- Zero LLM cost confirmed: pure Cypher traversal at query time
- Issue #44 (reduce Python to I/O glue) closed as a result
- Issue #59 (Cypher as thought) remains open — next: queries themselves become graph nodes
