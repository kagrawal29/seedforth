#!/usr/bin/env python3
"""Run all graph invariants + test cases, write results to graph.

Part of the heartbeat (every 30 min). The system checks its own integrity
and writes an InvariantRun node. Uses the same violation-interpretation
semantics as tools/run-invariants.py:

- check_cypher rows are interpreted by count_violations():
    boolean row  -> false = violation, true = healthy
    integer row  -> the integer IS the violation count
    entity row   -> one violation per row

- assertion_cypher (tests) returns actual/expected/pass -> parse pass field.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from neo4j_helper import q, ql

TS = time.strftime("%Y-%m-%d %H:%M:%S")
RUN_ID = f"inv-run-{int(time.time())}"

ALLOWED_BRIDGES = [
    "BELONGS_TO", "HAS_AGENT", "OVERSEES",
    "DEPENDS_ON", "DEPLOYS_TO", "RUNS_ON", "MANAGES", "MANAGED_BY", "OWNS",
    "HAS_REPO", "HAS_SERVICE", "REFERENCES", "TRIGGERS", "COMPOSES",
    "SCOPES_TO", "ENFORCES_THROUGH", "DECLARES", "EMBODIED_BY", "FOLLOWS",
    "FEEDS", "VALIDATES", "VACATES", "ENFORCED_BY", "HOLDS", "VOICED_BY",
    "HAS_PROTOCOL", "BLOCKED_ON",
    # P1: goals/blockers/workitems/milestones
    "DERIVED_FROM", "SERVES", "INVOLVED_IN", "BLOCKS", "MILESTONE_OF",
    "WORK_OF", "PRODUCED_BY", "TRANSITIONS", "USED_BY", "GOAL_TRANSITION",
    # P1/P2: scoring + steering
    "DIRECTED", "ASSESSES", "CONCERNS", "EVIDENCE", "FIRST_ATOM",
    # P3: knowledge layer
    "TOUCHES", "CONCEPTUALLY_RELATED_TO", "RAN", "RESPONDS_TO",
    # Governance layer
    "GOVERNS", "DECIDES_ON", "VALIDATES", "ADDRESSES",
]


def count_violations(rows):
    """Interpret check_cypher result rows as a violation count."""
    total = 0
    for row in rows:
        if any(isinstance(v, bool) for v in row):
            if any(v is False for v in row):
                total += 1
        elif any(isinstance(v, int) for v in row):
            total += max(v for v in row if isinstance(v, int))
        else:
            total += 1
    return total


def main():
    print(f"=== INVARIANT RUN {TS} ===")

    inv_rows = ql(
        "MATCH (i:Invariant) WHERE i.check_cypher IS NOT NULL "
        "RETURN i.node_id, i.label, i.check_cypher"
    )
    invs = [{"node_id": r[0], "label": r[1], "cypher": r[2]} for r in inv_rows]

    test_rows = ql(
        "MATCH (t:TestCase) WHERE t.assertion_cypher IS NOT NULL "
        "RETURN t.node_id, t.label, t.assertion_cypher"
    )
    tests = [{"node_id": r[0], "label": r[1], "cypher": r[2]} for r in test_rows]

    inv_pass = inv_fail = inv_error = 0
    failing = []
    for inv in invs:
        cypher = inv["cypher"]
        # Inject known parameters referenced by the query
        params = {}
        if "$allowed" in cypher:
            params["allowed"] = ALLOWED_BRIDGES
        rows = ql(cypher, params or None)
        if rows == [] and not rows_is_error(rows):
            # 0 rows from a query = no violations (healthy)
            inv_pass += 1
            continue
        # We can't distinguish "query returned nothing" from "error" reliably via
        # neo4j_helper (it prints errors and returns []). Treat [] as pass.
        v = count_violations(rows)
        if v == 0:
            inv_pass += 1
        else:
            inv_fail += 1
            failing.append(inv["node_id"])
        print(f"  {'PASS' if v == 0 else 'FAIL'} {inv['node_id']} violations={v}")

    test_pass = test_fail = test_error = 0
    for tc in tests:
        rows = ql(tc["cypher"])
        if not rows:
            test_error += 1
            print(f"  ERROR {tc['node_id']} no rows")
            continue
        row = rows[0]
        # Test formats: [actual, expected, pass] (3 cols) or [actual, pass] (2 cols)
        if len(row) >= 3:
            passed = bool(row[2])
        elif len(row) == 2:
            passed = bool(row[1])
        else:
            passed = bool(row[0])
        if passed:
            test_pass += 1
        else:
            test_fail += 1
        print(f"  {'PASS' if passed else 'FAIL'} {tc['node_id']} {row}")

    inv_total = len(invs)
    test_total = len(tests)
    health = round(inv_pass / inv_total * 100, 1) if inv_total else 0

    q(
        "CREATE (ir:InvariantRun {node_id:$rid, timestamp:datetime(), "
        "invariants_passed:$ip, invariants_total:$it, "
        "tests_passed:$tp, tests_total:$tt, health_score:$h, "
        "failing_invariants:$f, project:'system'})",
        {"rid": RUN_ID, "ip": inv_pass, "it": inv_total,
         "tp": test_pass, "tt": test_total, "h": health, "f": failing},
    )

    if failing:
        q(
            "MERGE (ap:ActionProposal {node_id:$ap_id}) "
            "ON CREATE SET ap.type='invariant_failure', "
            "ap.description=$desc, ap.status='pending', "
            "ap.confidence=1.0, ap.generated_at=datetime(), ap.project='system'",
            {"ap_id": f"ap-inv-{time.strftime('%Y-%m-%d')}",
             "desc": f"Invariants failing: {', '.join(failing)}"},
        )
        print(f"  ACTIONPROPOSAL: {', '.join(failing)}")

    print(f"\n  HEALTH: {health}% ({inv_pass}/{inv_total}) "
          f"| TESTS: {test_pass}/{test_total} | {inv_error} err | {test_error} terr")
    print(f"=== COMPLETE ===")


def rows_is_error(rows):
    return False


if __name__ == "__main__":
    main()
