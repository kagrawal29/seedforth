// @node_id: seedforth-ecosystem-map-v1
// @label: "SeedForth Ecosystem Map — servers, services, projects, agents, repos"
// @kind: knowledge
//
// Complete map of the SeedForth ecosystem. Every project, server, service,
// agent, and repository is a node. Relationships describe what depends on what,
// what runs where, and who manages what.
//
// Delta-server is the backbone. Charlie-server runs audioworld outreach.
// Pulse-server is off-limits (not represented here).
// ============================================================================

// ############################################################################
// SERVERS
// ############################################################################
MERGE (ds:Server {node_id: 'server-delta'})
SET ds.project = 'seedforth',
    ds.name = 'delta-server',
    ds.ip = '143.110.226.214',
    ds.ssh_alias = 'delta-server',
    ds.provider = 'digitalocean',
    ds.description = 'Primary SeedForth infrastructure server. Runs Tetrahedron bot, Delta bot, Observatory, Neo4j, FalkorDB, Qdrant, and all delta-managed projects.',
    ds.status = 'active';

MERGE (cs:Server {node_id: 'server-charlie'})
SET cs.project = 'seedforth',
    cs.name = 'charlie-server',
    cs.ip = '142.93.223.13',
    cs.ssh_alias = 'charlie-server',
    cs.provider = 'digitalocean',
    cs.description = 'Secondary server running AudioWorld/Charlie LinkedIn outreach system.',
    cs.status = 'active';

// ############################################################################
// SERVICES on delta-server
// ############################################################################
UNWIND [
  {id: 'svc-delta',             name: 'delta.service',           desc: 'Discord bot giving projects their own OpenCode agents', ports: '', health: 'active'},
  {id: 'svc-tetrahedron-bot',   name: 'tetrahedron-bot.service', desc: 'Tetrahedron Discord supervisor bot', ports: '', health: 'active'},
  {id: 'svc-observatory',       name: 'observatory.service',     desc: 'Fleet monitoring dashboard on :8888', ports: '8888', health: 'active'},
  {id: 'svc-loom',              name: 'loom.service',            desc: 'Loom service', ports: '', health: 'active'},
  {id: 'svc-droplet-agent',     name: 'droplet-agent.service',   desc: 'Droplet management agent', ports: '', health: 'active'},
  {id: 'svc-supervisor',        name: 'supervisor.service',      desc: 'Process supervisor for delta projects', ports: '', health: 'active'},
  {id: 'svc-ttyd',              name: 'ttyd.service',            desc: 'Web terminal via ttyd', ports: '', health: 'active'},
  {id: 'svc-neo4j',             name: 'mycelium-neo4j',          desc: 'Neo4j 5.26 Community — the graph database (bolt on :7687, http on :7474)', ports: '7687,7474', health: 'active'},
  {id: 'svc-falkordb',          name: 'docker-falkordb-1',       desc: 'FalkorDB — Redis-protocol graph database (:6380)', ports: '6380', health: 'active'},
  {id: 'svc-qdrant',            name: 'qdrant',                  desc: 'Qdrant vector search engine (:6333)', ports: '6333', health: 'active'}
] AS svc
MERGE (s:Service {node_id: svc.id})
SET s.project = 'seedforth',
    s.name = svc.name,
    s.description = svc.desc,
    s.ports = svc.ports,
    s.health = svc.health,
    s.last_checked_at = datetime();

MATCH (ds:Server {node_id: 'server-delta'}), (s:Service)
WHERE s.project = 'seedforth'
  AND s.node_id IN ['svc-delta','svc-tetrahedron-bot','svc-observatory','svc-loom','svc-droplet-agent','svc-supervisor','svc-ttyd','svc-neo4j','svc-falkordb','svc-qdrant']
MERGE (ds)-[:HAS_SERVICE]->(s);

// ############################################################################
// SEEDFORTH PROJECTS (from AGENTS.md registry)
// ############################################################################
UNWIND [
  {name: 'mycelium',       desc: 'Living knowledge graph — the map of everything. This graph.', repo: 'kagrawal29/mycelium',            status: 'active',     runtime: 'cypher',   category: 'core'},
  {name: 'tetrahedron',    desc: 'Remote server orchestrator + personal OS. Discord bot supervisor.', repo: 'kagrawal29/tetrahedron',    status: 'active',     runtime: 'python',   category: 'core'},
  {name: 'delta',          desc: 'Discord bot giving projects their own OpenCode agents. Project registry + channel management.', repo: 'kagrawal29/delta', status: 'active', runtime: 'python', category: 'core'},
  {name: 'audioworld',     desc: 'LinkedIn outreach system on charlie-server.', repo: 'kagrawal29/audioworld', status: 'active',       runtime: 'python',   category: 'client'},
  {name: 'arie',           desc: 'LinkedIn intelligence agent (single-user prototype). Precedes ember.', repo: 'kagrawal29/arie',       status: 'hibernating', runtime: 'python', category: 'product'},
  {name: 'ember',          desc: 'Multi-tenant LinkedIn management (scaled arie).', repo: 'kagrawal29/ember',                          status: 'hibernating', runtime: 'python', category: 'product'},
  {name: 'solveOS',        desc: 'Problem Solving as a Service — lead gen intelligence and opportunity matching.', repo: 'kagrawal29/solve-os', status: 'hibernating', runtime: 'python', category: 'product'},
  {name: 'revti-digital',  desc: 'Charlie agent system for Revti Digital — Discord + Drive + Gmail.', repo: 'kagrawal29/revti-digital', status: 'hibernating', runtime: 'python', category: 'client'},
  {name: 'pulse-dashboard',desc: 'Next.js dashboard — product analytics frontend.', repo: 'kagrawal29/pulse-dashboard',                status: 'hibernating', runtime: 'nextjs', category: 'product'},
  {name: 'news-commodity-link', desc: 'News/commodity correlation research.', repo: 'kagrawal29/news-commodity-link',                   status: 'hibernating', runtime: 'python', category: 'research'},
  {name: 'AI-product-quotes',   desc: 'Client brief-to-proposal pipeline.', repo: 'kagrawal29/ai-product-quotes',                       status: 'config-only', runtime: 'none', category: 'internal'},
  {name: 'ojas-life',           desc: 'Brand identity and business docs.', repo: 'kagrawal29/ojas-life',                               status: 'config-only', runtime: 'none', category: 'client'},
  {name: 'performance-marketing', desc: 'Marketing dashboard mockup.', repo: 'kagrawal29/performance-marketing-dashboard',             status: 'config-only', runtime: 'none', category: 'internal'},
  {name: 'sports-corridor',     desc: 'Sports business plans.', repo: 'kagrawal29/sports-corridor',                                    status: 'config-only', runtime: 'none', category: 'client'},
  {name: 'flowing-indian',      desc: 'Flow/movement practice site — marketing + Razorpay events funnel. Vercel deploy.', repo: 'kartiksahu/flowing-indian-website', status: 'active', runtime: 'nextjs', category: 'client'},
  {name: 'sceneforth-os',       desc: 'Starter Reel Pack micro-earner — guided brand intake + bespoke campaign preview + Razorpay checkout. Local only.', repo: '', status: 'built', runtime: 'nextjs', category: 'product'},
  {name: 'ai-camera-proposal',  desc: 'AI road inspection proposal documents.', repo: '',                                              status: 'config-only', runtime: 'none', category: 'internal'},
  {name: 'website',             desc: 'SeedForth landing page — Infinite Agency concept.', repo: 'kagrawal29/seedforth-website',       status: 'active',     runtime: 'html', category: 'marketing'},
  {name: 'agent-vinod',         desc: 'Discord bot for autonomous project management (Qubit Capital).', repo: 'Qubit-Capital/Agent-Vinod', status: 'hibernating', runtime: 'python', category: 'client'},
  {name: 'bootcamp-delta',      desc: 'Delta ecosystem container — bootcamp project.', repo: '',                                         status: 'hibernating', runtime: 'opencode', category: 'delta-ecosystem'},
  {name: 'cajon-sensei-eco',    desc: 'Delta ecosystem — cajon sensei instruction project.', repo: '',                                   status: 'hibernating', runtime: 'opencode', category: 'delta-ecosystem'},
  {name: 'flowing-reels',       desc: 'Delta ecosystem — flowing reels project.', repo: '',                                              status: 'hibernating', runtime: 'opencode', category: 'delta-ecosystem'},
  {name: 'delta-hub',           desc: 'Delta ecosystem hub project.', repo: 'kagrawal29/delta-hub',                                      status: 'hibernating', runtime: 'opencode', category: 'delta-ecosystem'}

] AS p
MERGE (proj:Project {node_id: 'proj-' + p.name})
SET proj.project = p.name,
    proj.name = p.name,
    proj.description = p.desc,
    proj.repo_url = CASE WHEN p.repo <> '' THEN 'https://github.com/' + p.repo ELSE '' END,
    proj.status = p.status,
    proj.runtime = p.runtime,
    proj.category = p.category,
    proj.created_at = coalesce(proj.created_at, datetime());

// ############################################################################
// DELTA-MANAGED PROJECTS (from delta-registry.json on delta-server)
// These are projects running under delta's supervision with dedicated linux users.
// ############################################################################
UNWIND [
  {name: 'delta-ashoonya-agent',            desc: 'Delta-managed agent project', type: 'standard',  status: 'hibernated'},
  {name: 'delta-gopal-website',             desc: 'Delta-managed website project', type: 'standard',  status: 'active'},
  {name: 'delta-heritage-diaries',          desc: 'Delta-managed heritage content project', type: 'standard', status: 'active'},
  {name: 'delta-laugh-lab',                 desc: 'Delta-managed comedy/laugh lab', type: 'standard',  status: 'hibernated'},
  {name: 'delta-linkedin-audioworld',       desc: 'Delta-managed LinkedIn — audioworld outreach', type: 'linkedin', status: 'active'},
  {name: 'delta-linkedin-deepak-kumar-patel', desc: 'Delta-managed LinkedIn — Deepak Kumar Patel', type: 'linkedin', status: 'active'},
  {name: 'delta-linkedin-himanshu-ghiya',   desc: 'Delta-managed LinkedIn — Himanshu Ghiya', type: 'linkedin', status: 'hibernated'},
  {name: 'delta-linkedin-kshitiz-agarwal',  desc: 'Delta-managed LinkedIn — Kshitiz Agarwal', type: 'linkedin', status: 'hibernated'},
  {name: 'delta-linkedin-simrat',           desc: 'Delta-managed LinkedIn — Simrat', type: 'linkedin', status: 'hibernated'},
  {name: 'delta-ojas-liife',                desc: 'Delta-managed Ojas Life project', type: 'standard',  status: 'hibernated'},
  {name: 'delta-omega',                     desc: 'Delta-managed omega project', type: 'standard',  status: 'hibernated'},
  {name: 'delta-onboarding-alex',           desc: 'Delta-managed onboarding for Alex (chiron type)', type: 'chiron', status: 'hibernated'},
  {name: 'delta-onboarding-ka',             desc: 'Delta-managed onboarding for KA', type: 'persistent', status: 'hibernated'},
  {name: 'delta-onboarding-kshitiz',        desc: 'Delta-managed onboarding for Kshitiz', type: 'persistent', status: 'hibernated'},
  {name: 'delta-ops-core',                  desc: 'Delta-managed operations core', type: 'standard',  status: 'hibernated'},
  {name: 'delta-optimum-nutrition',         desc: 'Delta-managed nutrition project', type: 'standard',  status: 'active'},
  {name: 'delta-personal-ka',               desc: 'Delta-managed personal KA', type: 'persistent', status: 'hibernated'},
  {name: 'delta-quiet-ember',               desc: 'Delta-managed quiet ember', type: 'standard',  status: 'hibernated'},
  {name: 'delta-seedforthing',              desc: 'Delta-managed seedforthing orchestration', type: 'standard',  status: 'active'},
  {name: 'delta-solve-os',                  desc: 'Delta-managed Solve OS', type: 'standard',  status: 'hibernated', repo: 'kagrawal29/solve-os'},
  {name: 'delta-zuuro',                     desc: 'Delta-managed zuuro project', type: 'standard',  status: 'active'},
  {name: 'delta-test-project',              desc: 'Delta-managed test project', type: 'standard',  status: 'hibernated'}
] AS dp
MERGE (dproj:Project {node_id: 'proj-' + dp.name})
SET dproj.project = dp.name,
    dproj.name = dp.name,
    dproj.description = dp.desc,
    dproj.project_type = dp.type,
    dproj.status = dp.status,
    dproj.category = 'delta-managed',
    dproj.runtime = 'opencode',
    dproj.managed_by = 'delta',
    dproj.created_at = coalesce(dproj.created_at, datetime());

// ############################################################################
// AGENTS
// ############################################################################
MERGE (a1:Agent {node_id: 'agent-tetrahedron'})
SET a1.project = 'tetrahedron',
    a1.name = 'Tetrahedron',
    a1.role = 'Personal OS + Infrastructure Commander',
    a1.runs_on = 'delta-server',
    a1.service = 'tetrahedron-bot.service',
    a1.description = 'Discord supervisor bot. Manages priorities, decomposes tasks, tracks projects, provisions servers, deploys agent stacks. Spawns subagents for heavy lifting.',
    a1.status = 'active';

MERGE (a2:Agent {node_id: 'agent-delta'})
SET a2.project = 'delta',
    a2.name = 'Delta',
    a2.role = 'Discord Agent Platform',
    a2.runs_on = 'delta-server',
    a2.service = 'delta.service',
    a2.description = 'Discord bot that creates isolated OpenCode agent instances per project channel. Each project gets its own linux user, home directory, and supervised agent process.',
    a2.status = 'active';

MERGE (a3:Agent {node_id: 'agent-audioworld'})
SET a3.project = 'audioworld',
    a3.name = 'AudioWorld / Charlie',
    a3.role = 'LinkedIn Outreach System',
    a3.runs_on = 'charlie-server',
    a3.description = 'LinkedIn outreach agent running on charlie-server. Manages multiple LinkedIn accounts for automated outreach and engagement.',
    a3.status = 'active';

// ############################################################################
// GITHUB REPOS
// ############################################################################
UNWIND [
  {id: 'repo-mycelium',          org: 'kagrawal29',  name: 'mycelium',        desc: 'Living knowledge graph core', visibility: 'private'},
  {id: 'repo-maverick',          org: 'Qubit-Capital', name: 'maverick',      desc: 'Team distribution of mycelium', visibility: 'private'},
  {id: 'repo-tetrahedron',       org: 'kagrawal29',  name: 'tetrahedron',     desc: 'Personal OS + infrastructure commander', visibility: 'private'},
  {id: 'repo-delta',             org: 'kagrawal29',  name: 'delta',           desc: 'Discord agent platform', visibility: 'private'},
  {id: 'repo-audioworld',        org: 'kagrawal29',  name: 'audioworld',      desc: 'LinkedIn outreach system', visibility: 'private'},
  {id: 'repo-ember',             org: 'kagrawal29',  name: 'ember',           desc: 'Multi-tenant LinkedIn management', visibility: 'private'},
  {id: 'repo-arie',              org: 'kagrawal29',  name: 'arie',            desc: 'LinkedIn intelligence agent prototype', visibility: 'private'},
  {id: 'repo-solve-os',          org: 'kagrawal29',  name: 'solve-os',        desc: 'Problem Solving as a Service', visibility: 'private'},
  {id: 'repo-revti-digital',     org: 'kagrawal29',  name: 'revti-digital',   desc: 'Charlie agent for Revti Digital', visibility: 'private'},
  {id: 'repo-website',           org: 'kagrawal29',  name: 'seedforth-website', desc: 'SeedForth landing page', visibility: 'private'},
  {id: 'repo-flowing-indian',    org: 'kartiksahu',  name: 'flowing-indian-website', desc: 'Flowing Indian site', visibility: 'public'},
  {id: 'repo-agent-vinod',       org: 'Qubit-Capital', name: 'Agent-Vinod',   desc: 'Discord bot for autonomous PM', visibility: 'private'},
  {id: 'repo-delta-hub',         org: 'kagrawal29',  name: 'delta-hub',       desc: 'Delta ecosystem hub', visibility: 'private'}
] AS r
MERGE (repo:Repository {node_id: r.id})
SET repo.project = 'seedforth',
    repo.full_name = r.org + '/' + r.name,
    repo.org = r.org,
    repo.name = r.name,
    repo.description = r.desc,
    repo.visibility = r.visibility,
    repo.url = 'https://github.com/' + r.org + '/' + r.name;

// ############################################################################
// CROSS-CONNECTIONS
// ############################################################################

// --- Projects -> Repos ---
MATCH (p:Project {node_id: 'proj-mycelium'}),      (r:Repository {node_id: 'repo-mycelium'})      MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-tetrahedron'}),    (r:Repository {node_id: 'repo-tetrahedron'})    MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-delta'}),          (r:Repository {node_id: 'repo-delta'})          MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-audioworld'}),     (r:Repository {node_id: 'repo-audioworld'})     MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-ember'}),          (r:Repository {node_id: 'repo-ember'})          MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-arie'}),           (r:Repository {node_id: 'repo-arie'})           MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-solveOS'}),        (r:Repository {node_id: 'repo-solve-os'})       MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-revti-digital'}),  (r:Repository {node_id: 'repo-revti-digital'})  MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-website'}),        (r:Repository {node_id: 'repo-website'})        MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-flowing-indian'}), (r:Repository {node_id: 'repo-flowing-indian'}) MERGE (p)-[:HAS_REPO]->(r);
MATCH (p:Project {node_id: 'proj-delta-hub'}),      (r:Repository {node_id: 'repo-delta-hub'})      MERGE (p)-[:HAS_REPO]->(r);

// --- Projects -> Servers (deployment location) ---
MATCH (p:Project {node_id: 'proj-mycelium'}),   (s:Server {node_id: 'server-delta'})   MERGE (p)-[:DEPLOYS_TO]->(s);
MATCH (p:Project {node_id: 'proj-tetrahedron'}), (s:Server {node_id: 'server-delta'})  MERGE (p)-[:DEPLOYS_TO]->(s);
MATCH (p:Project {node_id: 'proj-delta'}),      (s:Server {node_id: 'server-delta'})   MERGE (p)-[:DEPLOYS_TO]->(s);
MATCH (p:Project {node_id: 'proj-audioworld'}), (s:Server {node_id: 'server-charlie'}) MERGE (p)-[:DEPLOYS_TO]->(s);

// --- Agents -> Projects they manage ---
MATCH (a:Agent {node_id: 'agent-tetrahedron'}), (p:Project {node_id: 'proj-tetrahedron'}) MERGE (a)-[:MANAGES]->(p);
MATCH (a:Agent {node_id: 'agent-delta'}),       (p:Project {node_id: 'proj-delta'})       MERGE (a)-[:MANAGES]->(p);
MATCH (a:Agent {node_id: 'agent-audioworld'}),   (p:Project {node_id: 'proj-audioworld'})  MERGE (a)-[:MANAGES]->(p);

// --- Agents run on Servers ---
MATCH (a:Agent {node_id: 'agent-tetrahedron'}), (s:Server {node_id: 'server-delta'})   MERGE (a)-[:RUNS_ON]->(s);
MATCH (a:Agent {node_id: 'agent-delta'}),       (s:Server {node_id: 'server-delta'})   MERGE (a)-[:RUNS_ON]->(s);
MATCH (a:Agent {node_id: 'agent-audioworld'}),   (s:Server {node_id: 'server-charlie'}) MERGE (a)-[:RUNS_ON]->(s);

// --- Delta manages all delta-managed projects ---
MATCH (d:Project {node_id: 'proj-delta'})
MATCH (dm:Project) WHERE dm.category = 'delta-managed' AND dm.managed_by = 'delta'
MERGE (dm)-[:MANAGED_BY]->(d);

// --- Dependency chain ---
MATCH (p:Project {node_id: 'proj-mycelium'}),   (s:Server {node_id: 'server-delta'}) MERGE (p)-[:DEPENDS_ON]->(s);
MATCH (p:Project {node_id: 'proj-tetrahedron'}), (d:Project {node_id: 'proj-delta'}) MERGE (p)-[:DEPENDS_ON]->(d);
MATCH (p:Project {node_id: 'proj-ember'}),      (a:Project {node_id: 'proj-arie'})   MERGE (p)-[:DEPENDS_ON]->(a);

// --- Service -> Service dependencies ---
MATCH (n:Service {node_id: 'svc-neo4j'})
MATCH (q:Service {node_id: 'svc-qdrant'})
MATCH (f:Service {node_id: 'svc-falkordb'})
MATCH (delta:Service {node_id: 'svc-delta'})
MATCH (tetra:Service {node_id: 'svc-tetrahedron-bot'})
MATCH (obs:Service {node_id: 'svc-observatory'})
MERGE (delta)-[:DEPENDS_ON]->(n)
MERGE (delta)-[:DEPENDS_ON]->(f)
MERGE (tetra)-[:DEPENDS_ON]->(n);

// ############################################################################
// PERSONA — Kshitiz (the human, alias Mycelium)
// ############################################################################
MERGE (pers:Persona {node_id: 'persona-kshitiz'})
SET pers.project = 'seedforth',
    pers.scope = 'seedforth',
    pers.role = 'Forest Steward / Founder',
    pers.does = 'Architect of the SeedForth ecosystem. Designs the graph, deploys the agents, holds the forest together. Every project, server, and agent traces back to this human.',
    pers.opener = 'From where I sit, looking at the entire ecosystem:',
    pers.sample_questions = [
      'What is the current state of every project?',
      'Which services are down?',
      'What depends on delta-server?',
      'Where is audioworld running?',
      'Which LinkedIn accounts are active?',
      'Update all project statuses from live sources'
    ],
    pers.declared_at = datetime();

MATCH (b:Being {node_id: 'being-seedforth'}), (p:Persona {node_id: 'persona-kshitiz'})
MERGE (b)-[:VOICED_BY]->(p);

// ############################################################################
// CYPHER ATOMS — the basic unit of LLM interaction
// ############################################################################
UNWIND [
  {id: 'atom-status-all',      semantic: 'Get status of all SeedForth projects — name, status, category, runtime', cypher: 'MATCH (p:Project) WHERE p.category <> "delta-managed" RETURN p.name, p.status, p.category, p.runtime ORDER BY p.category, p.status, p.name', fire_count: 0},
  {id: 'atom-delta-projects',  semantic: 'List all delta-managed projects with their status and type', cypher: 'MATCH (p:Project {category: "delta-managed"}) RETURN p.name, p.status, p.project_type ORDER BY p.status, p.name', fire_count: 0},
  {id: 'atom-servers-health',  semantic: 'Show all servers and their running services with health', cypher: 'MATCH (s:Server)-[:HAS_SERVICE]->(svc:Service) RETURN s.name AS server, svc.name AS service, svc.health, svc.ports ORDER BY s.name, svc.name', fire_count: 0},
  {id: 'atom-active-projects', semantic: 'List only active projects across SeedForth', cypher: 'MATCH (p:Project) WHERE p.status = "active" RETURN p.name, p.description, p.runtime ORDER BY p.category, p.name', fire_count: 0},
  {id: 'atom-agents-status',   semantic: 'Show all agents, their status, role, and which server they run on', cypher: 'MATCH (a:Agent) RETURN a.name, a.role, a.runs_on, a.status ORDER BY a.name', fire_count: 0},
  {id: 'atom-dependencies',    semantic: 'Show what depends on what — project and service dependency graph', cypher: 'MATCH (a)-[:DEPENDS_ON]->(b) RETURN a.name, labels(a)[0] AS type_a, b.name, labels(b)[0] AS type_b', fire_count: 0},
  {id: 'atom-repo-map',        semantic: 'Map projects to their GitHub repositories', cypher: 'MATCH (p:Project)-[:HAS_REPO]->(r:Repository) RETURN p.name, r.full_name, r.visibility ORDER BY p.name', fire_count: 0},
  {id: 'atom-deployments',     semantic: 'Which servers do projects deploy to', cypher: 'MATCH (p:Project)-[:DEPLOYS_TO]->(s:Server) RETURN p.name, s.name AS server, s.ip ORDER BY p.name', fire_count: 0},
  {id: 'atom-delta-managed-by', semantic: 'Show which delta-managed projects belong to which parent', cypher: 'MATCH (dm:Project)-[:MANAGED_BY]->(d:Project {node_id: "proj-delta"}) RETURN dm.name, dm.status, dm.project_type ORDER BY dm.status, dm.name', fire_count: 0},
  {id: 'atom-forest-constitution', semantic: 'Show the forest constitution — sovereignty rules and invariants', cypher: 'MATCH (promise:ForestPromise)-[:DECLARES]->(r:SovereigntyRule) RETURN r.node_id, r.rule, r.severity ORDER BY r.severity', fire_count: 0},
  {id: 'atom-what-runs-where', semantic: 'What runs where — all projects and services per server', cypher: 'MATCH (s:Server) OPTIONAL MATCH (s)-[:HAS_SERVICE]->(svc:Service) OPTIONAL MATCH (p:Project)-[:DEPLOYS_TO]->(s) RETURN s.name, collect(DISTINCT svc.name) AS services, collect(DISTINCT p.name) AS projects', fire_count: 0},
  {id: 'atom-hibernating',     semantic: 'List all hibernating or config-only projects', cypher: 'MATCH (p:Project) WHERE p.status IN ["hibernating","config-only","built"] RETURN p.name, p.status, p.description ORDER BY p.status, p.name', fire_count: 0},
  {id: 'atom-invariants-check', semantic: 'Check all invariants for violations', cypher: 'MATCH (i:Invariant {project: "seedforth"}) RETURN i.label, i.severity ORDER BY i.severity', fire_count: 0},
  {id: 'atom-count-all',       semantic: 'Total node count across the ecosystem', cypher: 'MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC', fire_count: 0}
] AS ca
MERGE (atom:CypherAtom {node_id: ca.id})
SET atom.project = 'seedforth',
    atom.semantic = ca.semantic,
    atom.cypher = ca.cypher,
    atom.fire_count = coalesce(atom.fire_count, ca.fire_count),
    atom.last_fired_at = coalesce(atom.last_fired_at, datetime());

// ############################################################################
// SEED THE GRAPH-SUMMARIZING PROTOCOL
// ############################################################################
MERGE (proto:Protocol {node_id: 'protocol-ecosystem-status'})
SET proto.project = 'seedforth',
    proto.label = 'Ecosystem Status Report',
    proto.protocol_type = 'report',
    proto.description = 'Runs the core CypherAtoms to produce a complete status report of the SeedForth ecosystem. Composable by the LLM — pick atoms, chain them via FOLLOWS, FEEDS results between them.',
    proto.cadence = 'on-demand',
    proto.enabled = true;

// Wire atoms into the protocol chain
MATCH (proto:Protocol {node_id: 'protocol-ecosystem-status'})
MATCH (a1:CypherAtom {node_id: 'atom-servers-health'}),
      (a2:CypherAtom {node_id: 'atom-active-projects'}),
      (a3:CypherAtom {node_id: 'atom-agents-status'}),
      (a4:CypherAtom {node_id: 'atom-hibernating'}),
      (a5:CypherAtom {node_id: 'atom-dependencies'})
MERGE (proto)-[:COMPOSES]->(a1)
MERGE (proto)-[:COMPOSES]->(a2)
MERGE (proto)-[:COMPOSES]->(a3)
MERGE (proto)-[:COMPOSES]->(a4)
MERGE (proto)-[:COMPOSES]->(a5)
MERGE (a1)-[:FOLLOWS]->(a2)
MERGE (a2)-[:FOLLOWS]->(a3)
MERGE (a3)-[:FOLLOWS]->(a4)
MERGE (a4)-[:FOLLOWS]->(a5);

// --- Being holds this protocol ---
MATCH (b:Being {node_id: 'being-seedforth'}), (proto:Protocol {node_id: 'protocol-ecosystem-status'})
MERGE (b)-[:HAS_PROTOCOL]->(proto);

RETURN 'SeedForth Ecosystem Map: 2 Servers + 10 Services + 23 SeedForth projects + 22 Delta projects + 3 Agents + 13 Repos + 1 Persona + 14 CypherAtoms + 1 Protocol + cross-connections = ' + toString(2+10+23+22+3+13+1+14+1) + ' new nodes + dense edge network' AS result;
