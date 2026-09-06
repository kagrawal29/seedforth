// @node_id: knowledge-tracked-projects
// @label: Tracked Projects Registry
// @kind: knowledge
// @description: Seeds known :Project nodes with metadata. Owners should update repo_url and scope after seeding.

// ============================================================================
// Core Projects (Mycelium Ecosystem)
// ============================================================================

// ATOM 1: Mycelium (primary)
MERGE (p:Project {name: 'mycelium'})
  SET p.description         = 'Living knowledge graph core — autonomous reasoning system',
      p.repo_url            = 'https://github.com/kagrawal29/mycelium',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'full',
      p.status              = 'active',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 2: Maverick (deprecated Qubit Capital provenance)
MERGE (p:Project {name: 'maverick'})
  SET p.description         = 'Team distribution of mycelium — canonical species minted for Qubit Capital residency',
      p.repo_url            = 'https://github.com/Qubit-Capital/maverick',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'full',
      p.status              = 'reference-only',
      p.active              = false,
      p.architecture_role   = 'reference',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 3: Maverick Meta (team intelligence)
MERGE (p:Project {name: 'maverick-meta'})
  SET p.description         = 'Team intelligence and meta-analysis for maverick residency',
      p.repo_url            = 'https://github.com/Qubit-Capital/maverick-meta',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'full',
      p.status              = 'reference-only',
      p.active              = false,
      p.architecture_role   = 'reference',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ============================================================================
// SeedForth Projects (pending scope confirmation)
// ============================================================================

// ATOM 4: VC AI Associate
MERGE (p:Project {name: 'VC-AI-Associate'})
  SET p.description         = 'Enterprise AI analyst for venture capital investment screening',
      p.repo_url            = 'https://github.com/Qubit-Capital/VC-AI-Associate',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'pending-scope-confirmation',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 5: arie (LinkedIn intelligence — single-user prototype)
MERGE (p:Project {name: 'arie'})
  SET p.description         = 'LinkedIn intelligence agent — single-user prototype phase',
      p.repo_url            = 'https://github.com/kagrawal29/arie',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'pending-scope-confirmation',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 6: ember (LinkedIn management — multi-tenant)
MERGE (p:Project {name: 'ember'})
  SET p.description         = 'Multi-tenant LinkedIn management platform — scaled version of arie',
      p.repo_url            = 'https://github.com/kagrawal29/ember',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'pending-scope-confirmation',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 7: solveOS
MERGE (p:Project {name: 'solveOS'})
  SET p.description         = 'Problem Solving as a Service — lead generation intelligence and opportunity matching',
      p.repo_url            = 'https://github.com/kagrawal29/solve-os',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'pending-scope-confirmation',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 8: pulse
MERGE (p:Project {name: 'pulse'})
  SET p.description         = 'Real-time dashboard and analytics platform',
      p.repo_url            = 'https://github.com/kagrawal29/pulse-dashboard',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'pending-scope-confirmation',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 9: revti-digital
MERGE (p:Project {name: 'revti-digital'})
  SET p.description         = 'Charlie agent system for Revti Digital — Discord + Drive + Gmail integration',
      p.repo_url            = 'https://github.com/kagrawal29/revti-digital',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'pending-scope-confirmation',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 10: tetrahedron (historical reference only)
MERGE (p:Project {name: 'tetrahedron'})
  SET p.description         = 'Retired remote server orchestrator and personal OS — preserved as historical reference',
      p.repo_url            = 'https://github.com/kagrawal29/tetrahedron',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'reference-only',
      p.active              = false,
      p.architecture_role   = 'reference',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ATOM 11: delta
MERGE (p:Project {name: 'delta'})
  SET p.description         = 'Discord bot framework giving projects their own Claude Code instances',
      p.repo_url            = 'https://github.com/kagrawal29/delta',
      p.owner_alias         = 'Mycelium',
      p.visibility          = 'private',
      p.ingestion_scope     = 'code',
      p.status              = 'pending-scope-confirmation',
      p.created_at          = datetime()
  RETURN p.name AS result;

// ============================================================================
// ATOM 12: Summary Report
// ============================================================================

MATCH (p:Project)
RETURN
    COUNT(p) AS total_projects,
    COUNT(CASE WHEN p.status = 'active' THEN 1 END) AS active_projects,
    COUNT(CASE WHEN p.status = 'pending-scope-confirmation' THEN 1 END) AS pending_confirmation,
    COLLECT(p.name ORDER BY p.name) AS all_projects,
    'tracked-projects seeded' AS status;
