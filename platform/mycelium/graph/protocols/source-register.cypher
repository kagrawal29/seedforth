// @kind: seed
// ============================================================================
// Protocol: Source Register
// ============================================================================
// Creates or updates a Source node that represents an external graph
// authorized to import data into mycelium.
//
// Parameters (via --param):
//   alias           string — short identifier used as namespace prefix
//                            (e.g. 'ember', 'arie', 'revti')
//   public_key      string — ed25519 hex public key of the signer who
//                            authorizes imports from this source
//   schema_version  string — e.g. 'v1' — used for future schema migrations
//   description     string — human-readable explanation of this source
//
// Each Source also gets:
//   node_id        source-<alias>
//   registered_at  ISO datetime
//   active         true
//
// Idempotent: MERGE on node_id.
//
// Every imported node will be tagged with:
//   provenance             = <alias>
//   :Imported              (secondary label)
//   :ImportedFrom_<Alias>  (secondary label, source-specific)
//   imported_at            ISO datetime at import time
//   imported_in_species    node_id of the Species under which this import
//                          was validated (set by import-external.cypher)
// ============================================================================

MERGE (s:Source {alias: $alias})
ON CREATE SET
  s.node_id = 'source-' + $alias,
  s.registered_at = toString(datetime()),
  s.active = true,
  s.file_type = 'source'
SET s.public_key = $public_key,
    s.schema_version = coalesce($schema_version, 'v1'),
    s.description = coalesce($description, ''),
    s.public_key_registered_at = toString(datetime())
RETURN s.node_id AS node_id,
       s.alias AS alias,
       substring(s.public_key, 0, 16) + '...' AS pubkey_preview,
       s.schema_version AS schema_version;
