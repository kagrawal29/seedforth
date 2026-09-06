// @node_id: protocol-run-tests
// @label: "Run Tests"
// ============================================================================
// Protocol: Run Tests
// ============================================================================
// Graph-native test runner. Reads every TestCase node, executes its assertion
// cypher dynamically via apoc.cypher.run, compares the first value of the
// first result row against the test's expected property, and writes the
// outcome back onto the TestCase as last_result / actual / last_run plus
// run_count and fail_count counters.
//
// Comparison rules:
//   1. The query to run is coalesce(t.assertion_cypher, t.cypher,
//      t.assertion_query). Tests with none of these properties are reported
//      failed with actual='__no_query__'. The legacy harness wrote three
//      different property names across different test generations;
//      assertion_cypher takes precedence to match the new protocol.
//   2. The actual value is the first value of the first result row, coerced
//      via toString. apoc.cypher.run returns a list of maps (one per row);
//      we take head() and pull the value of the first key.
//   3. If t.expected is set, pass iff toLower(toString(first_val)) =
//      toLower(toString(t.expected)). Case-insensitive because the legacy
//      Python harness wrote 'True' (Python title-case) while Cypher returns
//      'true'. If t.expected is null, the assertion is expected to return a
//      boolean directly — pass iff toLower(actual) = 'true'.
//   4. If the assertion query throws (syntax error, deprecated function,
//      missing label, etc.), the test is marked failed with actual prefixed
//      '__error__'. Errors do not abort the protocol — each test runs in its
//      own transaction via CALL ... IN TRANSACTIONS ON ERROR CONTINUE.
//
// Side effects on each TestCase:
//   actual         string   first value of first row (or sentinel)
//   last_result    string   'pass' | 'fail'
//   last_run       string   ISO datetime
//   run_count      int      monotonic counter
//   fail_count     int      monotonic counter (only on fail)
//
// IMPORTANT: All five output properties above mutate TestCase nodes on every
// run. They are NOT currently in the SkipKey list, so every protocol run
// drifts every TestCase leaf_hash and therefore root_hash. See parent agent
// follow-up note — they need to be added to graph/protocols/skip-keys-init.
//
// Idempotent: running twice with no graph change produces the same
// pass/fail verdicts (counters increment, but verdicts are stable).
//
// Dependencies: APOC (apoc.cypher.doIt — used so legacy self-mutating
// assertions that SET back on the TestCase still work; doIt accepts both
// read and write statements).
// ============================================================================


// --- Phase 1: pre-mark every TestCase with an error sentinel -----------------
// Phase 2 overwrites this on success. Anything still wearing __error__ after
// phase 2 had its assertion query throw and its row was rolled back by
// IN TRANSACTIONS ON ERROR CONTINUE.

MATCH (t:TestCase)
WHERE coalesce(t.enabled, true) = true
SET t._run_actual = '__error__',
    t._run_first = null;


// --- Phase 2: execute each assertion in its own transaction ------------------
// IN TRANSACTIONS ON ERROR CONTINUE wraps each TestCase in its own auto-commit
// transaction. A throw in apoc.cypher.run rolls back that one row but leaves
// the rest of the protocol intact.

MATCH (t:TestCase)
WHERE coalesce(t.enabled, true) = true
WITH t, coalesce(t.assertion_cypher, t.cypher, t.assertion_query) AS query
CALL {
  WITH t, query
  WITH t, query WHERE query IS NOT NULL
  CALL apoc.cypher.doIt(query, {}) YIELD value
  WITH t, collect(value) AS rows
  WITH t,
       CASE WHEN size(rows) = 0 THEN null ELSE head(rows) END AS first_row
  WITH t,
       CASE
         WHEN first_row IS NULL THEN '__no_row__'
         ELSE toString(first_row[head(keys(first_row))])
       END AS actual_str
  SET t._run_actual = actual_str
} IN TRANSACTIONS OF 1 ROWS ON ERROR CONTINUE;


// --- Phase 3: handle tests with no executable cypher at all ------------------

MATCH (t:TestCase)
WHERE coalesce(t.enabled, true) = true
  AND t.assertion_cypher IS NULL AND t.cypher IS NULL AND t.assertion_query IS NULL
SET t._run_actual = '__no_query__';


// --- Phase 4: decide verdicts and write output properties --------------------

MATCH (t:TestCase)
WHERE coalesce(t.enabled, true) = true
WITH t, t._run_actual AS actual_str
WITH t, actual_str,
     CASE
       WHEN actual_str = '__error__' THEN 'fail'
       WHEN actual_str = '__no_query__' THEN 'fail'
       WHEN actual_str = '__no_row__' THEN 'fail'
       WHEN t.expected IS NOT NULL AND toLower(toString(t.expected)) = toLower(actual_str) THEN 'pass'
       WHEN t.expected IS NULL AND toLower(actual_str) = 'true' THEN 'pass'
       ELSE 'fail'
     END AS verdict
SET t.actual = actual_str,
    t.last_result = verdict,
    t.last_run = toString(datetime()),
    t.run_count = coalesce(t.run_count, 0) + 1,
    t.fail_count = coalesce(t.fail_count, 0) + CASE WHEN verdict = 'fail' THEN 1 ELSE 0 END
REMOVE t._run_actual, t._run_first;


// --- Phase 5: emit summary ---------------------------------------------------
// Summary counts ALL TestCase nodes, split by enabled state. Deferred tests
// are tracked but don't gate the runner's exit code.

MATCH (t:TestCase)
WITH collect({
       node_id: t.node_id,
       label: t.label,
       verdict: t.last_result,
       enabled: coalesce(t.enabled, true),
       deferred_reason: t.deferred_reason
     }) AS results
WITH results,
     [r IN results WHERE r.enabled = true] AS active,
     [r IN results WHERE r.enabled = false] AS deferred
WITH results, active, deferred,
     size(active) AS active_total,
     size([r IN active WHERE r.verdict = 'pass']) AS passed,
     size([r IN active WHERE r.verdict = 'fail']) AS failed,
     [r IN active WHERE r.verdict = 'fail' | r.node_id] AS failed_ids,
     size(deferred) AS deferred_count
RETURN active_total AS total, passed, failed, failed_ids, deferred_count;
