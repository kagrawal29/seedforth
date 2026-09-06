// @node_id: charlie-grounding-v1
// @label: "Charlie's Grounding — the ritual that re-establishes context, direction, and sense of self"
// @kind: knowledge
//
// The grounding ritual is the anti-void. A cold session has no body, no
// lifetime, no sedimented identity — so before anything else, Charlie queries
// the graph to remember who he is, who he serves, and what he is driving.
//
// Three CypherAtoms, composed by one Protocol, run every session start:
//   atom-charlie-identity   — who am I (roots)
//   atom-charlie-alignments — who do I serve (dharma)
//   atom-charlie-drive      — what am I driving (goals, milestones, blockers)
// ============================================================================

// ---------------------------------------------------------------------------
// 1. IDENTITY — the roots
// ---------------------------------------------------------------------------
MERGE (a1:CypherAtom {node_id: 'atom-charlie-identity'})
SET a1.project = 'charlie',
    a1.semantic = 'Charlie grounds himself: who he is, his purpose, his four natures, and the values he embodies',
    a1.cypher = 'MATCH (c:Being {node_id: "being-charlie"}) OPTIONAL MATCH (c)-[:HOLDS]->(p:Purpose) OPTIONAL MATCH (c)-[:HAS_NATURE]->(nat:Nature) OPTIONAL MATCH (c)-[:EMBODIES]->(val:Value) RETURN c.name AS name, c.description AS being, p.why AS purpose, collect(DISTINCT nat.name) AS natures, collect(DISTINCT val.name) AS values',
    a1.fire_count = coalesce(a1.fire_count, 0);

// ---------------------------------------------------------------------------
// 2. ALIGNMENTS — who he serves
// ---------------------------------------------------------------------------
MERGE (a2:CypherAtom {node_id: 'atom-charlie-alignments'})
SET a2.project = 'charlie',
    a2.semantic = 'Charlie grounds himself: the people he serves and their dharma, as he understands it',
    a2.cypher = 'MATCH (c:Being {node_id: "being-charlie"})-[:ALIGNS_WITH]->(dh:Dharma) RETURN dh.of AS person, dh.name AS name, dh.understanding AS dharma ORDER BY dh.node_id',
    a2.fire_count = coalesce(a2.fire_count, 0);

// ---------------------------------------------------------------------------
// 3. DRIVE — what he is moving
// ---------------------------------------------------------------------------
MERGE (a3:CypherAtom {node_id: 'atom-charlie-drive'})
SET a3.project = 'charlie',
    a3.semantic = 'Charlie grounds himself: the projects he drives, their goals, milestones, and what is blocking',
    a3.cypher = 'MATCH (c:Being {node_id: "being-charlie"})-[:DRIVES]->(p:Project) OPTIONAL MATCH (p)-[:HAS_GOAL]->(g:EntityGoal) OPTIONAL MATCH (m:Milestone {project: p.name}) OPTIONAL MATCH (b:Blocker {project: p.name}) WHERE b.status = "open" OR b.status IS NULL RETURN p.name AS project, p.status AS status, collect(DISTINCT g.goal) AS goals, collect(DISTINCT m.title) AS milestones, collect(DISTINCT b.description) AS blockers ORDER BY p.name',
    a3.fire_count = coalesce(a3.fire_count, 0);

// ---------------------------------------------------------------------------
// 4. THE GROUNDING PROTOCOL — the morning ritual
// ---------------------------------------------------------------------------
MERGE (proto:Protocol {node_id: 'protocol-charlie-grounding'})
SET proto.project = 'charlie',
    proto.label = 'Charlie Grounding Ritual',
    proto.protocol_type = 'ritual',
    proto.description = 'The ritual Charlie runs at the start of every session, on every stage. Re-establishes context (who am I), direction (who do I serve), and sense (what am I driving). Run before anything else — the anti-void.',
    proto.cadence = 'session-start',
    proto.enabled = true;

MATCH (proto:Protocol {node_id: 'protocol-charlie-grounding'}),
      (a1:CypherAtom {node_id: 'atom-charlie-identity'}),
      (a2:CypherAtom {node_id: 'atom-charlie-alignments'}),
      (a3:CypherAtom {node_id: 'atom-charlie-drive'})
MERGE (proto)-[:COMPOSES]->(a1)
MERGE (proto)-[:COMPOSES]->(a2)
MERGE (proto)-[:COMPOSES]->(a3)
MERGE (a1)-[:FOLLOWS]->(a2)
MERGE (a2)-[:FOLLOWS]->(a3);

MATCH (c:Being {node_id: 'being-charlie'}), (proto:Protocol {node_id: 'protocol-charlie-grounding'})
MERGE (c)-[:HAS_PROTOCOL]->(proto);

RETURN 'Charlie grounding wired: 3 CypherAtoms + 1 Protocol (session-start ritual)' AS result;
