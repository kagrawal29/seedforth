---
id: patterns-doc-to-graph-llm-boundary
category: patterns
type: knowledge
discovered: 2026-04-11
last-validated: 2026-04-11
confidence: medium
source: Sahil LangSmith traces 2026-04-10T21:31 — building competitive intelligence graph from market research data
tags: [graph, llm, doc-to-graph, falkordb, cypher, competitive-research, parsing, structured-data, cost-optimization]
relevant-when: ingesting research data into graph, deciding when to use LLM vs deterministic parsing, building graph from documents
related: [architecture-cypher-native-pipeline, architecture-memory-layer-decisions, pattern-competitor-research-dataset]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---

# Doc-to-Graph LLM Boundary: Parse Structure Deterministically, Use LLM Only for Fuzzy Parts

## What
Most document-to-graph ingestion does NOT need an LLM. Structured data people think is unstructured can be parsed deterministically. Use LLMs only for content that is genuinely fuzzy, ambiguous, or unstructured narrative.

## Decision Table

| Source | LLM needed? | Tool |
|---|---|---|
| JSON / YAML / TOML | **No** | `json.loads()` + loop |
| CSV / Excel | **No** | pandas |
| Markdown tables | **No** | regex / markdown parser |
| API responses | **No** | direct field extraction |
| Free-text descriptions | **Yes** | LLM extraction |
| Ambiguous entity matching | **Yes** | LLM with examples |
| Sentiment / opinion extraction | **Yes** | LLM |
| Narrative synthesis | **Yes** | LLM |

## Process: Define Schema First
Before writing any code, define the graph schema:
- Node labels and their properties
- Relationship types
- Even 5 minutes on schema design beats "let the LLM decide"

Sahil's competitive intelligence graph: `Competitor | Platform | Report | Theme | Pattern` nodes. Schema-first, then deterministic parsing of research CSVs, then LLM only for thematic analysis of free-text content.

## Why This Matters
LLM cost per ingestion run adds up. For an always-on meta-intelligence system processing daily signals, deterministic parsing is the sustainable path. Reserve LLM calls for the genuinely irreducible cases.

## Visualizing the Result
Once the graph is built, a self-contained HTML visualization (force-directed graph) can be generated without any additional dependencies:
```
open docs/architecture/agent-harness/graph-visualizer.html
```
No server, no install — paste into Cypher for Neo4j/FalkorDB reload.
