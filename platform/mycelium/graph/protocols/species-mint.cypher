// @kind: seed
// ============================================================================
// Protocol: Species Mint
// ============================================================================
// Creates a candidate Species committing to the current graph state.
// The candidate starts unsigned — witnesses sign via species-sign.cypher,
// and species-canonize.cypher flips the canonical bit once quorum is met.
//
// Idempotency:
//   - If the current Being.root_hash already matches the current canonical
//     species's manifest_root, nothing to mint — returns "noop-no-drift".
//   - If a candidate already exists with the same manifest_root, returns
//     "noop-candidate-exists" with the existing candidate's node_id.
//   - Otherwise mints a new candidate.
//
// Chain-layer transparency:
//   merkle-properties.cypher excludes Species/WitnessSignature/Witness from
//   the hash input, so adding this candidate does NOT drift Being.root_hash.
//   The candidate's manifest_root commits to state-minus-chain, which is the
//   only interpretation that stays stable across chain mutations.
//
// Parameters: none — reads everything from graph state.
//
// Side effects:
//   - Creates exactly one new :Species :CandidateSpecies node
//   - Creates a :DESCENDED_FROM edge to the current canonical species
//   - Does NOT move Being.CURRENT_SPECIES (canonize does that)
// ============================================================================


// --- Step 1: read current state commitment + current canonical species ------
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b.root_hash AS current_root
MATCH (parent:Species)
WHERE parent.canonical = true
  AND parent.algorithm = 'phase-b-v1'
WITH current_root, parent
ORDER BY parent.minted_at DESC
LIMIT 1
WITH current_root, parent,
     parent.manifest_root AS parent_root


// --- Step 2: idempotency checks ---------------------------------------------
// If nothing has drifted since the parent was canonized, mint is a no-op.
WITH current_root, parent, parent_root,
     CASE WHEN current_root = parent_root THEN true ELSE false END AS no_drift
OPTIONAL MATCH (existing:Species:CandidateSpecies {manifest_root: current_root})
  WHERE existing.algorithm = 'phase-b-v1'
WITH current_root, parent, parent_root, no_drift, existing

// Collapse to one row with the decision
WITH current_root, parent, parent_root, no_drift, existing,
     CASE
       WHEN no_drift THEN 'noop-no-drift'
       WHEN existing IS NOT NULL THEN 'noop-candidate-exists'
       ELSE 'mint'
     END AS decision


// --- Step 3: mint the candidate if needed -----------------------------------
// FOREACH is the cypher-native way to conditionally execute writes.

FOREACH (_ IN CASE WHEN decision = 'mint' THEN [1] ELSE [] END |
  CREATE (c:Species:CandidateSpecies {
    node_id: 'species-candidate-' + substring(current_root, 0, 16),
    algorithm: 'phase-b-v1',
    candidate: true,
    canonical: false,
    signed: false,
    parent_dna: parent_root,
    manifest_root: current_root,
    quorum_required: coalesce(parent.quorum_required, 1),
    git_branch: 'species/candidate-' + substring(current_root, 0, 16),
    minted_at: toString(datetime()),
    minted_from: 'species-mint.cypher',
    label: 'Candidate Species (phase-b-v1, root=' + substring(current_root, 0, 12) + ')',
    file_type: 'species',
    description: 'Candidate species pending witness signatures. Commits to Being.root_hash at mint time. Promoted to canonical by species-canonize.cypher once quorum_required WitnessSignatures accumulate.'
  })
  MERGE (c)-[:DESCENDED_FROM]->(parent)
);


// --- Step 4: return the outcome ---------------------------------------------
// Find the most recent candidate with this manifest_root (just created or
// pre-existing), plus the decision code.
MATCH (b:Being {node_id: 'being-mycelium'})
WITH b.root_hash AS current_root
OPTIONAL MATCH (c:Species:CandidateSpecies {manifest_root: current_root})
  WHERE c.algorithm = 'phase-b-v1'
WITH current_root, c
ORDER BY c.minted_at DESC
LIMIT 1
OPTIONAL MATCH (parent:Species {canonical: true, algorithm: 'phase-b-v1'})
WITH current_root, c, parent
ORDER BY parent.minted_at DESC
LIMIT 1
RETURN
  CASE
    WHEN c IS NOT NULL AND c.manifest_root = current_root AND c.candidate = true
    THEN 'candidate-ready'
    ELSE 'no-candidate'
  END AS status,
  c.node_id AS candidate_id,
  c.manifest_root AS candidate_manifest_root,
  c.parent_dna AS candidate_parent_dna,
  parent.node_id AS canonical_parent_id;
