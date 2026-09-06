// @node_id: protocol-walk-counter
// @label: "Walk Counter (Observability protocol for INFERRED_SIMILAR usage)"
// ============================================================================
// Protocol: Walk Counter (Observability protocol for INFERRED_SIMILAR usage)
// ============================================================================
// Instruments :INFERRED_SIMILAR edges with usage tracking. Every time a query
// traverses an INFERRED_SIMILAR edge, that edge should accumulate walk_count.
//
// Since Cypher doesn't have edge-walk hooks, this protocol runs periodically
// and infers walks from recent :QueryTrace data. It reads the last N QueryTrace
// nodes and extracts touched_ids (which nodes each trace touched). For each
// pair of touched nodes, it checks if an :INFERRED_SIMILAR edge exists and
// increments walk_count + last_walked_at.
//
// Key metric: after 1000 queries, edges with walk_count > 10 are load-bearing;
// edges with walk_count = 0 are noise. The heartbeat can preferentially decay
// low-walk edges faster.
//
// Parameters:
//   since_ms      integer — only count traces fired in the last N milliseconds.
//                           Default 3600000 (1 hour).
//   batch_size    integer — max traces to examine in one run.
//                           Default 100 (safety limit).
//
// Side effects:
//   - SET r.walk_count = coalesce(r.walk_count, 0) + <count per edge>
//   - SET r.last_walked_at = timestamp()
//
// New SkipKey entries required (must be registered):
//   walk_count, last_walked_at (category: observability)
//
// Returns:
//   edges_walked      — total edges incremented in this run
//   edges_seen        — total INFERRED_SIMILAR edges in graph
//   max_walk_count    — highest walk_count observed on any edge
//   avg_walk_count    — average walk_count across all walked edges
//   traces_processed  — number of traces examined
// ============================================================================

// --- Phase 0: Register SkipKey nodes for walk tracking ----------------------

MERGE (sk:SkipKey {node_id: 'skipkey-walk_count'})
  SET sk.key = 'walk_count',
      sk.category = 'observability',
      sk.reason = 'Edge usage counter for INFERRED_SIMILAR; tracks load-bearing paths';

MERGE (sk:SkipKey {node_id: 'skipkey-last_walked_at'})
  SET sk.key = 'last_walked_at',
      sk.category = 'observability',
      sk.reason = 'Timestamp of last walk on INFERRED_SIMILAR edge';

// --- Phase 1: Collect recent QueryTrace records with touched_ids -----------

WITH
  coalesce($since_ms, 3600000) AS since_ms,
  coalesce($batch_size, 100) AS batch_size
WITH since_ms, batch_size, timestamp() - since_ms AS cutoff_ms

MATCH (qt:QueryTrace)
WHERE qt.invoked_epoch_ms >= cutoff_ms
  AND size(coalesce(qt.touched_ids, [])) > 0
WITH REDUCE(ids=[], qt IN collect(qt) | ids + qt.touched_ids) AS all_touched_flattened

// --- Phase 2: Get unique IDs and prepare pairs ---

WITH [id IN apoc.coll.toSet(all_touched_flattened) | id] AS all_touched_ids,
     size(all_touched_flattened) AS traces_processed

WITH CASE
       WHEN size(all_touched_ids) > 0
       THEN apoc.coll.combinations(all_touched_ids, 2)
       ELSE []
     END AS id_pairs,
     traces_processed

// --- Phase 2b: Guard against empty UNWIND ---

WITH id_pairs, traces_processed,
     CASE WHEN size(id_pairs) = 0 THEN [1] ELSE id_pairs END AS guard_or_pairs,
     CASE WHEN size(id_pairs) = 0 THEN true ELSE false END AS is_guarded

UNWIND guard_or_pairs AS item
WITH item, traces_processed, is_guarded,
     CASE WHEN is_guarded THEN null ELSE item END AS pair

OPTIONAL MATCH (n_a {node_id: pair[0]})-[r:INFERRED_SIMILAR]-(n_b {node_id: pair[1]})
WHERE r IS NOT NULL AND pair IS NOT NULL
SET r.walk_count = coalesce(r.walk_count, 0) + 1,
    r.last_walked_at = timestamp()

WITH count(r) AS edges_walked, traces_processed
MATCH (n1)-[rr:INFERRED_SIMILAR]-(n2)
RETURN
  edges_walked,
  count(DISTINCT rr) AS edges_seen,
  max(rr.walk_count) AS max_walk_count,
  round(avg(rr.walk_count) * 100) / 100 AS avg_walk_count,
  traces_processed,
  'walk-counter complete' AS status;
