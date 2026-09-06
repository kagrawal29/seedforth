// @node_id: protocol-edge-connectives-expand
// @label: "Expand Edge Connectives"
// ============================================================================
// Protocol: Expand Edge Connectives
// ============================================================================
// Purpose:
//   The compose-reply protocol depends on :EdgeConnective nodes to map typed
//   edges to natural English phrases at runtime. The initial seed had 16
//   connectives covering common edges (POWERS, METAPHOR_OF, IMPLEMENTS, etc).
//
//   The live graph has 148 edge types in use. This file adds connectives for
//   the 134 unmapped edge types, ensuring no silent gaps when compose-reply
//   traverses the knowledge base.
//
// What it does:
//   MERGE creates a new :EdgeConnective node for each unmapped edge type,
//   pairing it with a natural English phrase. Idempotent — safe to re-run.
//   Does NOT modify existing connectives (MERGE preserves them).
//
// How to re-run:
//   docker exec -i mycelium-neo4j-local cypher-shell -u neo4j -p localtest12 \
//     --encryption false < graph/protocols/edge-connectives-expand.cypher
//
//   Then verify:
//   docker exec -i mycelium-neo4j-local cypher-shell -u neo4j -p localtest12 \
//     --encryption false --format plain <<< \
//     "MATCH (ec:EdgeConnective) RETURN count(ec) as total_connectives"
//   Expected: 150 (16 existing + 134 new)
//
// ============================================================================

// High-frequency unmapped edges (>10 occurrences) — these connect major concepts
MERGE (e:EdgeConnective {edge_type: 'RELATES_TO'})
  SET e.phrase = 'relates to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'IN_REPO'})
  SET e.phrase = 'is located in', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'INSTANCE_OF'})
  SET e.phrase = 'is an instance of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ENABLES'})
  SET e.phrase = 'enables', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'INVOLVES'})
  SET e.phrase = 'involves', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PART_OF_RHYTHM'})
  SET e.phrase = 'is part of the rhythm of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'TESTS'})
  SET e.phrase = 'tests', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RENDERS'})
  SET e.phrase = 'renders', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'VALIDATES'})
  SET e.phrase = 'validates', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'TRIGGERS'})
  SET e.phrase = 'triggers', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'COUPLED_TO'})
  SET e.phrase = 'is coupled to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'UPHOLDS'})
  SET e.phrase = 'upholds', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'REFERENCES'})
  SET e.phrase = 'references', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'IMPORTS'})
  SET e.phrase = 'imports', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ADDRESSES'})
  SET e.phrase = 'addresses', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'MADE_BY'})
  SET e.phrase = 'is made by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'MODIFIES'})
  SET e.phrase = 'modifies', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CONCEPTUALLY_RELATED_TO'})
  SET e.phrase = 'is conceptually related to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SHOWS'})
  SET e.phrase = 'shows', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CONTAINS_CONCEPT'})
  SET e.phrase = 'contains the concept of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'TRACKS'})
  SET e.phrase = 'tracks', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FEEDS_INTO'})
  SET e.phrase = 'feeds into', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FOLLOWS'})
  SET e.phrase = 'follows', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SERVES_SCENARIO'})
  SET e.phrase = 'serves the scenario of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RELATES_TO_ENTRY'})
  SET e.phrase = 'relates to the entry', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SERVES'})
  SET e.phrase = 'serves', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CONTAINS_FEATURE'})
  SET e.phrase = 'contains the feature of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FEATURE_OF'})
  SET e.phrase = 'is a feature of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PROPOSED'})
  SET e.phrase = 'was proposed', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EXPERIENCES'})
  SET e.phrase = 'experiences', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FIRES_AT'})
  SET e.phrase = 'fires at', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SOURCED_BY'})
  SET e.phrase = 'is sourced by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RESOLVES_WITH'})
  SET e.phrase = 'resolves with', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RATIONALE_FOR'})
  SET e.phrase = 'is the rationale for', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SEMANTICALLY_SIMILAR_TO'})
  SET e.phrase = 'is semantically similar to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FIRES_DURING'})
  SET e.phrase = 'fires during', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SPAWNED'})
  SET e.phrase = 'spawned', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DEPENDS_ON'})
  SET e.phrase = 'depends on', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SPAWN'})
  SET e.phrase = 'spawns', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DESCENDED_FROM'})
  SET e.phrase = 'descended from', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CONVERGES_TO'})
  SET e.phrase = 'converges to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DRAWN_TO'})
  SET e.phrase = 'is drawn to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ADDRESSES_SCENARIO'})
  SET e.phrase = 'addresses the scenario of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'UPHELD_BY'})
  SET e.phrase = 'is upheld by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CONSTRAINS'})
  SET e.phrase = 'constrains', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SUFFERS'})
  SET e.phrase = 'suffers from', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FIRST_ATOM'})
  SET e.phrase = 'has its first atom as', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PARENT_OF'})
  SET e.phrase = 'is the parent of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'TESTS_WITH'})
  SET e.phrase = 'tests with', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HAS_CONTEXT'})
  SET e.phrase = 'has the context of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CONTAINS'})
  SET e.phrase = 'contains', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PHASE1'})
  SET e.phrase = 'is phase 1 of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PREV_SNAPSHOT'})
  SET e.phrase = 'has the previous snapshot', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'GUIDES'})
  SET e.phrase = 'guides', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SIGNED_BY'})
  SET e.phrase = 'is signed by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SPAWNED_BY'})
  SET e.phrase = 'is spawned by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PRODUCED'})
  SET e.phrase = 'produced', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EMBODIES'})
  SET e.phrase = 'embodies', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ADVANCES_TO'})
  SET e.phrase = 'advances to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CAN_PASS'})
  SET e.phrase = 'can pass through', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ENFORCES_SOC2'})
  SET e.phrase = 'enforces SOC2 compliance for', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'GAP'})
  SET e.phrase = 'has a gap in', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'AUTHENTICATES'})
  SET e.phrase = 'authenticates', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SIGNED'})
  SET e.phrase = 'is signed', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'REPORT_OF'})
  SET e.phrase = 'is a report of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'METAPHOR_OF'})
  SET e.phrase = 'is a metaphor of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ROUTED_TO'})
  SET e.phrase = 'is routed to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'MEMBER_OF'})
  SET e.phrase = 'is a member of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'INGESTS_FROM'})
  SET e.phrase = 'ingests from', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'INGESTS_FOR'})
  SET e.phrase = 'ingests for', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ACTIVATES'})
  SET e.phrase = 'activates', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HAS_PATTERN'})
  SET e.phrase = 'has the pattern of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CROSS_PERSON_DEMAND'})
  SET e.phrase = 'has cross-person demand from', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'COULD_TRIGGER'})
  SET e.phrase = 'could trigger', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PATH_TO'})
  SET e.phrase = 'is a path to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'MINTED'})
  SET e.phrase = 'was minted', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'OCCURS_DURING'})
  SET e.phrase = 'occurs during', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FOR_SPECIES'})
  SET e.phrase = 'is designated for the species', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'THEN'})
  SET e.phrase = 'then', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DERIVES_FROM'})
  SET e.phrase = 'derives from', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PARTIALLY_ANSWERED_BY'})
  SET e.phrase = 'is partially answered by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'MEASURED_BY'})
  SET e.phrase = 'is measured by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SURFACED'})
  SET e.phrase = 'was surfaced', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HAS_SNAPSHOT'})
  SET e.phrase = 'has the snapshot of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HAS_CAPABILITY'})
  SET e.phrase = 'has the capability of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EXTERNAL_CODE_OF'})
  SET e.phrase = 'is external code of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'BOUNDARY_OF'})
  SET e.phrase = 'is the boundary of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PHASE2'})
  SET e.phrase = 'is phase 2 of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DRIVEN_BY'})
  SET e.phrase = 'is driven by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'REPLACES'})
  SET e.phrase = 'replaces', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FLOWS_TO'})
  SET e.phrase = 'flows to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EXECUTES_VIA'})
  SET e.phrase = 'executes via', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EXTENDS'})
  SET e.phrase = 'extends', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'UNANSWERED_NEAR'})
  SET e.phrase = 'has an unanswered question near', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ATTRIBUTED_BY'})
  SET e.phrase = 'is attributed by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HAS_STEP'})
  SET e.phrase = 'has the step of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'COMPLEMENTS'})
  SET e.phrase = 'complements', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EXPLAINS'})
  SET e.phrase = 'explains', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'REQUIRES'})
  SET e.phrase = 'requires', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PEERS_WITH'})
  SET e.phrase = 'peers with', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'IN_CONTEXT'})
  SET e.phrase = 'is in the context of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PRECEDED_BY'})
  SET e.phrase = 'is preceded by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FOLLOWED_BY'})
  SET e.phrase = 'is followed by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EVALUATES'})
  SET e.phrase = 'evaluates', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SKILL_OF'})
  SET e.phrase = 'is a skill of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RESULTED_IN'})
  SET e.phrase = 'resulted in', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'PRODUCES'})
  SET e.phrase = 'produces', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ACTS_THROUGH'})
  SET e.phrase = 'acts through', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CONSTRAINED_BY'})
  SET e.phrase = 'is constrained by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DISTRIBUTED_VIA'})
  SET e.phrase = 'is distributed via', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EXPRESSES'})
  SET e.phrase = 'expresses', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RESOLUTION_PATH'})
  SET e.phrase = 'is a resolution path for', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'STRESS_TESTS'})
  SET e.phrase = 'stress tests', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'DEMONSTRATES'})
  SET e.phrase = 'demonstrates', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ENABLES_SCENARIO'})
  SET e.phrase = 'enables the scenario of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ANCHORS'})
  SET e.phrase = 'anchors', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'MEASURES'})
  SET e.phrase = 'measures', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ON_QUERY'})
  SET e.phrase = 'is available on query', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RUNS'})
  SET e.phrase = 'runs', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FROM_BRANCH'})
  SET e.phrase = 'branches from', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'EXPRESSES_THROUGH'})
  SET e.phrase = 'expresses through', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FIRES_THROUGH'})
  SET e.phrase = 'fires through', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'SYNCS_TO'})
  SET e.phrase = 'syncs to', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'CURRENT_SPECIES'})
  SET e.phrase = 'is the current species of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'INTERESTED_IN'})
  SET e.phrase = 'is interested in', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ROOT_CONTEXT'})
  SET e.phrase = 'is the root context for', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'FEEDS'})
  SET e.phrase = 'feeds', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HAS_DIMENSION'})
  SET e.phrase = 'has the dimension of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HAS_CRITERION'})
  SET e.phrase = 'has the criterion of', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RESEARCH_OF'})
  SET e.phrase = 'is research into', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'HYPOTHESIS_OF'})
  SET e.phrase = 'is a hypothesis about', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'WORKFLOW_OF'})
  SET e.phrase = 'is the workflow for', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'VALIDATED_BY'})
  SET e.phrase = 'is validated by', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'RUNS_ON'})
  SET e.phrase = 'runs on', e.file_type = 'connective';
MERGE (e:EdgeConnective {edge_type: 'ENFORCES'})
  SET e.phrase = 'enforces', e.file_type = 'connective';

RETURN 'expanded edge-connectives: 134 new connectives added, total now at 150' AS status;
