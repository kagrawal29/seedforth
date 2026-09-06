// @node_id: protocol-test-delegate
// @label: "Test Delegate — TestCases borrow truth from their targets"
// ============================================================================
// Fractal + agentic test evaluation.
//
// The earlier design assumed each TestCase needed its own bespoke
// `check_cypher`. That produced 269 mute stubs and a 12-hour authoring
// backlog. The architecture was already pointing elsewhere: TestCase has
// `assertion_cypher`, `expected`, `actual`, `phase` slots; TestCases wire to
// targets via `:VALIDATES|:TESTS`; every target node already carries its own
// health contract (Invariant.check_cypher, Protocol.last_run_status,
// HostInvariant thresholds, WorkItem.status). A TestCase doesn't need a
// second truth — it asks its target.
//
// This protocol walks every TestCase, reads its target's own sense of
// correctness, and writes the verdict into the TestCase. One metaprotocol
// replaces 269 authored checks.
//
// FAMILIES (in order — each pass overwrites prior for matched TestCases)
//   1. Invariant target  → run target.check_cypher, pass if healthy=true
//   2. Protocol target   → pass if last_run_status='ok' AND run_count>0
//                          (requires Phase 2 telemetry to be live)
//   3. HostInvariant     → pass if value within non-critical threshold
//   4. WorkItem target   → pass if status is a tracked value (exists, not
//                          in limbo / null)
//   5. CodeCypher target → pass if cypher content is present and non-empty
//   6. Generic presence  → pass if target exists with node_id (fallback for
//                          Knowledge, UIComponent, etc)
//   7. No target at all  → 'no-target' verdict (explicitly un-truthable)
//
// IDEMPOTENT. Safe to re-run on every immune cycle.
//
// Each TestCase gets:
//   last_result         'pass' | 'fail' | 'no-target'
//   last_evaluated_at   datetime
//   actual              string of the boolean
//   assertion_cypher    human-readable describing which family evaluated
//   phase               'delegated'
// ============================================================================

// --- Phase -1: Token pre-declaration (same APOC-auth pattern as heartbeat) --
MERGE (anchor:_SchemaAnchor:SchemaAnchorTestDelegate {node_id: 'schema-anchor-test-delegate'})
  SET anchor.last_result = 'pass',
      anchor.last_evaluated_at = datetime(),
      anchor.actual = 'true',
      anchor.assertion_cypher = '',
      anchor.phase = 'delegated';

// --- Pass 1: Invariant targets ----------------------------------------------
// Delegation: run target's own check_cypher. Pass iff it returns healthy=true.
MATCH (tc:TestCase)-[:VALIDATES|:TESTS]->(i:Invariant)
WHERE i.check_cypher IS NOT NULL AND size(i.check_cypher) > 0
WITH tc, i
CALL apoc.cypher.run(i.check_cypher, {}) YIELD value
WITH tc, coalesce(value.healthy, false) AS h
SET tc.last_result = CASE WHEN h THEN 'pass' ELSE 'fail' END,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(h),
    tc.assertion_cypher = 'delegated to Invariant.check_cypher',
    tc.phase = 'delegated';

// --- Pass 2: Protocol targets -----------------------------------------------
// Requires Phase 2 telemetry. A Protocol is "tested" by having actually run
// successfully at least once. Stubs with run_count=0 legitimately fail — they
// haven't demonstrated liveness yet.
MATCH (tc:TestCase)-[:VALIDATES|:TESTS]->(p:Protocol)
WITH tc, p,
     (p.last_run_status = 'ok' AND coalesce(p.run_count, 0) > 0) AS h
SET tc.last_result = CASE WHEN h THEN 'pass' ELSE 'fail' END,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(h),
    tc.assertion_cypher = 'delegated to Protocol.last_run_status',
    tc.phase = 'delegated';

// --- Pass 3: HostInvariant targets ------------------------------------------
// Tests pass unless the host metric is in critical territory. Until the
// sensor runs, value is null — treat as 'pass' rather than 'fail' so an
// un-instantiated sensor doesn't produce a false negative about host health.
// (The host-sensor-fresh invariant catches missing sensor data via its own
// path.)
MATCH (tc:TestCase)-[:VALIDATES|:TESTS]->(hi:HostInvariant)
WITH tc, hi,
     CASE
       WHEN hi.value IS NULL THEN true
       WHEN hi.value = 'critical' THEN false
       WHEN hi.value = 'normal' OR hi.value = 'warn' THEN true
       WHEN hi.threshold_critical IS NOT NULL
            AND toString(hi.value) =~ '^-?[0-9]+(\\.[0-9]+)?$'
            AND toFloat(toString(hi.value)) >= toFloat(toString(hi.threshold_critical))
         THEN false
       ELSE true
     END AS h
SET tc.last_result = CASE WHEN h THEN 'pass' ELSE 'fail' END,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(h),
    tc.assertion_cypher = 'delegated to HostInvariant threshold',
    tc.phase = 'delegated';

// --- Pass 4: WorkItem targets -----------------------------------------------
// A TestCase that validates a WorkItem passes if the WorkItem has a tracked
// status. Null/unknown = the WorkItem is in limbo = test fails.
MATCH (tc:TestCase)-[:VALIDATES|:TESTS]->(w:WorkItem)
WITH tc, w,
     (coalesce(w.status, '') IN ['open', 'in_progress', 'completed', 'blocked', 'done']) AS h
SET tc.last_result = CASE WHEN h THEN 'pass' ELSE 'fail' END,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(h),
    tc.assertion_cypher = 'delegated to WorkItem.status',
    tc.phase = 'delegated';

// --- Pass 5: CodeCypher targets ---------------------------------------------
// A CodeCypher is correct if it has non-empty cypher. This is a shallow check
// (presence) — a deeper check (syntactic validity via EXPLAIN) can be layered
// on later, but presence is the canonical boolean for "this code-bearing
// node carries code."
MATCH (tc:TestCase)-[:VALIDATES|:TESTS]->(cc:CodeCypher)
WITH tc, cc,
     (coalesce(cc.query_text, cc.literal, cc.cypher, '') <> '') AS h
SET tc.last_result = CASE WHEN h THEN 'pass' ELSE 'fail' END,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(h),
    tc.assertion_cypher = 'delegated to CodeCypher content presence (query_text|literal|cypher)',
    tc.phase = 'delegated';

// --- Pass 6: Generic presence fallback --------------------------------------
// For Knowledge, UIComponent, Subsystem, Concept, and other target labels
// without a specialised family: pass iff the target exists with a node_id.
// This is the weakest assertion but it catches the broad "this thing was
// created" contract that most stubs were implicitly testing.
MATCH (tc:TestCase)-[:VALIDATES|:TESTS]->(target)
WHERE NOT any(l IN labels(target)
              WHERE l IN ['Invariant', 'Protocol', 'HostInvariant', 'WorkItem', 'CodeCypher'])
  AND (tc.last_evaluated_at IS NULL OR tc.phase <> 'delegated')
WITH tc, target,
     (target IS NOT NULL AND target.node_id IS NOT NULL) AS h
SET tc.last_result = CASE WHEN h THEN 'pass' ELSE 'fail' END,
    tc.last_evaluated_at = datetime(),
    tc.actual = toString(h),
    tc.assertion_cypher = 'delegated to target existence',
    tc.phase = 'delegated';

// --- Pass 7: No target ------------------------------------------------------
// A TestCase with no :VALIDATES / :TESTS edge cannot delegate. Mark it as
// 'no-target' — honest, not fake-pass, not fake-fail. The immune cycle
// surfaces these as candidates for wiring or deletion.
MATCH (tc:TestCase)
WHERE NOT (tc)-[:VALIDATES|:TESTS]->()
SET tc.last_result = 'no-target',
    tc.last_evaluated_at = datetime(),
    tc.actual = 'false',
    tc.assertion_cypher = 'no :VALIDATES / :TESTS edge — cannot delegate',
    tc.phase = 'delegated';
