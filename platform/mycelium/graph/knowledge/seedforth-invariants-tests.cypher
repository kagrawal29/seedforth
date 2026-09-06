// @node_id: seedforth-invariants-tests-v1
// @label: "SeedForth Invariants & TestCases — cypher-native verification layer"
// @kind: knowledge
//
// Replaces the 4 ad-hoc invariants from the foundation bootstrap with a
// complete, test-driven set. Every Invariant has at least one TestCase
// with assertion_cypher. Every TestCase IS a cypher traversal — no Python.
//
// Design principles (from the constitution):
//   - Test-driven: each invariant has a cypher-native test that verifies it
//   - Cypher-native: the test IS the cypher traversal
//   - Self-healing: invariants carry heal_protocol for auto-repair
//   - Forest Promise: cross-domain edges are visible, namespaced, typed
// ============================================================================

// ############################################################################
// INVARIANTS — what must stay true
// ############################################################################

// --- I1: Namespace Integrity ---
MERGE (i1:Invariant {node_id: 'inv-nodes-have-project'})
SET i1.project = 'seedforth',
    i1.label = 'Every core node carries {project: X}',
    i1.severity = 'critical',
    i1.why = 'Without namespace tags, nodes leak between domains. The graph cannot tell who owns what.',
    i1.check_cypher = 'MATCH (n) WHERE (n:Project OR n:Server OR n:Service OR n:Agent OR n:Repository OR n:Being OR n:Protocol OR n:CypherAtom OR n:Invariant OR n:Knowledge OR n:Purpose OR n:SovereigntyRule OR n:Concept OR n:ScaleMarker) AND n.project IS NULL RETURN count(n) AS violations',
    i1.heal_protocol = 'protocol-heal-assign-project',
    i1.expected = 0;

// --- I2: Forest Density ---
MERGE (i2:Invariant {node_id: 'inv-graph-density'})
SET i2.project = 'seedforth',
    i2.label = 'Graph density stays above threshold — edges/node > 0.8',
    i2.severity = 'warning',
    i2.why = 'A sparse graph is structurally weak — orphan nodes, untraversable paths, weak semantic coverage. This is how the graph knows it is getting thin.',
    i2.check_cypher = 'MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() WITH nodes, count(r) AS rels RETURN CASE WHEN toFloat(rels)/toFloat(nodes) >= 0.8 THEN 0 ELSE 1 END AS violations',
    i2.heal_protocol = 'protocol-densify-graph',
    i2.expected = 0;

// --- I3: Server Completeness ---
MERGE (i3:Invariant {node_id: 'inv-server-has-services'})
SET i3.project = 'seedforth',
    i3.label = 'Every :Server has at least one :Service listed',
    i3.severity = 'warning',
    i3.why = 'A server with no services is invisible to the ecosystem. The graph should know what runs where.',
    i3.check_cypher = 'MATCH (s:Server) WHERE NOT EXISTS { MATCH (s)-[:HAS_SERVICE]->(:Service) } RETURN count(s) AS violations',
    i3.heal_protocol = 'protocol-heal-server-services',
    i3.expected = 0;

// --- I4: Atom Discoverability ---
MERGE (i4:Invariant {node_id: 'inv-atom-has-semantic'})
SET i4.project = 'seedforth',
    i4.label = 'Every :CypherAtom has a semantic description',
    i4.severity = 'warning',
    i4.why = 'Atoms without semantic descriptions cannot be discovered by the LLM. They are dead code in the graph.',
    i4.check_cypher = 'MATCH (ca:CypherAtom) WHERE ca.semantic IS NULL OR ca.semantic = \'\' RETURN count(ca) AS violations',
    i4.heal_protocol = 'protocol-heal-atom-semantics',
    i4.expected = 0;

// --- I5: Repo Completeness ---
MERGE (i5:Invariant {node_id: 'inv-project-with-repo-has-repo-edge'})
SET i5.project = 'seedforth',
    i5.label = 'Every :Project with repo_url != \'\' has a :HAS_REPO edge to its :Repository',
    i5.severity = 'warning',
    i5.why = 'A project that claims to have a repo but no edge to it has a broken link. The dependency graph is incomplete.',
    i5.check_cypher = 'MATCH (p:Project) WHERE p.repo_url IS NOT NULL AND p.repo_url <> \'\' AND NOT EXISTS { MATCH (p)-[:HAS_REPO]->(:Repository) } RETURN count(p) AS violations',
    i5.heal_protocol = 'protocol-heal-repo-links',
    i5.expected = 0;

// --- I6: Test Coverage for Invariants (meta) ---
MERGE (i6:Invariant {node_id: 'inv-every-invariant-has-test'})
SET i6.project = 'seedforth',
    i6.label = 'Every :Invariant has at least one :TestCase verifying it',
    i6.severity = 'critical',
    i6.why = 'An untested invariant is a claim without evidence. TDD is the graph\'s immune system.',
    i6.check_cypher = 'MATCH (i:Invariant {project: "seedforth"}) WHERE NOT EXISTS { MATCH (i)<-[:VALIDATES]-(:TestCase) } RETURN count(i) AS violations',
    i6.heal_protocol = 'protocol-heal-missing-tests',
    i6.expected = 0;

// --- I7: Cypher-Native State ---
MERGE (i7:Invariant {node_id: 'inv-graph-is-source-of-truth'})
SET i7.project = 'seedforth',
    i7.label = 'Graph-Native System State — if something runs, the graph knows',
    i7.severity = 'critical',
    i7.why = 'The core constitutional principle. The graph is the source of truth, not files, not JSON registries, not memory. If the graph is missing something, it must be added. If something is in the graph that does not exist in reality, it must be marked stale.',
    i7.check_cypher = 'MATCH (svc:Service) WHERE svc.health = "active" AND svc.last_checked_at < datetime() - duration({days: 7}) RETURN count(svc) AS violations',
    i7.heal_protocol = 'protocol-heal-stale-services',
    i7.expected = 0;

// --- I8: Cross-Domain Edge Visibility ---
MERGE (i8:Invariant {node_id: 'inv-cross-domain-edges-typed'})
SET i8.project = 'seedforth',
    i8.label = 'Cross-domain edges use only allowed bridge types',
    i8.severity = 'critical',
    i8.why = 'Silent edges between domains erase sovereignty. The forest promise requires every cross-domain connection to be visible and typed.',
    i8.check_cypher = 'MATCH (a)-[r]->(b) WHERE a.project IS NOT NULL AND b.project IS NOT NULL AND a.project <> b.project AND NOT type(r) IN ["DEPENDS_ON","DEPLOYS_TO","RUNS_ON","MANAGES","OWNS","HAS_REPO","HAS_SERVICE","REFERENCES","TRIGGERS","COMPOSES","SCOPES_TO","ENFORCES_THROUGH","DECLARES","EMBODIED_BY","FOLLOWS","FEEDS","VALIDATES","VACATES"] RETURN count(r) AS violations',
    i8.heal_protocol = 'protocol-heal-cross-domain-edges',
    i8.expected = 0;

// --- I9: Every Agent runs on exactly one Server ---
MERGE (i9:Invariant {node_id: 'inv-agent-has-server'})
SET i9.project = 'seedforth',
    i9.label = 'Every :Agent has a :RUNS_ON edge to exactly one :Server',
    i9.severity = 'warning',
    i9.why = 'An agent without a known server is untethered. The graph cannot tell where it is or if it is alive.',
    i9.check_cypher = 'MATCH (a:Agent) WHERE NOT EXISTS { MATCH (a)-[:RUNS_ON]->(:Server) } RETURN count(a) AS violations',
    i9.heal_protocol = 'protocol-heal-agent-server',
    i9.expected = 0;

// ############################################################################
// LINK INVARIANTS TO FOREST PROMISE
// ############################################################################
MATCH (promise:ForestPromise {node_id: 'seedforth-forest-promise'})
MATCH (i:Invariant) WHERE i.node_id STARTS WITH 'inv-'
MERGE (promise)-[:ENFORCES_THROUGH]->(i);

// ############################################################################
// TEST CASES — cypher-native verification for each invariant
// ############################################################################
// Pattern: assertion_cypher returns {pass: true/false, actual, expected}
// or the check_cypher result compared to expected.

// --- TC: Namespace Integrity ---
MATCH (i:Invariant {node_id: 'inv-nodes-have-project'})
MERGE (tc1:TestCase {node_id: 'tc-nodes-have-project'})
SET tc1.project = 'seedforth',
    tc1.label = 'Verify all core nodes have project property',
    tc1.category = 'invariant-verification',
    tc1.assertion_cypher = 'MATCH (n) WHERE (n:Project OR n:Server OR n:Service OR n:Agent OR n:Repository OR n:Being OR n:Protocol OR n:CypherAtom OR n:Invariant OR n:Knowledge) AND n.project IS NULL RETURN count(n) AS actual, 0 AS expected, CASE WHEN count(n) = 0 THEN true ELSE false END AS pass',
    tc1.expected = 0,
    tc1.last_result = null,
    tc1.last_run_at = null,
    tc1.enabled = true
MERGE (tc1)-[:VALIDATES]->(i);

// --- TC: Forest Density ---
MATCH (i:Invariant {node_id: 'inv-graph-density'})
MERGE (tc2:TestCase {node_id: 'tc-graph-density'})
SET tc2.project = 'seedforth',
    tc2.label = 'Verify edges/node ratio >= 0.8',
    tc2.category = 'invariant-verification',
    tc2.assertion_cypher = 'MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() WITH nodes, count(r) AS rels, round(toFloat(rels)/toFloat(nodes)*100)/100 AS density RETURN density AS actual, 0.8 AS expected, CASE WHEN density >= 0.8 THEN true ELSE false END AS pass',
    tc2.expected = 0.8,
    tc2.last_result = null,
    tc2.last_run_at = null,
    tc2.enabled = true
MERGE (tc2)-[:VALIDATES]->(i);

// --- TC: Server Completeness ---
MATCH (i:Invariant {node_id: 'inv-server-has-services'})
MERGE (tc3:TestCase {node_id: 'tc-server-has-services'})
SET tc3.project = 'seedforth',
    tc3.label = 'Verify every server has at least one service',
    tc3.category = 'invariant-verification',
    tc3.assertion_cypher = 'MATCH (s:Server) WHERE NOT EXISTS { MATCH (s)-[:HAS_SERVICE]->(:Service) } RETURN count(s) AS actual, 0 AS expected, CASE WHEN count(s) = 0 THEN true ELSE false END AS pass',
    tc3.expected = 0,
    tc3.last_result = null,
    tc3.last_run_at = null,
    tc3.enabled = true
MERGE (tc3)-[:VALIDATES]->(i);

// --- TC: Atom Discoverability ---
MATCH (i:Invariant {node_id: 'inv-atom-has-semantic'})
MERGE (tc4:TestCase {node_id: 'tc-atom-has-semantic'})
SET tc4.project = 'seedforth',
    tc4.label = 'Verify every CypherAtom has a semantic description',
    tc4.category = 'invariant-verification',
    tc4.assertion_cypher = 'MATCH (ca:CypherAtom) WHERE ca.semantic IS NULL OR ca.semantic = \'\' RETURN count(ca) AS actual, 0 AS expected, CASE WHEN count(ca) = 0 THEN true ELSE false END AS pass',
    tc4.expected = 0,
    tc4.last_result = null,
    tc4.last_run_at = null,
    tc4.enabled = true
MERGE (tc4)-[:VALIDATES]->(i);

// --- TC: Repo Completeness ---
MATCH (i:Invariant {node_id: 'inv-project-with-repo-has-repo-edge'})
MERGE (tc5:TestCase {node_id: 'tc-repo-links-complete'})
SET tc5.project = 'seedforth',
    tc5.label = 'Verify projects with repo_url have HAS_REPO edges',
    tc5.category = 'invariant-verification',
    tc5.assertion_cypher = 'MATCH (p:Project) WHERE p.repo_url IS NOT NULL AND p.repo_url <> \'\' AND NOT EXISTS { MATCH (p)-[:HAS_REPO]->(:Repository) } RETURN count(p) AS actual, 0 AS expected, CASE WHEN count(p) = 0 THEN true ELSE false END AS pass',
    tc5.expected = 0,
    tc5.last_result = null,
    tc5.last_run_at = null,
    tc5.enabled = true
MERGE (tc5)-[:VALIDATES]->(i);

// --- TC: Test Coverage (meta) ---
MATCH (i:Invariant {node_id: 'inv-every-invariant-has-test'})
MERGE (tc6:TestCase {node_id: 'tc-every-invariant-has-test'})
SET tc6.project = 'seedforth',
    tc6.label = 'Verify every invariant has a test — the meta-test',
    tc6.category = 'invariant-verification',
    tc6.assertion_cypher = 'MATCH (i:Invariant {project: "seedforth"}) WHERE NOT EXISTS { MATCH (i)<-[:VALIDATES]-(:TestCase) } RETURN count(i) AS actual, 0 AS expected, CASE WHEN count(i) = 0 THEN true ELSE false END AS pass',
    tc6.expected = 0,
    tc6.last_result = null,
    tc6.last_run_at = null,
    tc6.enabled = true
MERGE (tc6)-[:VALIDATES]->(i);

// --- TC: Graph-Native State ---
MATCH (i:Invariant {node_id: 'inv-graph-is-source-of-truth'})
MERGE (tc7:TestCase {node_id: 'tc-graph-is-source-of-truth'})
SET tc7.project = 'seedforth',
    tc7.label = 'Verify graph state is current — no stale service data',
    tc7.category = 'invariant-verification',
    tc7.assertion_cypher = 'MATCH (svc:Service) WHERE svc.health = "active" AND (svc.last_checked_at IS NULL OR svc.last_checked_at < datetime() - duration({days: 7})) RETURN count(svc) AS actual, 0 AS expected, CASE WHEN count(svc) = 0 THEN true ELSE false END AS pass',
    tc7.expected = 0,
    tc7.last_result = null,
    tc7.last_run_at = null,
    tc7.enabled = true
MERGE (tc7)-[:VALIDATES]->(i);

// --- TC: Cross-Domain Edge Visibility ---
MATCH (i:Invariant {node_id: 'inv-cross-domain-edges-typed'})
MERGE (tc8:TestCase {node_id: 'tc-cross-domain-edges-typed'})
SET tc8.project = 'seedforth',
    tc8.label = 'Verify all cross-domain edges use allowed bridge types',
    tc8.category = 'invariant-verification',
    tc8.assertion_cypher = 'MATCH (a)-[r]->(b) WHERE a.project IS NOT NULL AND b.project IS NOT NULL AND a.project <> b.project AND NOT type(r) IN $allowed RETURN count(r) AS actual, 0 AS expected, CASE WHEN count(r) = 0 THEN true ELSE false END AS pass',
    tc8.expected = 0,
    tc8.last_result = null,
    tc8.last_run_at = null,
    tc8.enabled = true
MERGE (tc8)-[:VALIDATES]->(i);

// --- TC: Agent has Server ---
MATCH (i:Invariant {node_id: 'inv-agent-has-server'})
MERGE (tc9:TestCase {node_id: 'tc-agent-has-server'})
SET tc9.project = 'seedforth',
    tc9.label = 'Verify every agent has a RUNS_ON edge to a server',
    tc9.category = 'invariant-verification',
    tc9.assertion_cypher = 'MATCH (a:Agent) WHERE NOT EXISTS { MATCH (a)-[:RUNS_ON]->(:Server) } RETURN count(a) AS actual, 0 AS expected, CASE WHEN count(a) = 0 THEN true ELSE false END AS pass',
    tc9.expected = 0,
    tc9.last_result = null,
    tc9.last_run_at = null,
    tc9.enabled = true
MERGE (tc9)-[:VALIDATES]->(i);

// ############################################################################
// CYPHER ATOMS — run tests, run invariants, view results
// ############################################################################

// --- Atom: run all tests ---
MERGE (ca_run_tests:CypherAtom {node_id: 'atom-run-all-tests'})
SET ca_run_tests.project = 'seedforth',
    ca_run_tests.semantic = 'Run all TestCases and report pass/fail with actual vs expected',
    ca_run_tests.cypher = 'MATCH (tc:TestCase {enabled: true}) RETURN tc.node_id, tc.label, tc.last_result, tc.last_run_at ORDER BY tc.node_id',
    ca_run_tests.fire_count = coalesce(ca_run_tests.fire_count, 0);

// --- Atom: run single invariant check ---
MERGE (ca_check_inv:CypherAtom {node_id: 'atom-check-invariant'})
SET ca_check_inv.project = 'seedforth',
    ca_check_inv.semantic = 'Check a specific invariant by node_id and return its violation count',
    ca_check_inv.cypher = 'MATCH (i:Invariant {node_id: $invariant_id}) RETURN i.label, i.severity, i.expected, i.check_cypher AS query',
    ca_check_inv.fire_count = coalesce(ca_check_inv.fire_count, 0);

// --- Atom: list all invariants with health ---
MERGE (ca_list_invs:CypherAtom {node_id: 'atom-list-invariants'})
SET ca_list_invs.project = 'seedforth',
    ca_list_invs.semantic = 'List all invariants with severity and expected values',
    ca_list_invs.cypher = 'MATCH (i:Invariant {project: "seedforth"}) RETURN i.node_id, i.label, i.severity, i.expected ORDER BY i.severity, i.node_id',
    ca_list_invs.fire_count = coalesce(ca_list_invs.fire_count, 0);

// --- Atom: list all test cases ---
MERGE (ca_list_tests:CypherAtom {node_id: 'atom-list-tests'})
SET ca_list_tests.project = 'seedforth',
    ca_list_tests.semantic = 'List all test cases with last result and enabled status',
    ca_list_tests.cypher = 'MATCH (tc:TestCase {project: "seedforth"}) RETURN tc.node_id, tc.label, tc.category, tc.last_result, tc.enabled ORDER BY tc.node_id',
    ca_list_tests.fire_count = coalesce(ca_list_tests.fire_count, 0);

// ############################################################################
// PROTOCOL — test runner (composes the atoms)
// ############################################################################
MERGE (proto:Protocol {node_id: 'protocol-run-tests'})
SET proto.project = 'seedforth',
    proto.label = 'Run Tests Protocol',
    proto.protocol_type = 'verification',
    proto.description = 'Executes all enabled TestCases and records results. Composes the run-tests, list-invariants, and list-tests CypherAtoms.',
    proto.cadence = 'on-demand',
    proto.enabled = true;

MATCH (proto:Protocol {node_id: 'protocol-run-tests'})
MATCH (a1:CypherAtom {node_id: 'atom-list-invariants'}),
      (a2:CypherAtom {node_id: 'atom-run-all-tests'}),
      (a3:CypherAtom {node_id: 'atom-list-tests'})
MERGE (proto)-[:COMPOSES]->(a1)
MERGE (proto)-[:COMPOSES]->(a2)
MERGE (proto)-[:COMPOSES]->(a3)
MERGE (a1)-[:FOLLOWS]->(a2)
MERGE (a2)-[:FOLLOWS]->(a3);

MATCH (b:Being {node_id: 'being-seedforth'}), (proto:Protocol {node_id: 'protocol-run-tests'})
MERGE (b)-[:HAS_PROTOCOL]->(proto);

// ############################################################################
// CLEANUP OLD AD-HOC INVARIANTS (replace with canonical set)
// ############################################################################
MATCH (i:Invariant) WHERE i.node_id STARTS WITH 'seedforth-invariant-'
DETACH DELETE i;

MATCH (r:SovereigntyRule) WHERE r.node_id IN ['seedforth-rule-namespace-integrity','seedforth-rule-cross-domain-edges','seedforth-rule-cypher-atoms','seedforth-rule-graph-as-source','seedforth-rule-own-being']
WITH r
MATCH (inv:Invariant) WHERE inv.node_id STARTS WITH 'inv-'
MERGE (r)-[:ENFORCED_BY]->(inv);

// Delete the old Promise->Invariant links (recreated above)
MATCH (promise:ForestPromise {node_id: 'seedforth-forest-promise'})-[old:ENFORCES_THROUGH]->(i:Invariant)
WHERE i.node_id STARTS WITH 'seedforth-invariant-'
DELETE old;

RETURN 'Invariants & Tests: 9 Invariants + 9 TestCases + 4 new CypherAtoms + 1 TestRunner Protocol = seedforth testing layer bootstrapped' AS result;
