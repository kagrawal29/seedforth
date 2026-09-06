// @node_id: protocol-adopt-node
// @label: "Adopt Node"
// ============================================================================
// Protocol: Adopt Node
// ============================================================================
// Promotes an :Imported node to a full citizen by removing the :Imported
// label. After adoption, the node is subject to ALL core invariants and
// TestCases that previously skipped it via the :Imported filter.
//
// Parameters (via --param):
//   node_id         string — the imported node to adopt
//   adopter_alias   string — who is adopting (for audit)
//
// Steps:
//   1. Validate: node exists, is currently :Imported, has a provenance property
//   2. Capture the original provenance + source for the adoption record
//   3. Remove :Imported label and all :ImportedFrom_* labels
//   4. Add :Adopted label + adoption metadata
//   5. Validation is caller's responsibility (wrap in a validate-merge
//      transaction if you want full checks); this protocol itself is
//      intentionally stateless so batch adoptions can be cheap
//
// The node keeps:
//   - provenance property (for permanent audit trail)
//   - imported_in_species property (to trace which import brought it in)
//
// The node loses:
//   - :Imported label
//   - :ImportedFrom_<Source> label
//
// The node gains:
//   - :Adopted label
//   - adopted_at property
//   - adopted_by property (the adopter_alias)
// ============================================================================

MATCH (n {node_id: $node_id})
WHERE n:Imported
  AND n.provenance IS NOT NULL
WITH n, n.provenance AS prov

// Remove the source-specific label via apoc.create.removeLabels
// (can't parameterize label names in pure cypher)
CALL apoc.create.removeLabels(n, ['Imported', 'ImportedFrom_' + prov]) YIELD node
WITH node AS n, prov

// Add :Adopted label
CALL apoc.create.addLabels(n, ['Adopted']) YIELD node
WITH node AS n, prov

SET n.adopted_at = toString(datetime()),
    n.adopted_by = $adopter_alias,
    n.adopted_from_provenance = prov

RETURN n.node_id AS node_id,
       labels(n) AS labels,
       n.adopted_from_provenance AS was_imported_from,
       n.adopted_at AS adopted_at;
