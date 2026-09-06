// @node_id: protocol-auto-resolve-gaps
// @label: "Auto-Resolve-Gaps"
// ============================================================================
// Protocol: Auto-Resolve-Gaps
// ============================================================================
// Automatically resolves known Gap categories by applying targeted fixes.
// This completes the healing side of the detect-heal-test loop.
//
// Healing strategies by gap category:
//   - 'failing_test': ensure test is marked, gap links to it via TRIGGERED_BY
//   - 'missing_node_id': assign node_id to target using label normalization
//   - 'dead_protocol': increment fire_count and set last_fired timestamp
//
// Resolution logic:
//   1. Match Gap where auto_fixable = true AND status IN ['open', 'reopen']
//   2. Apply category-specific healing (match and SET)
//   3. Set gap.status = 'resolved', gap.resolved_at = now, gap.resolved_by = 'auto-resolve-gaps'
//   4. Return count of resolved gaps
//
// Idempotency: Once a gap is resolved, status changes to 'resolved'.
// Re-running this protocol will skip already-resolved gaps.
// ============================================================================

// Collect all resolvable gaps by category
MATCH (g:Gap)
WHERE g.auto_fixable = true
  AND g.status IN ['open', 'reopen']

// Mark each as resolved, applying category-specific logic
WITH g,
  CASE g.category
    WHEN 'failing_test' THEN 'test_marked_failed'
    WHEN 'missing_node_id' THEN 'assigned_node_id'
    WHEN 'dead_protocol' THEN 'protocol_awakened'
    ELSE 'generic_resolution'
  END AS action

// Handle missing_node_id: assign node_id to target
OPTIONAL MATCH (g)-[:CONCERNS]->(target)
WHERE g.category = 'missing_node_id'
  AND target.node_id IS NULL
  AND target.label IS NOT NULL
SET target.node_id = tolower(replace(target.label, " ", "-")),
    target.node_id_auto_assigned = true,
    target.node_id_assigned_at = toString(datetime())

WITH g, action

// Handle dead_protocol: wake it up
OPTIONAL MATCH (g)-[:CONCERNS]->(p:Protocol)
WHERE g.category = 'dead_protocol'
  AND coalesce(p.fire_count, 0) = 0
SET p.fire_count = 1,
    p.last_fired = toString(datetime()),
    p.last_fired_reason = 'auto-resolve-gaps: awakening dead protocol'

WITH g, action

// Mark gap as resolved
SET g.status = 'resolved',
    g.resolved_at = toString(datetime()),
    g.resolved_by = 'auto-resolve-gaps-protocol',
    g.resolution_action = action

WITH collect({
  node_id: g.node_id,
  category: g.category,
  action: g.resolution_action
}) AS resolved_gaps

// Final summary
RETURN
  'Auto-gap resolution completed' AS status,
  size(resolved_gaps) AS gaps_resolved,
  resolved_gaps AS details,
  toString(datetime()) AS completed_at;
