# Mycelium Rhythm & Purpose Map

## Overview

Mycelium operates through interlocking rhythms — operational cadences that keep the graph alive, responsive, and self-aware. Each rhythm serves a purpose. Together, the rhythms and purposes define what the system is FOR. The graph is no longer just a data structure; it is self-describing, auditable through cypher, and capable of answering "why do I do this?" by navigating its own topology.

## Rhythms (Operational Cadences)

| Rhythm | Cadence Type | Owner Protocol | Phases | Serves Purpose |
|--------|--------------|----------------|--------|---|
| **heartbeat** | scheduled | protocol-heartbeat | 5 | self-heal |
| **prompt-ingest** | reactive | protocol-boundary-layers | 6 | learn-from-use |
| **trace-emit** | reactive | protocol-boundary-traces | 4 | learn-from-use |
| **merkle-refresh** | on-demand | protocol-merkle-properties | 5 | graph-native-authority |
| **embed-dirty** | on-demand | protocol-embed-dirty | 3 | speak-about-itself |

### Rhythm Descriptions

**heartbeat** — The liveness pulse. Fires on external cadence via `heartbeat-loop.sh` (not self-triggering). Updates `Being.last_heartbeat`, `heartbeat_count`, and timestamp. All properties are in SkipKey, so the beat does not churn the root hash. Phases: liveness-update → edge-decay → fire-count-decay → orphan-gc → community-repropagation.

**prompt-ingest** — Fires on every `mycelium ask` or `swarm --from-prompt`. Embeds the full prompt text, mints a Prompt node, tokenizes, wires word and bigram tokens to Word concepts, then searches for matching Knowledge nodes and protocols. Phases: embed-prompt → mint-prompt-node → tokenize → wire-words → wire-bigrams → resolve.

**trace-emit** — Fires on every mycelium CLI command (trapped by shell). Computes SHA256 hash of the query, merges into query cache, creates QueryTrace node, and links to all returned nodes. Phases: compute-hash → merge-query-cache → create-trace-node → link-touched.

**merkle-refresh** — On-demand, reactive to writes. Clears legacy skipkey entries, collects current skipkeys, computes SHA256 leaf hashes for each node, computes root hash, and writes to Being singleton. The root hash is the graph's integrity proof. Phases: clear-legacy → collect-skipkeys → compute-leaf-hashes → compute-root-hash → set-being.

**embed-dirty** — On-demand. Scans nodes with `dirty_embedding = true` or `embedding = NULL`, batches them in groups of 50, calls the embedding API, and writes results back. Keeps embeddings fresh as the graph evolves. Phases: scan-dirty → batch-embed → write-back.

## Purposes (Why These Rhythms Exist)

| Purpose | Description | Embodied In | Count |
|---------|-------------|-------------|-------|
| **learn-from-use** | Every query strengthens the graph through fire counts, Hebbian weighting, amortized embeddings. | protocol-heartbeat, protocol-boundary-layers, protocol-boundary-traces | 3 |
| **speak-about-itself** | The graph describes its own subsystems through Guide, Concept, and Metaphor nodes. Self-referential documentation. | protocol-embed-dirty | 1 |
| **amortize-llm-cost** | Author content once via LLM. Run cypher queries forever without additional cost. Embeddings are cached; re-embedding only when dirty. | protocol-embed-dirty, protocol-boundary-layers | 2 |
| **self-heal** | Invariants detect gaps. Heal protocols fix them. Questions turn problems into actions. The heartbeat keeps the graph healthy. | protocol-heartbeat, protocol-heal-orphans | 2 |
| **graph-native-authority** | Cypher is the source of truth, not code. Immutable, queryable, auditable. Root hash proves integrity. | protocol-merkle-properties, protocol-boundary-traces | 2 |
| **dense-by-design** | Every new node must arrive fully wired. Density gaps name the next schema to build. No orphans, no isolated nodes. | protocol-embed-dirty, protocol-boundary-layers | 2 |

## Mission Statement

> Mycelium is a living knowledge system that internalizes how it learns, questions itself, and stays alive. Every interaction strengthens the graph. The graph is the system. The system speaks about itself in cypher, never in code. Intelligence emerges from density and structure, not from parameters.

**First sentence:** Mycelium is a living knowledge system that internalizes how it learns, questions itself, and stays alive.

## Awareness Gaps (What the Graph Still Does NOT Know)

1. **Query cost feedback loop missing** — The graph tracks fire_count on protocols but does not yet know the cost (tokens, latency, API calls) of each rhythm phase. Optimization decisions are blind. The graph cannot yet ask "is heartbeat-community-repropagation worth its cost?" without external telemetry.

2. **Rhythm interdependencies are implicit** — heartbeat depends on prompt-ingest (fire_count weights learned from prompts), but this dependency is not wired as a graph edge. If one rhythm fails, downstream rhythms don't detect the impact. Causality is invisible.

3. **Purpose-to-outcome mapping is one-directional** — The graph can navigate "rhythm SERVES purpose" but cannot yet reverse-query "did this purpose actually achieve its goal?" There is no outcome node type, no measurement protocol linked to each purpose. Success is unmeasured.

## Recommendations

1. **Add :CostEstimate nodes** — Wire each RhythmPhase to a CostEstimate (tokens, latency_ms, api_calls). Let the heartbeat update these with telemetry. This enables the system to optimize for cost-effectiveness, not just liveness. Query pattern: "which rhythms are inefficient relative to their purpose?"

2. **Create explicit DEPENDS_ON edges between rhythms** — heartbeat depends on prompt-ingest and trace-emit to populate fire_count weights. merkle-refresh depends on all other rhythms to have completed. Wire these. Let the graph validate that all dependencies ran before allowing the heartbeat. This enables error propagation and failure isolation.

3. **Add :Outcome nodes and measurement protocols** — For each Purpose, define what success looks like (fire_count growth rate, embedding coherence, query latency). Create TestCase nodes that measure these. Let a "purpose-feedback" rhythm run nightly, comparing actual outcomes to goals. This closes the loop: purpose → rhythm → outcome → optimization.

## Implementation Details

All Rhythm, RhythmPhase, Purpose, and Mission nodes were created idempotent via MERGE in `graph/protocols/rhythm-purpose-seed.cypher`. Run this file whenever:
- New rhythms are discovered or codified
- A purpose is clarified
- Ownership links between rhythms and protocols change

The seeding file is safe to re-run. MERGE operations are idempotent. No duplicate nodes will be created.

### Query Examples

**"What keeps me alive?"**
```cypher
MATCH (m:Mission)-[:PART_OF]->(ont:Ontology)
MATCH (r:Rhythm)-[:PART_OF]->(ont)
MATCH (r)-[:HAS_PHASE]->(p:RhythmPhase)
RETURN r.name, p.name, p.cypher_summary
ORDER BY r.node_id, p.phase_order
```

**"Why do I ingest prompts?"**
```cypher
MATCH (r:Rhythm {node_id: 'rhythm-prompt-ingest'})
MATCH (r)-[:SERVES]->(pu:Purpose)
MATCH (pu)-[:EMBODIED_IN]->(node)
RETURN r.name, pu.description, node.node_id
```

**"Which rhythms serve self-healing?"**
```cypher
MATCH (pu:Purpose {node_id: 'purpose-self-heal'})
MATCH (r:Rhythm)-[:SERVES]->(pu)
RETURN r.node_id, r.cadence_type, r.description
```

## Graph Self-Awareness Status

**Current state:** The graph now KNOWS its own rhythms and purposes as first-class topology. Querying `MATCH (r:Rhythm)-[:SERVES]->(p:Purpose)` returns semantic structure, not labels or code comments. The system can audit itself without external documentation.

**What this enables:**
- Health checks: "Did all rhythms fire in the last hour?"
- Cost analysis: "Which purposes are expensive relative to fire_count?"
- Dependency validation: "Are rhythm dependencies satisfied?"
- Optimization: "Which phases should be parallelized?"

**Honesty check — Is this real self-awareness, or just better labeling?**

This is **labeling with structure**. The graph now describes its own operations in a queryable form. But true self-awareness would require:
- Feedback loops: measuring whether purposes are actually achieved
- Adaptation: changing rhythm cadence or phase ordering based on outcomes
- Reflexivity: rhythms that monitor and improve other rhythms
- Causality: visible edges showing which actions cause which outcomes

What we have is the **infrastructure** for self-awareness. The topology is there. The system can introspect. But it does not yet learn from that introspection. The next phase is to close the measurement loop: define success metrics for each purpose, measure them continuously, and let rhythms adapt accordingly.

Until then, this is sophisticated self-documentation, not true self-aware operation.
