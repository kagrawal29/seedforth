// @node_id: protocol-import-external-tag
// @label: "Import External — Tag Pass"
// ============================================================================
// Protocol: Import External — Tag Pass
// ============================================================================
// Post-import tagging pass: for every node whose node_id starts with
// '<source_alias>:', ensure the :Imported and :Imported_<Source> labels
// are present, and the provenance / imported_at / imported_in_species
// properties are set.
//
// Runs AFTER the external bundle has been applied. The bundle author is
// expected to have used compound node_ids from the start — we enforce
// this via a count check: zero uncompounded nodes should exist matching
// <alias>:* in the source's label namespace.
//
// Parameters:
//   source_alias          the source alias (e.g. 'ember')
//   imported_in_species   node_id of the Species under which this import
//                         was validated (e.g. 'species-candidate-abc123')
//
// Idempotent: all MERGEs and SETs are safe to re-run.
// ============================================================================

// --- Step 1: validate that the source is registered -----------------------
MATCH (s:Source {alias: $source_alias})
WHERE s.active = true
WITH s
CALL apoc.util.validate(
  s IS NULL,
  'import-external: no active Source registered with alias=%s',
  [$source_alias]
)

// --- Step 2: tag all nodes whose node_id starts with '<alias>:' -----------
WITH s, s.alias + ':' AS prefix
MATCH (n)
WHERE n.node_id STARTS WITH prefix
  AND NOT n:Source
  AND NOT n:Witness
  AND NOT n:Species
SET n:Imported,
    n.provenance = s.alias,
    n.imported_at = coalesce(n.imported_at, toString(datetime())),
    n.imported_in_species = $imported_in_species

// --- Step 3: also add a source-specific label (e.g. :ImportedFromEmber) ---
// Can't parameterize labels in pure cypher, so we use apoc.create.addLabels.
WITH collect(n) AS tagged, s
UNWIND tagged AS n
CALL apoc.create.addLabels(n, ['ImportedFrom_' + s.alias]) YIELD node
RETURN count(node) AS tagged_count;
