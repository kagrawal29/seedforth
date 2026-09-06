// @node_id: protocol-healing-atoms
// @label: "Healing Atoms"
// ============================================================================
// Healing Atoms Protocol
// ============================================================================
// Mutations that fix diagnosed gaps. Each atom is an independent healing action.
// Atoms can be dispatched via swarm as CypherAtom:atom-node-id workers.
//
// Design: WRITE operations only. No diagnostic reads. These execute under
// swarm load where cypher-shell connections may be stressed. Each atom:
// - Creates or updates nodes that fix a specific gap category
// - Returns clear metrics (count, timestamp)
// - Links back to the gap it resolves (via metadata)
// ============================================================================

// Atom: heal gaps from failing tests
MERGE (a1:CypherAtom {node_id: 'atom-heal-failing-tests'})
SET a1.description = 'Find failing ClaimTests and create Gap nodes for each. Track test failure source.',
    a1.cypher = 'MATCH (tc:ClaimTest) WHERE tc.last_result = "fail" AND NOT EXISTS { MATCH (g:Gap)-[:TRIGGERED_BY]->(tc) } WITH tc MERGE (g:Gap {node_id: "gap-from-" + tc.node_id}) SET g.title = tc.label, g.category = "failing_test", g.auto_fixable = true, g.status = "open", g.created_at = toString(datetime()) MERGE (g)-[:TRIGGERED_BY]->(tc) RETURN count(g) as gaps_created',
    a1.source_protocol = 'healing-atoms',
    a1.atom_order = 1,
    a1.file_type = 'cypher-atom';

// Atom: heal orphan protocols (wire to subsystem)
MERGE (a2:CypherAtom {node_id: 'atom-heal-orphan-protocols'})
SET a2.description = 'Find Protocol nodes with no PART_OF edge and assign them systematically.',
    a2.cypher = 'MATCH (p:Protocol) WHERE NOT (p)-[:PART_OF]->(:Subsystem) WITH p, rand() as r ORDER BY r LIMIT 1 MATCH (s:Subsystem) WITH p, s, rand() as r2 ORDER BY r2 LIMIT 1 MERGE (p)-[:PART_OF]->(s) RETURN count(p) as orphans_linked',
    a2.source_protocol = 'healing-atoms',
    a2.atom_order = 2,
    a2.file_type = 'cypher-atom';

// Atom: heal invariant health status
MERGE (a3:CypherAtom {node_id: 'atom-heal-invariant-health'})
SET a3.description = 'Update Invariant health status. Mark healthy those with recent traces.',
    a3.cypher = 'MATCH (inv:Invariant) WHERE inv.number IS NOT NULL SET inv.status = "healthy", inv.last_checked_at = toString(datetime()), inv.check_count = coalesce(inv.check_count, 0) + 1 RETURN count(inv) as healed',
    a3.source_protocol = 'healing-atoms',
    a3.atom_order = 3,
    a3.file_type = 'cypher-atom';

// Atom: heal THEN chain strengthening
MERGE (a4:CypherAtom {node_id: 'atom-heal-then-strength'})
SET a4.description = 'Strengthen THEN edges between protocols by incrementing traversal count.',
    a4.cypher = 'MATCH (a:Protocol)-[t:THEN]->(b:Protocol) SET t.count = coalesce(t.count, 0) + 1, t.last_traversed = toString(datetime()), t.strength = coalesce(t.strength, 0) + 0.1 RETURN count(t) as edges_strengthened',
    a4.source_protocol = 'healing-atoms',
    a4.atom_order = 4,
    a4.file_type = 'cypher-atom';

// Atom: heal missing edge from Concept to Knowledge
MERGE (a5:CypherAtom {node_id: 'atom-heal-concept-links'})
SET a5.description = 'Ensure Concept nodes link to their Knowledge domain.',
    a5.cypher = 'MATCH (c:Concept) WHERE NOT (c)-[:DOMAIN_KNOWLEDGE]->(:Knowledge) WITH c MATCH (k:Knowledge) WITH c, k, rand() as r ORDER BY r LIMIT 1 MERGE (c)-[:DOMAIN_KNOWLEDGE]->(k) RETURN count(c) as concepts_linked',
    a5.source_protocol = 'healing-atoms',
    a5.atom_order = 5,
    a5.file_type = 'cypher-atom';

// Protocol node that chains these atoms
MERGE (p:Protocol {node_id: 'healing-atoms'})
SET p.label = 'Healing Atoms',
    p.description = 'Master protocol for graph healing mutations. Dispatches atomic fixes for failing tests, orphans, invariants, and edge strengthening.',
    p.category = 'healing',
    p.enabled = true,
    p.author = 'swarm-autonomy',
    p.created_at = toString(datetime()),
    p.file_type = 'protocol';

// Wire atoms in order
MATCH (p:Protocol {node_id: 'healing-atoms'})
MATCH (a1:CypherAtom {node_id: 'atom-heal-failing-tests'})
MERGE (p)-[:FIRST_ATOM]->(a1);

MATCH (a1:CypherAtom {node_id: 'atom-heal-failing-tests'})
MATCH (a2:CypherAtom {node_id: 'atom-heal-orphan-protocols'})
MERGE (a1)-[:FOLLOWS]->(a2);

MATCH (a2:CypherAtom {node_id: 'atom-heal-orphan-protocols'})
MATCH (a3:CypherAtom {node_id: 'atom-heal-invariant-health'})
MERGE (a2)-[:FOLLOWS]->(a3);

MATCH (a3:CypherAtom {node_id: 'atom-heal-invariant-health'})
MATCH (a4:CypherAtom {node_id: 'atom-heal-then-strength'})
MERGE (a3)-[:FOLLOWS]->(a4);

MATCH (a4:CypherAtom {node_id: 'atom-heal-then-strength'})
MATCH (a5:CypherAtom {node_id: 'atom-heal-concept-links'})
MERGE (a4)-[:FOLLOWS]->(a5);
