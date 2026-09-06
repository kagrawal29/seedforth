// @node_id: protocol-strengthen-edges
// @label: "Strengthen Edges (Phase 14c — Hebbian edge accumulation)"
// ============================================================================
// Protocol: Strengthen Edges (Phase 14c — Hebbian edge accumulation)
// ============================================================================
// Walks recent :Query and :QueryTrace records, accumulates evidence about
// which edges were traversed, and increments r.fire_count + r.last_fired_at
// on those edges. Over repeated calls, hot paths compound weight; cold paths
// stay flat.
//
// Intent: the graph learns a preference over its own edges. A query planner
// or traversal helper can then ORDER BY r.fire_count DESC to follow the
// paths the system has historically used. "Neurons that fire together wire
// together" — and once wired, the next fire prefers them.
//
// Implementation: this first version is coarse. It increments fire_count
// on EVERY edge incident to nodes that were cited in a recent QueryTrace's
// touched_ids list. Finer granularity (which specific edge the cypher
// traversed) would require Neo4j PROFILE output parsing, which isn't
// available from inside a cypher session.
//
// Parameters (optional):
//   lookback_min    integer — how many minutes of QueryTrace history to
//                              consider. Default 60.
//   increment       integer — how much to add per observed traversal.
//                              Default 1.
//
// Side effects:
//   - SET r.fire_count = coalesce(r.fire_count, 0) + increment
//   - SET r.last_fired_at = toString(datetime())
//
// New SkipKey entries required (already added):
//   fire_count, last_fired_at (category: hebbian)
// ============================================================================

WITH
  coalesce($lookback_min, 60) AS lookback_min,
  coalesce($increment, 1) AS increment
WITH lookback_min, increment,
     timestamp() - (lookback_min * 60 * 1000) AS since_ms

// --- Step 1: find recent QueryTraces with non-empty touched_ids -------------
MATCH (qt:QueryTrace)
WHERE qt.invoked_epoch_ms >= since_ms
  AND size(coalesce(qt.touched_ids, [])) > 0
WITH increment, collect(DISTINCT qt.touched_ids) AS all_touched_lists

// --- Step 2: flatten to a distinct set of touched node_ids -----------------
UNWIND all_touched_lists AS touched_list
UNWIND touched_list AS touched_id
WITH increment, collect(DISTINCT touched_id) AS touched_ids_distinct
WHERE size(touched_ids_distinct) > 0

// --- Step 3: find edges between pairs of touched nodes ---------------------
MATCH (a)-[r]-(b)
WHERE a.node_id IN touched_ids_distinct
  AND b.node_id IN touched_ids_distinct
  AND a.node_id < b.node_id  // canonical ordering to avoid double-counting
WITH r, increment

// --- Step 4: bump the edge counter ------------------------------------------
SET r.fire_count = coalesce(r.fire_count, 0) + increment,
    r.last_fired_at = toString(datetime())

RETURN count(r) AS edges_strengthened;
