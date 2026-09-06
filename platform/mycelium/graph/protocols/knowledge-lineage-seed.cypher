// @kind: seed
// ============================================================================
// Protocol: Knowledge Lineage Seed
// ============================================================================
// Extends the docs layer with the full research → UI lineage model.
// Every step from an unformed research note all the way to a shipped UI
// component gets its own node label + provenance edges. Trustable,
// testable, auditable, aware.
//
// The lineage chain (conceptual, not enforced):
//
//   :Research  (notes, papers, fragments)
//       -[:ORIGINATES]->
//   :Hypothesis  (if X then Y, unproven)
//       -[:LEADS_TO]->
//   :Skill  (reusable capability: "how to X")
//       -[:POWERS]->
//   :Workflow  (sequence of operations achieving a goal)
//       -[:COMPOSES]->
//   :CypherAtom  (atomic cypher executed at graph runtime)
//       -[:IMPLEMENTED_BY]->
//   :ExternalCode  (the actual .py/.sh/.ts file)
//       -[:SURFACES_IN]->
//   :UIComponent (already exists in legacy graph)
//       -[:USED_BY]->
//   :Person  (user / agent / subagent)
//
// And:
//   :Subagent  — an autonomous agent with its own system prompt + tools
//   :Schema    — data shape, typed contract
//   :Feature   — product-level capability (user-visible)
//   :AuditTrail — trail of mutations, who did what when
//
// These are declared as :Concept nodes here with minimal seed instances
// illustrating the chain. Real research/features get added incrementally
// as the system grows. This file is the VOCABULARY, not the content.
// ============================================================================


// --- New concepts (lineage vocabulary) --------------------------------------

MERGE (c:Concept {node_id: 'concept-research'})
SET c.name = 'Research', c.order = 20, c.category = 'lineage',
    c.description = 'A note, paper, fragment, or unformed idea that could eventually become something. Researches have author, created_at, tags, and an optional :ORIGINATES edge to one or more :Hypothesis nodes that the research suggests. They are auditable — every reader can see where an idea came from.',
    c.example = 'MATCH (r:Research {topic: "Hebbian learning"}) RETURN r.content, r.author, r.created_at',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-hypothesis'})
SET c.name = 'Hypothesis', c.order = 21, c.category = 'lineage',
    c.description = 'An if-X-then-Y claim that is not yet verified. Carries a confidence score, evidence links (to :Research and :TestCase nodes), and a status (proposed | investigating | supported | refuted). A hypothesis becomes a :Skill or a :Feature when verified.',
    c.example = 'MATCH (h:Hypothesis {status: "investigating"}) RETURN h.claim, h.confidence',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-skill'})
SET c.name = 'Skill', c.order = 22, c.category = 'lineage',
    c.description = 'A reusable capability — "how to do X". Skills are bundles of :CypherAtom + :ExternalCode + :IntegrationPoint that together achieve a goal. Skills can be composed into :Workflow nodes. A skill has an owner, a maturity level, and a test coverage score.',
    c.example = 'MATCH (s:Skill)-[:POWERS]->(w:Workflow) RETURN s.name, w.name',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-workflow'})
SET c.name = 'Workflow', c.order = 23, c.category = 'lineage',
    c.description = 'A sequence of operations achieving a user-level goal. Workflows :COMPOSE :CypherAtoms and/or :Skills, and each step is auditable via QueryTrace. Workflows can be :TRIGGERED_BY events (commit, webhook, cron) and have expected duration + success criteria.',
    c.example = 'MATCH (w:Workflow {name: "onboard-contributor"})-[:COMPOSES]->(atom:CypherAtom) RETURN atom.node_id, atom.semantic',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-subagent'})
SET c.name = 'Subagent', c.order = 24, c.category = 'lineage',
    c.description = 'An autonomous agent with its own system prompt, tool set, and identity. Subagents have a name, role, system_prompt, tools (list of :Command or :Skill node_ids), owner, and a :TRACE edge to every QueryTrace they originate. The graph tracks which subagent did what — full provenance per action.',
    c.example = 'MATCH (sa:Subagent)-[:USES_SKILL]->(sk:Skill) RETURN sa.name, sk.name',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-schema'})
SET c.name = 'Schema', c.order = 25, c.category = 'lineage',
    c.description = 'A typed contract — the shape of a node label, the shape of an edge, the shape of an external API response. Schemas have a version, a set of required fields, optional fields, and an example. Validated at ingestion time by validate-merge.',
    c.example = 'MATCH (sc:Schema {for_label: "Species"}) RETURN sc.version, sc.required_fields',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-feature'})
SET c.name = 'Feature', c.order = 26, c.category = 'lineage',
    c.description = 'A user-visible product capability. Features :IMPLEMENT :Workflow + :Skill, :SURFACE_IN :UIComponent, and have acceptance criteria (:TestCase list). Every feature carries its lineage from the :Research it came from, through :Hypothesis, to shipped code + UI. Feature flags can mark features as experimental/stable/deprecated.',
    c.example = 'MATCH (f:Feature)-[:SURFACES_IN]->(ui:UIComponent) RETURN f.name, ui.label',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-audittrail'})
SET c.name = 'AuditTrail', c.order = 27, c.category = 'lineage',
    c.description = 'The chain of mutations on a node or subsystem. Every write goes through validate-merge which mints a candidate species — the species chain itself IS the audit trail at the system level. For per-node audit, each node can carry modified_by, modified_at, and a :LAST_MODIFIED_BY edge to a :Person or :Subagent.',
    c.example = 'MATCH (n)-[:LAST_MODIFIED_BY]->(p:Person) WHERE n.modified_at > "2026-04-01" RETURN n.node_id, p.alias',
    c.file_type = 'concept';


// --- Worked example: a tiny end-to-end lineage chain -----------------------
// One Research note, one Hypothesis, one Skill, one Workflow, one Feature,
// connected by typed edges. Proves the chain pattern with real nodes the
// graph can query.

MERGE (r:Research {node_id: 'research-hebbian-graph-learning'})
SET r.topic = 'Fire-together-wire-together for graph traversal',
    r.content = 'Neural Hebbian learning suggests that edges traversed frequently should strengthen over time. Applied to a knowledge graph, this could let the system learn which cypher patterns are its hot paths without explicit indexing. Evidence: Hebbian (1949), modern reinforcement learning on graphs, query-result caching literature.',
    r.author = 'Mycelium',
    r.created_at = toString(datetime()),
    r.tags = ['graph', 'learning', 'hebbian', 'hot-paths'],
    r.file_type = 'research';

MERGE (h:Hypothesis {node_id: 'hypothesis-edge-fire-count'})
SET h.claim = 'If we increment a fire_count on every traversed edge and prefer high-count edges at query time, the graph will self-optimize its access patterns without explicit indexing.',
    h.confidence = 0.7,
    h.status = 'investigating',
    h.authored_at = toString(datetime()),
    h.file_type = 'hypothesis';

MERGE (s:Skill {node_id: 'skill-hebbian-strengthening'})
SET s.name = 'Hebbian Edge Strengthening',
    s.description = 'Given recent query traces, increment fire_count on edges between pairs of cited nodes. Weight accumulates in repeated co-citation patterns.',
    s.maturity = 'prototype',
    s.owner = 'Mycelium',
    s.file_type = 'skill';

MERGE (w:Workflow {node_id: 'workflow-strengthen-recent'})
SET w.name = 'Strengthen Recent Paths',
    w.description = 'Periodic workflow: read QueryTraces from last 60 minutes, extract touched_ids, increment fire_count on edges between them.',
    w.trigger = 'cron(5m)',
    w.success_criteria = 'No error + at least one edge updated per invocation when QueryTraces exist',
    w.file_type = 'workflow';

MERGE (f:Feature {node_id: 'feature-self-learning-graph'})
SET f.name = 'Self-Learning Graph Traversal',
    f.description = 'The graph accumulates evidence about which paths it actually uses, and traversals prefer strong paths. No explicit indexing required.',
    f.status = 'experimental',
    f.user_facing_name = '(internal)',
    f.file_type = 'feature';


// --- Wire the lineage ------------------------------------------------------
MATCH (r:Research {node_id: 'research-hebbian-graph-learning'})
MATCH (h:Hypothesis {node_id: 'hypothesis-edge-fire-count'})
MERGE (r)-[:ORIGINATES]->(h);

MATCH (h:Hypothesis {node_id: 'hypothesis-edge-fire-count'})
MATCH (s:Skill {node_id: 'skill-hebbian-strengthening'})
MERGE (h)-[:LEADS_TO]->(s);

MATCH (s:Skill {node_id: 'skill-hebbian-strengthening'})
MATCH (w:Workflow {node_id: 'workflow-strengthen-recent'})
MERGE (s)-[:POWERS]->(w);

MATCH (w:Workflow {node_id: 'workflow-strengthen-recent'})
MATCH (a:CypherAtom {source_protocol: 'protocol-strengthen-edges'})
MERGE (w)-[:COMPOSES]->(a);

MATCH (w:Workflow {node_id: 'workflow-strengthen-recent'})
MATCH (f:Feature {node_id: 'feature-self-learning-graph'})
MERGE (f)-[:IMPLEMENTS_VIA]->(w);

MATCH (f:Feature {node_id: 'feature-self-learning-graph'})
MATCH (h:Hypothesis {node_id: 'hypothesis-edge-fire-count'})
MERGE (f)-[:TESTS_HYPOTHESIS]->(h);


// --- Link to the ontology hub so these are not orphans --------------------
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (c:Concept) WHERE c.category = 'lineage'
MERGE (c)-[:DESCRIBES_IN]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (r:Research) MERGE (r)-[:RESEARCH_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (h:Hypothesis) MERGE (h)-[:HYPOTHESIS_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (sk:Skill) WHERE sk.owner IS NOT NULL MERGE (sk)-[:SKILL_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (w:Workflow) MERGE (w)-[:WORKFLOW_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (f:Feature) MERGE (f)-[:FEATURE_OF]->(o);


RETURN 'seeded lineage vocabulary + worked example (research → feature)' AS status;
