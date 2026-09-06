// @node_id: protocol-reactive-triggers
// @label: "Reactive Invariants — APOC Trigger Suite"
// ============================================================================
// Protocol: Reactive Triggers for Invariant Dirty-Flagging
// ============================================================================
// Installs 3 APOC triggers that react to graph mutations in real-time,
// instead of relying only on the 10s heartbeat poll. Triggers fire on:
//   1. GraphNode creation without embedding
//   2. Protocol.cypher property mutations
//   3. Invariant.threshold changes
//
// Each trigger sets a dirty_flag on Being so the heartbeat picks up the
// need for re-evaluation without waiting for the next full sweep.
//
// TRIGGER INSTALLATION:
// This file is a reference. Installation happens via:
//   python3 graph/runner/install-triggers.py
// Which reads these queries and calls apoc.trigger.install() for each.
//
// KNOWN ISSUE (Neo4j 2026.03.1 brew on macOS):
// apoc.trigger.install() fails with "writes must pass through leader" even on single-node PRIMARY.
// Root cause: Neo4j driver over cypher-shell doesn't route WRITE transactions to primary correctly.
// The database IS primary (verified via SHOW DATABASES), but APOC's internal write fails.
// Workaround: None without restart. apoc.trigger.enabled=true in neo4j.conf is not the blocker
// (APOC is loaded and available). The blocker is transaction routing.
// For production (FalkorDB), triggers install via MCP stream without this constraint.
// Status (2026-04-17): Triggers are DESIGNED but UNINSTALLED. Ready for FalkorDB.
//
// IDEMPOTENT: install-triggers.py drops + reinstalls, so safe to re-run.
// ============================================================================

// --- TRIGGER 1: Embedding Dirty on GraphNode Insert ------
// When a new :GraphNode is created without an embedding property,
// set needs_embedding=true immediately. Reduces embedding-dirty latency
// from 10s to <100ms.
//
// Selector: phase='after', events=['create'] => runs AFTER node creation
// Action: Check if :GraphNode label added; if so and embedding IS NULL,
//         set needs_embedding=true on Being dirty flags.
//
// Cypher statement:
UNWIND ($createdNodes) AS node
WITH node
WHERE labels(node) CONTAINS 'GraphNode'
  AND node.embedding IS NULL
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.needs_embedding = true
RETURN node.node_id, 'embedding_dirty_triggered' AS action;

// --- TRIGGER 2: Protocol Atom Sync Dirty on cypher Change ------
// When a Protocol.cypher property changes (code edit), immediately
// delete the HAS_ATOM chain so the next bootstrap re-decomposes the
// protocol into atoms. Prevents stale atom execution.
//
// Selector: phase='after', events=['set'] => runs AFTER SET operations
// Action: If a Protocol node's cypher property was modified, DELETE all
//         HAS_ATOM relationships from that Protocol, and mark Being
//         dirty for protocol-bootstrap.
//
// Cypher statement:
UNWIND ($assignedNodeProperties) AS prop
WITH prop.node AS node, prop.key AS key
WHERE labels(node) CONTAINS 'Protocol'
  AND key = 'cypher'
MATCH (node)-[a:HAS_ATOM]->(atom)
DELETE a
WITH node
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.atom_dirty = true
RETURN node.node_id, 'atom_sync_dirty_triggered' AS action;

// --- TRIGGER 3: Invariant Dirty on Threshold Change ------
// When an Invariant.threshold property changes, mark the invariant
// for re-evaluation and set Being.invariant_dirty flag. Ensures
// threshold adjustments take effect immediately, not waiting 10s.
//
// Selector: phase='after', events=['set'] => runs AFTER SET operations
// Action: If an Invariant node's threshold was modified, set the
//         invariant's dirty=true and flag Being for invariant re-run.
//
// Cypher statement:
UNWIND ($assignedNodeProperties) AS prop
WITH prop.node AS node, prop.key AS key
WHERE labels(node) CONTAINS 'Invariant'
  AND (key STARTS WITH 'healthy_range' OR key = 'threshold')
SET node.dirty = true
WITH node
MATCH (b:Being {node_id: 'being-mycelium'})
SET b.invariant_dirty = true
RETURN node.node_id, 'invariant_dirty_triggered' AS action;
