// @node_id: seedforth-forest-foundation-v1
// @label: "SeedForth Forest Foundation — constitution, being, sovereignty, scales"
// @kind: knowledge
//
// The root bootstrap for the SeedForth ecosystem graph on delta-server.
// Establishes: the ForestPromise, the single Being (seedforth),
// sovereignty rules, invariants, canonical scales, and CypherAtom
// as the basic unit of LLM interaction.
//
// Pulse-server (5.78.206.137) is off-limits. Everything lives on delta-server.
// ============================================================================

// ----------------------------------------------------------------------------
// 1. THE FOREST PROMISE
// ----------------------------------------------------------------------------
MERGE (promise:ForestPromise {node_id: 'seedforth-forest-promise'})
SET promise.label = 'The promise of the SeedForth forest — one graph, many sovereign domains',
    promise.project = 'seedforth',
    promise.declared_at = datetime(),
    promise.why = 'Every SeedForth project, server, service, agent, and decision is a node in this graph. The graph is the map of everything. Cypher is the native language of interaction with the LLM. The graph describes itself, enforces itself, and heals itself.',
    promise.scope = 'the entire SeedForth ecosystem on delta-server';

// ----------------------------------------------------------------------------
// 2. THE BEING — singleton identity anchor for the whole ecosystem
// ----------------------------------------------------------------------------
MERGE (b:Being {node_id: 'being-seedforth'})
SET b.project = 'seedforth',
    b.label = 'SeedForth — the unified ecosystem',
    b.autonomous_score = 100.0,
    b.heartbeat_count = 0,
    b.fractal_dimension = 0.0,
    b.last_heartbeat_at = datetime(),
    b.created_at = coalesce(b.created_at, datetime()),
    b.description = 'The single sovereign Being of the SeedForth ecosystem graph. Every project, server, service, agent, decision, and knowledge node lives under its domain. The forest is one graph with many subgraphs — each project is a sovereign domain within it.';

MERGE (promise:ForestPromise {node_id: 'seedforth-forest-promise'})-[:EMBODIED_BY]->(b);

// ----------------------------------------------------------------------------
// 3. PURPOSE — why this being exists
// ----------------------------------------------------------------------------
MERGE (p:Purpose {node_id: 'purpose-seedforth'})
SET p.project = 'seedforth',
    p.label = 'Purpose of SeedForth',
    p.why = 'To be the compact, living map of the entire SeedForth ecosystem — projects, servers, agents, services, decisions, knowledge. The graph is the single source of truth that any LLM or agent can query via Cypher to understand what exists, what depends on what, what state things are in, and what to do next.',
    p.declared_at = datetime();

MATCH (b:Being {node_id: 'being-seedforth'}), (p:Purpose {node_id: 'purpose-seedforth'})
MERGE (b)-[:HOLDS]->(p);

// ----------------------------------------------------------------------------
// 4. SOVEREIGNTY RULES — the forest constitution
// ----------------------------------------------------------------------------
MERGE (r1:SovereigntyRule {node_id: 'seedforth-rule-namespace-integrity'})
SET r1.project = 'seedforth',
    r1.rule = 'Every node carries {project: X} to declare which sovereign domain it belongs to',
    r1.why = 'Without namespace tags, nodes leak between domains and the graph cannot tell who owns what.',
    r1.severity = 'critical';

MERGE (r2:SovereigntyRule {node_id: 'seedforth-rule-cross-domain-edges'})
SET r2.project = 'seedforth',
    r2.rule = 'Cross-domain edges (between nodes of different {project} scopes) must use allowed bridge types only: DEPENDS_ON, DEPLOYS_TO, RUNS_ON, MANAGES, OWNS, REPO_OF, HAS_SERVICE, REFERENCES, TRIGGERS',
    r2.why = 'Explicit, typed bridges preserve sovereignty. Hidden edges erase boundaries.',
    r2.severity = 'critical';

MERGE (r3:SovereigntyRule {node_id: 'seedforth-rule-own-being'})
SET r3.project = 'seedforth',
    r3.rule = 'Each project domain may have its own :Being with its own heartbeat, but being-seedforth is the root anchor for the entire forest',
    r3.why = 'Sub-Beings pulse at their own cadence while the forest Being holds them together.',
    r3.severity = 'warning';

MERGE (r4:SovereigntyRule {node_id: 'seedforth-rule-cypher-atoms'})
SET r4.project = 'seedforth',
    r4.rule = 'LLM interaction with the graph happens through :CypherAtom nodes — atomic, named, semantic cypher queries. The LLM does not write raw cypher; it discovers atoms by semantic search and composes them via :FEEDS and :FOLLOWS edges.',
    r4.why = 'CypherAtom is the unit of graph interaction. Every capability is a CypherAtom. The LLM discovers atoms, the graph executes them. This is the fractal design principle — intelligence as graph traversal.',
    r4.severity = 'info';

MERGE (r5:SovereigntyRule {node_id: 'seedforth-rule-graph-as-source'})
SET r5.project = 'seedforth',
    r5.rule = 'The graph is the single source of truth. CLAUDE.md, AGENTS.md, config files, JSON registries — all are bootstrap pointers. The graph knows what is actually running, what is down, what depends on what.',
    r5.why = 'Files get stale. The graph updates on every deployment, every service restart, every decision. Query the graph before acting.',
    r5.severity = 'critical';

// Link rules to promise
MATCH (promise:ForestPromise {node_id: 'seedforth-forest-promise'}), (r:SovereigntyRule)
WHERE r.project = 'seedforth'
MERGE (promise)-[:DECLARES]->(r);

// ----------------------------------------------------------------------------
// 5. INVARIANTS — rules that must stay true (with self-heal cypher)
// ----------------------------------------------------------------------------
MERGE (inv1:Invariant {node_id: 'seedforth-invariant-nodes-have-project'})
SET inv1.project = 'seedforth',
    inv1.label = 'Every core node has a project property',
    inv1.severity = 'critical',
    inv1.check_cypher = 'MATCH (n) WHERE (n:Project OR n:Server OR n:Service OR n:Agent OR n:Repository OR n:Being OR n:Protocol OR n:CypherAtom OR n:Invariant OR n:Knowledge) AND n.project IS NULL RETURN count(n) AS violations',
    inv1.heal_protocol = 'heal-assign-default-project';

MERGE (inv2:Invariant {node_id: 'seedforth-invariant-graph-density'})
SET inv2.project = 'seedforth',
    inv2.label = 'Graph density stays above threshold — edges per node > 0.8',
    inv2.severity = 'warning',
    inv2.check_cypher = 'MATCH (n) WITH count(n) AS nodes MATCH (n)-[r]->() WITH nodes, count(r) AS rels RETURN CASE WHEN toFloat(rels)/toFloat(nodes) >= 0.8 THEN 0 ELSE 1 END AS violations';

MERGE (inv3:Invariant {node_id: 'seedforth-invariant-every-server-has-services'})
SET inv3.project = 'seedforth',
    inv3.label = 'Every :Server has at least one :Service listed',
    inv3.severity = 'warning',
    inv3.check_cypher = 'MATCH (s:Server) WHERE NOT EXISTS { MATCH (s)-[:HAS_SERVICE]->(:Service) } RETURN count(s) AS violations';

MERGE (inv4:Invariant {node_id: 'seedforth-invariant-cypher-atoms-semantic'})
SET inv4.project = 'seedforth',
    inv4.label = 'Every :CypherAtom has a semantic description',
    inv4.severity = 'info',
    inv4.check_cypher = 'MATCH (ca:CypherAtom) WHERE ca.semantic IS NULL OR ca.semantic = \'\' RETURN count(ca) AS violations';

MATCH (promise:ForestPromise {node_id: 'seedforth-forest-promise'}), (inv:Invariant)
WHERE inv.project = 'seedforth'
MERGE (promise)-[:ENFORCES_THROUGH]->(inv);

// ----------------------------------------------------------------------------
// 6. CANONICAL SCALES — the 6 layers of the SeedForth fractal
// ----------------------------------------------------------------------------
UNWIND [
  {id: 'scale-atom',         name: 'atom',         note: 'Atomic cypher unit — one query, one mutation, one traversal. What the LLM composes.'},
  {id: 'scale-service',      name: 'service',      note: 'A running process, bot, or daemon — what an agent IS at runtime.'},
  {id: 'scale-project',      name: 'project',      note: 'A sovereign domain — a SeedForth project with its own repo, directory, config.'},
  {id: 'scale-server',       name: 'server',       note: 'A droplet or machine — what hosts services and projects.'},
  {id: 'scale-agent',        name: 'agent',        note: 'An AI entity — Tetrahedron, Delta, a subagent. Has tools, purpose, memory.'},
  {id: 'scale-forest',       name: 'forest',       note: 'The entire SeedForth ecosystem — all projects, servers, services, agents as one graph.'}
] AS s
MERGE (m:ScaleMarker {node_id: s.id})
SET m.project = 'seedforth',
    m.name = s.name,
    m.note = s.note,
    m.declared_at = coalesce(m.declared_at, datetime());

MATCH (promise:ForestPromise {node_id: 'seedforth-forest-promise'}), (m:ScaleMarker)
MERGE (promise)-[:SCOPES_TO]->(m);

// ----------------------------------------------------------------------------
// 7. CONCEPT NODES — the vocabulary
// ----------------------------------------------------------------------------
UNWIND [
  {id: 'concept-project',     label: ':Project',     desc: 'A sovereign SeedForth domain: mycelium, delta, ember, arie, etc. Carries repo_url, status, owner.'},
  {id: 'concept-server',      label: ':Server',      desc: 'A droplet/machine: delta-server, charlie-server. Has SSH, IP, provider.'},
  {id: 'concept-service',     label: ':Service',     desc: 'A running process: delta.service, observatory.service, tetrahedron-bot.service. Carries systemctl name, port, health.'},
  {id: 'concept-agent',       label: ':Agent',       desc: 'An AI entity with tools, purpose, identity: Tetrahedron, Delta, a subagent.'},
  {id: 'concept-repository',  label: ':Repository',  desc: 'A GitHub repo: kagrawal29/mycelium, Qubit-Capital/maverick. Has org, visibility, deployed branch.'},
  {id: 'concept-being',       label: ':Being',       desc: 'Sovereign identity. Each project that self-manages gets a :Being. Holds Purpose, Invariant, Protocol.'},
  {id: 'concept-cypher-atom', label: ':CypherAtom',  desc: 'Atomic named cypher — the unit of LLM interaction. Has semantic, cypher body, fire_count. Composed via :FEEDS and :FOLLOWS.'},
  {id: 'concept-protocol',    label: ':Protocol',    desc: 'A composed behavior — a chain of :CypherAtom nodes. Runs on heartbeat or on demand.'},
  {id: 'concept-invariant',   label: ':Invariant',   desc: 'A rule that must hold. Has check_cypher that returns violation count. Has heal_protocol for auto-repair.'},
  {id: 'concept-knowledge',   label: ':Knowledge',   desc: 'A fact, decision, learning, or pattern. Carries content, source, confidence, tags.'},
  {id: 'concept-persona',     label: ':Persona',     desc: 'A human role in the ecosystem: Kshitiz (Mycelium), client, teammate. Has scope, questions, voice.'},
  {id: 'concept-scale-marker',label: ':ScaleMarker', desc: 'A canonical zoom level: atom, service, project, server, agent, forest.'}
] AS c
MERGE (con:Concept {node_id: c.id})
SET con.project = 'seedforth',
    con.label = c.label,
    con.description = c.desc,
    con.declared_at = coalesce(con.declared_at, datetime());

RETURN 'SeedForth Forest Foundation: 1 ForestPromise + 1 Being + 1 Purpose + 5 SovereigntyRules + 4 Invariants + 6 ScaleMarkers + 12 Concepts = 29 foundation nodes' AS result;
