// @node_id: protocol-system-awareness
// @label: "System Awareness — Tier 3 Heartbeat (every 100 ticks)"
// ============================================================================
// Protocol: System Awareness — Tier 3 Heartbeat (every 100 ticks)
// ============================================================================
// The graph's ability to see ALL its own gaps INSTANTLY at runtime.
// Produces a :SystemState snapshot node every Tier 3 cycle with complete vitals.
//
// Execution cadence: Tier 3 = every 100 heartbeat ticks (~8-10 minutes at default).
// IDEMPOTENT: Uses MERGE on state-${timestamp()}. Each state is immutable once created.
//
// Output: :SystemState node with 20+ dimensions measured simultaneously.
// Lifecycle: Compare to PREVIOUS state, compute deltas, raise :Question if degraded.
// Wiring: (state)-[:STATE_OF]->(:Being)
//         (state)-[:FOLLOWS_STATE]->(prev_state)
// ============================================================================

WITH timestamp() AS ts_ms,
     toString(datetime()) AS ts_iso

// Count all dimensions in a single pass
MATCH (n) WITH ts_ms, ts_iso, count(n) AS total_node_count
MATCH ()-[r]->() WITH ts_ms, ts_iso, total_node_count, count(r) AS total_edge_count

// --- Compute all statistics ---

WITH ts_ms, ts_iso, total_node_count, total_edge_count,
     // Density = edges / (nodes * (nodes - 1) / 2)
     CASE WHEN total_node_count > 1
       THEN total_edge_count * 2.0 / (total_node_count * (total_node_count - 1))
       ELSE 0.0
     END AS density_ratio

// Stale embeddings and vocabulary
OPTIONAL MATCH (n) WHERE n.embedding IS NOT NULL AND (n.embed_ts IS NULL OR n.embed_ts < ts_ms - 604800000)
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio,
     count(n) AS stale_embedding_count

OPTIONAL MATCH (w:Word) WHERE NOT w.is_stopword
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count,
     count(w) AS word_count

OPTIONAL MATCH (p:Prompt)
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count,
     count(p) AS prompt_count

OPTIONAL MATCH (bg) WHERE bg:Bigram OR (bg.entity_type = 'bigram')
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count,
     count(bg) AS bigram_count

// Walk coverage: Fraction of edges marked as walked
OPTIONAL MATCH (n1)-[r:INFERRED_SIMILAR]->(n2) WHERE r.last_walked_at IS NOT NULL
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count,
     count(r) AS walked_edges
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edges,
     CASE WHEN total_edge_count > 0 THEN (walked_edges * 100.0 / total_edge_count) ELSE 0.0 END AS walked_edge_pct

// Fractal lifecycle completeness
OPTIONAL MATCH (label_node)
WHERE (label_node:Label OR label_node.is_label = true)
  AND label_node.lifecycle_stage IS NOT NULL
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct,
     count(DISTINCT label_node.node_id) AS labels_with_lifecycle

// Health metrics: Collect status
OPTIONAL MATCH (hm:HealthMetric)
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle,
     SIZE([h IN collect(hm) WHERE h.current_status = 'healthy']) AS healthy_count,
     SIZE([h IN collect(hm) WHERE h.current_status = 'low']) AS low_count,
     SIZE([h IN collect(hm) WHERE h.current_status = 'high']) AS high_count

// Claim test status
OPTIONAL MATCH (ct:ClaimTest)
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count,
     SIZE([c IN collect(ct.current_status) WHERE c = 'pass']) AS passing_claims,
     SIZE([c IN collect(ct.current_status) WHERE c = 'fail']) AS failing_claims,
     SIZE([c IN collect(ct.current_status) WHERE c = 'untested']) AS untested_claims

// Economics: Dead and amortizing protocols
OPTIONAL MATCH (p:Protocol) WHERE p.amortization_status = 'dead'
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims,
     count(p) AS dead_protocols,
     0.0 AS total_spend_usd

OPTIONAL MATCH (p:Protocol) WHERE p.amortization_status IN ['amortizing', 'amortized']
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims, dead_protocols, total_spend_usd,
     count(p) AS amortizing_protocols

// Questions (pending, critical)
OPTIONAL MATCH (q:Question) WHERE q.status IN ['open', 'pending']
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims, dead_protocols, amortizing_protocols, total_spend_usd,
     SIZE([q_open IN collect(q.priority) WHERE q_open = 'block']) AS pending_questions_block,
     SIZE([q_warn IN collect(q.priority) WHERE q_warn = 'warn']) AS pending_questions_warn

// Connectivity: Disconnected subsystem pairs
OPTIONAL MATCH (s1:Subsystem), (s2:Subsystem) WHERE id(s1) < id(s2)
  AND NOT (s1)-[:DEPENDS_ON|:IMPLEMENTS|:METAPHOR_OF|:MEASURED_BY|:SERVES|:PART_OF|:MONITORED_BY]->(s2)
  AND NOT (s2)-[:DEPENDS_ON|:IMPLEMENTS|:METAPHOR_OF|:MEASURED_BY|:SERVES|:PART_OF|:MONITORED_BY]->(s1)
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims, dead_protocols, amortizing_protocols, total_spend_usd, pending_questions_block, pending_questions_warn,
     count(*) AS disconnected_subsystem_pairs

// Biological subsystems metrics - get current timestamp
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims, dead_protocols, amortizing_protocols, total_spend_usd, pending_questions_block, pending_questions_warn, disconnected_subsystem_pairs,
     apoc.date.currentTimestamp() AS now_ts

// Ingestion rate: prompts per hour
OPTIONAL MATCH (p:Prompt) WHERE p.created_at IS NOT NULL AND p.created_at > now_ts - 3600000
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims, dead_protocols, amortizing_protocols, total_spend_usd, pending_questions_block, pending_questions_warn, disconnected_subsystem_pairs, now_ts,
     count(p) AS ingestion_rate

// Metabolism rate: new edges per hour
OPTIONAL MATCH (n1)-[r]->(n2) WHERE r.last_touched_ms > now_ts - 3600000
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims, dead_protocols, amortizing_protocols, total_spend_usd, pending_questions_block, pending_questions_warn, disconnected_subsystem_pairs, now_ts, ingestion_rate,
     count(r) AS metabolism_rate

// Excretion rate: orphans GC'd in last hour
OPTIONAL MATCH (hb:Heartbeat) WHERE hb.timestamp_ms > now_ts - 3600000 AND hb.orphan_count IS NOT NULL
WITH ts_ms, ts_iso, total_node_count, total_edge_count, density_ratio, stale_embedding_count, word_count, prompt_count, bigram_count, walked_edge_pct, labels_with_lifecycle, healthy_count, low_count, high_count, passing_claims, failing_claims, untested_claims, dead_protocols, amortizing_protocols, total_spend_usd, pending_questions_block, pending_questions_warn, disconnected_subsystem_pairs, ingestion_rate, metabolism_rate,
     sum(hb.orphan_count) AS excretion_rate

// --- Create the SystemState snapshot node ---

MERGE (being:Being {node_id: 'being-mycelium'})

MERGE (state:SystemState {
  node_id: 'state-' + toString(ts_ms),
  measured_at: ts_iso,
  measured_ms: ts_ms
})
SET state.node_count = total_node_count,
    state.edge_count = total_edge_count,
    state.density = density_ratio,
    state.stale_embeddings = stale_embedding_count,
    state.healthy_metrics = healthy_count,
    state.low_metrics = low_count,
    state.high_metrics = high_count,
    state.passing_claims = passing_claims,
    state.failing_claims = failing_claims,
    state.untested_claims = untested_claims,
    state.dead_protocols = dead_protocols,
    state.amortizing_protocols = amortizing_protocols,
    state.total_spend_usd = total_spend_usd,
    state.pending_questions_block = pending_questions_block,
    state.pending_questions_warn = pending_questions_warn,
    state.disconnected_subsystem_pairs = disconnected_subsystem_pairs,
    state.word_count = word_count,
    state.prompt_count = prompt_count,
    state.bigram_count = bigram_count,
    state.walked_edge_pct = walked_edge_pct,
    state.labels_with_full_lifecycle = labels_with_lifecycle,
    state.ingestion_rate = ingestion_rate,
    state.metabolism_rate = metabolism_rate,
    state.excretion_rate = coalesce(excretion_rate, 0),
    state.file_type = 'system-state'

MERGE (state)-[:STATE_OF]->(being)

WITH state, being

// Compare to previous state
OPTIONAL MATCH (prev:SystemState) WHERE prev.measured_ms < state.measured_ms
WITH state, prev ORDER BY prev.measured_ms DESC LIMIT 1

WITH state, prev,
     CASE WHEN prev IS NULL THEN 0 ELSE state.node_count - prev.node_count END AS node_delta,
     CASE WHEN prev IS NULL THEN 0 ELSE state.edge_count - prev.edge_count END AS edge_delta,
     CASE WHEN prev IS NULL THEN 0.0 ELSE state.density - prev.density END AS density_delta,
     CASE WHEN prev IS NULL THEN 0 ELSE state.stale_embeddings - prev.stale_embeddings END AS stale_delta,
     CASE WHEN prev IS NULL THEN 0 ELSE state.healthy_metrics - prev.healthy_metrics END AS healthy_delta,
     CASE WHEN prev IS NULL THEN 0 ELSE state.low_metrics - prev.low_metrics END AS low_delta,
     CASE WHEN prev IS NULL THEN 0 ELSE state.high_metrics - prev.high_metrics END AS high_delta,
     CASE WHEN prev IS NULL THEN 0 ELSE state.failing_claims - prev.failing_claims END AS claims_delta,
     CASE WHEN prev IS NULL THEN 0 ELSE state.disconnected_subsystem_pairs - prev.disconnected_subsystem_pairs END AS disconnect_delta

SET state.node_delta = node_delta,
    state.edge_delta = edge_delta,
    state.density_delta = density_delta,
    state.stale_delta = stale_delta,
    state.healthy_delta = healthy_delta,
    state.low_delta = low_delta,
    state.high_delta = high_delta,
    state.claims_delta = claims_delta,
    state.disconnect_delta = disconnect_delta

// Wire state to previous state if it exists
FOREACH (ignored IN CASE WHEN prev IS NOT NULL THEN [1] ELSE [] END |
  MERGE (state)-[:FOLLOWS_STATE]->(prev)
)

// Raise Questions if significant degradation detected
FOREACH (ignored IN CASE WHEN density_delta < -0.05 THEN [1] ELSE [] END |
  MERGE (q:Question {node_id: 'q-density-drop-' + toString(state.measured_ms)})
  SET q.priority = 'warn',
      q.status = 'open',
      q.title = 'Graph density degraded > 5%',
      q.description = 'Density dropped from ' + toString(coalesce(prev.density, 0)) + ' to ' + toString(state.density),
      q.raised_by = 'system-awareness',
      q.raised_at = state.measured_at,
      q.file_type = 'question'
  MERGE (q)-[:ABOUT]->(state)
)

FOREACH (ignored IN CASE WHEN low_delta > 2 THEN [1] ELSE [] END |
  MERGE (q:Question {node_id: 'q-health-decline-' + toString(state.measured_ms)})
  SET q.priority = 'warn',
      q.status = 'open',
      q.title = 'Health metrics degraded',
      q.description = 'Low metrics increased by ' + toString(low_delta) + ', now at ' + toString(state.low_metrics),
      q.raised_by = 'system-awareness',
      q.raised_at = state.measured_at,
      q.file_type = 'question'
  MERGE (q)-[:ABOUT]->(state)
)

FOREACH (ignored IN CASE WHEN claims_delta > 1 THEN [1] ELSE [] END |
  MERGE (q:Question {node_id: 'q-claims-failing-' + toString(state.measured_ms)})
  SET q.priority = 'block',
      q.status = 'open',
      q.title = 'Claim test failures increased',
      q.description = 'Failing claims increased by ' + toString(claims_delta) + ', now at ' + toString(state.failing_claims),
      q.raised_by = 'system-awareness',
      q.raised_at = state.measured_at,
      q.file_type = 'question'
  MERGE (q)-[:ABOUT]->(state)
)

FOREACH (ignored IN CASE WHEN disconnect_delta > 1 THEN [1] ELSE [] END |
  MERGE (q:Question {node_id: 'q-subsystem-disconnect-' + toString(state.measured_ms)})
  SET q.priority = 'warn',
      q.status = 'open',
      q.title = 'Subsystem connectivity lost',
      q.description = 'Disconnected pairs increased by ' + toString(disconnect_delta),
      q.raised_by = 'system-awareness',
      q.raised_at = state.measured_at,
      q.file_type = 'question'
  MERGE (q)-[:ABOUT]->(state)
)

RETURN {
  state_id: state.node_id,
  measured_ms: state.measured_ms,
  nodes: state.node_count,
  edges: state.edge_count,
  density: state.density,
  healthy: state.healthy_metrics,
  low: state.low_metrics,
  high: state.high_metrics,
  passing_claims: state.passing_claims,
  failing_claims: state.failing_claims,
  ingestion_rate: state.ingestion_rate,
  metabolism_rate: state.metabolism_rate,
  excretion_rate: state.excretion_rate,
  questions_raised: CASE WHEN prev IS NULL THEN 0
                         ELSE (CASE WHEN density_delta < -0.05 THEN 1 ELSE 0 END +
                              CASE WHEN low_delta > 2 THEN 1 ELSE 0 END +
                              CASE WHEN claims_delta > 1 THEN 1 ELSE 0 END +
                              CASE WHEN disconnect_delta > 1 THEN 1 ELSE 0 END)
                    END
} AS result
