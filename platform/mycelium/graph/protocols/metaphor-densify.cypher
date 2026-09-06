// @node_id: protocol-metaphor-densify
// @label: "Metaphor Densify"
// ============================================================================
// Protocol: Metaphor Densify
// ============================================================================
// Wires the 7 :Metaphor nodes into the graph densely and meaningfully by
// creating typed outbound edges to every Protocol, Concept, DesignPrinciple,
// Subsystem, IntegrationPoint, CypherAtom, Document, and GraphNode they
// illuminate.
//
// The 7 metaphors and their targets:
//
//   metaphor-heartbeat   -> protocol-heartbeat, script-heartbeat-loop,
//                           atom-heartbeat-beat, atom-heartbeat-report,
//                           cmd-heartbeat, concept-being,
//                           design-self-describe
//
//   metaphor-immune      -> protocol-immune, design-auto-heal,
//                           guide-immune-system,
//                           uxcrit-self-healing-heartbeat,
//                           concept-invariant
//
//   metaphor-synapse     -> protocol-strengthen-edges, concept-cypheratom,
//                           concept-querytrace, ipoint-atomize-cypher,
//                           design-cypher-native
//
//   metaphor-dna         -> protocol-merkle-properties,
//                           protocol-dna-fingerprint,
//                           protocol-genome-verify,
//                           protocol-verify-lineage,
//                           ipoint-sign-species, concept-species,
//                           concept-witness, guide-merkle-integrity,
//                           design-graph-is-source
//
//   metaphor-speciation  -> protocol-species-mint (via genus node),
//                           protocol-genome-verify,
//                           protocol-verify-lineage,
//                           concept-species, design-graph-is-source
//
//   metaphor-cell        -> subsystem-mycelium-core,
//                           subsystem-embed-sidecar,
//                           subsystem-crypto-sidecar,
//                           subsystem-tetrahedron,
//                           ipoint-embed-dirty, ipoint-sign-species,
//                           ipoint-atomize-cypher,
//                           design-cypher-native
//
//   metaphor-forest-mycelium -> ontology-mycelium,
//                               concept-source,
//                               protocol-semantic-densify,
//                               protocol-semantic-cluster,
//                               design-graph-is-source
//
// Edge types used:
//   :METAPHOR_OF  — this metaphor is a metaphor of / maps onto this node
//   :EXPLAINS     — this metaphor explains / illuminates this design principle
//                   or concept
//
// Idempotent: pure MERGE, no CREATE. Re-running is safe and produces no
// duplicate edges. Existing edges already present before this protocol
// (e.g. METAPHOR_OF ontology-mycelium, SEEMS_LIKE concept-X) are left
// untouched.
//
// Summary: the final WITH block returns per-metaphor edge counts, total
// edges, and the count of metaphors that now have >= 3 outgoing typed edges.
// ============================================================================


// ── metaphor-heartbeat ────────────────────────────────────────────────────────
// applied_to: protocol-heartbeat + heartbeat-loop.sh
// METAPHOR_OF: protocol, related atoms, command, liveness script
// EXPLAINS:    design-self-describe (pulse = how observers confirm aliveness)

MATCH (m:Metaphor {node_id: "metaphor-heartbeat"})
MATCH (p1)  WHERE p1.node_id  = "protocol-heartbeat"
MATCH (p2)  WHERE p2.node_id  = "atom-heartbeat-beat"
MATCH (p3)  WHERE p3.node_id  = "atom-heartbeat-report"
MATCH (p4)  WHERE p4.node_id  = "cmd-heartbeat"
MATCH (p5)  WHERE p5.node_id  = "script-heartbeat-loop"
MATCH (p6)  WHERE p6.node_id  = "concept-being"
MATCH (dp1) WHERE dp1.node_id = "design-self-describe"

MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p4)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p5)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p6)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp1)

WITH true AS done


// ── metaphor-immune ───────────────────────────────────────────────────────────
// applied_to: graph/protocols/immune.cypher + invariant heal_protocol field
// METAPHOR_OF: protocol-immune, guide-immune-system, uxcrit node
// EXPLAINS:    design-auto-heal (invariant unhealthy → triggers heal_protocol)

MATCH (m:Metaphor {node_id: "metaphor-immune"})
MATCH (p1)  WHERE p1.node_id  = "protocol-immune"
MATCH (p2)  WHERE p2.node_id  = "guide-immune-system"
MATCH (p3)  WHERE p3.node_id  = "uxcrit-self-healing-heartbeat"
MATCH (p4)  WHERE p4.node_id  = "concept-invariant"
MATCH (dp1) WHERE dp1.node_id = "design-auto-heal"

MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p4)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp1)

WITH true AS done


// ── metaphor-synapse ──────────────────────────────────────────────────────────
// applied_to: CypherAtom + FEEDS edges + fire_count + strengthen-edges.cypher
// METAPHOR_OF: protocol-strengthen-edges, concept-cypheratom,
//              concept-querytrace, ipoint-atomize-cypher
// EXPLAINS:    design-cypher-native (atoms fire via FEEDS, Hebbian wiring)

MATCH (m:Metaphor {node_id: "metaphor-synapse"})
MATCH (p1)  WHERE p1.node_id  = "protocol-strengthen-edges"
MATCH (p2)  WHERE p2.node_id  = "concept-cypheratom"
MATCH (p3)  WHERE p3.node_id  = "concept-querytrace"
MATCH (p4)  WHERE p4.node_id  = "ipoint-atomize-cypher"
MATCH (dp1) WHERE dp1.node_id = "design-cypher-native"

MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p4)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp1)

WITH true AS done


// ── metaphor-dna ──────────────────────────────────────────────────────────────
// applied_to: Species.manifest_root + merkle-properties + species lifecycle
// METAPHOR_OF: protocol-merkle-properties, protocol-dna-fingerprint,
//              protocol-genome-verify, protocol-verify-lineage,
//              ipoint-sign-species, concept-species, concept-witness,
//              guide-merkle-integrity
// EXPLAINS:    design-graph-is-source (graph reproduces itself across time
//              via manifest_root SHA commitments + DESCENDED_FROM edges)

MATCH (m:Metaphor {node_id: "metaphor-dna"})
MATCH (p1)  WHERE p1.node_id  = "protocol-merkle-properties"
MATCH (p2)  WHERE p2.node_id  = "protocol-dna-fingerprint"
MATCH (p3)  WHERE p3.node_id  = "protocol-genome-verify"
MATCH (p4)  WHERE p4.node_id  = "protocol-verify-lineage"
MATCH (p5)  WHERE p5.node_id  = "ipoint-sign-species"
MATCH (p6)  WHERE p6.node_id  = "concept-species"
MATCH (p7)  WHERE p7.node_id  = "concept-witness"
MATCH (p8)  WHERE p8.node_id  = "guide-merkle-integrity"
MATCH (dp1) WHERE dp1.node_id = "design-graph-is-source"

MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p4)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p5)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p6)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p7)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p8)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp1)

WITH true AS done


// ── metaphor-speciation ───────────────────────────────────────────────────────
// applied_to: species-mint + fresh genesis under phase-b algorithm
// METAPHOR_OF: protocol-genome-verify, protocol-verify-lineage,
//              concept-species, ipoint-sign-species
// EXPLAINS:    design-graph-is-source (lineage chain = graph self-reproduction)
//              design-merkle-properties (manifest_root seals each generation)

MATCH (m:Metaphor {node_id: "metaphor-speciation"})
MATCH (p1)  WHERE p1.node_id  = "protocol-genome-verify"
MATCH (p2)  WHERE p2.node_id  = "protocol-verify-lineage"
MATCH (p3)  WHERE p3.node_id  = "concept-species"
MATCH (p4)  WHERE p4.node_id  = "ipoint-sign-species"
MATCH (dp1) WHERE dp1.node_id = "design-graph-is-source"
MATCH (dp2) WHERE dp2.node_id = "design-merkle-properties"

MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p4)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp1)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp2)

WITH true AS done


// ── metaphor-cell ─────────────────────────────────────────────────────────────
// applied_to: Subsystem + IntegrationPoint
// METAPHOR_OF: all 4 Subsystem nodes, all 4 IntegrationPoint nodes
// EXPLAINS:    design-cypher-native (cells communicate in cypher)

MATCH (m:Metaphor {node_id: "metaphor-cell"})
MATCH (s1)  WHERE s1.node_id  = "subsystem-mycelium-core"
MATCH (s2)  WHERE s2.node_id  = "subsystem-embed-sidecar"
MATCH (s3)  WHERE s3.node_id  = "subsystem-crypto-sidecar"
MATCH (s4)  WHERE s4.node_id  = "subsystem-tetrahedron"
MATCH (i1)  WHERE i1.node_id  = "ipoint-embed-dirty"
MATCH (i2)  WHERE i2.node_id  = "ipoint-sign-species"
MATCH (i3)  WHERE i3.node_id  = "ipoint-atomize-cypher"
MATCH (i4)  WHERE i4.node_id  = "ipoint-import-external-graph"
MATCH (dp1) WHERE dp1.node_id = "design-cypher-native"

MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(s1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(s2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(s3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(s4)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(i1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(i2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(i3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(i4)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp1)

WITH true AS done


// ── metaphor-forest-mycelium ──────────────────────────────────────────────────
// applied_to: the whole system, its name
// METAPHOR_OF: ontology-mycelium, concept-source, protocol-semantic-densify,
//              protocol-semantic-cluster
// EXPLAINS:    design-graph-is-source (many organisms, one substrate)
//              design-self-describe (separate organisms, shared identity layer)

MATCH (m:Metaphor {node_id: "metaphor-forest-mycelium"})
MATCH (p1)  WHERE p1.node_id  = "ontology-mycelium"
MATCH (p2)  WHERE p2.node_id  = "concept-source"
MATCH (p3)  WHERE p3.node_id  = "protocol-semantic-densify"
MATCH (p4)  WHERE p4.node_id  = "protocol-semantic-cluster"
MATCH (dp1) WHERE dp1.node_id = "design-graph-is-source"
MATCH (dp2) WHERE dp2.node_id = "design-self-describe"

MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p1)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p2)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p3)
MERGE (m)-[:METAPHOR_OF {wired_by: "metaphor-densify.cypher"}]->(p4)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp1)
MERGE (m)-[:EXPLAINS    {wired_by: "metaphor-densify.cypher"}]->(dp2)

WITH true AS done


// ── Summary ───────────────────────────────────────────────────────────────────
// Return per-metaphor edge counts, total edges across all 7 metaphors,
// and count of metaphors now carrying >= 3 outgoing typed edges.

MATCH (m:Metaphor)-[r:METAPHOR_OF|EXPLAINS]->(x)
WITH m.node_id AS metaphor_id, count(DISTINCT r) AS edge_count
WITH
  collect({metaphor: metaphor_id, edges: edge_count}) AS per_metaphor,
  sum(edge_count)                                      AS total_edges,
  count(CASE WHEN edge_count >= 3 THEN 1 END)          AS metaphors_with_3plus_edges
RETURN per_metaphor, total_edges, metaphors_with_3plus_edges
