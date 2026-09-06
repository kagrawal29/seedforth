// @node_id: protocol-propagate-being-template
// @label: "Propagate Being Template faculties across every sovereign scope"
// @kind: protocol
// @fsd_layer: features
//
// Heal protocol for invariant-being-has-full-faculties. For every Being
// missing a required faculty (Purpose, Invariant-with-heal, TestCase,
// WorkItem, LocalProtocol), emit an :ActionProposal naming the gap so the
// team can land the scope-specific content in a PR. No silent mutation:
// the protocol PROPOSES, humans RESOLVE.
//
// This is where dreaming becomes fractalization: a single template recurs at
// every scope, same shape different content. Each ActionProposal is a seed
// crystal asking to be realized in its local subgraph.
// ============================================================================

MATCH (b:Being), (tpl:BeingTemplate {node_id: 'being-template-v1'})
WITH b, tpl, b.project AS scope

// For each required faculty, check presence and emit a proposal if missing
UNWIND [
  {kind: 'Purpose',       label: ':Purpose'},
  {kind: 'Invariant',     label: ':Invariant with heal_protocol'},
  {kind: 'TestCase',      label: ':TestCase'},
  {kind: 'WorkItem',      label: ':WorkItem'},
  {kind: 'LocalProtocol', label: ':Protocol with schedule'}
] AS need
CALL (b, scope, need) {
  WITH b, scope, need
  OPTIONAL MATCH (n) WHERE
    n.project = scope
    AND CASE need.kind
      WHEN 'Purpose'       THEN n:Purpose
      WHEN 'Invariant'     THEN n:Invariant AND n.heal_protocol IS NOT NULL
      WHEN 'TestCase'      THEN n:TestCase
      WHEN 'WorkItem'      THEN n:WorkItem
      WHEN 'LocalProtocol' THEN n:Protocol AND n.schedule IS NOT NULL
      ELSE false
    END
  WITH b, scope, need, count(n) AS present
  WHERE present = 0
  MERGE (ap:ActionProposal {node_id: 'ap-being-missing-' + need.kind + '-' + scope})
  SET ap.project = 'mycelium',
      ap.for_scope = scope,
      ap.missing = need.label,
      ap.title = scope + ' is missing ' + need.label + ' — required by Being Template v1',
      ap.status = 'open',
      ap.proposed_at = datetime(),
      ap.rationale = 'Phase 0 of fractal-manifestation-plan: every Being must carry the same minimum faculty set so Hebbian signal has somewhere to route.'
  MERGE (ap)-[:FOR_BEING]->(b)
}
RETURN 'Being-template gaps proposed — one :ActionProposal per missing faculty per Being.' AS checkpoint;
