// @kind: seed
// ============================================================================
// Protocol: Compose Reply Seed
// ============================================================================
// Seeds the vocabulary needed by compose-reply.cypher:
//
//   :SwarmRole       — one per retrieval role (definition, metaphor, mechanism,
//                      principle, lineage, example, contrast). Each role carries
//                      its preferred labels, preferred edges, and output verb.
//
//   :EdgeConnective  — maps a typed edge name to an English connective phrase.
//                      compose-reply reads this at runtime so the connective
//                      table stays editable as graph data, not code.
//
//   :Skill           — skill-compose-reply, the user-facing skill that fans
//                      out role-based workers against a subgraph community
//                      and stitches a natural-language reply.
//
// Runs idempotent (MERGE-only) so re-running this file is safe.
// ============================================================================

// --- :SwarmRole vocabulary ------------------------------------------------

MERGE (r:SwarmRole {node_id: 'role-definition'})
SET r.role = 'definition',
    r.preferred_labels = ['Concept', 'Subsystem'],
    r.preferred_edges = ['DESCRIBES_IN', 'PART_OF'],
    r.verb = 'is',
    r.order = 1,
    r.description = 'What this thing fundamentally is. Pulls the closest Concept or Subsystem in the subgraph.',
    r.file_type = 'swarm-role';

MERGE (r:SwarmRole {node_id: 'role-metaphor'})
SET r.role = 'metaphor',
    r.preferred_labels = ['Metaphor'],
    r.preferred_edges = ['METAPHOR_OF'],
    r.verb = 'can be thought of as',
    r.order = 2,
    r.description = 'The biological/physical metaphor the system uses to make this thing intuitive.',
    r.file_type = 'swarm-role';

MERGE (r:SwarmRole {node_id: 'role-mechanism'})
SET r.role = 'mechanism',
    r.preferred_labels = ['Protocol', 'CypherAtom'],
    r.preferred_edges = ['IMPLEMENTS', 'POWERS', 'IMPLEMENTED_BY'],
    r.verb = 'is implemented via',
    r.order = 3,
    r.description = 'The concrete cypher protocol or atom that makes this thing real.',
    r.file_type = 'swarm-role';

MERGE (r:SwarmRole {node_id: 'role-principle'})
SET r.role = 'principle',
    r.preferred_labels = ['DesignPrinciple', 'Invariant'],
    r.preferred_edges = ['DESCRIBES_IN', 'PRINCIPLE_OF'],
    r.verb = 'rests on the principle that',
    r.order = 4,
    r.description = 'The invariant or design principle this thing is bound by.',
    r.file_type = 'swarm-role';

MERGE (r:SwarmRole {node_id: 'role-lineage'})
SET r.role = 'lineage',
    r.preferred_labels = ['Research', 'Hypothesis', 'Feature'],
    r.preferred_edges = ['ORIGINATES', 'LEADS_TO', 'IMPLEMENTS_VIA', 'TESTS_HYPOTHESIS'],
    r.verb = 'originated from',
    r.order = 5,
    r.description = 'Where this came from — research, hypothesis, or feature lineage.',
    r.file_type = 'swarm-role';

MERGE (r:SwarmRole {node_id: 'role-command'})
SET r.role = 'command',
    r.preferred_labels = ['Command'],
    r.preferred_edges = ['INVOKES', 'ALIAS_OF'],
    r.verb = 'the CLI gesture for this is',
    r.order = 5,
    r.description = 'The concrete mycelium CLI command the user can run to interact with this thing.',
    r.file_type = 'swarm-role';

MERGE (r:SwarmRole {node_id: 'role-example'})
SET r.role = 'example',
    r.preferred_labels = ['Guide', 'TestCase', 'CypherAtom'],
    r.preferred_edges = ['DOCUMENTS_IN'],
    r.verb = 'you can see this in action via',
    r.order = 6,
    r.description = 'A concrete usage example — a guide, test case, or worked atom.',
    r.file_type = 'swarm-role';


// --- :EdgeConnective map (typed edges → English phrases) -------------------

MERGE (e:EdgeConnective {edge_type: 'POWERS'})
  SET e.phrase = 'powers', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'METAPHOR_OF'})
  SET e.phrase = 'can be thought of as', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'IMPLEMENTS_VIA'})
  SET e.phrase = 'is implemented via', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'IMPLEMENTS'})
  SET e.phrase = 'implements', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'IMPLEMENTED_BY'})
  SET e.phrase = 'is implemented by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ORIGINATES'})
  SET e.phrase = 'originated as', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'LEADS_TO'})
  SET e.phrase = 'which led to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DESCRIBES_IN'})
  SET e.phrase = 'is described under', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DOCUMENTS_IN'})
  SET e.phrase = 'is documented in', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'COMPOSES'})
  SET e.phrase = 'composes into', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'TESTS_HYPOTHESIS'})
  SET e.phrase = 'tests the hypothesis that', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SURFACES_IN'})
  SET e.phrase = 'surfaces in', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SEEMS_LIKE'})
  SET e.phrase = 'resembles', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PART_OF'})
  SET e.phrase = 'is part of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PRINCIPLE_OF'})
  SET e.phrase = 'is a founding principle of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'INFERRED_SIMILAR'})
  SET e.phrase = 'is semantically close to', e.file_type = 'connective';


// --- :Skill node + lineage wiring ------------------------------------------

MERGE (s:Skill {node_id: 'skill-compose-reply'})
SET s.name = 'Compose Natural-Language Reply',
    s.description = 'Take a prompt embedding, resolve the seed node semantic community as scope, dispatch role-based retrieval (definition, metaphor, mechanism, principle, lineage, example), pairwise-clip fragments by cosine to keep only coherent ones, stitch into a sentence using EdgeConnective mappings, and cache the result as a Query node for reuse.',
    s.maturity = 'prototype',
    s.owner = 'Mycelium',
    s.file_type = 'skill';

// Wire the skill to its supporting protocols (MATCH only — they may not all exist)
MATCH (s:Skill {node_id: 'skill-compose-reply'})
MATCH (p:Protocol {node_id: 'protocol-compose-reply-seed'})
MERGE (s)-[:POWERS]->(p);


// --- Link the skill to the Ontology hub so it doesn't orphan ---------------
MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (s:Skill {node_id: 'skill-compose-reply'})
MERGE (s)-[:SKILL_OF]->(o);


// --- Also make sure the seed file is registered as a Protocol --------------
MERGE (p:Protocol {node_id: 'protocol-compose-reply-seed'})
SET p.label = 'Compose Reply Seed',
    p.description = 'Seeds SwarmRole vocabulary, EdgeConnective map, and the skill-compose-reply node.',
    p.file_type = 'protocol',
    p.source_file = 'graph/protocols/compose-reply-seed.cypher';


RETURN 'seeded compose-reply vocabulary: 6 SwarmRole, 16 EdgeConnective, 1 Skill' AS status;
