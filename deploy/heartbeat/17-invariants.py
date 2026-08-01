#!/usr/bin/env python3
"""Run all graph invariants + test cases and write results to the graph.

Part of the heartbeat. Every 30 min the system checks its own integrity:
- Runs each Invariant.check_cypher (rows returned = violations)
- Runs each TestCase.assertion_cypher (parses pass field)
- Writes an InvariantRun node with summary + per-invariant results
- Creates ActionProposal if any invariant is failing

Uses the fast HTTP API via neo4j_helper.
"""
import base64
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from neo4j_helper import q, ql, scalar

TS = time.strftime("%Y-%m-%d %H:%M:%S")
RUN_ID = f"inv-run-{int(time.time())}"

ALLOWED_BRIDGES = [
    "BELONGS_TO", "HAS_AGENT", "OVERSEES",
    "DEPENDS_ON", "DEPLOYS_TO", "RUNS_ON", "MANAGES", "MANAGED_BY", "OWNS",
    "HAS_REPO", "HAS_SERVICE", "REFERENCES", "TRIGGERS", "COMPOSES",
    "SCOPES_TO", "ENFORCES_THROUGH", "DECLARES", "EMBODIED_BY", "FOLLOWS",
    "FEEDS", "VALIDATES", "VACATES", "ENFORCED_BY", "HOLDS", "VOICED_BY",
    "HAS_PROTOCOL", "BLOCKED_ON",
]


def fetch_nodes(label):
    """Fetch invariant/testcase nodes via HTTP API."""
    rows = ql(
        f"MATCH (n:{label}) WHERE n.check_cypher IS NOT NULL "
        "RETURN n.node_id, n.label, n.check_cypher"
    ) if label == "Invariant" else ql(
        f"MATCH (n:{label}) WHERE n.assertion_cypher IS NOT NULL "
        "RETURN n.node_id, n.label, n.assertion_cypher"
    )
    result = []
    for r in rows:
        result.append({"node_id": r[0], "label": r[1], "cypher": r[2]})
    return result


def run_check(cypher, is_test=False):
    """Run a cypher, return (pass_bool, detail)."""
    try:
        rows = ql(cypher)
    except Exception as e:
        return False, f"ERROR: {e}"
    if is_test:
        # Test cases return actual/expected/pass
        if not rows:
            return False, "no rows"
        row = rows[0]
        if len(row) >= 3:
            return bool(row[2]), f"actual={row[0]} expected={row[1]}"
        if len(row) == 1:
            return bool(row[0]), f"actual={row[0]}"
        return False, f"unexpected shape: {row}"
    else:
        # Invariants: rows returned = violations. 0 rows = pass
        if not rows:
            return True, "0 violations"
        return False, f"{len(rows)} violation(s)"


def main():
    print(f"=== INVARIANT RUN {TS} ===")
    inv_results = []
    for inv in fetch_nodes("Invariant"):
        passed, detail = run_check(inv["cypher"], is_test=False)
        inv_results.append({**inv, "passed": passed, "detail": detail})
        print(f"  {'PASS' if passed else 'FAIL'} {inv['node_id']} {detail}")

    test_results = []
    for tc in fetch_nodes("TestCase"):
        passed, detail = run_check(tc["cypher"], is_test=True)
        test_results.append({**tc, "passed": passed, "detail": detail})
        print(f"  {'PASS' if passed else 'FAIL'} {tc['node_id']} {detail}")

    inv_pass = sum(1 for r in inv_results if r["passed"])
    inv_total = len(inv_results)
    test_pass = sum(1 for r in test_results if r["passed"])
    test_total = len(test_results)
    health = round(inv_pass / inv_total * 100, 1) if inv_total else 0
    failing = [r["node_id"] for r in inv_results if not r["passed"]]

    # Write InvariantRun node
    q(
        "CREATE (ir:InvariantRun {node_id:$rid, timestamp:datetime(), "
        "invariants_passed:$ip, invariants_total:$it, "
        "tests_passed:$tp, tests_total:$tt, health_score:$h, "
        "failing_invariants:$f, project:'system'})",
        {"rid": RUN_ID, "ip": inv_pass, "it": inv_total,
         "tp": test_pass, "tt": test_total, "h": health, "f": failing},
    )

    # Create ActionProposal if failing
    if failing:
        q(
            "MERGE (ap:ActionProposal {node_id:$ap_id}) "
            "ON CREATE SET ap.type='invariant_failure', "
            "ap.description=$desc, ap.status='pending', "
            "ap.confidence=1.0, ap.generated_at=datetime(), ap.project='system'",
            {"ap_id": f"ap-inv-{time.strftime('%Y-%m-%d')}",
             "desc": f"Invariants failing: {', '.join(failing)}"},
        )
        print(f"  ACTIONPROPOSAL: invariants failing ({failing})")

    print(f"\n  HEALTH: {health}% ({inv_pass}/{inv_total})")
    print(f"  TESTS: {test_pass}/{test_total}")
    print(f"=== COMPLETE ===")


if __name__ == "__main__":
    main()
