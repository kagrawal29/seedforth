// @node_id: protocol-heartbeat-core
// @label: "Heartbeat Core — per-tick maintenance cycle"
// ============================================================================
// Protocol: Heartbeat with Decay
// ============================================================================
// Gives the graph its breath. Updates Being.last_heartbeat and
// Being.heartbeat_count on every run. Intended to be called on a cadence
// (shell loop, systemd timer, or any external scheduler).
//
// Since this protocol now runs decay in the same tick, heartbeat frequency
// determines the decay rate. One beat = one coherent maintenance cycle.
//
// Properties touched on Being:
//   last_heartbeat          epoch ms    (timestamp())
//   last_heartbeat_at       string      ISO 8601
//   heartbeat_count         integer     monotonically increasing
//   alive                   boolean     always true after a successful beat
//
// IMPORTANT: all four properties above must be in the Merkle skip_keys list
// (see graph/protocols/skip-keys-init.cypher) so heartbeat does not churn
// root_hash. Without skip_keys, every beat would change Being's leaf_hash
// which would cascade into root_hash — making the Merkle layer worthless for
// integrity because the root would never be stable.
//
// NEW: decay properties (weight, last_touched_ms, last_fired_ms) are also
// registered as SkipKey so they don't drift the root on every tick.
//
// Idempotent by construction: it's a pure property update on a singleton,
// plus decay operations that are safe to re-run.
// ============================================================================

// --- Phase -1: Pre-declare all property tokens for APOC executor -----------
// APOC's periodic executor runs with reduced token-write permissions.
// Any attempt to create a NEW property name (never-before-seen) fails with
// AuthorizationViolation. This phase pre-touches all property names this
// protocol will set, ensuring they exist in the schema before Phase 0+.
// Pattern: MERGE a temporary anchor and SET all properties on it once.

MERGE (anchor:_SchemaAnchor {node_id: 'schema-anchor-heartbeat'})
  SET anchor.weight = 1.0,
      anchor.last_touched_ms = 0,
      anchor.last_fired_ms = 0,
      anchor.last_heartbeat = 0,
      anchor.last_heartbeat_at = '',
      anchor.heartbeat_count = 0,
      anchor.alive = true,
      anchor.key = '',
      anchor.category = '',
      anchor.reason = '',
      anchor.fire_count = 0,
      anchor.semantic_community_id = '',
      anchor.vital_node_count = 0,
      anchor.vital_edge_count = 0,
      anchor.vital_density = 0.0,
      anchor.vital_root_hash = '',
      anchor.vital_measured_at = '',
      anchor.vital_measured_ms = 0,
      anchor.vital_stale_embeddings = 0,
      anchor.current_value = 0,
      anchor.last_evaluated_at = '',
      anchor.last_duration_ms = 0,
      anchor.current_status = '',
      anchor.cosine = 0.0,
      anchor.classified_at = '',
      anchor.classifier = '',
      anchor.walk_count = 0,
      anchor.last_walked_at = 0,
      anchor.amortization_status = '',
      anchor.last_fired_at = '';

// --- Phase 0: Register new SkipKey nodes for decay properties ----------------
// Ensures weight, last_touched_ms, and last_fired_ms don't drift merkle root.

MERGE (sk:SkipKey {node_id: 'skipkey-weight'})
  SET sk.key = 'weight',
      sk.category = 'decay',
      sk.reason = 'Edge weight decays on every tick; excluded from Merkle to allow stable root during decay cycles';

MERGE (sk:SkipKey {node_id: 'skipkey-last_touched_ms'})
  SET sk.key = 'last_touched_ms',
      sk.category = 'decay',
      sk.reason = 'Edge freshness timestamp; updated when edge is created/merged, excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-last_fired_ms'})
  SET sk.key = 'last_fired_ms',
      sk.category = 'decay',
      sk.reason = 'Node firing timestamp; decremented as fire_count ages, excluded from Merkle';

// --- Phase 1: Update liveness on Being singleton ----

MERGE (b:Being {node_id: 'being-mycelium'})
SET b.last_heartbeat = timestamp(),
    b.last_heartbeat_at = toString(datetime()),
    b.heartbeat_count = coalesce(b.heartbeat_count, 0) + 1,
    b.alive = true;

// --- Phase 2a: Decay INFERRED_SIMILAR edge weights (every 100 beats) ------
// SELECTIVE decay: walked edges survive, unwalked edges die.
//
// GATED every 100 beats (~17 min at 10s cadence). Touches ~98K edges each
// time it runs — running per-tick caused GC pressure that crashed Neo4j
// around beat 78 with 1GB heap. Semantics unchanged: same decay envelope,
// just applied in larger steps. 0.999^100 ≈ 0.905 per 100 beats, so an
// unwalked edge still reaches prune threshold (0.1) in the same ~3 days.

MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
WITH b.heartbeat_count AS hb WHERE hb IS NOT NULL AND hb % 100 = 0
MATCH (n1)-[r:INFERRED_SIMILAR]->(n2)
WHERE (r.last_walked_at IS NULL OR r.last_walked_at < timestamp() - 3600000)
  AND (r.last_touched_ms IS NULL OR r.last_touched_ms < timestamp() - 1000)
SET r.weight = coalesce(r.weight, 1.0) * 0.905;

// --- Phase 2b: Prune edges below weight threshold (every 100 beats) -------
// Same gating — only meaningful immediately after decay step above.

MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
WITH b.heartbeat_count AS hb WHERE hb IS NOT NULL AND hb % 100 = 0
MATCH (n1)-[r:INFERRED_SIMILAR]->(n2)
WHERE coalesce(r.weight, 1.0) < 0.1
DELETE r;

// --- Phase 3: Stale fire_count decrement for nodes (every 100 beats) ---
// Nodes with last_fired_ms older than 30 days get fire_count decremented by 1.
// GATED every 100 beats — full 12K node scan, every-tick was wasted work for
// 30-day decay. 100 beats at 10s = ~17 min, fine granularity for monthly decay.

MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
WITH b.heartbeat_count AS hb WHERE hb IS NOT NULL AND hb % 100 = 0
MATCH (n)
WHERE (n.last_fired_ms IS NULL OR n.last_fired_ms < timestamp() - 2592000000)
  AND n.fire_count IS NOT NULL
SET n.fire_count = CASE WHEN n.fire_count > 0 THEN n.fire_count - 1 ELSE 0 END;

// --- Phase 4: Orphan garbage collection (every 100 beats) ---
// Match nodes with NO edges (in or out) that are not essential types.
// Also skip if referenced by Skill or Protocol wiring.
// GATED every 100 beats — full label-filtered scan was a major hot path on
// every tick. Orphan threshold is also 30 days, so 17-min cadence is fine.

MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
WITH b.heartbeat_count AS hb WHERE hb IS NOT NULL AND hb % 100 = 0
MATCH (orphan)
WHERE NOT orphan:Being
  AND NOT orphan:Ontology
  AND NOT orphan:Genesis
  AND NOT orphan:Word
  AND NOT orphan:SkipKey
  AND NOT orphan:Species
  AND NOT orphan:LegacySpecies
  AND NOT orphan:CanonicalSpecies
  AND NOT orphan:Witness
  AND NOT orphan:WitnessSignature
  AND NOT orphan:LegacyWitnessSignature
  AND NOT orphan:Protocol
  AND NOT orphan:Skill
  AND NOT orphan:QueryTrace
  AND NOT orphan:Concept
  AND NOT orphan:Guide
  AND NOT orphan:DesignPrinciple
  AND NOT orphan:Metaphor
  AND NOT orphan:Invariant
  AND NOT orphan:Command
  AND NOT orphan:Persona
  AND NOT orphan:Rhythm
  AND NOT orphan:RhythmPhase
  AND NOT orphan:Purpose
  AND NOT orphan:Mission
  AND NOT orphan:HealthMetric
  AND NOT orphan:Question
  AND NOT orphan:QuestionTemplate
  AND NOT orphan:Subsystem
  AND NOT orphan:Model
  AND NOT orphan:SwarmRole
  AND NOT orphan:EdgeConnective
  AND NOT orphan:TestDimension
  AND NOT orphan:ClaimTest
  AND NOT orphan:Feature
  AND NOT orphan:Research
  AND NOT orphan:Hypothesis
  AND NOT orphan:Workflow
  AND NOT orphan:APOCProcedure
  AND NOT orphan:APOCFunction
  AND NOT orphan:APOCCategory
  AND (orphan.last_modified_ms IS NULL OR orphan.last_modified_ms < timestamp() - 2592000000)
  AND NOT (orphan)-[:HAS_PARAMETER]->()
  AND NOT (orphan)<-[:HAS_PARAMETER]-()
  AND NOT (orphan)-[:WIRES]->()
  AND NOT (orphan)<-[:WIRES]-()
OPTIONAL MATCH (orphan)-[any_edge]-()
WITH orphan, count(any_edge) AS edge_count
WHERE edge_count = 0
DETACH DELETE orphan;

// --- Phase 5: Community re-propagation (every 100 beats) ---
// For each node, adopt the most common semantic_community_id among its
// INFERRED_SIMILAR neighbors. This gradually fixes the singleton problem.
// GATED every 100 beats — touches ~7-12K nodes plus their INFERRED_SIMILAR
// neighbors; was a per-tick hot path. Singleton convergence is gradual by
// nature, so 17-min cadence loses nothing.

MATCH (b:Being {node_id: 'being-mycelium'}) WITH b LIMIT 1
WITH b.heartbeat_count AS hb WHERE hb IS NOT NULL AND hb % 100 = 0
MATCH (n)
WHERE n.semantic_community_id IS NOT NULL
OPTIONAL MATCH (n)-[r:INFERRED_SIMILAR]-(neighbor)
WHERE neighbor.semantic_community_id IS NOT NULL
WITH n,
     collect(neighbor.semantic_community_id) AS neighbor_communities
WITH n, neighbor_communities,
     CASE
       WHEN size(neighbor_communities) = 0 THEN n.semantic_community_id
       ELSE neighbor_communities[0]
     END AS new_community,
     n.semantic_community_id AS old_community
WHERE new_community <> old_community
SET n.semantic_community_id = new_community;

// ============================================================================
// TIER 2: EVERY 10 TICKS (~10 min at 60s cadence)
// Measurement + freshness checks
// ============================================================================

MATCH (b:Being {node_id: 'being-mycelium'})
WITH b, b.heartbeat_count AS hb
WHERE hb % 10 = 0

// Phase 6: Vital-sign measurement — snapshot current state on Being
WITH b
MATCH (n) WITH b, count(n) AS node_count
MATCH ()-[r]->() WITH b, node_count, count(r) AS edge_count
SET b.vital_node_count = node_count,
    b.vital_edge_count = edge_count,
    b.vital_density = toFloat(edge_count) / node_count,
    b.vital_root_hash = b.root_hash,
    b.vital_measured_at = toString(datetime()),
    b.vital_measured_ms = timestamp();

// Phase 7: Embed-dirty count — flag if stale embeddings exceed threshold
// GATED every 100 beats (was every 10). Full unlabeled scan over all leaf-hashed
// nodes (~7K) was running 6x per Phase 9 cadence; once-per-100 is enough for a
// staleness counter that drives no immediate action.
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b WHERE b.heartbeat_count % 100 = 0
MATCH (n)
WHERE n.leaf_hash IS NOT NULL
  AND n.embedding IS NOT NULL
  AND n.embedding_for_leaf_hash IS NOT NULL
  AND n.leaf_hash <> n.embedding_for_leaf_hash
WITH b, count(n) AS stale_embeds
SET b.vital_stale_embeddings = stale_embeds;

// Phase 8: Amortization recount — bridge atom fire_count to Protocol
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b WHERE b.heartbeat_count % 10 = 0
MATCH (a:CypherAtom) WHERE a.source_protocol IS NOT NULL AND coalesce(a.fire_count, 0) > 0
WITH a.source_protocol AS pid, sum(a.fire_count) AS atom_fires
MATCH (p:Protocol {node_id: pid})
SET p.fire_count = atom_fires,
    p.amortization_status = CASE
      WHEN atom_fires = 0 THEN 'dead'
      WHEN atom_fires < 10 THEN 'un-amortized'
      WHEN atom_fires < 100 THEN 'amortizing'
      ELSE 'amortized'
    END;


// ============================================================================
// TIER 3: EVERY 100 TICKS (~100 min at 60s cadence)
// Deep evaluation + classification
// ============================================================================

// Phase 9: HealthMetric evaluation — run every metric's check_cypher
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b WHERE b.heartbeat_count % 100 = 0
MATCH (hm:HealthMetric) WHERE hm.check_cypher IS NOT NULL
WITH hm, timestamp() AS start_ms
CALL apoc.cypher.run(hm.check_cypher, {}) YIELD value AS row
WITH hm, row.value AS val, start_ms, timestamp() - start_ms AS duration_ms
SET hm.current_value = val,
    hm.last_evaluated_at = toString(datetime()),
    hm.last_duration_ms = duration_ms,
    hm.current_status = CASE
      WHEN val >= coalesce(hm.healthy_min, -999999) AND val <= coalesce(hm.healthy_max, 999999) THEN 'healthy'
      WHEN val < coalesce(hm.healthy_min, -999999) THEN 'low'
      ELSE 'high'
    END
CREATE (qt:QueryTrace {
  node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
  protocol_id: 'protocol-heartbeat-core',
  phase: 'health-metric-eval',
  duration_ms: duration_ms,
  fired_at: toString(datetime()),
  invoked_epoch_ms: timestamp(),
  metric_node_id: hm.node_id,
  cypher_summary: 'HealthMetric.check_cypher evaluation',
  file_type: 'query-trace'
})
MERGE (qt)-[:FIRED_BY]->(p:Protocol {node_id: 'protocol-heartbeat-core'});

// Phase 10: Semantic-classify unclassified nodes
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b WHERE b.heartbeat_count % 100 = 0
MATCH (c:Concept) WHERE c.embedding IS NOT NULL
WITH collect(c) AS concepts
MATCH (n:GraphNode)
WHERE n.embedding IS NOT NULL
  AND n.node_id IS NOT NULL
  AND NOT n:Concept AND NOT n:Guide AND NOT n:QueryTrace AND NOT n:Query
  AND NOT EXISTS { MATCH (n)-[:SEEMS_LIKE]->(:Concept) }
UNWIND concepts AS c
WITH n, c, vector.similarity.cosine(n.embedding, c.embedding) AS score
WHERE score >= 0.55
WITH n, c, score ORDER BY n.node_id, score DESC
WITH n, collect({c: c, s: score}) AS ranked
WHERE size(ranked) > 0
WITH n, ranked[0].c AS best_concept, ranked[0].s AS best_score
MERGE (n)-[r:SEEMS_LIKE]->(best_concept)
ON CREATE SET r.cosine = best_score,
              r.classified_at = toString(datetime()),
              r.classifier = 'heartbeat-auto';


// ============================================================================
// TIER 4: EVERY 1000 TICKS (~17 hours at 60s cadence)
// Deep maintenance + self-healing
// ============================================================================

// Phase 11: Trace summarization — roll up QueryTraces older than 7 days
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b WHERE b.heartbeat_count % 1000 = 0
MATCH (qt:QueryTrace)
WHERE qt.invoked_epoch_ms < timestamp() - 604800000
WITH qt LIMIT 500
DETACH DELETE qt;

// Phase 12: ClaimTest evaluation — run every claim test
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b WHERE b.heartbeat_count % 1000 = 0
MATCH (ct:ClaimTest) WHERE ct.check_cypher IS NOT NULL
WITH ct, timestamp() AS start_ms
CALL apoc.cypher.run(ct.check_cypher, {}) YIELD value AS row
WITH ct, row.value AS val, start_ms, timestamp() - start_ms AS duration_ms
SET ct.current_value = val,
    ct.last_evaluated_at = toString(datetime()),
    ct.last_duration_ms = duration_ms,
    ct.current_status = CASE
      WHEN val >= coalesce(ct.target_min, -999999) AND val <= coalesce(ct.target_max, 999999) THEN 'passing'
      ELSE 'failing'
    END
CREATE (qt:QueryTrace {
  node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
  protocol_id: 'protocol-heartbeat-core',
  phase: 'claim-test-eval',
  duration_ms: duration_ms,
  fired_at: toString(datetime()),
  invoked_epoch_ms: timestamp(),
  test_node_id: ct.node_id,
  cypher_summary: 'ClaimTest.check_cypher evaluation',
  file_type: 'query-trace'
})
MERGE (qt)-[:FIRED_BY]->(p:Protocol {node_id: 'protocol-heartbeat-core'});


// Phase 13: DREAM — the graph explores its own topology without a goal
// Mandala detection: find nodes with identical typed-edge signatures.
// These are structurally self-similar — the fractal made visible.
// Dreams heal: they surface patterns the waking graph never looked for.
// Full dream protocol (5 modes) in graph/protocols/dream.cypher runs
// standalone; this inline version runs the lightest mode on rhythm.
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b WHERE b.heartbeat_count % 1000 = 0
MATCH (n) WHERE n.node_id IS NOT NULL
OPTIONAL MATCH (n)-[r]->() WHERE type(r) <> 'INFERRED_SIMILAR'
WITH n, apoc.coll.sort(collect(DISTINCT type(r))) AS sig
WITH sig, collect(n.node_id) AS members, count(n) AS cnt
WHERE cnt >= 3 AND size(sig) >= 2
WITH sig, members, cnt LIMIT 5
CREATE (d:DreamInsight {
  node_id: 'dream-hb-' + toString(timestamp()) + '-' + toString(cnt),
  type: 'mandala',
  edge_signature: sig,
  member_count: cnt,
  sample_members: members[0..5],
  dreamed_at: toString(datetime()),
  dreamed_by: 'heartbeat-rhythm',
  file_type: 'dream-insight'
});


// ============================================================================
// SELF-WALK: The heartbeat walks its own critical edges
// ============================================================================
// The heartbeat touches Being, Invariants, HealthMetrics, Rhythms on every
// tick. Those edges are load-bearing BY DEFINITION — they're what keeps the
// graph alive. Walk-count them so selective decay never prunes them.
// This is the graph mapping its own traversals from its own scripts.

// Structural self-walk: ANY node wired to the heartbeat rhythm via
// MONITORED_BY gets its INFERRED_SIMILAR neighborhood walk-counted.
// New subsystems are automatically protected by adding one edge:
//   (:NewNode)-[:MONITORED_BY]->(:Rhythm {node_id: 'rhythm-heartbeat'})
// No code change needed. The wiring IS the enforcement.
MATCH (:Rhythm {node_id: 'rhythm-heartbeat'})<-[:MONITORED_BY]-(monitored)
MATCH (monitored)-[e:INFERRED_SIMILAR]-(neighbor)
SET e.walk_count = coalesce(e.walk_count, 0) + 1,
    e.last_walked_at = timestamp(),
    e.weight = 1.0;

// Also walk Being's own edges (Being may not have MONITORED_BY but is always core)
MATCH (b:Being {node_id: 'being-mycelium'})-[r:INFERRED_SIMILAR]-(neighbor)
SET r.walk_count = coalesce(r.walk_count, 0) + 1,
    r.last_walked_at = timestamp(),
    r.weight = 1.0;


// --- Phase 14: Immune cycle (every 10 beats) --------------------------------
// Fire the full immune cycle (detect + heal + recheck + propose + score)
// by running protocol-immune-cycle's cypher via apoc.cypher.runMany.
// Gated by `heartbeat_count % 10 = 0` so it runs once per 10 beats, not every tick.
// When the gate fails (other 9 beats), the WITH eliminates all rows and the
// downstream MATCH + CALL do not execute.
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b.heartbeat_count AS hb
WHERE hb IS NOT NULL AND hb % 10 = 0
MATCH (p:Protocol {node_id: 'protocol-immune-cycle'})
WHERE p.cypher IS NOT NULL AND size(p.cypher) > 0
WITH p, timestamp() AS start_ms
CALL apoc.cypher.runMany(p.cypher, {}) YIELD result
WITH p, count(result) AS stmts, start_ms, timestamp() - start_ms AS duration_ms
SET p.fire_count = coalesce(p.fire_count, 0) + 1,
    p.last_fired_at = toString(datetime()),
    p.last_duration_ms = duration_ms
CREATE (qt:QueryTrace {
  node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
  protocol_id: 'protocol-heartbeat-core',
  phase: 'immune-cycle-fire',
  duration_ms: duration_ms,
  fired_at: toString(datetime()),
  invoked_epoch_ms: timestamp(),
  fired_protocol_id: p.node_id,
  stmt_count: stmts,
  cypher_summary: 'protocol-immune-cycle.cypher via apoc.cypher.runMany',
  file_type: 'query-trace'
})
MERGE (qt)-[:FIRED_BY]->(p);


// --- Final Summary Report ---

MATCH (b:Being)
WITH b.heartbeat_count AS heartbeat_count_new, b.root_hash AS root_hash_before
MATCH ()-[r:INFERRED_SIMILAR]->()
WITH heartbeat_count_new, root_hash_before, count(r) AS inferred_edges_remaining

RETURN
  heartbeat_count_new,
  inferred_edges_remaining,
  root_hash_before,
  'heartbeat tick with decay complete' AS status;
