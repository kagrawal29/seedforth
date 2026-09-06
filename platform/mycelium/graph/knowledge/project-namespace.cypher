// @node_id: knowledge-project-namespace
// @label: Project Namespace Schema
// @kind: knowledge
// @description: Defines the :Project node type and scoping constraints for multi-project subgraphs

// ============================================================================
// Create the unique constraint on Project.name
// ============================================================================
// This ensures each project has a unique identifier across the graph.

CREATE CONSTRAINT project_name_unique IF NOT EXISTS
  FOR (p:Project) REQUIRE p.name IS UNIQUE;

// ============================================================================
// ATOM 1: Project Node Type Definition
// ============================================================================
// Seed one minimal :Project node to demonstrate the schema
//
// Properties on each :Project:
//   - name (required, unique): Project identifier (lowercase, no spaces)
//   - description: Human-readable description of the project
//   - repo_url: GitHub or internal repository URL
//   - owner_alias: Forest alias of the owning entity (e.g., 'Mycelium', 'Tetrahedron')
//   - visibility: 'public' or 'private'
//   - ingestion_scope: One of 'git' (commits/branches only), 'code' (source files only), or 'full' (both + events)
//   - status: 'active', 'paused', 'archived', or 'pending-scope-confirmation'
//   - created_at: Timestamp of project creation in graph
//
// CONVENTION: Every node that belongs to a subgraph (scoped to this project)
// has a {project: <name>} property on the node. The :Project node itself
// does NOT carry the project property — it IS the namespace root.

MERGE (p:Project {name: 'mycelium'})
  SET p.description         = 'Living knowledge graph core — autonomous reasoning system',
      p.repo_url            = 'https://github.com/kagrawal29/mycelium',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'full',
      p.status              = 'active',
      p.created_at          = datetime()
  RETURN p.node_id AS result;

// ============================================================================
// ATOM 2: Scoping Convention Document
// ============================================================================
// Record the convention that enables multi-project isolation via property-based scoping

MERGE (doc:Knowledge {node_id: 'knowledge-project-scoping-convention'})
  SET doc.label             = 'Project Scoping Convention',
      doc.description       = 'How nodes are scoped to projects via {project: X} property',
      doc.content           = 'Every node that belongs to a subgraph (data, protocols, tests, state) ' +
                              'must have a {project: "<project_name>"} property. ' +
                              'This allows queries to evaluate per-project invariants, healing, and autonomy. ' +
                              'The :Project node itself does NOT have this property — ' +
                              'it IS the namespace root and parent of all scoped nodes. ' +
                              'Edges can cross project boundaries only for specified read-intent types: ' +
                              'COUPLING, CROSS_COUPLES_TO, REFERENCES, INFERRED_SIMILAR. ' +
                              'Write-intent edges like MUTATES, OVERRIDES, SCHEDULES must not cross project boundaries.',
      doc.created_at        = datetime()
  RETURN doc.node_id AS result;

// ============================================================================
// ATOM 3: Wire schema documents to the ontology
// ============================================================================
// Link the scoping convention to any existing Concept nodes that need to understand isolation

OPTIONAL MATCH (ont:Ontology)
WHERE ont IS NOT NULL
WITH ont
MATCH (doc:Knowledge {node_id: 'knowledge-project-scoping-convention'})
MERGE (doc)-[:INVARIANT_OF]->(ont)
RETURN COUNT(doc) AS wired;

// ============================================================================
// ATOM 4: Summary Report
// ============================================================================

MATCH (p:Project)
RETURN
    COUNT(p) AS total_projects_seeded,
    COLLECT(p.name) AS project_names,
    'project-namespace schema loaded' AS status;
