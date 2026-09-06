#!/usr/bin/env python3
"""
Self-Test Harness — the system verifies its own mechanisms work.

Reads TestCase nodes from the Asgard graph. Each TestCase carries:
  setup_cypher     — create test fixtures
  assertion_cypher — query to verify
  expected         — expected result (string comparison)
  teardown_cypher  — clean up fixtures

Writes a HealthCheck node with pass/fail summary after each run.
Cypher-native: the tests ARE graph queries. No Python logic for assertions
beyond string comparison of Cypher results.

Issue #51. Unblocks #54 (immune system).
"""

import json
import os
import sys
from datetime import datetime, timezone

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"


def connect():
    from falkordb import FalkorDB
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(GRAPH_NAME)


def fetch_tests(g):
    """Return all TestCase nodes as dicts."""
    r = g.query(
        "MATCH (tc:TestCase) "
        "RETURN tc.node_id, tc.setup_cypher, tc.assertion_cypher, "
        "tc.expected, tc.teardown_cypher"
    )
    tests = []
    for row in (r.result_set or []):
        tests.append({
            "node_id": row[0],
            "setup_cypher": row[1],
            "assertion_cypher": row[2],
            "expected": row[3],
            "teardown_cypher": row[4],
        })
    return tests


def run_one(g, tc):
    """Run a single test case. Returns (passed: bool, detail: str)."""
    node_id = tc["node_id"]

    # Setup
    if tc.get("setup_cypher"):
        try:
            g.query(tc["setup_cypher"])
        except Exception as e:
            return False, f"setup failed: {e}"

    # Assertion
    try:
        r = g.query(tc["assertion_cypher"])
        # Flatten result to a comparable string
        if r.result_set and len(r.result_set) > 0:
            actual = str(r.result_set[0][0])
        else:
            actual = ""
    except Exception as e:
        _teardown(g, tc)
        return False, f"assertion query failed: {e}"

    # Compare
    expected = str(tc.get("expected", ""))
    passed = actual == expected

    # Teardown (always)
    _teardown(g, tc)

    if passed:
        return True, "ok"
    else:
        return False, f"expected '{expected}', got '{actual}'"


def _teardown(g, tc):
    if tc.get("teardown_cypher"):
        try:
            g.query(tc["teardown_cypher"])
        except Exception:
            pass  # teardown failures logged but don't affect result


def write_health_check(g, results, ts):
    """Write a HealthCheck node summarizing the run."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    status = "green" if failed == 0 else "red"

    # Build failure details (truncated for node storage)
    failures = [
        f"{r['node_id']}: {r['detail'][:80]}"
        for r in results if not r["passed"]
    ]
    failure_text = "; ".join(failures)[:500].replace("'", "\\'")

    def esc(s):
        if s is None:
            return ""
        return str(s).replace("\\", "\\\\").replace("'", "\\'")

    g.query(
        f"MERGE (hc:HealthCheck {{node_id: 'healthcheck-selftest'}}) "
        f"SET hc.last_run = '{esc(ts)}', "
        f"hc.total = {total}, "
        f"hc.passed = {passed}, "
        f"hc.failed = {failed}, "
        f"hc.status = '{status}', "
        f"hc.failures = '{failure_text}'"
    )


def main():
    try:
        g = connect()
    except Exception as e:
        print(f"Self-test: cannot connect to FalkorDB — {e}")
        sys.exit(1)

    tests = fetch_tests(g)
    if not tests:
        print("Self-test: no TestCase nodes found")
        sys.exit(0)

    ts = datetime.now(timezone.utc).isoformat()
    results = []

    for tc in tests:
        passed, detail = run_one(g, tc)
        results.append({"node_id": tc["node_id"], "passed": passed, "detail": detail})
        mark = "PASS" if passed else "FAIL"
        print(f"  [{mark}] {tc['node_id']}: {detail}")

    # Write summary to graph
    try:
        write_health_check(g, results, ts)
    except Exception as e:
        print(f"  Warning: could not write HealthCheck node — {e}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    print(f"Self-test: {passed}/{total} passed, {failed} failed")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
