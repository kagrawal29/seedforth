// @kind: seed
// ============================================================================
// Protocol: Rhythm + Purpose Layer Seed
// ============================================================================
// Introduces the :Rhythm, :RhythmPhase, :Purpose, and :Mission layers as
// first-class graph citizens. The graph becomes self-aware of its own operational
// rhythms and the purposes they serve.
//
// New node types:
//   :Rhythm          operational cadence (heartbeat, prompt-ingest, trace-emit,
//                    merkle-refresh, embed-dirty). Owns phases, knows its purpose.
//   :RhythmPhase     a stage within a rhythm. Ordered, has cypher_summary,
//                    duration_avg_ms.
//   :Purpose         why the system does something (learn-from-use, speak-about-
//                    itself, amortize-llm-cost, self-heal, graph-native-authority,
//                    dense-by-design).
//   :Mission         the overarching statement of what mycelium is FOR.
//
// New edge types:
//   HAS_PHASE        Rhythm → RhythmPhase (ordered)
//   PHASE_OF         RhythmPhase → Rhythm (reverse)
//   OWNED_BY         Rhythm → Protocol (which protocol embodies this rhythm)
//   SERVES           Rhythm → Purpose (what purpose does this rhythm serve)
//   EMBODIED_IN      Purpose → Protocol | Concept | Invariant | Guide
//   PART_OF          Purpose/Rhythm → Mission/Ontology
//
// Wiring into existing graph:
//   - Every Rhythm links to the owning Protocol
//   - Every Rhythm links to one or more Purposes
//   - Every Purpose links to evidence (protocols, concepts, invariants, guides)
//   - Mission and Ontology are linked
//   - RhythmPhases are wired in order
//
// The graph becomes self-aware of its own operational design. The system can
// now answer: "What am I for?" and "How do I stay alive?" through cypher.
//
// Idempotent (MERGE only). Safe to re-run.
// ============================================================================


// --- Part 1: Create :Rhythm nodes ---

MERGE (rhythm:Rhythm:GraphNode {
  node_id: 'rhythm-heartbeat',
  name: 'heartbeat',
  cadence_type: 'scheduled',
  last_tick_at: datetime({epochMillis: 1776302190459}),
  tick_count: 1491843,
  description: 'Liveness pulse. Updates Being singleton with fresh heartbeat count and timestamp. Fires on external cadence via heartbeat-loop.sh. All properties in SkipKey so beat does not churn root_hash.'
})
SET rhythm.created_at = datetime()
SET rhythm.ontology = 'ontology-mycelium';

MERGE (rhythm:Rhythm:GraphNode {
  node_id: 'rhythm-prompt-ingest',
  name: 'prompt-ingest',
  cadence_type: 'reactive',
  last_tick_at: datetime(),
  tick_count: 0,
  description: 'Fires on every mycelium ask / swarm --from-prompt. Embeds prompt, mints node, tokenizes, wires words and bigrams, resolves references.'
})
SET rhythm.created_at = datetime();

MERGE (rhythm:Rhythm:GraphNode {
  node_id: 'rhythm-trace-emit',
  name: 'trace-emit',
  cadence_type: 'reactive',
  last_tick_at: datetime(),
  tick_count: 0,
  description: 'Fires on every mycelium CLI command via trap. Computes hash, merges query cache, creates trace node, links touched nodes.'
})
SET rhythm.created_at = datetime();

MERGE (rhythm:Rhythm:GraphNode {
  node_id: 'rhythm-merkle-refresh',
  name: 'merkle-refresh',
  cadence_type: 'on-demand',
  last_tick_at: datetime(),
  tick_count: 0,
  description: 'Reactive to writes. Clears legacy skipkeys, collects skipkeys, computes leaf and root hashes, updates Being singleton.'
})
SET rhythm.created_at = datetime();

MERGE (rhythm:Rhythm:GraphNode {
  node_id: 'rhythm-embed-dirty',
  name: 'embed-dirty',
  cadence_type: 'on-demand',
  last_tick_at: datetime(),
  tick_count: 0,
  description: 'Scans dirty nodes, batches embeddings, writes results. Keeps embeddings fresh as graph evolves.'
})
SET rhythm.created_at = datetime();


// --- Part 2: Create :RhythmPhase nodes and wire them ---

// Heartbeat phases
MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-heartbeat-liveness-update',
  name: 'liveness-update',
  phase_order: 1,
  cypher_summary: 'Update Being.last_heartbeat and last_heartbeat_at with current timestamp',
  duration_avg_ms: 5
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-heartbeat-edge-decay',
  name: 'edge-decay',
  phase_order: 2,
  cypher_summary: 'Reduce edge_weight on edges where last_fired < 30 days ago. Decay rate depends on edge type.',
  duration_avg_ms: 50
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-heartbeat-fire-count-decay',
  name: 'fire-count-decay',
  phase_order: 3,
  cypher_summary: 'Reduce fire_count on Protocols and Concepts. Prevents ancient patterns from dominating ranking.',
  duration_avg_ms: 30
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-heartbeat-orphan-gc',
  name: 'orphan-gc',
  phase_order: 4,
  cypher_summary: 'Delete nodes with no incoming edges except PART_OF or OWNED_BY. Cleans up junk.',
  duration_avg_ms: 100
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-heartbeat-community-repropagation',
  name: 'community-repropagation',
  phase_order: 5,
  cypher_summary: 'Recompute semantic_community for all nodes based on current embeddings and topology.',
  duration_avg_ms: 200
})
SET phase.created_at = datetime();

// Wire heartbeat phases
MATCH (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MATCH (phase:RhythmPhase WHERE phase.node_id IN [
  'rhythm-phase-heartbeat-liveness-update',
  'rhythm-phase-heartbeat-edge-decay',
  'rhythm-phase-heartbeat-fire-count-decay',
  'rhythm-phase-heartbeat-orphan-gc',
  'rhythm-phase-heartbeat-community-repropagation'
])
MERGE (rhythm)-[:HAS_PHASE {order: phase.phase_order}]->(phase)
MERGE (phase)-[:PHASE_OF]->(rhythm);

// Prompt ingest phases
MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-prompt-ingest-embed',
  name: 'embed-prompt',
  phase_order: 1,
  cypher_summary: 'Call embedding API on the full prompt text.',
  duration_avg_ms: 150
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-prompt-ingest-mint',
  name: 'mint-prompt-node',
  phase_order: 2,
  cypher_summary: 'Create Prompt node with text, embedding, timestamp.',
  duration_avg_ms: 5
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-prompt-ingest-tokenize',
  name: 'tokenize',
  phase_order: 3,
  cypher_summary: 'Split prompt into tokens. Create Token nodes.',
  duration_avg_ms: 20
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-prompt-ingest-wire-words',
  name: 'wire-words',
  phase_order: 4,
  cypher_summary: 'Wire Tokens to Word concepts. Merge if word exists, create if new.',
  duration_avg_ms: 50
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-prompt-ingest-wire-bigrams',
  name: 'wire-bigrams',
  phase_order: 5,
  cypher_summary: 'Create Bigram nodes for consecutive token pairs. Wire to word tokens.',
  duration_avg_ms: 40
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-prompt-ingest-resolve',
  name: 'resolve',
  phase_order: 6,
  cypher_summary: 'Find matching Knowledge nodes, Concepts, Protocols. Create SIMILAR edges.',
  duration_avg_ms: 300
})
SET phase.created_at = datetime();

// Wire prompt ingest phases
MATCH (rhythm:Rhythm {node_id: 'rhythm-prompt-ingest'})
MATCH (phase:RhythmPhase WHERE phase.node_id IN [
  'rhythm-phase-prompt-ingest-embed',
  'rhythm-phase-prompt-ingest-mint',
  'rhythm-phase-prompt-ingest-tokenize',
  'rhythm-phase-prompt-ingest-wire-words',
  'rhythm-phase-prompt-ingest-wire-bigrams',
  'rhythm-phase-prompt-ingest-resolve'
])
MERGE (rhythm)-[:HAS_PHASE {order: phase.phase_order}]->(phase)
MERGE (phase)-[:PHASE_OF]->(rhythm);

// Trace emit phases
MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-trace-emit-hash',
  name: 'compute-hash',
  phase_order: 1,
  cypher_summary: 'SHA256 of query text. Deterministic. Lookup in existing QueryTrace nodes.',
  duration_avg_ms: 10
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-trace-emit-cache-merge',
  name: 'merge-query-cache',
  phase_order: 2,
  cypher_summary: 'Merge result hash into QueryTrace cache. Increment fire_count if exists.',
  duration_avg_ms: 10
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-trace-emit-create-node',
  name: 'create-trace-node',
  phase_order: 3,
  cypher_summary: 'Create QueryTrace node with hash, query text, invoked_by, invoked_epoch_ms.',
  duration_avg_ms: 5
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-trace-emit-link-touched',
  name: 'link-touched',
  phase_order: 4,
  cypher_summary: 'Wire QueryTrace to all nodes returned by the query. Create TOUCHED_IN edges.',
  duration_avg_ms: 50
})
SET phase.created_at = datetime();

// Wire trace emit phases
MATCH (rhythm:Rhythm {node_id: 'rhythm-trace-emit'})
MATCH (phase:RhythmPhase WHERE phase.node_id IN [
  'rhythm-phase-trace-emit-hash',
  'rhythm-phase-trace-emit-cache-merge',
  'rhythm-phase-trace-emit-create-node',
  'rhythm-phase-trace-emit-link-touched'
])
MERGE (rhythm)-[:HAS_PHASE {order: phase.phase_order}]->(phase)
MERGE (phase)-[:PHASE_OF]->(rhythm);

// Merkle refresh phases
MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-merkle-refresh-clear-legacy',
  name: 'clear-legacy',
  phase_order: 1,
  cypher_summary: 'Delete skipkey entries older than 1 hour.',
  duration_avg_ms: 50
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-merkle-refresh-collect-skipkeys',
  name: 'collect-skipkeys',
  phase_order: 2,
  cypher_summary: 'Gather all node IDs marked in SkipKey. These are properties that do not affect root_hash.',
  duration_avg_ms: 20
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-merkle-refresh-leaf-hashes',
  name: 'compute-leaf-hashes',
  phase_order: 3,
  cypher_summary: 'For each node (excluding SkipKey props), hash its type + properties + edges.',
  duration_avg_ms: 500
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-merkle-refresh-root-hash',
  name: 'compute-root-hash',
  phase_order: 4,
  cypher_summary: 'Hash all leaf hashes together. This is the graph integrity proof.',
  duration_avg_ms: 30
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-merkle-refresh-set-being',
  name: 'set-being',
  phase_order: 5,
  cypher_summary: 'Write root_hash and previous_root_hash to Being singleton.',
  duration_avg_ms: 5
})
SET phase.created_at = datetime();

// Wire merkle refresh phases
MATCH (rhythm:Rhythm {node_id: 'rhythm-merkle-refresh'})
MATCH (phase:RhythmPhase WHERE phase.node_id IN [
  'rhythm-phase-merkle-refresh-clear-legacy',
  'rhythm-phase-merkle-refresh-collect-skipkeys',
  'rhythm-phase-merkle-refresh-leaf-hashes',
  'rhythm-phase-merkle-refresh-root-hash',
  'rhythm-phase-merkle-refresh-set-being'
])
MERGE (rhythm)-[:HAS_PHASE {order: phase.phase_order}]->(phase)
MERGE (phase)-[:PHASE_OF]->(rhythm);

// Embed dirty phases
MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-embed-dirty-scan',
  name: 'scan-dirty',
  phase_order: 1,
  cypher_summary: 'Find all nodes with dirty_embedding = true or embedding = NULL. Batch collect.',
  duration_avg_ms: 100
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-embed-dirty-batch-embed',
  name: 'batch-embed',
  phase_order: 2,
  cypher_summary: 'Call embedding API in batches of 50 nodes. Reuse cached embeddings when possible.',
  duration_avg_ms: 1000
})
SET phase.created_at = datetime();

MERGE (phase:RhythmPhase:GraphNode {
  node_id: 'rhythm-phase-embed-dirty-write-back',
  name: 'write-back',
  phase_order: 3,
  cypher_summary: 'Store new embeddings on nodes. Set dirty_embedding = false. Update embedding_model timestamp.',
  duration_avg_ms: 200
})
SET phase.created_at = datetime();

// Wire embed dirty phases
MATCH (rhythm:Rhythm {node_id: 'rhythm-embed-dirty'})
MATCH (phase:RhythmPhase WHERE phase.node_id IN [
  'rhythm-phase-embed-dirty-scan',
  'rhythm-phase-embed-dirty-batch-embed',
  'rhythm-phase-embed-dirty-write-back'
])
MERGE (rhythm)-[:HAS_PHASE {order: phase.phase_order}]->(phase)
MERGE (phase)-[:PHASE_OF]->(rhythm);


// --- Part 3: Wire Rhythms to their Protocols ---

MATCH (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
OPTIONAL MATCH (protocol:Protocol {node_id: 'protocol-heartbeat'})
WITH rhythm, protocol
FOREACH (p IN CASE WHEN protocol IS NOT NULL THEN [protocol] ELSE [] END |
  MERGE (rhythm)-[:OWNED_BY]->(p)
);

MATCH (rhythm:Rhythm {node_id: 'rhythm-prompt-ingest'})
OPTIONAL MATCH (protocol:Protocol {node_id: 'protocol-boundary-layers'})
WITH rhythm, protocol
FOREACH (p IN CASE WHEN protocol IS NOT NULL THEN [protocol] ELSE [] END |
  MERGE (rhythm)-[:OWNED_BY]->(p)
);

MATCH (rhythm:Rhythm {node_id: 'rhythm-trace-emit'})
OPTIONAL MATCH (protocol:Protocol {node_id: 'protocol-boundary-traces'})
WITH rhythm, protocol
FOREACH (p IN CASE WHEN protocol IS NOT NULL THEN [protocol] ELSE [] END |
  MERGE (rhythm)-[:OWNED_BY]->(p)
);

MATCH (rhythm:Rhythm {node_id: 'rhythm-merkle-refresh'})
OPTIONAL MATCH (protocol:Protocol {node_id: 'protocol-merkle-properties'})
WITH rhythm, protocol
FOREACH (p IN CASE WHEN protocol IS NOT NULL THEN [protocol] ELSE [] END |
  MERGE (rhythm)-[:OWNED_BY]->(p)
);

MATCH (rhythm:Rhythm {node_id: 'rhythm-embed-dirty'})
OPTIONAL MATCH (protocol:Protocol {node_id: 'protocol-embed-dirty'})
WITH rhythm, protocol
FOREACH (p IN CASE WHEN protocol IS NOT NULL THEN [protocol] ELSE [] END |
  MERGE (rhythm)-[:OWNED_BY]->(p)
);


// --- Part 4: Create :Purpose nodes ---

MERGE (purpose:Purpose:GraphNode {
  node_id: 'purpose-learn-from-use',
  name: 'learn-from-use',
  description: 'Every query strengthens the graph. Fire counts, Hebbian weighting, amortized embeddings.'
})
SET purpose.created_at = datetime();

MERGE (purpose:Purpose:GraphNode {
  node_id: 'purpose-speak-about-itself',
  name: 'speak-about-itself',
  description: 'The graph describes its own subsystems through :Guide, :Concept, :Metaphor nodes.'
})
SET purpose.created_at = datetime();

MERGE (purpose:Purpose:GraphNode {
  node_id: 'purpose-amortize-llm-cost',
  name: 'amortize-llm-cost',
  description: 'Author content once via LLM, run cypher queries forever without additional cost.'
})
SET purpose.created_at = datetime();

MERGE (purpose:Purpose:GraphNode {
  node_id: 'purpose-self-heal',
  name: 'self-heal',
  description: 'Invariants detect gaps. Heal protocols fix them. Questions turn problems into actions.'
})
SET purpose.created_at = datetime();

MERGE (purpose:Purpose:GraphNode {
  node_id: 'purpose-graph-native-authority',
  name: 'graph-native-authority',
  description: 'Cypher is the source of truth, not code. Immutable, queryable, auditable.'
})
SET purpose.created_at = datetime();

MERGE (purpose:Purpose:GraphNode {
  node_id: 'purpose-dense-by-design',
  name: 'dense-by-design',
  description: 'Every new node arrives wired. Density gaps name the next schema to build.'
})
SET purpose.created_at = datetime();


// --- Part 5: Wire Purposes to evidence nodes ---

// purpose-learn-from-use embodied in heartbeat, boundary-layers, boundary-traces
MATCH (purpose:Purpose {node_id: 'purpose-learn-from-use'})
MATCH (protocol:Protocol WHERE protocol.node_id IN ['protocol-heartbeat', 'protocol-boundary-layers', 'protocol-boundary-traces'])
MERGE (purpose)-[:EMBODIED_IN]->(protocol);

// purpose-speak-about-itself embodied in guides and concepts
MATCH (purpose:Purpose {node_id: 'purpose-speak-about-itself'})
OPTIONAL MATCH (guide:Guide {node_id: 'guide-agent-contract'})
WITH purpose, guide
FOREACH (g IN CASE WHEN guide IS NOT NULL THEN [guide] ELSE [] END |
  MERGE (purpose)-[:EMBODIED_IN]->(g)
);

// purpose-amortize-llm-cost embodied in embed-dirty and boundary-layers
MATCH (purpose:Purpose {node_id: 'purpose-amortize-llm-cost'})
MATCH (protocol:Protocol WHERE protocol.node_id IN ['protocol-embed-dirty', 'protocol-boundary-layers'])
MERGE (purpose)-[:EMBODIED_IN]->(protocol);

// purpose-self-heal embodied in heartbeat and heal protocols
MATCH (purpose:Purpose {node_id: 'purpose-self-heal'})
MATCH (protocol:Protocol WHERE protocol.node_id IN ['protocol-heartbeat', 'protocol-heal-orphans'])
MERGE (purpose)-[:EMBODIED_IN]->(protocol);

// purpose-graph-native-authority embodied in merkle-refresh and boundary-traces
MATCH (purpose:Purpose {node_id: 'purpose-graph-native-authority'})
MATCH (protocol:Protocol WHERE protocol.node_id IN ['protocol-merkle-properties', 'protocol-boundary-traces'])
MERGE (purpose)-[:EMBODIED_IN]->(protocol);

// purpose-dense-by-design embodied in embed-dirty and boundary-layers
MATCH (purpose:Purpose {node_id: 'purpose-dense-by-design'})
MATCH (protocol:Protocol WHERE protocol.node_id IN ['protocol-embed-dirty', 'protocol-boundary-layers'])
MERGE (purpose)-[:EMBODIED_IN]->(protocol);


// --- Part 6: Create :Mission node ---

MERGE (mission:Mission:GraphNode {
  node_id: 'mission-mycelium',
  name: 'Mycelium Mission',
  statement: 'Mycelium is a living knowledge system that internalizes how it learns, questions itself, and stays alive. Every interaction strengthens the graph. The graph is the system. The system speaks about itself in cypher, never in code. Intelligence emerges from density and structure, not from parameters.'
})
SET mission.created_at = datetime();


// --- Part 7: Wire Rhythms to Purposes ---

MATCH (rhythm:Rhythm {node_id: 'rhythm-heartbeat'})
MATCH (purpose:Purpose {node_id: 'purpose-self-heal'})
MERGE (rhythm)-[:SERVES]->(purpose);

MATCH (rhythm:Rhythm {node_id: 'rhythm-prompt-ingest'})
MATCH (purpose:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (rhythm)-[:SERVES]->(purpose);

MATCH (rhythm:Rhythm {node_id: 'rhythm-trace-emit'})
MATCH (purpose:Purpose {node_id: 'purpose-learn-from-use'})
MERGE (rhythm)-[:SERVES]->(purpose);

MATCH (rhythm:Rhythm {node_id: 'rhythm-merkle-refresh'})
MATCH (purpose:Purpose {node_id: 'purpose-graph-native-authority'})
MERGE (rhythm)-[:SERVES]->(purpose);

MATCH (rhythm:Rhythm {node_id: 'rhythm-embed-dirty'})
MATCH (purpose:Purpose {node_id: 'purpose-speak-about-itself'})
MERGE (rhythm)-[:SERVES]->(purpose);


// --- Part 8: Wire Purposes to Mission ---

MATCH (purpose:Purpose)
MATCH (mission:Mission {node_id: 'mission-mycelium'})
MERGE (purpose)-[:PART_OF]->(mission);


// --- Part 9: Wire Rhythms and Mission to Ontology ---

MATCH (rhythm:Rhythm)
MATCH (ontology:Ontology {node_id: 'ontology-mycelium'})
MERGE (rhythm)-[:PART_OF]->(ontology);

MATCH (mission:Mission)
MATCH (ontology:Ontology {node_id: 'ontology-mycelium'})
MERGE (mission)-[:PART_OF]->(ontology);

WITH 'Rhythm + Purpose Layer Seeded' AS status
MATCH (r:Rhythm)
WITH status, count(r) AS rhythm_count
MATCH (p:RhythmPhase)
WITH status, rhythm_count, count(p) AS phase_count
MATCH (pu:Purpose)
WITH status, rhythm_count, phase_count, count(pu) AS purpose_count
MATCH (m:Mission)
RETURN status, rhythm_count, phase_count, purpose_count, count(m) AS mission_count;
