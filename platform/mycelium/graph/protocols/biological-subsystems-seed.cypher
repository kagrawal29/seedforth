// @kind: seed
// ============================================================================
// Protocol: Biological Subsystems Seed
// ============================================================================
// Maps the 3 biological subsystems (ingestion, metabolism, excretion)
// as first-class graph citizens with full wiring to protocols, metaphors,
// health metrics, purposes, and the heartbeat rhythm.
//
// IDEMPOTENT: All operations use MERGE. Safe to re-run.
// Wiring pattern: (:Subsystem)-[edge_type]->(:Target)
//
// The three subsystems:
//  1. subsystem-ingestion — "How data enters the graph"
//  2. subsystem-metabolism — "How raw data is transformed into structure"
//  3. subsystem-excretion — "How waste is removed and graph stays clean"
// ============================================================================

// --- Phase 0: Get reference nodes (ontology, heartbeat, metaphors, purposes) ---

MATCH (ontology:Ontology {node_id: 'ontology-mycelium'})
MATCH (hb:Rhythm {node_id: 'rhythm-heartbeat'})
MATCH (m_cell:Metaphor {node_id: 'metaphor-cell'})
MATCH (m_synapse:Metaphor {node_id: 'metaphor-synapse'})
MATCH (m_immune:Metaphor {node_id: 'metaphor-immune'})
MATCH (p_learn:Purpose {node_id: 'purpose-learn-from-use'})
MATCH (p_dense:Purpose {node_id: 'purpose-dense-by-design'})
MATCH (p_heal:Purpose {node_id: 'purpose-self-heal'})

WITH ontology, hb, m_cell, m_synapse, m_immune, p_learn, p_dense, p_heal

// --- Phase 1: Create SUBSYSTEM-INGESTION ---
// "How data enters the graph"

MERGE (sub_ingest:Subsystem {node_id: 'subsystem-ingestion'})
SET sub_ingest.name = 'ingestion',
    sub_ingest.description = 'How data enters the graph: prompts, vocabulary, traces, raw signals. The membrane intake.',
    sub_ingest.metaphor_concept = 'Cell membrane intake',
    sub_ingest.file_type = 'subsystem'

// Wire ingestion to its implementing protocols
MERGE (proto_prompt:Protocol {node_id: 'protocol-prompt-ingest'})
SET proto_prompt.name = 'prompt-ingest'
MERGE (sub_ingest)-[:IMPLEMENTS]->(proto_prompt)

MERGE (proto_vocab:Protocol {node_id: 'protocol-vocabulary-backfill'})
SET proto_vocab.name = 'vocabulary-backfill'
MERGE (sub_ingest)-[:IMPLEMENTS]->(proto_vocab)

MERGE (proto_apoc:Protocol {node_id: 'protocol-apoc-ingest'})
SET proto_apoc.name = 'apoc-ingest'
MERGE (sub_ingest)-[:IMPLEMENTS]->(proto_apoc)

MERGE (proto_trace:Protocol {node_id: 'protocol-emit-trace'})
SET proto_trace.name = 'emit-trace'
MERGE (sub_ingest)-[:IMPLEMENTS]->(proto_trace)

// Wire ingestion to metaphor (cell membrane)
MERGE (sub_ingest)-[:METAPHOR_OF]->(m_cell)

// Wire ingestion to health metrics
MERGE (hm_vocab:HealthMetric {node_id: 'hm-vocabulary-word-count'})
MERGE (sub_ingest)-[:MEASURED_BY]->(hm_vocab)

MERGE (hm_prompt_res:HealthMetric {node_id: 'hm-vocabulary-prompt-resolution-rate'})
MERGE (sub_ingest)-[:MEASURED_BY]->(hm_prompt_res)

// Wire ingestion to purpose
MERGE (sub_ingest)-[:SERVES]->(p_learn)

// Wire ingestion to ontology
MERGE (sub_ingest)-[:PART_OF]->(ontology)

// Wire ingestion to heartbeat for monitoring
MERGE (sub_ingest)-[:MONITORED_BY]->(hb)

// --- Phase 2: Create SUBSYSTEM-METABOLISM ---
// "How raw data is transformed into structure"

MERGE (sub_metab:Subsystem {node_id: 'subsystem-metabolism'})
SET sub_metab.name = 'metabolism',
    sub_metab.description = 'How raw data is transformed into structure: densification, classification, clustering, composition. The synapse forming.',
    sub_metab.metaphor_concept = 'Synapse formation and plasticity',
    sub_metab.file_type = 'subsystem'

// Wire metabolism to its implementing protocols
MERGE (proto_densify:Protocol {node_id: 'protocol-semantic-densify'})
SET proto_densify.name = 'semantic-densify'
MERGE (sub_metab)-[:IMPLEMENTS]->(proto_densify)

MERGE (proto_classify:Protocol {node_id: 'protocol-semantic-classify'})
SET proto_classify.name = 'semantic-classify'
MERGE (sub_metab)-[:IMPLEMENTS]->(proto_classify)

MERGE (proto_cluster:Protocol {node_id: 'protocol-semantic-cluster'})
SET proto_cluster.name = 'semantic-cluster'
MERGE (sub_metab)-[:IMPLEMENTS]->(proto_cluster)

MERGE (proto_atomize:Protocol {node_id: 'protocol-atomize-protocol'})
SET proto_atomize.name = 'atomize-protocol'
MERGE (sub_metab)-[:IMPLEMENTS]->(proto_atomize)

MERGE (proto_embed:Protocol {node_id: 'protocol-embed-dirty'})
SET proto_embed.name = 'embed-dirty'
MERGE (sub_metab)-[:IMPLEMENTS]->(proto_embed)

MERGE (proto_compose:Protocol {node_id: 'protocol-compose-reply'})
SET proto_compose.name = 'compose-reply'
MERGE (sub_metab)-[:IMPLEMENTS]->(proto_compose)

// Wire metabolism to metaphor (synapse)
MERGE (sub_metab)-[:METAPHOR_OF]->(m_synapse)

// Wire metabolism to health metrics
MERGE (hm_atom_live:HealthMetric {node_id: 'hm-atom-liveness'})
MERGE (sub_metab)-[:MEASURED_BY]->(hm_atom_live)

MERGE (hm_embed:HealthMetric {node_id: 'hm-embedding-coverage'})
MERGE (sub_metab)-[:MEASURED_BY]->(hm_embed)

// Wire metabolism to purpose
MERGE (sub_metab)-[:SERVES]->(p_dense)

// Wire metabolism to ontology
MERGE (sub_metab)-[:PART_OF]->(ontology)

// Wire metabolism to heartbeat for monitoring
MERGE (sub_metab)-[:MONITORED_BY]->(hb)

// --- Phase 3: Create SUBSYSTEM-EXCRETION ---
// "How waste is removed and the graph stays clean"

MERGE (sub_excr:Subsystem {node_id: 'subsystem-excretion'})
SET sub_excr.name = 'excretion',
    sub_excr.description = 'How waste is removed and graph stays clean: orphan GC, trace summarization, stale decay, question backlog management. The immune system.',
    sub_excr.metaphor_concept = 'Immune system cleanup and defense',
    sub_excr.file_type = 'subsystem'

// Wire excretion to its implementing protocols
// Heartbeat phases 2-4 handle decay
MERGE (proto_heartbeat:Protocol {node_id: 'protocol-heartbeat'})
SET proto_heartbeat.name = 'heartbeat'
MERGE (sub_excr)-[:IMPLEMENTS]->(proto_heartbeat)

MERGE (proto_trace_summ:Protocol {node_id: 'protocol-trace-summarize'})
SET proto_trace_summ.name = 'trace-summarize'
MERGE (sub_excr)-[:IMPLEMENTS]->(proto_trace_summ)

MERGE (proto_walk_counter:Protocol {node_id: 'protocol-walk-counter'})
SET proto_walk_counter.name = 'walk-counter'
MERGE (sub_excr)-[:IMPLEMENTS]->(proto_walk_counter)

// Wire excretion to metaphor (immune)
MERGE (sub_excr)-[:METAPHOR_OF]->(m_immune)

// Wire excretion to health metrics
MERGE (hm_trace_accum:HealthMetric {node_id: 'hm-trace-accumulation'})
SET hm_trace_accum.name = 'trace-accumulation',
    hm_trace_accum.layer = 'housekeeping',
    hm_trace_accum.description = 'Count of Trace nodes accumulated (should decay over time)',
    hm_trace_accum.check_cypher = 'MATCH (t:Trace) RETURN count(t) AS value',
    hm_trace_accum.healthy_min = 0,
    hm_trace_accum.healthy_max = 10000,
    hm_trace_accum.unit = 'count',
    hm_trace_accum.file_type = 'health-metric'
MERGE (sub_excr)-[:MEASURED_BY]->(hm_trace_accum)

MERGE (hm_question_backlog:HealthMetric {node_id: 'hm-question-backlog'})
SET hm_question_backlog.name = 'question-backlog',
    hm_question_backlog.layer = 'autonomy',
    hm_question_backlog.description = 'Count of open Question nodes raised by system (self-awareness alerts)',
    hm_question_backlog.check_cypher = 'MATCH (q:Question {status: "open"}) RETURN count(q) AS value',
    hm_question_backlog.healthy_min = 0,
    hm_question_backlog.healthy_max = 100,
    hm_question_backlog.unit = 'count',
    hm_question_backlog.file_type = 'health-metric'
MERGE (sub_excr)-[:MEASURED_BY]->(hm_question_backlog)

// Wire excretion to purpose
MERGE (sub_excr)-[:SERVES]->(p_heal)

// Wire excretion to ontology
MERGE (sub_excr)-[:PART_OF]->(ontology)

// Wire excretion to heartbeat for monitoring
MERGE (sub_excr)-[:MONITORED_BY]->(hb)

// --- Phase 4: Create cross-subsystem dependency wiring ---
// The three subsystems form a functional pipeline

MERGE (sub_ingest)-[:FLOWS_TO]->(sub_metab)
MERGE (sub_metab)-[:FLOWS_TO]->(sub_excr)
MERGE (sub_excr)-[:FLOWS_TO]->(sub_ingest)  // Circular: cleanup enables intake

// --- Phase 5: Return summary ---

RETURN {
  subsystems_created: 3,
  subsystem_ingestion: {
    node_id: 'subsystem-ingestion',
    protocols: 4,
    health_metrics: 2,
    metaphor: 'metaphor-cell',
    purpose: 'purpose-learn-from-use'
  },
  subsystem_metabolism: {
    node_id: 'subsystem-metabolism',
    protocols: 6,
    health_metrics: 2,
    metaphor: 'metaphor-synapse',
    purpose: 'purpose-dense-by-design'
  },
  subsystem_excretion: {
    node_id: 'subsystem-excretion',
    protocols: 3,
    health_metrics: 2,
    metaphor: 'metaphor-immune',
    purpose: 'purpose-self-heal'
  },
  total_protocol_edges: 13,
  total_metric_edges: 6,
  total_subsystem_edges: 3,
  cross_subsystem_flow: 3,
  idempotent_merge_count: 'all nodes'
} AS summary
