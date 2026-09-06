// @kind: seed
// ============================================================================
// Protocol: Species Sign
// ============================================================================
// Records a WitnessSignature against a candidate species. The witness is
// responsible for having already verified the candidate's validity
// (invariants, tests, proof-of-work whatever) before calling this.
//
// Phase 2 uses a sha256-based commitment as a placeholder. The commitment
// is a cypher-native deterministic function of (witness_alias, species_dna,
// manifest_root) — not asymmetric crypto, so anyone with read access could
// forge one. This is fine for a single-operator development chain. Phase 2.5
// replaces this with real ed25519 verification via a Python sidecar that
// takes (dna, public_key, signature) and exits 0/1.
//
// Parameters (via cypher-shell --param or :param):
//   witness_alias      string  — must match an existing Witness.alias
//   species_node_id    string  — node_id of the candidate to sign
//   signed_at          string  — ISO datetime (or null, defaults to now)
//   signature          string  — optional hex signature (ed25519 from
//                                 Phase 2.5 witness-sign.sh), null triggers
//                                 the cypher-native sha256-commitment fallback
//   algorithm          string  — optional, 'ed25519' | 'sha256-commitment';
//                                 defaults to 'sha256-commitment' when null
//
// Phase 2 (commitment-only): pass signature=null and algorithm=null. This
// computes a deterministic sha256 of (public_key, manifest_root, parent_dna,
// node_id) inside cypher — reproducible from the public key alone, so it is
// NOT forgery-resistant. Fine for a single-operator dev chain.
//
// Phase 2.5 (ed25519): witness-sign.sh passes a real ed25519 signature of
// "manifest_root|parent_dna|node_id" (produced by mycelium-crypto.py sign)
// together with algorithm='ed25519'. The signature field is stored as
// opaque hex; verification happens outside cypher via
// mycelium-crypto.py verify before canonize promotes the species. species-
// canonize filters out signatures that don't verify against the witness's
// registered public key.
//
// Idempotency: MERGE on WitnessSignature node_id keyed by
// (species_node_id, witness_alias). Re-running this protocol for the same
// (witness, species) pair is a no-op after the first invocation.
//
// Side effects:
//   - Creates or updates one WitnessSignature node linked to the species
//   - Leaves species.signed as-is (that's canonize's job)
// ============================================================================

MATCH (w:Witness {alias: $witness_alias})
WHERE NOT w:LegacyWitness
WITH w
MATCH (c:Species {node_id: $species_node_id})
WHERE c.algorithm = 'phase-b-v1'
WITH w, c,
     coalesce($signed_at, toString(datetime())) AS sig_time,
     coalesce($signature,
       apoc.util.sha256([
         coalesce(w.public_key, 'no-public-key'),
         c.manifest_root,
         coalesce(c.parent_dna, 'genesis'),
         c.node_id
       ])
     ) AS sig,
     coalesce($algorithm, 'sha256-commitment') AS sig_alg
MERGE (ws:WitnessSignature {
  node_id: 'witsig-' + substring(c.manifest_root, 0, 16) + '-' + w.alias
})
ON CREATE SET
  ws.witness_alias = w.alias,
  ws.public_key = w.public_key,
  ws.species_dna = c.manifest_root,
  ws.species_node_id = c.node_id,
  ws.signature = sig,
  ws.signed_at = sig_time,
  ws.algorithm = sig_alg,
  ws.signed_message = c.manifest_root + '|' + coalesce(c.parent_dna, 'genesis') + '|' + c.node_id,
  ws.file_type = 'witness-signature',
  ws.label = 'Witness ' + w.alias + ' signature of ' + substring(c.manifest_root, 0, 12)
ON MATCH SET
  ws.signature = sig,
  ws.algorithm = sig_alg,
  ws.re_signed_at = sig_time
MERGE (ws)-[:SIGNS]->(c)
MERGE (ws)-[:SIGNED_BY]->(w)
RETURN ws.node_id AS signature_node_id,
       ws.witness_alias AS witness,
       ws.species_node_id AS species,
       ws.algorithm AS algorithm,
       substring(ws.signature, 0, 16) + '...' AS signature_preview;
