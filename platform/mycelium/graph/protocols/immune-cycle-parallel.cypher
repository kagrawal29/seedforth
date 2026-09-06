// @node_id: protocol-immune-cycle-parallel
// @label: "Immune Cycle Parallel — apoc.periodic.iterate runner"
// ============================================================================
// Protocol: Immune Cycle Parallel Execution (wi-v2-05)
// ============================================================================
// Parallel execution of invariant checks using apoc.periodic.iterate.
// This is the optimized version of immune-cycle.cypher using APOC's parallel
// job scheduling. Each invariant's check_cypher executes concurrently.
//
// Key design:
//   - Within a Protocol, atoms remain sequential (HAS_ATOM order preserved)
//   - Across independent Protocols/items, execution parallelizes
//   - concurrency:4 respects Neo4j thread budget on local 1G heap
//   - batchSize:10 amortizes transaction overhead
//   - parallel:true enables concurrent batch processing
//
// Metrics:
//   - Baseline (sequential immune-cycle): ~86ms
//   - Target (parallel): ~20ms (4-5x speedup)
//   - Measurement stored in QueryTrace with phase='immune-cycle-parallel'
//
// Opt-in only. Heartbeat.cypher runs sequential version by default;
// orchestrator enables this when ready. APOC.periodic.iterate can be
// restrictive (no WRITE in the per-item query), so this version evaluates
// invariants (read-only) and defers healing to separate step.
// ============================================================================

// --- Phase 1: Parallel Detection -----------------------------------------------
// Use apoc.periodic.iterate to check all invariants in parallel.
// Each item processes one invariant's check_cypher.

WITH timestamp() AS cycle_start_ms
MATCH (inv:Invariant)
WHERE inv.check_cypher IS NOT NULL
  AND inv.node_id IS NOT NULL
  AND coalesce(inv.enabled, true) = true
WITH collect(inv.node_id) AS inv_ids, cycle_start_ms

CALL apoc.periodic.iterate(
  'UNWIND $inv_ids AS inv_id RETURN inv_id',
  'MATCH (i:Invariant {node_id: inv_id})
   CALL apoc.cypher.run(i.check_cypher, {}) YIELD value
   WITH i, value, keys(value)[0] AS result_key
   WITH i, collect(value[result_key]) AS results
   RETURN i.node_id AS inv_id,
          CASE
            WHEN any(r IN results WHERE r = false) THEN "unhealthy"
            WHEN any(r IN results WHERE r IS NULL) THEN "unhealthy"
            ELSE "healthy"
          END AS health_status',
  {
    inv_ids: inv_ids,
    parallel: true,
    batchSize: 10,
    concurrency: 4
  }
) YIELD batches, total, timeTaken, committedOperations

// --- Phase 2: Record measurements -----------------------------------------------
WITH cycle_start_ms, batches, total, timeTaken, committedOperations

CREATE (qt:QueryTrace {
  node_id: 'qt-' + toString(timestamp()) + '-' + apoc.text.random(6, 'a-z0-9'),
  protocol_id: 'protocol-immune-cycle-parallel',
  phase: 'immune-cycle-parallel',
  duration_ms: timeTaken,
  wall_clock_ms: timestamp() - cycle_start_ms,
  fired_at: toString(datetime()),
  invoked_epoch_ms: timestamp(),
  batches_processed: batches,
  total_invariants: total,
  committed_ops: committedOperations,
  cypher_summary: 'Parallel invariant evaluation via apoc.periodic.iterate',
  file_type: 'query-trace'
})

// --- Phase 3: Healing (deferred, sequential) -----------------------------------
// After parallel detection, run heals sequentially. Heals are typically
// fast (create/update operations) and benefit from predictable ordering.
WITH qt
MATCH (inv:Invariant {health_status: 'unhealthy'})
WHERE inv.heal_protocol IS NOT NULL
MATCH (heal:Protocol {node_id: inv.heal_protocol})
WHERE heal.cypher IS NOT NULL AND size(heal.cypher) > 0
CALL apoc.cypher.run(heal.cypher, {}) YIELD value AS _heal_result
WITH inv, heal, qt
SET heal.fire_count = coalesce(heal.fire_count, 0) + 1,
    heal.last_fired_at = toString(datetime())

// --- Phase 4: Recheck after heals (deferred, sequential) -----------------------
WITH inv, heal, qt
CALL apoc.cypher.run(inv.check_cypher, {}) YIELD value
WITH inv, heal, qt, value, keys(value)[0] AS result_key
WITH inv, heal, qt, collect(value[result_key]) AS results
WITH inv, heal, qt,
     CASE
       WHEN any(r IN results WHERE r = false) THEN 'unhealthy'
       WHEN any(r IN results WHERE r IS NULL) THEN 'unhealthy'
       ELSE 'healthy'
     END AS post_heal_status
SET inv.health_status = post_heal_status,
    inv.heal_attempted_at = toString(datetime()),
    inv.heal_outcome = post_heal_status,
    inv.healed_by = heal.node_id

// --- Phase 5: Propose ActionProposals for unhealable unhealthy ----------------
WITH qt
MATCH (inv:Invariant {health_status: 'unhealthy'})
WHERE inv.heal_protocol IS NULL
MERGE (ap:ActionProposal {node_id: 'ap-heal-' + inv.node_id})
  ON CREATE SET ap.created_at = toString(datetime()),
                ap.reason = 'invariant unhealthy, no heal_protocol assigned',
                ap.invariant = inv.node_id,
                ap.invariant_label = coalesce(inv.label, inv.node_id),
                ap.proposed_action = 'assign heal_protocol or resolve manually',
                ap.status = 'pending'
  ON MATCH SET ap.last_seen = toString(datetime()),
               ap.status = coalesce(ap.status, 'pending')
MERGE (ap)-[:PROPOSES_HEAL_FOR]->(inv)

// --- Phase 6: Update Being.autonomous_score ------------------------------------
WITH qt
MATCH (inv:Invariant) WHERE coalesce(inv.enabled, true) = true
WITH qt, count(inv) AS total,
     sum(CASE WHEN inv.health_status = 'healthy' THEN 1 ELSE 0 END) AS healthy,
     sum(CASE WHEN inv.health_status = 'unhealthy' THEN 1 ELSE 0 END) AS unhealthy,
     sum(CASE WHEN inv.health_status = 'unknown' OR inv.health_status IS NULL THEN 1 ELSE 0 END) AS unknown
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.invariants_total = total,
    b.invariants_healthy = healthy,
    b.invariants_unhealthy = unhealthy,
    b.invariants_unknown = unknown,
    b.autonomous_score = CASE WHEN total > 0 THEN (healthy * 100 / total) ELSE 0 END,
    b.last_immune_cycle = toString(datetime()),
    b.last_immune_cycle_parallel = toString(datetime())

MERGE (qt)-[:FIRED_BY]->(p:Protocol {node_id: 'protocol-immune-cycle-parallel'})
