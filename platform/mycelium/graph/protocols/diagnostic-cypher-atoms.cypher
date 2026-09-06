// @node_id: protocol-diagnostic-cypher-atoms
// @label: "Diagnostic CypherAtom Nodes"
// ============================================================================
// Protocol: Diagnostic CypherAtom Nodes
// ============================================================================
// Self-diagnostic query layer: CypherAtom nodes that enable natural language
// access to diagnostic queries. When someone asks "what protocols are dead",
// the ask system embeds the query, finds the matching atom via vector search,
// and executes the atom's source_cypher to get real diagnostic data.
//
// These atoms bridge the gap between semantic search and diagnostic execution.
// ============================================================================

// --- Atom 1: What protocols are dead? ------------------------------------
// Identifies protocols that have never been executed (fire_count = 0)
MERGE (a:CypherAtom {node_id: 'atom-diagnostic-dead-protocols'})
ON CREATE SET
  a.semantic = 'What protocols are dead? Which protocols have zero fires? Find inactive protocols.',
  a.source_cypher = 'MATCH (p:Protocol) WHERE coalesce(p.fire_count, 0) = 0 RETURN p.node_id, p.label, p.description, p.fire_count ORDER BY p.label',
  a.source_protocol = 'protocol-self-diagnostic',
  a.file_type = 'cypher-atom',
  a.category = 'diagnostic',
  a.fire_count = 0,
  a.created_at = toString(datetime())
ON MATCH SET a.last_checked = toString(datetime());

// --- Atom 2: Which claim tests are failing? --------------------------------
// Identifies test cases with failed or null results
MERGE (a:CypherAtom {node_id: 'atom-diagnostic-failing-tests'})
ON CREATE SET
  a.semantic = 'Which test cases are failing? What tests have failed results? Show broken tests.',
  a.source_cypher = 'MATCH (tc:TestCase) WHERE tc.last_result IN [\'fail\', NULL] OR tc.last_result IS NULL RETURN tc.node_id, tc.label, tc.last_result, tc.expected, tc.actual ORDER BY tc.label',
  a.source_protocol = 'protocol-self-diagnostic',
  a.file_type = 'cypher-atom',
  a.category = 'diagnostic',
  a.fire_count = 0,
  a.created_at = toString(datetime())
ON MATCH SET a.last_checked = toString(datetime());

// --- Atom 3: Which invariants are unhealthy? --------------------------------
// Identifies invariants with non-healthy status
MERGE (a:CypherAtom {node_id: 'atom-diagnostic-unhealthy-invariants'})
ON CREATE SET
  a.semantic = 'What invariants are unhealthy? Which invariants are not healthy? Show broken constraints.',
  a.source_cypher = 'MATCH (inv:Invariant) WHERE inv.status <> \'healthy\' RETURN inv.number, inv.label, inv.status, inv.description ORDER BY inv.number',
  a.source_protocol = 'protocol-self-diagnostic',
  a.file_type = 'cypher-atom',
  a.category = 'diagnostic',
  a.fire_count = 0,
  a.created_at = toString(datetime())
ON MATCH SET a.last_checked = toString(datetime());

// --- Atom 4: What gaps exist? -----------------------------------------------
// Lists all knowledge gaps with their severity levels
MERGE (a:CypherAtom {node_id: 'atom-diagnostic-gaps'})
ON CREATE SET
  a.semantic = 'What knowledge gaps exist? Show all gaps in the system with severity.',
  a.source_cypher = 'MATCH (g:Gap) RETURN g.node_id, g.label, g.severity, g.description, g.status ORDER BY g.severity DESC, g.label',
  a.source_protocol = 'protocol-self-diagnostic',
  a.file_type = 'cypher-atom',
  a.category = 'diagnostic',
  a.fire_count = 0,
  a.created_at = toString(datetime())
ON MATCH SET a.last_checked = toString(datetime());

// --- Atom 5: What is the amortization health? --------------------------------
// Summarizes protocol counts by amortization status
MERGE (a:CypherAtom {node_id: 'atom-diagnostic-amortization-health'})
ON CREATE SET
  a.semantic = 'What is the amortization health? How many protocols in each amortization status? System efficiency summary.',
  a.source_cypher = 'MATCH (p:Protocol) RETURN coalesce(p.amortization_status, \'unknown\') AS status, count(*) AS count ORDER BY count DESC',
  a.source_protocol = 'protocol-self-diagnostic',
  a.file_type = 'cypher-atom',
  a.category = 'diagnostic',
  a.fire_count = 0,
  a.created_at = toString(datetime())
ON MATCH SET a.last_checked = toString(datetime());

// --- Atom 6: Which subsystems have no health metrics? ----------------------
// Finds subsystems without measurement edges
MERGE (a:CypherAtom {node_id: 'atom-diagnostic-unmeasured-subsystems'})
ON CREATE SET
  a.semantic = 'Which subsystems have no health metrics? Find subsystems without measurement edges. Unmeasured components.',
  a.source_cypher = 'MATCH (ss:Subsystem) WHERE NOT EXISTS((ss)-[:MEASURED_BY]->()) RETURN ss.node_id, ss.label, ss.description, ss.status ORDER BY ss.label',
  a.source_protocol = 'protocol-self-diagnostic',
  a.file_type = 'cypher-atom',
  a.category = 'diagnostic',
  a.fire_count = 0,
  a.created_at = toString(datetime())
ON MATCH SET a.last_checked = toString(datetime());

RETURN 'Diagnostic CypherAtom schema initialized' AS status;
