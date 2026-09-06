// @node_id: invariant-scope-isolation
// @label: "Nodes in dev/prod graphs must declare team or product scope"
// @scope: team
// ============================================================================
// Enforces the personal / team / product scope split architecturally, so the
// graph itself polices which nodes may propagate through the PR → autodeploy
// → bootstrap pipeline onto the shared (dev / prod) surface.
//
// Rule: every user-authored node in a shared graph must carry a scope
// property in {"team", "product"}. Nodes with scope="personal" (session
// handoffs, per-architect TODOs, etc) must NOT appear here — they live in
// the architect's local memory + local Neo4j only.
//
// Exempt labels: nodes produced by the ingest pipeline (:Commit, :Issue,
// :QueryTrace, :ConversationTrace, :CypherAtom, :TestRun, :BootstrapRun)
// carry their own scoping and are not subject to this invariant.
//
// Heal protocol surfaces an :ActionProposal for each violating node with a
// one-line fix recipe. Runs every heartbeat.
// ============================================================================

MERGE (inv:Invariant {node_id: 'invariant-scope-isolation'})
SET inv.label             = 'Nodes in dev/prod graphs must declare team or product scope',
    inv.scope             = 'team',
    inv.severity          = 'critical',
    inv.category          = 'graph-topology',
    inv.enforces_principle = 'personal-scope-stays-local',
    inv.heal_protocol_id  = 'protocol-scope-isolation-check',
    inv.heal_protocol     = 'scope-isolation-check',

    // Exempt labels: ingest-side machinery + runtime history.
    inv.exempt_labels = [
      'Commit', 'Issue', 'QueryTrace', 'ConversationTrace',
      'CypherAtom', 'TestRun', 'BootstrapRun', 'BootstrapFailure',
      'Trace', 'ActionProposal', 'DreamProposal', 'FractalEcho',
      'SchedulerJob', 'RepoFile', 'GraphNode'
    ],

    inv.check_cypher =
      "MATCH (n) " +
      "WHERE n.scope IS NULL " +
      "AND NONE(lbl IN labels(n) WHERE lbl IN " +
      "['Commit','Issue','QueryTrace','ConversationTrace','CypherAtom','TestRun','BootstrapRun','BootstrapFailure','Trace','ActionProposal','DreamProposal','FractalEcho','SchedulerJob','RepoFile','GraphNode']" +
      ") " +
      "WITH collect(n.node_id)[0..20] AS offenders, count(n) AS total " +
      "RETURN " +
      "  total = 0 AS healthy, " +
      "  total AS violation_count, " +
      "  offenders AS sample, " +
      "  CASE WHEN total = 0 THEN 'All non-ingest nodes carry scope' " +
      "       ELSE 'Found ' + toString(total) + ' nodes missing scope; sample: ' + toString(offenders) END AS reason",

    inv.forbidden_scope_on_shared = 'personal',

    inv.forbidden_check_cypher =
      "MATCH (n) WHERE n.scope = 'personal' " +
      "WITH collect(n.node_id)[0..20] AS offenders, count(n) AS total " +
      "RETURN " +
      "  total = 0 AS healthy, " +
      "  total AS violation_count, " +
      "  offenders AS sample, " +
      "  CASE WHEN total = 0 THEN 'No personal-scoped nodes leaked into shared graph' " +
      "       ELSE 'Personal-scoped nodes MUST NOT be in dev/prod; move to architect local memory: ' + toString(offenders) END AS reason",

    inv.created_at        = datetime('2026-04-21T11:00:00Z');

RETURN
  'invariant-scope-isolation registered; enforces team/product scoping on shared graph' AS status;
