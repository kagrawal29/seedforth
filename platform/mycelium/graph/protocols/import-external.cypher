// @node_id: protocol-import-external
// @label: "Import External"
// ============================================================================
// Protocol: Import External
// ============================================================================
// Imports nodes from an external authorized :Source. Each imported node is
// labeled :Imported and receives the caller-specified label (e.g., :Person,
// :Organization). The node is wired to the Source via :IMPORTED_FROM edge.
//
// Imported nodes are subject to a reduced invariant set (many invariants skip
// :Imported nodes). Adoption via protocol-adopt-node promotes them to full
// citizens once the importing person is confident in their quality.
//
// Parameters (via --param):
//   source_id   string — the :Source node_id (e.g., 'source-ember')
//   nodes       list of objects — each with:
//               node_id    string — unique identifier for the imported node
//               label      string — primary label (e.g., 'Person', 'Organization')
//               properties object — all properties to set on the node
//
// Behavior:
//   1. MATCH the Source to verify it exists
//   2. For each node in $nodes:
//      a. MERGE the node using (node_id, primary label) as the key
//      b. SET :Imported label + all properties from the object
//      c. Wire (node)-[:IMPORTED_FROM]->(source)
//   3. Verify all wirings complete
//   4. Return count of imported nodes (new + merged)
//
// Idempotent: MERGE prevents duplicates. Re-running with the same nodes
// is a no-op except it updates properties.
// ============================================================================

MATCH (source:Source {node_id: $source_id})
WHERE source IS NOT NULL
WITH source

// Process each node in the import list
UNWIND $nodes AS node_spec

MERGE (n {node_id: node_spec.node_id})
SET n:Imported,
    n:Node,
    n.provenance = $source_id,
    n.imported_at = toString(datetime()),
    n.imported_from_source = source.node_id

// Apply the caller's label (e.g., :Person, :Organization)
CALL apoc.create.addLabels(n, [node_spec.label]) YIELD node AS n_labeled

// Set all properties from the object
WITH n_labeled, node_spec, source
CALL apoc.map.setKey(n_labeled, node_spec.properties) YIELD value
WITH n_labeled, source

// Wire the node to its source
MERGE (n_labeled)-[:IMPORTED_FROM]->(source)

WITH n_labeled
RETURN n_labeled.node_id AS imported_node_id,
       labels(n_labeled) AS labels_applied,
       n_labeled.imported_at AS timestamp;
