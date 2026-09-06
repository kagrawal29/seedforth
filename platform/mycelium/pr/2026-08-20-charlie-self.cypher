// Make Charlie (and the system) self-aware from the graph — not from files.
// atom-charlie-self: one query returns who he is, his mechanisms, his team, his
// workstreams, and the models available. Added to the founder grounding.

MERGE (a:CypherAtom {node_id: 'atom-charlie-self'})
SET a.semantic = 'Charlie full self-awareness: who he is, his protocols and cadence, his team of divisions, the projects he drives, active workstreams, and the models available',
    a.cypher = 'MATCH (c:Being {node_id: "being-charlie"}) OPTIONAL MATCH (c)-[:HOLDS]->(pu:Purpose) OPTIONAL MATCH (c)-[:HAS_NATURE]->(n:Nature) OPTIONAL MATCH (c)-[:HAS_PROTOCOL]->(pr:Protocol) OPTIONAL MATCH (c)-[:DELEGATES_TO]->(sa:SubAgent) OPTIONAL MATCH (c)-[:DRIVES]->(p:Project) OPTIONAL MATCH (w:Workstream) OPTIONAL MATCH (m:Model) RETURN pu.why AS purpose, collect(DISTINCT n.name) AS natures, collect(DISTINCT pr.label + " [cadence:" + coalesce(pr.cadence,"?") + "]") AS protocols, collect(DISTINCT sa.name + " (" + sa.role + ")") AS divisions, collect(DISTINCT p.name) AS projects, collect(DISTINCT w.name + " -> " + w.branch + " (" + w.status + ")") AS workstreams, collect(DISTINCT m.name + " [" + reduce(s="", c IN m.capabilities | s + c + " ") + "]") AS models';

// Insert self-awareness into the founder grounding: identity -> alignments -> drive -> self -> briefing -> focus
MATCH (a2:CypherAtom {node_id: 'atom-charlie-alignments'})
MATCH (a3:CypherAtom {node_id: 'atom-charlie-drive'})
MATCH (a4:CypherAtom {node_id: 'atom-charlie-briefing'})
MATCH (self:CypherAtom {node_id: 'atom-charlie-self'})
MERGE (a3)-[:FOLLOWS]->(self)
MERGE (self)-[:FOLLOWS]->(a4);
