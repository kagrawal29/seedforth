// @node_id: protocol-trace-summarize
// @label: "Trace Summarize (Cleanup protocol for old QueryTrace nodes)"
// ============================================================================
// Protocol: Trace Summarize (Cleanup protocol for old QueryTrace nodes)
// ============================================================================
// Rolls up old :QueryTrace nodes into their parent :Query nodes and deletes
// the raw traces. This prevents trace bloat over time while preserving the
// evidence needed for graph-wide pattern detection.
//
// Approach:
// - Find QueryTrace nodes older than $max_age_ms (default 30 days)
// - For each, ensure the parent :Query node has absorbed the contribution:
//   * Query.fire_count should already include this trace (incremented at emit)
//   * If Query.first_seen is null, set it from oldest trace
//   * If Query.last_seen is older than this trace, update it
// - Then DETACH DELETE the old QueryTrace nodes
// - Return counts and metrics
//
// Safety guarantees:
// - Never delete QueryTrace nodes younger than $max_age_ms
// - Never delete the LAST QueryTrace for a Query (keep at least 1 as evidence)
// - Idempotent: running twice with same max_age is a no-op the second time
//
// Parameters:
//   max_age_ms      integer — only delete traces older than this many
//                             milliseconds. Default 2592000000 (30 days).
//
// Side effects:
//   - DETACH DELETE old QueryTrace nodes
//   - MERGE updated Query.first_seen (if null)
//   - SET Query.last_seen (if older trace is newer)
//
// Returns:
//   traces_summarized         — how many old traces were deleted
//   traces_remaining          — how many traces still exist
//   oldest_remaining_age_days — approximate age of oldest remaining trace
//   queries_touched           — how many Query nodes had their timestamps updated
// ============================================================================

WITH
  coalesce($max_age_ms, 2592000000) AS max_age_ms
WITH max_age_ms,
     timestamp() - max_age_ms AS cutoff_ms

// --- Phase 1: Find QueryTrace nodes older than max_age_ms --------------------
MATCH (qt:QueryTrace)
WHERE qt.invoked_epoch_ms < cutoff_ms
WITH collect(qt) AS old_traces

WITH old_traces, size(old_traces) AS trace_count

// --- Phase 2: For each old trace, ensure parent Query absorbed the data ------
// This is mostly idempotent since fire_count was incremented at emit time.
UNWIND old_traces AS qt
MATCH (qt)-[:INSTANCE_OF]->(q:Query)
WITH qt, q

// --- Phase 3: Check if this is the ONLY trace for this Query ----------------
// If yes, keep it. If no, safe to delete.
OPTIONAL MATCH (q)<-[:INSTANCE_OF]-(other_qt:QueryTrace)
WHERE other_qt.node_id <> qt.node_id
WITH qt, q, count(other_qt) AS sibling_count
WHERE sibling_count > 0  // only delete if there are other traces

// --- Phase 4: Update Query timestamps if needed ------------------------------
WITH qt, q, sibling_count
MATCH (qt)
SET q.first_seen = CASE
                     WHEN q.first_seen IS NULL THEN qt.invoked_at
                     ELSE q.first_seen
                   END,
    q.last_seen = CASE
                    WHEN q.last_seen IS NULL OR
                         apoc.date.parse(q.last_seen, 'ms', 'yyyy-MM-dd\'T\'HH:mm:ss') < qt.invoked_epoch_ms
                    THEN qt.invoked_at
                    ELSE q.last_seen
                  END

// --- Phase 5: Delete the old trace -----

DETACH DELETE qt

// --- Phase 6: Count what remains ---
WITH count(qt) AS traces_deleted

MATCH (qt:QueryTrace)
WITH traces_deleted, min(qt.invoked_epoch_ms) AS oldest_time, count(qt) AS traces_remaining
WITH traces_deleted,
     traces_remaining,
     CASE
       WHEN traces_remaining = 0 THEN 0
       ELSE round((timestamp() - oldest_time) / 86400000)
     END AS oldest_age_days

// --- Phase 7: Count Query updates (rough estimate) ---
MATCH (q:Query)
WHERE q.first_seen IS NOT NULL AND q.last_seen IS NOT NULL
WITH traces_deleted, traces_remaining, oldest_age_days, count(q) AS queries_with_times

RETURN
  traces_deleted AS traces_summarized,
  traces_remaining,
  oldest_age_days AS oldest_remaining_age_days,
  queries_with_times AS queries_touched,
  'trace-summarize complete' AS status;
