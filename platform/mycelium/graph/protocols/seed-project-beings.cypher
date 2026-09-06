// @node_id: protocol-seed-project-beings
// @label: Seed Project Beings
// @description: Creates one :Being per known :Project for autonomous subgraph monitoring
// @applies_to: Projects

// ============================================================================
// Protocol: Seed Project Beings
// ============================================================================
// For each :Project node (active or pending-scope-confirmation),
// create exactly one :Being with ordinal scoping pattern.
//
// Scope: Each Being is scoped to its project via {project: <name>} property.
//
// Idempotent: Uses MERGE, so multiple runs are safe.
// ============================================================================

MATCH (p:Project)
  WHERE p.name IS NOT NULL
WITH p
MERGE (b:Being {project: p.name, node_id: 'being-' + p.name})
  SET b.label                 = 'Being of ' + p.name,
      b.description           = 'Autonomous agent for project ' + p.name,
      b.autonomous_score      = 100.0,
      b.last_heartbeat_at     = datetime(),
      b.created_at            = datetime(),
      // Metadata for identification
      b.project_name          = p.name,
      b.is_project_being      = true
WITH b, p
// Wire Being to its parent Project
MERGE (b)-[:SCOPED_TO]->(p)
RETURN
    b.project AS project,
    b.node_id AS being_node_id,
    b.autonomous_score AS initial_autonomy,
    'being seeded' AS status;
