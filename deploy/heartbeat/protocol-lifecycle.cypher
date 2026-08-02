// ============================================================
// protocol-lifecycle — graph-native lifecycle transitions
// Reasoning lives IN the graph as CypherAtom chains.
// Reads :FleetProgress (from progress-score) and :Project state,
// proposes lifecycle transitions via :ActionProposal (ConfirmLifecycle).
// ============================================================

// --- Protocol node ---
MERGE (p:Protocol {node_id: 'protocol-lifecycle'})
SET p.label = 'Lifecycle - detect stalled/active/complete transitions',
    p.cadence = 'deep', p.enabled = true, p.project = 'system';

// --- Atom 0: seed lifecycle_state from runtime status where missing ---
MERGE (a0:CypherAtom {node_id: 'atom-lifecycle-seed'})
SET a0.semantic = 'Seed lifecycle_state on projects that lack it (from FleetProgress + context)',
    a0.project = 'system',
    a0.cypher = '''
MATCH (p:Project) WHERE p.lifecycle_state IS NULL AND p.status IS NOT NULL
WITH p,
  CASE
    WHEN p.status IN ['hibernated','hibernating','config-only'] THEN 'dormant'
    WHEN p.status = 'built' THEN 'complete'
    ELSE 'seed'
  END AS st
SET p.lifecycle_state = st
''';

// --- Atom 1: active -> stalled (no real progress in 7 days) ---
MERGE (a1:CypherAtom {node_id: 'atom-lifecycle-active-to-stalled'})
SET a1.semantic = 'Flag active projects with no producing progress as stalled',
    a1.project = 'system',
    a1.cypher = '''
MATCH (p:Project {lifecycle_state: 'active'})
OPTIONAL MATCH (fp:FleetProgress {entity: p.name})
WHERE fp.producing = true
WITH p, fp WHERE fp IS NULL
CREATE (le:LifecycleEvent {
  node_id: 'le-' + p.name + '-' + toString(timestamp()),
  entity: p.name, from_state: 'active', to_state: 'stalled',
  reason: 'No real progress (weight < 1.0) in 7 days',
  triggered_by: 'auto-rule', created_at: datetime(), project: p.name
})
MERGE (le)-[:TRANSITIONS {decay_protected:true}]->(p)
SET p.lifecycle_state = 'stalled', p.updated_at = datetime()
WITH p
MERGE (ap:ActionProposal {node_id: 'ap-lifecycle-' + p.name + '-' + toString(date())})
ON CREATE SET ap.type = 'ConfirmLifecycle', ap.entity = p.name,
  ap.description = 'Auto-flagged ' + p.name + ' as stalled (no real progress). Confirm or rescue.',
  ap.status = 'pending', ap.confidence = 0.85,
  ap.generated_at = datetime(), ap.project = p.name
''';

// --- Atom 2: stalled -> active (progress resumed) ---
MERGE (a2:CypherAtom {node_id: 'atom-lifecycle-stalled-to-active'})
SET a2.semantic = 'Restore stalled projects that resumed producing progress',
    a2.project = 'system',
    a2.cypher = '''
MATCH (p:Project {lifecycle_state: 'stalled'})
MATCH (fp:FleetProgress {entity: p.name})
WHERE fp.producing = true
CREATE (le:LifecycleEvent {
  node_id: 'le-' + p.name + '-' + toString(timestamp()),
  entity: p.name, from_state: 'stalled', to_state: 'active',
  reason: 'Real progress resumed (weight >= 1.0)',
  triggered_by: 'auto-rule', created_at: datetime(), project: p.name
})
MERGE (le)-[:TRANSITIONS {decay_protected:true}]->(p)
SET p.lifecycle_state = 'active', p.updated_at = datetime()
''';

// --- Atom 3: active -> complete (no open work, no progress = finished) ---
MERGE (a3:CypherAtom {node_id: 'atom-lifecycle-active-to-complete'})
SET a3.semantic = 'Propose complete for active projects with no goals open and no progress',
    a3.project = 'system',
    a3.cypher = '''
MATCH (p:Project {lifecycle_state: 'active'})
OPTIONAL MATCH (g:EntityGoal {project: p.name, status: 'active'})
WITH p, count(g) AS open_goals
OPTIONAL MATCH (fp:FleetProgress {entity: p.name})
WHERE fp.producing = true
WITH p, open_goals, fp WHERE open_goals = 0 AND fp IS NULL
MERGE (ap:ActionProposal {node_id: 'ap-complete-' + p.name + '-' + toString(date())})
ON CREATE SET ap.type = 'ConfirmLifecycle', ap.entity = p.name,
  ap.description = p.name + ' has no open goals and no progress. Propose complete/maintenance.',
  ap.status = 'pending', ap.confidence = 0.9,
  ap.generated_at = datetime(), ap.project = p.name
''';

// --- Chain: 0 -> 1 -> 2 -> 3 ---
MATCH (a0:CypherAtom {node_id: 'atom-lifecycle-seed'})
MATCH (a1:CypherAtom {node_id: 'atom-lifecycle-active-to-stalled'})
MATCH (a2:CypherAtom {node_id: 'atom-lifecycle-stalled-to-active'})
MATCH (a3:CypherAtom {node_id: 'atom-lifecycle-active-to-complete'})
MERGE (a0)-[:FOLLOWS {decay_protected:true}]->(a1)
MERGE (a1)-[:FOLLOWS {decay_protected:true}]->(a2)
MERGE (a2)-[:FOLLOWS {decay_protected:true}]->(a3);

// --- Protocol points at first atom ---
MATCH (p:Protocol {node_id: 'protocol-lifecycle'})
MATCH (a0:CypherAtom {node_id: 'atom-lifecycle-seed'})
MERGE (p)-[:FIRST_ATOM {decay_protected:true}]->(a0);
