// @node_id: tracked-repos-qubit-capital
// @label: "Tracked Qubit Capital repos — subgraphs of the forest"
// @kind: knowledge
//
// The four Qubit-Capital repositories we ingest as subgraphs. Each becomes
// a sovereign :Project under mycelium's forest, with its own :Being,
// :Invariants, :TestCases — identical topology to mycelium core, scoped
// via {project: X}.
//
// Coupling to mycelium core is via [:CROSS_COUPLING] edges (emergent, dream
// round), never via direct writes. Each subgraph is sovereign; mycelium is
// the forest that makes them visible to each other.
// ============================================================================

// ----------------------------------------------------------------------------
// Root: :Project {name: 'maverick'} — the entry point subgraph (mycelium's
// team distribution). Already seeded by tracked-projects.cypher but re-MERGEd
// here idempotently to anchor the Qubit subgraph cluster.
// ----------------------------------------------------------------------------
MERGE (root:Project {name: 'maverick'})
SET root.description = 'Team distribution of mycelium — Qubit Capital residency entry point',
    root.repo_url = 'https://github.com/Qubit-Capital/maverick',
    root.owner_alias = 'Mycelium',
    root.visibility = 'private',
    root.ingestion_scope = 'full',
    root.status = 'active',
    root.org = 'Qubit-Capital',
    root.updated_at = datetime();

// ----------------------------------------------------------------------------
// The 4 Qubit-Capital subgraphs
// ----------------------------------------------------------------------------

MERGE (p:Project {name: 'vc-ai-associate'})
SET p.description = 'Maverick product frontend — AI junior VC analyst UI',
    p.repo_url = 'https://github.com/Qubit-Capital/VC-AI-Assoicate',
    p.default_branch = 'main',
    p.owner_alias = 'pending',
    p.visibility = 'private',
    p.ingestion_scope = 'full',
    p.status = 'active',
    p.org = 'Qubit-Capital',
    p.size_kb = 17789,
    p.role_in_forest = 'product-frontend',
    p.updated_at = datetime();

MERGE (p:Project {name: 'maverick-market-research'})
SET p.description = 'Market research, competitive intelligence, and positioning documents',
    p.repo_url = 'https://github.com/Qubit-Capital/maverick-market-research',
    p.default_branch = 'main',
    p.owner_alias = 'pending',
    p.visibility = 'private',
    p.ingestion_scope = 'full',
    p.status = 'active',
    p.org = 'Qubit-Capital',
    p.size_kb = 170735,
    p.role_in_forest = 'market-intelligence',
    p.updated_at = datetime();

MERGE (p:Project {name: 'maverick-marketing'})
SET p.description = 'Maverick go-to-market + marketing artifacts',
    p.repo_url = 'https://github.com/Qubit-Capital/maverick-marketing',
    p.default_branch = 'main',
    p.owner_alias = 'pending',
    p.visibility = 'private',
    p.ingestion_scope = 'full',
    p.status = 'active',
    p.org = 'Qubit-Capital',
    p.size_kb = 1428,
    p.role_in_forest = 'gtm',
    p.updated_at = datetime();

MERGE (p:Project {name: 'maverick-dev'})
SET p.description = 'Maverick product/platform development hub',
    p.repo_url = 'https://github.com/Qubit-Capital/Maverick-Dev',
    p.default_branch = 'main',
    p.owner_alias = 'pending',
    p.visibility = 'private',
    p.ingestion_scope = 'full',
    p.status = 'active',
    p.org = 'Qubit-Capital',
    p.size_kb = 796,
    p.role_in_forest = 'platform-dev',
    p.updated_at = datetime();

// ----------------------------------------------------------------------------
// Link subgraphs to maverick root as :SIBLING_IN_FOREST — they are peer
// subgraphs that share the Qubit Capital org context, with maverick as the
// distribution spine teammates use.
// ----------------------------------------------------------------------------
MATCH (root:Project {name: 'maverick'}),
      (p:Project)
WHERE p.org = 'Qubit-Capital' AND p.name <> 'maverick'
MERGE (root)-[:SIBLING_IN_FOREST]->(p);

// ----------------------------------------------------------------------------
// Seed one :Being per tracked project. Mirrors the fractal: every tree has
// its own heartbeat center.
// ----------------------------------------------------------------------------
MATCH (p:Project) WHERE p.org = 'Qubit-Capital'
MERGE (b:Being {node_id: 'being-' + p.name})
SET b.project = p.name,
    b.autonomous_score = 100.0,
    b.last_heartbeat_at = datetime(),
    b.created_at = coalesce(b.created_at, datetime()),
    b.updated_at = datetime()
MERGE (p)-[:EMBODIES]->(b);

RETURN 'Qubit-Capital forest seeded: ' +
       toString(size([(p:Project) WHERE p.org = 'Qubit-Capital' | p])) +
       ' projects, each with its own :Being.' AS result;
