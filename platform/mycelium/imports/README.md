# `imports/` — External graph bundles

Drop cypher bundles from other graphs here to import them into mycelium
under a namespaced, read-only `:Imported` subgraph.

## Directory layout

```
imports/
  <source_alias>/
    source.json          source metadata — public_key, schema_version, description
    2026-04-16-batch.cypher
    2026-04-17-delta.cypher
```

Every bundle lives under `imports/<source_alias>/<file>.cypher`. The
`source_alias` segment of the path determines which `Source` node the
bundle belongs to. Mycelium registers the source (via `source-register.sh`)
before the first import lands, using the metadata in `source.json`.

## `source.json` format

```json
{
  "public_key": "4607d8ff2db3a652a7b9ebc75c125e46fb63c6d1779beffb6605289593c4d585",
  "schema_version": "v1",
  "description": "Ember — LinkedIn management system, user + concept + trace graph"
}
```

Public key is the source's ed25519 hex key. Private key stays with the
source owner. Future (Phase 8+): bundles will be signed by the source's
key and verified at import time.

## Bundle format

Every `MERGE` statement MUST use a compound `node_id` of the form
`"<source_alias>:<original-id>"`. CI rejects bundles that contain any
non-namespaced node_ids with a clear error message.

Example — `imports/ember/2026-04-16-users-and-concepts.cypher`:

```cypher
MERGE (p:Person {node_id: 'ember:user-rajesh'})
SET p.label = 'Rajesh (Ember user)',
    p.active = true,
    p.file_type = 'person';

MERGE (p:Person {node_id: 'ember:user-priya'})
SET p.label = 'Priya (Ember user)',
    p.active = true,
    p.file_type = 'person';

MERGE (c:Concept {node_id: 'ember:concept-connection-strength'})
SET c.label = 'LinkedIn connection strength metric',
    c.file_type = 'concept';

MATCH (p:Person {node_id: 'ember:user-rajesh'}),
      (c:Concept {node_id: 'ember:concept-connection-strength'})
MERGE (p)-[:INTERESTED_IN]->(c);
```

The compound-id rule is enforced at both local and CI layers:
`graph/runner/import-external.sh` pre-scans the file with a regex and
rejects it before touching Neo4j.

## What happens on PR

The `graph-import.yml` workflow:

1. Spins ephemeral Neo4j 5.22 + APOC
2. Seeds from the base branch's `graph-state.cypher`
3. Detects changed `imports/**.cypher` files
4. For each one: infers the `<source_alias>` from the path, registers
   the source (if `source.json` is present) via `source-register.sh`,
   runs `import-external.sh` end-to-end
5. Posts a sticky PR comment with:
   - :white_check_mark: or :x: per bundle
   - post-import Merkle root
   - total `:Imported` node count
   - the cypher error if any validation rule tripped

On success, the newly-imported nodes land with `:Imported` +
`:ImportedFrom_<Source>` labels and `provenance` = `<source_alias>`.
They are read-only until a separate PR adopts specific nodes via
`graph/runner/adopt-node.sh`.

## Tagging guarantees

After a successful import, every imported node carries:

```
labels:             [OriginalLabel, Imported, ImportedFrom_<Source>, GraphNode]
provenance:         "<source_alias>"
imported_at:        ISO datetime of the import transaction
imported_in_species: node_id of the candidate Species for the new state
```

The `:Imported` label is what scopes-out the node from core-scoped
invariants and tests (via `WHERE NOT n:Imported` where applicable).
Adoption removes `:Imported` and `:ImportedFrom_<Source>`, adds
`:Adopted`, and keeps `provenance` forever as audit trail.

## Adoption from imported

```
graph/runner/adopt-node.sh ember:user-rajesh <your-alias>
```

Runs inside a `validate-merge` transaction — if the adopted node would
break any enabled invariant or test, the whole adoption rolls back and
the node stays `:Imported`.

## Not yet supported

- Signed bundles: `source.json.public_key` is stored but not yet used
  to verify a signed manifest. Phase 8+ will require bundles to include
  a signature over their content.
- Schema translation: mycelium accepts whatever labels/properties the
  source sends. No normalization layer. Downstream queries must know
  each source's vocabulary.
- Deletion imports: currently only additive `MERGE` is supported.
  Deleting external-graph state requires an adoption + explicit
  un-adoption flow that hasn't been designed yet.
