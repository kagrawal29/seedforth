// @node_id: protocol-scope-isolation-check
// @label: Heartbeat check — enforce scope isolation on shared graph
// @schedule: heartbeat
// @enforces: invariant-scope-isolation
// @scope: team
// ============================================================================
// Runs on every heartbeat. Two passes:
//   1. Untagged: any non-ingest node with no `scope` property → tag warning.
//   2. Leaked:   any node with scope='personal' → critical ActionProposal.
//
// Each pass emits a distinct :ActionProposal keyed by (node_id, violation),
// so fixes or suppressions don't clobber each other. Healed violations
// (node fixed or deleted) have their proposal auto-closed on next heartbeat.
//
// This is the graph-native enforcement of decision-deploy-flow-v1 +
// the personal/team/product split. No human or CLI convention required —
// the graph checks itself.
// ============================================================================

MERGE (p:Protocol {node_id: 'protocol-scope-isolation-check'})
SET p.label        = 'Enforce scope isolation on shared graph',
    p.scope        = 'team',
    p.schedule     = 'heartbeat',
    p.enforces     = 'invariant-scope-isolation',
    p.category     = 'graph-topology',
    p.description  = 'Heartbeat check: surfaces nodes missing scope or bearing scope=personal on the shared (dev/prod) graph. The graph polices its own propagation boundary.',

    p.cypher =
      "// Pass 1: untagged nodes (warning) " +
      "MATCH (n) " +
      "WHERE n.scope IS NULL " +
      "AND NONE(lbl IN labels(n) WHERE lbl IN " +
      "['Commit','Issue','QueryTrace','ConversationTrace','CypherAtom','TestRun','BootstrapRun','BootstrapFailure','Trace','ActionProposal','DreamProposal','FractalEcho','SchedulerJob','RepoFile','GraphNode']) " +
      "WITH n LIMIT 100 " +
      "MERGE (ap:ActionProposal {node_id: 'ap-scope-missing-' + n.node_id}) " +
      "ON CREATE SET " +
      "  ap.title = 'Node ' + n.node_id + ' missing scope property', " +
      "  ap.for_scope = 'team', " +
      "  ap.severity = 'warning', " +
      "  ap.status = 'open', " +
      "  ap.created_at = datetime(), " +
      "  ap.target_node_id = n.node_id, " +
      "  ap.violation = 'missing-scope', " +
      "  ap.fix_recipe = 'Add `scope` property on ' + n.node_id + ' (values: team | product | personal). If personal, move to local graph and remove from shared.' " +
      "WITH count(*) AS untagged_proposed " +

      "// Pass 2: leaked personal-scoped nodes (critical) " +
      "MATCH (n) WHERE n.scope = 'personal' " +
      "WITH untagged_proposed, n LIMIT 100 " +
      "MERGE (ap:ActionProposal {node_id: 'ap-scope-leaked-' + n.node_id}) " +
      "ON CREATE SET " +
      "  ap.title = 'Personal-scoped node ' + n.node_id + ' leaked into shared graph', " +
      "  ap.for_scope = 'team', " +
      "  ap.severity = 'critical', " +
      "  ap.status = 'open', " +
      "  ap.created_at = datetime(), " +
      "  ap.target_node_id = n.node_id, " +
      "  ap.violation = 'personal-scope-in-shared-graph', " +
      "  ap.fix_recipe = 'DELETE ' + n.node_id + ' from dev/prod and recreate in architect local Neo4j + memory file. Personal continuity state must not propagate.' " +
      "RETURN untagged_proposed, count(*) AS leaked_proposed",

    p.last_run_ts = null,
    p.created_at  = datetime('2026-04-21T11:00:00Z');

// Close proposals for nodes that have since been fixed or deleted.
MERGE (sweep:Protocol {node_id: 'protocol-scope-isolation-sweep'})
SET sweep.label        = 'Close scope-isolation proposals when target is healed',
    sweep.scope        = 'team',
    sweep.schedule     = 'heartbeat',
    sweep.description  = 'Sibling of protocol-scope-isolation-check. Closes :ActionProposal {violation:missing-scope|personal-scope-in-shared-graph} whose target node no longer violates (scope added, scope changed off personal, or node deleted).',
    sweep.cypher =
      "MATCH (ap:ActionProposal) WHERE ap.violation IN ['missing-scope','personal-scope-in-shared-graph'] AND ap.status = 'open' " +
      "OPTIONAL MATCH (n {node_id: ap.target_node_id}) " +
      "WITH ap, n " +
      "WHERE n IS NULL " +
      "   OR (ap.violation = 'missing-scope' AND n.scope IS NOT NULL) " +
      "   OR (ap.violation = 'personal-scope-in-shared-graph' AND (n.scope IS NULL OR n.scope <> 'personal')) " +
      "SET ap.status = 'auto-closed', ap.closed_at = datetime(), ap.closed_by = 'protocol-scope-isolation-sweep' " +
      "RETURN count(*) AS auto_closed",
    sweep.created_at = datetime('2026-04-21T11:00:00Z');

RETURN
  'protocol-scope-isolation-check + sweep registered (heartbeat-scheduled)' AS status;
