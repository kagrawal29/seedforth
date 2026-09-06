// @node_id: invariants-project-template
// @label: Project Template Invariants
// @description: Defines three core invariants that every :Project subgraph must satisfy
// @applies_to: Projects

// ============================================================================
// INVARIANT 1: Project Being Exists
// ============================================================================
// Every :Project must have exactly one :Being in its namespace.
//
// Healthy when:
//   - MATCH (p:Project) MATCH (b:Being {project: p.name}) RETURN COUNT(DISTINCT b) = 1
//
// Unhealthy when:
//   - No Being exists for the project, OR
//   - Multiple Beings claim the same project scope
//
// This is critical: each project needs an autonomy agent to monitor its health.

MERGE (inv:Invariant {node_id: 'inv-project-being-exists'})
  SET inv.label              = 'Project Being Exists',
      inv.description        = 'Every :Project must have exactly one :Being in its namespace',
      inv.severity           = 'critical',
      inv.category           = 'project-structure',
      inv.heal_protocol_id   = 'protocol-seed-project-beings',
      inv.heal_protocol      = 'protocol-seed-project-beings',

      // --- check_cypher ---------------------------------------------------
      // For each project, verify exactly one Being exists with project scoping.
      // Returns { healthy: bool, reason: string, affected_projects: [string] }
      // -------------------------------------------------------------------
      inv.check_cypher       =
        'MATCH (p:Project) ' +
        'WITH p ' +
        'OPTIONAL MATCH (b:Being {project: p.name}) ' +
        'WITH p, COUNT(DISTINCT b) AS being_count ' +
        'WITH COLLECT({project: p.name, count: being_count}) AS project_states ' +
        'WITH [x IN project_states WHERE x.count <> 1] AS unhealthy ' +
        'RETURN ' +
        '  SIZE(unhealthy) = 0 AS healthy, ' +
        '  CASE ' +
        '    WHEN SIZE(unhealthy) = 0 THEN "All projects have exactly one Being" ' +
        '    ELSE "Projects with missing/duplicate Beings: " + toString([x.project IN unhealthy]) ' +
        '  END AS reason, ' +
        '  [x.project IN unhealthy] AS affected_projects',

      inv.created_at         = datetime();

// ============================================================================
// INVARIANT 2: Project Heartbeat Fresh
// ============================================================================
// Each :Being (project-scoped) must have last_heartbeat_at within the last 30 minutes,
// OR the project must be marked paused.
//
// Healthy when:
//   - Being.last_heartbeat_at is recent (< 30 min ago), OR
//   - Project.status = 'paused'
//
// Unhealthy when:
//   - Being.last_heartbeat_at is stale (>= 30 min), AND
//   - Project.status <> 'paused'
//
// This detects dead or hung project agents.

MERGE (inv:Invariant {node_id: 'inv-project-heartbeat-fresh'})
  SET inv.label              = 'Project Heartbeat Fresh',
      inv.description        = 'Project :Being must heartbeat within 30 minutes or project must be paused',
      inv.severity           = 'warning',
      inv.category           = 'project-liveness',
      inv.heal_protocol_id   = null,
      inv.heal_protocol      = null,

      // --- check_cypher ---------------------------------------------------
      // Check each project's Being heartbeat freshness.
      // Returns { healthy: bool, reason: string, stale_projects: [string] }
      // -------------------------------------------------------------------
      inv.check_cypher       =
        'MATCH (p:Project) ' +
        'OPTIONAL MATCH (b:Being {project: p.name}) ' +
        'WITH p, b, ' +
        '  CASE ' +
        '    WHEN b IS NULL THEN -1 ' +
        '    WHEN b.last_heartbeat_at IS NULL THEN -1 ' +
        '    ELSE duration.inSeconds(b.last_heartbeat_at, datetime()).seconds ' +
        '  END AS seconds_since_heartbeat ' +
        'WITH COLLECT({project: p.name, status: p.status, age_sec: seconds_since_heartbeat}) AS states ' +
        'WITH [x IN states WHERE (x.age_sec >= 0 AND x.age_sec >= 1800 AND x.status <> "paused")] AS stale ' +
        'RETURN ' +
        '  SIZE(stale) = 0 AS healthy, ' +
        '  CASE ' +
        '    WHEN SIZE(stale) = 0 THEN "All project Beings are fresh or paused" ' +
        '    ELSE "Stale projects (no heartbeat in 30min): " + toString([x.project IN stale]) ' +
        '  END AS reason, ' +
        '  [x.project IN stale] AS stale_projects',

      inv.created_at         = datetime();

// ============================================================================
// INVARIANT 3: Project No Cross-Writes
// ============================================================================
// No node with {project: A} should have a write-intent edge to a node with {project: B}.
//
// Write-intent edges: MUTATES, OVERRIDES, SCHEDULES, MODIFIES
// Read-intent edges (allowed): COUPLING, CROSS_COUPLES_TO, REFERENCES, INFERRED_SIMILAR
//
// Healthy when:
//   - No cross-project write edges exist
//
// Unhealthy when:
//   - A node scoped to project A has a MUTATES/OVERRIDES/SCHEDULES edge
//     to a node scoped to project B (where A <> B)
//
// This prevents accidental mutations bleeding across project boundaries.

MERGE (inv:Invariant {node_id: 'inv-project-no-cross-writes'})
  SET inv.label              = 'Project No Cross-Writes',
      inv.description        = 'No write-intent edges (MUTATES, OVERRIDES, SCHEDULES) can cross project boundaries',
      inv.severity           = 'critical',
      inv.category           = 'project-isolation',
      inv.heal_protocol_id   = null,
      inv.heal_protocol      = null,

      // --- check_cypher ---------------------------------------------------
      // Detect cross-project write edges.
      // Write intent types: MUTATES, OVERRIDES, SCHEDULES, MODIFIES
      // Returns { healthy: bool, reason: string, violation_count: int }
      // -------------------------------------------------------------------
      inv.check_cypher       =
        'MATCH (src)-[rel:MUTATES|OVERRIDES|SCHEDULES|MODIFIES]->(dst) ' +
        'WHERE src.project IS NOT NULL AND dst.project IS NOT NULL ' +
        'WITH src, dst, type(rel) AS edge_type, src.project AS src_project, dst.project AS dst_project ' +
        'WITH COLLECT({from: src_project, to: dst_project, type: edge_type}) AS violations ' +
        'WITH [x IN violations WHERE x.from <> x.to] AS cross_project_writes ' +
        'RETURN ' +
        '  SIZE(cross_project_writes) = 0 AS healthy, ' +
        '  CASE ' +
        '    WHEN SIZE(cross_project_writes) = 0 THEN "No cross-project write edges detected" ' +
        '    ELSE "Found " + toString(SIZE(cross_project_writes)) + " cross-project write violations" ' +
        '  END AS reason, ' +
        '  SIZE(cross_project_writes) AS violation_count',

      inv.created_at         = datetime();

// ============================================================================
// ATOM: Wire invariants to monitoring infrastructure
// ============================================================================

OPTIONAL MATCH (heartbeat:Rhythm   {node_id: 'rhythm-heartbeat'})
OPTIONAL MATCH (heal:Purpose       {node_id: 'purpose-self-heal'})
OPTIONAL MATCH (ont:Ontology)
WITH heartbeat, heal, ont

MATCH (inv:Invariant)
  WHERE inv.node_id IN ['inv-project-being-exists', 'inv-project-heartbeat-fresh', 'inv-project-no-cross-writes']

FOREACH (_ IN CASE WHEN heartbeat IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:MONITORED_BY]->(heartbeat)
)

FOREACH (_ IN CASE WHEN heal IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:EMBODIES]->(heal)
)

FOREACH (_ IN CASE WHEN ont IS NOT NULL THEN [1] ELSE [] END |
  MERGE (inv)-[:INVARIANT_OF]->(ont)
);

// ============================================================================
// ATOM: Summary Report
// ============================================================================

MATCH (inv:Invariant)
  WHERE inv.node_id IN ['inv-project-being-exists', 'inv-project-heartbeat-fresh', 'inv-project-no-cross-writes']
RETURN
    COUNT(inv) AS invariants_loaded,
    COLLECT(inv.label) AS invariant_labels,
    'project-template-invariants loaded' AS status;
