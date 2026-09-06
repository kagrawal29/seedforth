// @kind: seed
// ============================================================================
// Protocol: Atom Schema Init (Phase 15 scaffolding)
// ============================================================================
// Seeds the schema concept for :CypherAtom — the atomic unit of graph
// behavior. Everything that used to be a monolithic Protocol.cypher
// (a wall-of-text cypher string) becomes a small graph of CypherAtoms
// connected by typed dataflow edges.
//
// Schema:
//
//   (:CypherAtom)
//      node_id          'atom-<short-hash>'
//      cypher           one atomic cypher statement (a single clause or
//                        small semantic unit — MATCH+WITH, or SET, or
//                        MERGE+ON CREATE)
//      input_vars       list of variables expected to be bound in the
//                        enclosing query when this atom runs
//      output_vars      list of variables this atom introduces/returns
//      semantic         natural language description ("find every node
//                        whose node_id is set and is not a QueryTrace")
//      category         'filter' | 'compute' | 'write' | 'aggregate' |
//                        'branch' | 'terminator'
//      side_effects     list of effects: ['WRITE', 'CREATE', 'DELETE',
//                        'NONE']
//      fire_count       Hebbian counter — incremented every time this
//                        atom is traversed during a protocol execution
//      embedding        vector for semantic search (matches Query.semantic
//                        pattern — populated by embed-dirty)
//
// Edges between atoms (dataflow graph):
//
//   (atom_a)-[:FEEDS { var }]->(atom_b)
//      atom_a's output_vars include var, which atom_b reads as input.
//      Represents dataflow — atom_b cannot fire until atom_a has fired
//      (or the var is bound from outside).
//
//   (atom_a)-[:FOLLOWS]->(atom_b)
//      atom_b runs after atom_a in sequential order. Used when dataflow
//      is implicit (e.g. atom_b reads the graph state that atom_a just
//      wrote).
//
//   (atom_a)-[:REPLACES]->(atom_b)
//      atom_a is a newer/better version of atom_b. Enables versioning
//      and gradual migration.
//
//   (atom_a)-[:CO_FIRED]->(atom_b)
//      Derived: atom_a and atom_b have been observed firing together
//      in protocols (weight = count). Auto-maintained by the Hebbian
//      strengthen-fired-together.cypher protocol.
//
// Protocols become walks: a :Protocol node has a
//   -[:FIRST_ATOM]->(:CypherAtom) entry point, and each atom's :FEEDS
//   and :FOLLOWS edges define the execution order. A "run atom chain"
//   interpreter walks the graph and executes each cypher statement in
//   order, binding output_vars into the environment.
//
// Migration strategy (incremental):
//   1. Phase 15a: this file — define the schema by creating a seed
//      CypherAtom that demonstrates the pattern (heartbeat's body split
//      into 2 atoms).
//   2. Phase 15b: atom-compiler — given a :Protocol node's legacy cypher
//      property, parse it into atoms and create the atom graph. Link
//      the protocol to its first atom via :FIRST_ATOM. Leaves the
//      legacy cypher property in place for backward compat.
//   3. Phase 15c: atom-runner — walks the atom chain and executes each
//      statement in a single transaction, with Hebbian fire_count
//      increments.
//   4. Phase 15d: switch the runners to use the atom interpreter instead
//      of the raw cypher property. Legacy property becomes dead weight,
//      can be dropped.
//   5. Phase 15e: embeddings + semantic NL → atom lookup. The graph
//      becomes truly navigable by meaning rather than by string match.
//
// This protocol just creates the first atoms as proof of concept.
// ============================================================================

// --- Atom 1: the "beat" — increment heartbeat_count on Being --------------
MERGE (a:CypherAtom {node_id: 'atom-heartbeat-beat'})
ON CREATE SET
  a.cypher = "MERGE (b:Being {node_id: 'being-mycelium'}) SET b.heartbeat_count = coalesce(b.heartbeat_count, 0) + 1, b.last_heartbeat = timestamp(), b.last_heartbeat_at = toString(datetime()), b.alive = true",
  a.category = 'write',
  a.side_effects = ['WRITE'],
  a.input_vars = [],
  a.output_vars = ['b'],
  a.semantic = 'Record one pulse of the graph being alive. Updates the Being singleton with a fresh heartbeat counter and timestamp. Does not change root_hash because the touched properties are in SkipKey.',
  a.fire_count = 0,
  a.phase_b_legacy = false,
  a.file_type = 'cypher-atom',
  a.source_protocol = 'protocol-heartbeat',
  a.atom_order = 1,
  a.first_seen = toString(datetime())
ON MATCH SET a.last_updated = toString(datetime());

// --- Atom 2: the "report" — return the new beat for logging --------------
MERGE (a:CypherAtom {node_id: 'atom-heartbeat-report'})
ON CREATE SET
  a.cypher = "RETURN b.heartbeat_count AS beat, b.last_heartbeat_at AS at",
  a.category = 'terminator',
  a.side_effects = ['NONE'],
  a.input_vars = ['b'],
  a.output_vars = ['beat', 'at'],
  a.semantic = 'Report the heartbeat counter and timestamp so the caller can log or display the current pulse.',
  a.fire_count = 0,
  a.phase_b_legacy = false,
  a.file_type = 'cypher-atom',
  a.source_protocol = 'protocol-heartbeat',
  a.atom_order = 2,
  a.first_seen = toString(datetime())
ON MATCH SET a.last_updated = toString(datetime());

// --- Dataflow edge: atom-1 FEEDS atom-2 via 'b' ---------------------------
MATCH (a1:CypherAtom {node_id: 'atom-heartbeat-beat'})
MATCH (a2:CypherAtom {node_id: 'atom-heartbeat-report'})
MERGE (a1)-[:FEEDS {var: 'b'}]->(a2);

// --- Link the Protocol to its entry atom ----------------------------------
MATCH (p:Protocol {node_id: 'protocol-heartbeat'})
MATCH (first:CypherAtom {node_id: 'atom-heartbeat-beat'})
MERGE (p)-[:FIRST_ATOM]->(first);

RETURN 'heartbeat atomized (2 atoms, 1 FEEDS edge, 1 FIRST_ATOM link)' AS status;
