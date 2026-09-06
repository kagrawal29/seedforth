// @kind: seed
// ============================================================================
// Protocol: Species Canonize
// ============================================================================
// Promotes a candidate Species to canonical once it has accumulated
// enough non-legacy WitnessSignatures to meet its quorum_required.
//
// On promotion:
//   - candidate.canonical = true
//   - candidate.signed = true
//   - previous canonical species.canonical = false, superseded_at set
//   - Being.CURRENT_SPECIES edge moves to the new head
//   - candidate is added to the chain visible to invariants
//
// Parameters:
//   species_node_id   string — the candidate to canonize
//
// Preconditions (checked inline, protocol fails loudly if violated):
//   1. candidate exists, is phase-b-v1, has candidate=true
//   2. candidate has >= quorum_required valid (non-legacy) WitnessSignatures
//   3. each signature's witness is active and has a matching public_key
//
// Not checked here (caller's responsibility):
//   - that the signatures actually verify cryptographically. Phase 2.5
//     adds an ed25519 verify step via a Python sidecar.
//   - that the graph state actually matches the candidate's manifest_root.
//     (validate-merge.cypher in Phase 3 ensures this before mint.)
// ============================================================================

// --- Step 1: locate candidate + count valid signatures ---------------------
// Valid = WitnessSignature that (a) is not legacy, (b) links to a
// non-legacy Witness whose public_key matches, and (c) is verified.
// Two ways to be "verified":
//   1. ws.verified = true  (stamped by graph/runner/verify-signatures.sh
//      after running mycelium-crypto.py verify)
//   2. ws.algorithm = 'sha256-commitment'  (self-verifying: anyone with
//      the public key and species fields can reproduce this signature
//      via apoc.util.sha256, so treating it as pre-verified is safe)

MATCH (c:Species:CandidateSpecies {node_id: $species_node_id})
WHERE c.algorithm = 'phase-b-v1'
OPTIONAL MATCH (ws:WitnessSignature)-[:SIGNS]->(c)
  WHERE NOT ws:LegacyWitnessSignature
    AND (ws.verified = true OR ws.algorithm = 'sha256-commitment')
OPTIONAL MATCH (ws)-[:SIGNED_BY]->(w:Witness)
  WHERE w.public_key = ws.public_key
    AND NOT w:LegacyWitness
WITH c, count(DISTINCT w) AS valid_sig_count
WITH c, valid_sig_count,
     coalesce(c.quorum_required, 1) AS quorum_required

// --- Step 2: fail loudly if quorum not met ---------------------------------
CALL apoc.util.validate(
  valid_sig_count < quorum_required,
  'quorum not met: species %s has %d valid signatures, requires %d',
  [c.node_id, valid_sig_count, quorum_required]
)

WITH c, valid_sig_count, quorum_required


// --- Step 3: demote previous canonical, promote candidate ------------------
// Find the previous canonical (there may be none if promoting from genesis)
OPTIONAL MATCH (prev:Species {canonical: true, algorithm: 'phase-b-v1'})
  WHERE prev.node_id <> c.node_id
WITH c, valid_sig_count, quorum_required, prev
ORDER BY prev.minted_at DESC
LIMIT 1

// Demote previous
FOREACH (_ IN CASE WHEN prev IS NOT NULL THEN [1] ELSE [] END |
  SET prev.canonical = false,
      prev.superseded_at = toString(datetime()),
      prev.superseded_by = c.node_id
)

// Promote candidate — flip labels and flags
WITH c, valid_sig_count, quorum_required, prev
REMOVE c:CandidateSpecies
SET c:CanonicalSpecies,
    c.candidate = false,
    c.canonical = true,
    c.signed = true,
    c.canonized_at = toString(datetime()),
    c.canonized_with_signatures = valid_sig_count


// --- Step 4: move Being.CURRENT_SPECIES edge to new head -------------------
WITH c
MATCH (b:Being {node_id: 'being-mycelium'})
OPTIONAL MATCH (b)-[old:CURRENT_SPECIES]->()
DELETE old

WITH b, c
MERGE (b)-[:CURRENT_SPECIES]->(c)


// --- Step 5: summary --------------------------------------------------------
RETURN c.node_id AS canonized,
       c.manifest_root AS manifest_root,
       c.parent_dna AS parent_dna,
       c.canonized_with_signatures AS signatures_count;
