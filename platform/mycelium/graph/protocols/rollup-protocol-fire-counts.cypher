// @node_id: protocol-rollup-protocol-fire-counts
// @label: "Rollup Protocol Fire Counts (Phase 14d — protocol amortization)"
// ============================================================================
// Protocol: Rollup Protocol Fire Counts (Phase 14d — protocol amortization)
// ============================================================================
// When mycelium ask fires, it creates QueryTrace and increments Query.fire_count.
// But Protocol.fire_count is never updated. This breaks the measurement loop:
// 92% of protocols show "dead" despite active use.
//
// This protocol fixes the gap by rolling up Query.fire_count to Protocol.fire_count.
// Strategy: For each Protocol, count matching active Queries by name pattern.
// ============================================================================

// Step 1: Collect all Queries with fire_count > 0
MATCH (q:Query)
WHERE coalesce(q.fire_count, 0) > 0
WITH collect(q) AS active_queries

// Step 2: For each Protocol, match by name pattern and sum fire_counts
UNWIND active_queries AS active_q
MATCH (p:Protocol)
WHERE coalesce(p.enabled, true) = true
  AND (
    // Match protocol by name: if query's command matches protocol name
    active_q.last_command = p.name
    OR active_q.last_command = p.label
    OR active_q.last_command CONTAINS p.name
  )
WITH p, collect(active_q.fire_count) AS matched_fire_counts

// Step 3: Sum the matched fire_counts
WITH p,
     reduce(total = 0, fc IN matched_fire_counts | total + fc) AS new_fire_count

// Step 4: Update protocol with new fire_count and status
SET p.fire_count = new_fire_count,
    p.last_fire_rollup = toString(datetime()),
    p.amortization_status = CASE
      WHEN new_fire_count = 0 THEN 'dead'
      WHEN new_fire_count >= 1 AND new_fire_count <= 2 THEN 'experimental'
      WHEN new_fire_count >= 3 AND new_fire_count <= 10 THEN 'active'
      WHEN new_fire_count >= 11 AND new_fire_count <= 50 THEN 'strengthened'
      WHEN new_fire_count >= 51 THEN 'critical'
      ELSE 'unknown'
    END

RETURN
  p.name AS protocol_name,
  new_fire_count AS fire_count,
  p.amortization_status AS status
ORDER BY new_fire_count DESC
LIMIT 50;
