// @node_id: protocol-classify-gaps
// @label: "Classify Gaps"
// ============================================================================
// Protocol: Classify Gaps
// ============================================================================
// Reads all Gap nodes with auto_fixable IS NULL.
// Classifies by category:
//   - if category IN ['missing_node_id', 'dead_protocol', 'orphan_node'] then auto_fixable=true
//   - otherwise auto_fixable=false (requires human judgment)
//
// Returns count of newly classified gaps and detailed classification breakdown.
// ============================================================================

// --- Phase 1: Classify gaps with auto_fixable = NULL ---

MATCH (g:Gap)
WHERE g.auto_fixable IS NULL
SET g.auto_fixable = CASE
  WHEN g.category IN ['missing_node_id', 'dead_protocol', 'orphan_node']
    THEN true
  ELSE false
END,
g.classified_by = 'classify-gaps-protocol',
g.classified_at = toString(datetime());

// --- Phase 2: Count newly classified gaps by classification ---

MATCH (g:Gap)
WHERE g.classified_by = 'classify-gaps-protocol'
  AND g.classified_at = toString(datetime())
RETURN
  g.auto_fixable,
  g.category,
  count(g) AS gap_count;

// --- Phase 3: Summary ---

MATCH (g:Gap)
WHERE g.auto_fixable IS NOT NULL
RETURN
  'gaps_classified' AS metric,
  count(CASE WHEN g.classified_by = 'classify-gaps-protocol' THEN 1 END) AS newly_classified,
  count(g) AS total_classified,
  count(CASE WHEN g.auto_fixable = true THEN 1 END) AS auto_fixable_count,
  count(CASE WHEN g.auto_fixable = false THEN 1 END) AS human_judgment_count
