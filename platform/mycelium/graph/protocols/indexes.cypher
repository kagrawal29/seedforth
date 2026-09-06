// @node_id: protocol-indexes-enforce
// @label: "Index Declarations + Enforcer"
// ============================================================================
// Protocol: Index Declarations as Graph Nodes + Enforcer
// v2 piece 1 of 8 (wi-v2-01-indexdecl). Makes physical schema graph-native.
// ============================================================================
// Today: CREATE INDEX runs are one-off in a session; they persist across
// Neo4j restarts but not across a graph wipe or a migration to a fresh env.
//
// Tomorrow (this file): every required index is declared as an IndexDecl node.
// Bootstrap walks IndexDecl and ensures matching Neo4j indexes exist.
// Dream round may later propose new IndexDecl if a filter field is hot and
// unindexed (slow QueryTrace.duration_ms observed).
//
// Schema:
//   (:IndexDecl {
//     node_id:     'idx-<label>-<property>',
//     label:       'Protocol',
//     property:    'node_id',
//     kind:        'RANGE' | 'VECTOR',
//     created_by:  'indexes.cypher' | 'dream-round' | 'manual',
//     reason:      'Primary key lookup used in heartbeat phase 5',
//     -- for VECTOR only:
//     dimensions:  768,
//     similarity:  'cosine'
//   })
//
// Enforcer:
//   Phase 1: MERGE IndexDecl nodes (this file's first block)
//   Phase 2: for each IndexDecl, CREATE INDEX IF NOT EXISTS with matching spec
//   Phase 3: (out of scope for v2.1) drop indexes that have no declaration
//
// Idempotent. Safe to re-run. Runs via apoc.cypher.runMany from bootstrap.
// ============================================================================


// --- Phase 1: declare all required indexes as graph nodes ------------------

// RANGE indexes on node_id — every label that has node_id nodes and is hot-queried
UNWIND [
  {label: 'Protocol',          reason: 'Lookup by node_id in heartbeat + immune + command dispatch'},
  {label: 'Invariant',         reason: 'Walked every immune cycle'},
  {label: 'TestCase',          reason: 'Walked every run-tests cycle'},
  {label: 'Being',             reason: 'Being singleton merkle root — hot read every heartbeat'},
  {label: 'Rhythm',            reason: 'Rhythm lookup per heartbeat phase'},
  {label: 'SkipKey',           reason: 'Read on every merkle recompute'},
  {label: 'CypherAtom',        reason: 'Atom decomposition (v2 piece 2) explodes this label'},
  {label: 'Gap',               reason: 'Gap-detect protocol scans this on every immune cycle'},
  {label: 'WorkItem',          reason: 'Dream round iterates WorkItems for planning'},
  {label: 'ActionProposal',    reason: 'Immune cycle MERGEs proposals by node_id'},
  {label: 'Knowledge',         reason: 'Cross-linking hot path'},
  {label: 'Concept',           reason: 'Semantic classification hot path'},
  {label: 'Module',            reason: 'CodeCypher ↔ Module coverage check'},
  {label: 'CodeCypher',        reason: 'Module coverage + code map'},
  {label: 'TestRun',           reason: 'Test history lookup'},
  {label: 'ConversationTrace', reason: 'Asgard cross-ingest'},
  {label: 'Commit',            reason: 'Asgard cross-ingest'},
  {label: 'Issue',             reason: 'GitHub sync via WorkItem.tracks_issue'},
  {label: 'UIComponent',       reason: 'Maverick UI mapping'},
  {label: 'GraphNode',         reason: 'Every embedded node; vector index queries resolve by label'},
  {label: 'Person',            reason: 'Auth: token_hash lookup via node_id'},
  {label: 'Witness',           reason: 'Consensus quorum check reads witnesses by node_id'},
  {label: 'Command',           reason: 'CLI dispatch (v2 piece 7 atomization)'},
  {label: 'IndexDecl',         reason: 'Self-reference: enforcer walks IndexDecl by label'},
  {label: 'MigrationPlan',     reason: 'Plan lookup for status + next-actions'}
] AS spec
MERGE (d:IndexDecl {node_id: 'idx-' + toLower(spec.label) + '-node_id'})
  ON CREATE SET
    d.label       = spec.label,
    d.property    = 'node_id',
    d.kind        = 'RANGE',
    d.created_by  = 'indexes.cypher',
    d.reason      = spec.reason,
    d.created_at  = toString(datetime())
  ON MATCH SET
    d.reason      = spec.reason,
    d.updated_at  = toString(datetime());


// VECTOR index on GraphNode.embedding — populated by embed-dirty + queried by semantic-densify
MERGE (d:IndexDecl {node_id: 'idx-graphnode-embedding'})
  ON CREATE SET
    d.label       = 'GraphNode',
    d.property    = 'embedding',
    d.kind        = 'VECTOR',
    d.dimensions  = 768,
    d.similarity  = 'cosine',
    d.index_name  = 'node_embeddings',
    d.created_by  = 'indexes.cypher',
    d.reason      = 'HNSW vector index for semantic-densify + ask + swarm',
    d.created_at  = toString(datetime())
  ON MATCH SET
    d.index_name  = 'node_embeddings',
    d.updated_at  = toString(datetime());


// RANGE indexes on QueryTrace — new timing support (wi-v2-02)
// Enables protocol-level performance analysis and slow-query detection
UNWIND [
  {property: 'protocol_id', reason: 'Trace all fires from a specific protocol'},
  {property: 'fired_at',    reason: 'Time-window queries; aggregate duration over periods'},
  {property: 'duration_ms', reason: 'Query performance analysis; find slow queries by threshold'}
] AS spec
MERGE (d:IndexDecl {node_id: 'idx-querytrace-' + spec.property})
  ON CREATE SET
    d.label       = 'QueryTrace',
    d.property    = spec.property,
    d.kind        = 'RANGE',
    d.created_by  = 'indexes.cypher',
    d.reason      = spec.reason,
    d.created_at  = toString(datetime())
  ON MATCH SET
    d.reason      = spec.reason,
    d.updated_at  = toString(datetime());


// RANGE indexes on CypherAtom — new atom decomposition support (wi-v2-03)
// Atom chains are walked by atom_id and protocol_id; order is sequential
UNWIND [
  {property: 'atom_id',     reason: 'Lookup individual atoms for execution + trace'},
  {property: 'protocol_id', reason: 'Walk atom chain for a protocol; filter by protocol FK'}
] AS spec
MERGE (d:IndexDecl {node_id: 'idx-cypheratom-' + spec.property})
  ON CREATE SET
    d.label       = 'CypherAtom',
    d.property    = spec.property,
    d.kind        = 'RANGE',
    d.created_by  = 'indexes.cypher',
    d.reason      = spec.reason,
    d.created_at  = toString(datetime())
  ON MATCH SET
    d.reason      = spec.reason,
    d.updated_at  = toString(datetime());


// --- Phase 2: enforcer lives OUTSIDE this file -----------------------------
// CREATE INDEX is DDL and apoc.cypher.doIt is sandbox-restricted for DDL.
// The Python bootstrap runs graph/runner/enforce-indexes.py after this file,
// which reads IndexDecl nodes and issues CREATE INDEX IF NOT EXISTS per decl.
// This file only owns the declarations — the enforcer is an I/O shim.


// --- Phase 3: summary of declarations --------------------------------------
MATCH (d:IndexDecl)
RETURN count(d) AS declared,
       sum(CASE WHEN d.kind = 'RANGE' THEN 1 ELSE 0 END) AS range_count,
       sum(CASE WHEN d.kind = 'VECTOR' THEN 1 ELSE 0 END) AS vector_count;
