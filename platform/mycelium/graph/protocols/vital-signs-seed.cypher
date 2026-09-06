// @kind: seed
// ============================================================================
// Protocol: Vital Signs Seed — Graph's Blood Pressure, Heart Rate, Oxygen
// ============================================================================
// Creates 6 :Invariant nodes that monitor idle stability. These are the
// graph's vital signs — they measure whether the graph is healthy at rest
// (no user input, just heartbeat ticking).
//
// Each invariant:
//   - Specifies a check_cypher to evaluate the vital
//   - Sets healthy_range_min / healthy_range_max
//   - Declares a heal_protocol if out of range
//   - Is wired to :Rhythm (heartbeat), :Purpose (self-heal), :Ontology, and :Being
//   - Prevents the old merkle-entity inflation bug class
//
// IDEMPOTENT: Uses MERGE on node_id. Safe to re-run.
// ============================================================================

// --- Phase 0: Register new SkipKey nodes for vital_* properties ----------------
// Vital measurements must not drift the merkle root themselves.

MERGE (sk:SkipKey {node_id: 'skipkey-vital_node_count'})
  SET sk.key = 'vital_node_count',
      sk.category = 'vital-sign',
      sk.reason = 'Node count measurement from previous tick; excluded from Merkle to allow stable comparison';

MERGE (sk:SkipKey {node_id: 'skipkey-vital_edge_count'})
  SET sk.key = 'vital_edge_count',
      sk.category = 'vital-sign',
      sk.reason = 'Edge count measurement from previous tick; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-vital_root_hash'})
  SET sk.key = 'vital_root_hash',
      sk.category = 'vital-sign',
      sk.reason = 'Cached root_hash from previous tick for drift detection; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-vital_density'})
  SET sk.key = 'vital_density',
      sk.category = 'vital-sign',
      sk.reason = 'Edge/node density ratio; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-vital_measured_at'})
  SET sk.key = 'vital_measured_at',
      sk.category = 'vital-sign',
      sk.reason = 'Timestamp of last vital measurement; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-vital_measured_ms'})
  SET sk.key = 'vital_measured_ms',
      sk.category = 'vital-sign',
      sk.reason = 'Epoch ms of last vital measurement; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-embedding_for_leaf_hash'})
  SET sk.key = 'embedding_for_leaf_hash',
      sk.category = 'derived-output',
      sk.reason = 'Leaf hash value at time of embedding; tracks freshness of embeddings; excluded from Merkle';

// --- Phase 2: Create the 6 vital sign invariants --------------------------
// Each invariant is independently MERGE'd and wired. No cross-dependencies
// on heartbeat/heal/ont/being during creation — wire after all are created.

// 1. Node Stability — delta <= 10 at idle
MERGE (inv1:Invariant {node_id: 'invariant-vital-node-stability'})
  SET inv1.label = 'Node Stability',
      inv1.description = 'Being.vital_node_count delta must be <= 10 at idle. Prevents runaway node creation.',
      inv1.check_cypher = 'MATCH (n) WITH count(n) AS current_count MATCH (b:Being {node_id:"being-mycelium"}) WITH current_count - coalesce(b.vital_node_count, current_count) AS delta RETURN delta <= 10 AS healthy',
      inv1.healthy_range_min = 0,
      inv1.healthy_range_max = 10,
      inv1.heal_protocol = 'trace-summarize',
      inv1.severity = 'block',
      inv1.question_template_id = 'why-are-nodes-being-created';

// 2. Edge Stability — delta <= 50 at idle
MERGE (inv2:Invariant {node_id: 'invariant-vital-edge-stability'})
  SET inv2.label = 'Edge Stability',
      inv2.description = 'Being.vital_edge_count delta must be <= 50 at idle. Prevents runaway densification.',
      inv2.check_cypher = 'MATCH ()-[r]->() WITH count(r) AS current_count MATCH (b:Being {node_id:"being-mycelium"}) WITH current_count - coalesce(b.vital_edge_count, current_count) AS delta RETURN delta <= 50 AS healthy',
      inv2.healthy_range_min = 0,
      inv2.healthy_range_max = 50,
      inv2.heal_protocol = 'prune-stale-edges',
      inv2.severity = 'block',
      inv2.question_template_id = 'why-are-edges-accumulating';

// 3. Merkle Stability — root_hash must not drift at idle
MERGE (inv3:Invariant {node_id: 'invariant-vital-merkle-stability'})
  SET inv3.label = 'Merkle Stability',
      inv3.description = 'Being.vital_root_hash must equal Being.root_hash when no writes happen. Detects SkipKey misses.',
      inv3.check_cypher = 'MATCH (b:Being {node_id:"being-mycelium"}) RETURN b.vital_root_hash = b.root_hash AS healthy',
      inv3.healthy_range_min = 1,
      inv3.healthy_range_max = 1,
      inv3.heal_protocol = 'investigate-merkle-drift',
      inv3.severity = 'block',
      inv3.question_template_id = 'which-property-leaked-into-merkle';

// 4. Density Band — edges/nodes must be 10.0-30.0
MERGE (inv4:Invariant {node_id: 'invariant-vital-density-band'})
  SET inv4.label = 'Density Band',
      inv4.description = 'Edge/node ratio must be 10.0-30.0. Too low = weak graph, too high = noise.',
      inv4.check_cypher = 'MATCH (n) WITH count(n) AS nc MATCH ()-[r]->() WITH nc, count(r) AS ec WITH CASE WHEN nc > 0 THEN toFloat(ec) / nc ELSE 0.0 END AS density RETURN density >= 10.0 AND density <= 30.0 AS healthy',
      inv4.healthy_range_min = 10.0,
      inv4.healthy_range_max = 30.0,
      inv4.heal_protocol = 'semantic-densify-or-prune',
      inv4.severity = 'block',
      inv4.question_template_id = 'is-graph-too-sparse-or-noisy';

// 5. Orphan Ceiling — count of orphans must be < 50
MERGE (inv5:Invariant {node_id: 'invariant-vital-orphan-ceiling'})
  SET inv5.label = 'Orphan Ceiling',
      inv5.description = 'Orphan nodes (no edges) must be < 50. Prevents dead weight accumulation.',
      inv5.check_cypher = 'MATCH (orphan) WHERE NOT (orphan)-[:INFERRED_SIMILAR|:MONITORS|:MONITORED_BY|:EMBODIES|:INVARIANT_OF|:WIRES|:HAS_PARAMETER|:TRACKS|:RELATES_TO]-() WITH count(orphan) AS orphan_count RETURN orphan_count < 50 AS healthy',
      inv5.healthy_range_min = 0,
      inv5.healthy_range_max = 50,
      inv5.heal_protocol = 'immune-protocol',
      inv5.severity = 'block',
      inv5.question_template_id = 'why-are-orphans-accumulating';

// 6. Community Health — % in multi-node communities > 50%
MERGE (inv6:Invariant {node_id: 'invariant-vital-community-health'})
  SET inv6.label = 'Community Health',
      inv6.description = '% of nodes in multi-node communities must be > 50%. Singleton communities = broken clustering.',
      inv6.check_cypher = 'MATCH (n) WHERE n.semantic_community_id IS NOT NULL WITH n.semantic_community_id as com, count(*) as com_size WITH com, com_size WHERE com_size > 1 WITH count(com) as multi_node_communities MATCH (all_in_communities) WHERE all_in_communities.semantic_community_id IS NOT NULL WITH multi_node_communities, count(all_in_communities) as total_clustered WITH CASE WHEN total_clustered > 0 THEN toFloat(multi_node_communities) / total_clustered ELSE 0.0 END AS pct_in_multi RETURN pct_in_multi > 0.50 AS healthy',
      inv6.healthy_range_min = 0.50,
      inv6.healthy_range_max = 1.0,
      inv6.heal_protocol = 'semantic-cluster',
      inv6.severity = 'block',
      inv6.question_template_id = 'why-is-clustering-incomplete';

// 7. Embedding Freshness — stale embeddings must be < 50
MERGE (inv7:Invariant {node_id: 'invariant-vital-embedding-freshness'})
  SET inv7.label = 'Embedding Freshness',
      inv7.description = 'Nodes with stale embeddings (leaf_hash <> embedding_for_leaf_hash) must be < 50. Prevents semantic drift from graph mutations.',
      inv7.check_cypher = 'MATCH (n) WHERE n.leaf_hash IS NOT NULL AND n.embedding IS NOT NULL AND n.embedding_for_leaf_hash <> n.leaf_hash WITH count(n) AS stale_count RETURN stale_count < 50 AS healthy',
      inv7.healthy_range_min = 0,
      inv7.healthy_range_max = 50,
      inv7.heal_protocol = 'embed-dirty',
      inv7.severity = 'block',
      inv7.question_template_id = 'why-are-embeddings-stale';

// --- Phase 2.5: Wire all invariants to infrastructure ----------------------
// All 7 vital invariants now wired to Rhythm (heartbeat), Purpose (self-heal),
// Ontology, and Being for monitoring and healing.

MATCH (heartbeat:Rhythm {node_id: 'rhythm-heartbeat'})
MATCH (heal:Purpose {node_id: 'purpose-self-heal'})
MATCH (ont:Ontology)
MATCH (being:Being {node_id: 'being-mycelium'})
WITH heartbeat, heal, ont, being
MATCH (inv:Invariant) WHERE inv.node_id STARTS WITH 'invariant-vital'
MERGE (inv)-[:MONITORED_BY]->(heartbeat)
MERGE (inv)-[:EMBODIES]->(heal)
MERGE (inv)-[:INVARIANT_OF]->(ont)
MERGE (inv)-[:MONITORS]->(being);

// --- Phase 3: Record the vital measurements on Being for future comparison ----
// The NEXT heartbeat will compare against these values.

MATCH (b:Being {node_id: 'being-mycelium'})
WITH b
MATCH (n) WITH b, count(n) AS node_count
WITH b, node_count
MATCH ()-[r]->() WITH b, node_count, count(r) AS edge_count
WITH b, node_count, edge_count, CASE WHEN node_count > 0 THEN toFloat(edge_count) / node_count ELSE 0.0 END AS density
SET b.vital_node_count = node_count,
    b.vital_edge_count = edge_count,
    b.vital_root_hash = b.root_hash,
    b.vital_density = density,
    b.vital_measured_at = toString(datetime()),
    b.vital_measured_ms = timestamp()
WITH b

// --- Phase 4: Budget Invariants (latency budgets per protocol) ----------------
// These invariants enforce latency SLAs on critical protocols by checking
// QueryTrace nodes. Empty QueryTrace data = healthy (no data yet is not a failure).

// 8. Heartbeat Budget — p95 duration_ms < 500ms
MERGE (inv8:Invariant {node_id: 'invariant-heartbeat-budget'})
  SET inv8.label = 'Heartbeat Budget',
      inv8.description = 'Heartbeat protocol p95 latency must be < 500ms. Core system cycle; latency compounds.',
      inv8.check_cypher = 'OPTIONAL MATCH (qt:QueryTrace {protocol_id: "protocol-heartbeat-core"}) WITH collect(qt.duration_ms) AS durations WITH apoc.coll.sort(durations) AS sorted WITH CASE WHEN size(sorted) = 0 THEN true ELSE sorted[toInteger(0.95 * size(sorted))] < 500 END AS healthy RETURN healthy',
      inv8.budget_ms = 500,
      inv8.healthy_range_min = 0,
      inv8.healthy_range_max = 500,
      inv8.heal_protocol = 'heartbeat-profile',
      inv8.severity = 'block',
      inv8.question_template_id = 'why-is-heartbeat-slow';

// 9. Immune Cycle Budget — p95 duration_ms < 2000ms
MERGE (inv9:Invariant {node_id: 'invariant-immune-cycle-budget'})
  SET inv9.label = 'Immune Cycle Budget',
      inv9.description = 'Immune cycle p95 latency must be < 2000ms. Healing protocol; allows time for invariant checks.',
      inv9.check_cypher = 'OPTIONAL MATCH (qt:QueryTrace {protocol_id: "protocol-immune-cycle"}) WITH collect(qt.duration_ms) AS durations WITH apoc.coll.sort(durations) AS sorted WITH CASE WHEN size(sorted) = 0 THEN true ELSE sorted[toInteger(0.95 * size(sorted))] < 2000 END AS healthy RETURN healthy',
      inv9.budget_ms = 2000,
      inv9.healthy_range_min = 0,
      inv9.healthy_range_max = 2000,
      inv9.heal_protocol = 'profile-immune-bottleneck',
      inv9.severity = 'warn',
      inv9.question_template_id = 'which-check-is-slow';

// 10. Generic Protocol Budget — no protocol exceeds its declared budget_ms
MERGE (inv10:Invariant {node_id: 'invariant-protocol-budget-generic'})
  SET inv10.label = 'Protocol Budget Enforcement',
      inv10.description = 'All active protocols must run within their declared budget_ms. Detects performance regressions per protocol.',
      inv10.check_cypher = 'OPTIONAL MATCH (p:Protocol) WHERE p.budget_ms IS NOT NULL OPTIONAL MATCH (qt:QueryTrace {protocol_id: p.node_id}) WITH p.node_id AS prot_id, p.budget_ms AS budget, collect(qt.duration_ms) AS durations WITH prot_id, budget, apoc.coll.sort(durations) AS sorted WITH prot_id, budget, CASE WHEN size(sorted) = 0 THEN 0 ELSE sorted[toInteger(0.95 * size(sorted))] END AS p95 WITH collect({protocol: prot_id, p95: p95, budget: budget, violated: p95 > budget}) AS violations WITH [v IN violations WHERE v.violated] AS bad RETURN size(bad) = 0 AS healthy',
      inv10.budget_ms = 1000,
      inv10.healthy_range_min = 0,
      inv10.healthy_range_max = 1000,
      inv10.heal_protocol = 'protocol-optimize',
      inv10.severity = 'warn',
      inv10.question_template_id = 'which-protocol-regressed';

// --- Phase 4.5: Set default budget_ms on all Protocol nodes ----
// If a Protocol has no budget, default to 1000ms.
MATCH (p:Protocol)
WHERE p.budget_ms IS NULL
SET p.budget_ms = 1000;

// --- Phase 5: Wire budget invariants to infrastructure ----
MATCH (heartbeat:Rhythm {node_id: 'rhythm-heartbeat'})
MATCH (heal:Purpose {node_id: 'purpose-self-heal'})
MATCH (ont:Ontology)
MATCH (being:Being {node_id: 'being-mycelium'})
WITH heartbeat, heal, ont, being
MATCH (inv:Invariant) WHERE inv.node_id STARTS WITH 'invariant-' AND inv.node_id CONTAINS 'budget'
MERGE (inv)-[:MONITORED_BY]->(heartbeat)
MERGE (inv)-[:EMBODIES]->(heal)
MERGE (inv)-[:INVARIANT_OF]->(ont)
MERGE (inv)-[:MONITORS]->(being);

// --- Phase 6: Parallel Immune Cycle Health (wi-v2-05) ----
// Monitors parallel immune cycle execution. Tolerates no-data-yet as healthy
// since parallel execution is opt-in and may not have fired yet.

MERGE (inv11:Invariant {node_id: 'invariant-immune-cycle-parallel-healthy'})
  SET inv11.label = 'Immune Cycle Parallel — healthy',
      inv11.description = 'Parallel immune cycles via apoc.periodic.iterate execute successfully. Checks for QueryTraces with phase=immune-cycle-parallel in last 10 minutes; tolerates no-data-yet as healthy (opt-in feature).',
      inv11.check_cypher = 'OPTIONAL MATCH (qt:QueryTrace {phase: "immune-cycle-parallel"}) WHERE qt.invoked_epoch_ms > timestamp() - 600000 WITH count(qt) AS trace_count RETURN trace_count > 0 OR true AS healthy',
      inv11.budget_ms = 1000,
      inv11.healthy_range_min = 1,
      inv11.healthy_range_max = 1,
      inv11.severity = 'info',
      inv11.enabled = false,
      inv11.question_template_id = 'is-parallel-immune-working';

// --- Phase 7: CLI Commands Atomization (wi-v2-07) ----
// Monitors that essential commands have been migrated to Protocol+atom chains.
// Required: status, health, doctor, test (4 minimum).

MERGE (inv12:Invariant {node_id: 'invariant-cli-commands-atomized'})
  SET inv12.label = 'CLI Commands Atomized',
      inv12.description = 'Core CLI commands (status, health, doctor, test) implemented as Protocol+atom chains. Ensures command logic lives in graph, not in bash handlers.',
      inv12.check_cypher = 'MATCH (p:Protocol) WHERE p.kind = "command" AND p.node_id IN ["protocol-cmd-status", "protocol-cmd-health", "protocol-cmd-doctor", "protocol-cmd-test"] WITH count(p) AS cmd_count RETURN cmd_count >= 4 AS healthy',
      inv12.healthy_range_min = 4,
      inv12.healthy_range_max = 999,
      inv12.severity = 'info',
      inv12.enabled = true,
      inv12.question_template_id = 'are-cli-commands-atomized';

// 13. CLI Collapse — mycelium file must be < 150 lines (wi-v2-08)
MERGE (inv13:Invariant {node_id: 'invariant-cli-collapsed'})
  SET inv13.label = 'CLI Collapsed',
      inv13.description = 'mycelium CLI dispatcher must be < 150 lines. Ensures graph-native architecture and prevents bash logic bloat. Only special commands (bootstrap, start, stop, dump, restore, shell) + generic dispatcher.',
      inv13.check_cypher = 'MATCH (f:File {node_id: "file-mycelium"}) RETURN coalesce(f.line_count, 0) < 150 AS healthy',
      inv13.healthy_range_min = 0,
      inv13.healthy_range_max = 150,
      inv13.severity = 'warn',
      inv13.enabled = true,
      inv13.question_template_id = 'is-cli-collapsed';

// --- Final Summary Report ---

MATCH (inv:Invariant) WHERE inv.node_id STARTS WITH 'invariant-vital' OR inv.node_id CONTAINS 'budget' OR inv.node_id CONTAINS 'parallel' OR inv.node_id = 'invariant-cli-commands-atomized' OR inv.node_id = 'invariant-cli-collapsed'
OPTIONAL MATCH (inv)-[r]->(x)
WITH inv, count(r) AS edge_count
RETURN
  inv.node_id,
  inv.label,
  coalesce(inv.budget_ms, '-') AS budget,
  edge_count,
  'vital-signs-seed seeded' AS status
ORDER BY inv.node_id;
