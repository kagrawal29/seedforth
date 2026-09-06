// @node_id: protocol-validate-merge
// @label: "Validate Merge (within-transaction check)"
// ============================================================================
// Protocol: Validate Merge (within-transaction check)
// ============================================================================
// This file is the VALIDATION block that runs inside an explicit transaction
// after a proposed merge has been applied. The caller (graph/runner/
// validate-merge.sh) wraps it with :begin → proposed_cypher → this file →
// :commit. Any apoc.util.validate throw inside this file aborts the
// transaction, rolling back both the proposed merge AND the validation
// scratch writes.
//
// Order of checks (fail-fast):
//   Step 1: run every enabled Invariant's check_cypher. If any unhealthy,
//           throw.
//   Step 2: run every enabled TestCase's assertion_cypher. If any fails,
//           throw.
//   Step 3: recompute merkle-properties leaf_hash + root_hash for the
//           post-merge state. This is non-throwing — it just updates
//           Being.root_hash so the mint step sees the new commitment.
//
// Throws on first failure with a descriptive message naming the failing
// invariant or test and its last_check_result / actual value.
//
// Note: this protocol does NOT include Phase 1's run-invariants/run-tests
// verbatim because those write state on every run (health, last_result,
// fail_count, etc.). Inside a transaction that gets rolled back, those
// writes are discarded — fine. But we want the failure MESSAGE to carry
// actionable info, so we re-implement a simplified inline version that
// raises on first failure.
//
// Dependencies: APOC (apoc.cypher.run, apoc.util.validate, apoc.convert.toJson).
// ============================================================================


// --- Step 1: run every enabled Invariant, fail-fast ------------------------
// For each invariant, execute its check_cypher via apoc.cypher.run, extract
// the first value of the first row, interpret as healthy/unhealthy, and
// throw via apoc.util.validate if unhealthy.

MATCH (i:Invariant)
WHERE coalesce(i.enabled, true) = true
  AND i.check_cypher IS NOT NULL
WITH i, i.check_cypher AS check_q
CALL apoc.cypher.run(check_q, {}) YIELD value
WITH i, collect(value) AS rows
WITH i,
     CASE WHEN size(rows) = 0 THEN null ELSE rows[0] END AS first_row
WITH i, first_row,
     CASE WHEN first_row IS NULL THEN null
          ELSE first_row[head(keys(first_row))] END AS v
WITH i, first_row, v,
     CASE
       WHEN v IS NULL THEN false
       WHEN v = true THEN true
       WHEN v = false THEN false
       WHEN apoc.meta.cypher.type(v) IN ['INTEGER', 'FLOAT'] THEN v > 0
       WHEN apoc.meta.cypher.type(v) = 'STRING' THEN toLower(toString(v)) IN ['healthy', 'ok', 'pass', 'true']
       ELSE false
     END AS healthy
WITH i, v, healthy
WHERE NOT healthy
WITH collect({id: i.node_id, label: i.label, value: toString(v)}) AS failures
CALL apoc.util.validate(
  size(failures) > 0,
  'validate-merge: invariant failures: %s',
  [apoc.convert.toJson(failures)]
)
RETURN 'invariants-ok' AS step;


// --- Step 2: run every enabled TestCase, fail-fast -------------------------

MATCH (t:TestCase)
WHERE coalesce(t.enabled, true) = true
WITH t, coalesce(t.assertion_cypher, t.cypher, t.assertion_query) AS qtext
WHERE qtext IS NOT NULL
CALL apoc.cypher.doIt(qtext, {}) YIELD value
WITH t, collect(value) AS rows
WITH t,
     CASE WHEN size(rows) = 0 THEN null ELSE rows[0] END AS first_row
WITH t, first_row,
     CASE WHEN first_row IS NULL THEN null
          ELSE first_row[head(keys(first_row))] END AS v
WITH t, v,
     CASE
       WHEN t.expected IS NOT NULL AND toLower(toString(v)) = toLower(toString(t.expected)) THEN true
       WHEN t.expected IS NULL AND toLower(toString(v)) = 'true' THEN true
       ELSE false
     END AS passed
WITH t, v, passed
WHERE NOT passed
WITH collect({id: t.node_id, label: t.label, actual: toString(v), expected: t.expected}) AS failures
CALL apoc.util.validate(
  size(failures) > 0,
  'validate-merge: test failures: %s',
  [apoc.convert.toJson(failures)]
)
RETURN 'tests-ok' AS step;


// --- Step 3: recompute merkle for the post-merge state ---------------------
// Same as graph/protocols/merkle-properties.cypher steps 2-3, inlined so
// the whole check runs in one transaction.

MATCH (n)
WHERE (n:Species OR n:LegacySpecies OR n:CanonicalSpecies
       OR n:WitnessSignature OR n:LegacyWitnessSignature OR n:Witness)
  AND n.leaf_hash IS NOT NULL
REMOVE n.leaf_hash;

MATCH (sk:SkipKey)
WITH collect(sk.key) AS skip_keys
MATCH (n)
WHERE n.node_id IS NOT NULL
  AND NOT n:QueryTrace
  AND NOT n:Species
  AND NOT n:LegacySpecies
  AND NOT n:CanonicalSpecies
  AND NOT n:WitnessSignature
  AND NOT n:LegacyWitnessSignature
  AND NOT n:Witness
WITH n, skip_keys,
     labels(n)[0] AS label,
     [k IN keys(n) WHERE NOT k IN skip_keys | k + '=' + apoc.convert.toJson(n[k])] AS raw_pairs
WITH n, label + '|' + apoc.text.join(apoc.coll.sort(raw_pairs), ';') AS serialized
WITH n, apoc.util.sha256([serialized]) AS leaf
WITH collect({n: n, leaf: leaf}) AS all_leaves
UNWIND all_leaves AS row
WITH row
SET row.n.leaf_hash = row.leaf;

MATCH (n) WHERE n.leaf_hash IS NOT NULL
WITH apoc.coll.sort(collect(n.leaf_hash)) AS sorted_hashes
WITH sorted_hashes,
     apoc.util.sha256(sorted_hashes) AS root,
     size(sorted_hashes) AS n_leaves
MERGE (b:Being {node_id: 'being-mycelium'})
SET b.root_hash = root,
    b.leaf_count = n_leaves,
    b.root_hash_computed_at = toString(datetime());

RETURN 'merkle-ok' AS step;
