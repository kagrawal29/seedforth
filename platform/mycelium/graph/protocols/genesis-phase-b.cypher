// @kind: seed
// ============================================================================
// Protocol: Genesis Phase B
// ============================================================================
// One-shot bootstrap: archive the legacy falkor-era Species chain and mint a
// fresh genesis Species under the Phase B merkle algorithm.
//
// Why we can't just extend the old chain:
//   - The 9 existing Species were minted under an unknown hashing algorithm
//     whose outputs don't match our Phase B merkle protocol.
//   - Old manifest_root values can't be verified against current graph state
//     because we don't know what they were hashing over.
//   - Extending a chain of unverifiable blocks with a new verifiable block
//     breaks the integrity guarantee: a reviewer can't walk the chain and
//     confirm each link, because the transition point is opaque.
//
// What we do instead:
//   - Add :LegacySpecies as a secondary label on all 9 existing Species.
//     Keeps them queryable as history, makes them ignorable in current
//     chain traversals.
//   - Flag them with pre_phase_b: true and legacy_archived_at: datetime().
//   - Do the same to existing WitnessSignature nodes — 5 of them — since
//     they signed legacy species under the legacy algorithm.
//   - Mint exactly ONE new Species: species-genesis-phase-b with
//     genesis=true, parent_dna=NULL, manifest_root=current Being.root_hash,
//     algorithm="phase-b-v1", canonical=true (because genesis is canonical
//     by definition — there is nothing prior to validate against).
//   - Link Being to it via a :CURRENT_SPECIES edge. Future mints will
//     advance this edge to the new head.
//
// Idempotent: uses MERGE on the genesis node_id. Safe to re-run — a second
// invocation is a no-op since legacy species are already labeled and the
// genesis node already exists.
//
// Invariants touched:
//   - invariant-exactly-one-genesis will PASS after this runs (exactly one
//     Species has genesis=true AND algorithm="phase-b-v1"; legacy species
//     are not considered because they lack the algorithm marker).
//   - invariant-genesis-no-parent will PASS (parent_dna IS NULL).
//   - invariant-quorum-enforced will still fail for the genesis species
//     because it's canonical=true without any WitnessSignature. Genesis
//     is special — the first block is canonical by fiat. We either relax
//     the invariant to allow genesis, OR we defer it until Phase 2.5 when
//     the first witness signs.
//
// Dependencies: APOC (datetime function). Merkle-properties must have run
// first so Being.root_hash is populated with the current state commitment.
// ============================================================================


// --- Step 1: archive the legacy species chain -------------------------------
// Add :LegacySpecies label and pre_phase_b marker. Leave all other
// properties intact for historical auditability.

MATCH (s:Species)
WHERE NOT s:LegacySpecies
  AND s.algorithm <> 'phase-b-v1'
  OR (s.algorithm IS NULL AND NOT s:LegacySpecies)
SET s:LegacySpecies,
    s.pre_phase_b = true,
    s.legacy_archived_at = toString(datetime());


// --- Step 2: archive the legacy witness signatures --------------------------
// Same treatment. 5 signatures from the old chain, all now relabeled.

MATCH (ws:WitnessSignature)
WHERE NOT ws:LegacyWitnessSignature
SET ws:LegacyWitnessSignature,
    ws.pre_phase_b = true,
    ws.legacy_archived_at = toString(datetime());


// --- Step 3: mint the fresh genesis species ---------------------------------
// MERGE keyed on node_id so this is idempotent. On first run, create with
// full property set; on subsequent runs, this is a no-op and the ON CREATE
// SET does nothing because the node already exists.

MATCH (b:Being {node_id: 'being-mycelium'})
WITH b, b.root_hash AS current_root
MERGE (g:Species {node_id: 'species-genesis-phase-b'})
ON CREATE SET
  g:CanonicalSpecies,
  g.label = 'Genesis Species (Phase B)',
  g.algorithm = 'phase-b-v1',
  g.genesis = true,
  g.canonical = true,
  g.signed = false,
  g.parent_dna = null,
  g.manifest_root = current_root,
  g.quorum_required = 1,
  g.git_branch = 'species/genesis-phase-b',
  g.minted_at = toString(datetime()),
  g.minted_from = 'genesis-phase-b.cypher',
  g.file_type = 'species',
  g.description = 'The first Species minted under the Phase B merkle algorithm. Commits to the state of the graph at the time of the Phase B transition. canonical=true by fiat — genesis blocks are canonical without witness signatures because there is nothing prior to validate against.'
ON MATCH SET
  g.manifest_root_last_refreshed = current_root;


// --- Step 4: link Being to the genesis via :CURRENT_SPECIES -----------------
// One-shot: remove any existing CURRENT_SPECIES edge (there shouldn't be
// one pre-genesis, but be safe), then create the link to the new genesis.

MATCH (b:Being {node_id: 'being-mycelium'})
OPTIONAL MATCH (b)-[old:CURRENT_SPECIES]->()
DELETE old;

MATCH (b:Being {node_id: 'being-mycelium'})
MATCH (g:Species {node_id: 'species-genesis-phase-b'})
MERGE (b)-[:CURRENT_SPECIES]->(g);


// --- Step 5: summary --------------------------------------------------------

MATCH (g:Species {node_id: 'species-genesis-phase-b'})
MATCH (b:Being {node_id: 'being-mycelium'})-[:CURRENT_SPECIES]->(g)
MATCH (legacy:LegacySpecies)
WITH g, count(legacy) AS legacy_count
MATCH (lw:LegacyWitnessSignature)
WITH g, legacy_count, count(lw) AS legacy_sigs
RETURN g.node_id AS genesis_node_id,
       g.manifest_root AS manifest_root,
       g.algorithm AS algorithm,
       legacy_count AS legacy_species_archived,
       legacy_sigs AS legacy_signatures_archived;
