#!/usr/bin/env python3
"""Run all graph invariants and test cases. Reports pass/fail/coverage.

Each :Invariant has a `check_cypher` that returns violating rows. Zero rows
means healthy (PASS); any row means a violation (FAIL). Each :TestCase has an
`assertion_cypher` that returns a `pass` column (true/false). Results are
written back onto the graph nodes so the graph stays the source of truth.

Transport: Neo4j HTTP transaction API (stdlib urllib, no driver needed) for
speed - cypher-shell costs ~15s per invocation on this box (JVM startup + bolt
handshake), the HTTP endpoint answers in <1s with native JSON. Falls back to
`docker exec mycelium-neo4j cypher-shell` if the HTTP API is unreachable.

Usage: python3 run-invariants.py [--verbose]
"""
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request

NEO4J_PASS = "9aac5c811e6d4f4f64a00c65666f3528"
NEO4J_URL = "http://127.0.0.1:7474/db/neo4j/tx/commit"
VERBOSE = "--verbose" in sys.argv
TS = time.strftime("%Y-%m-%d %H:%M:%S")

ALLOWED_BRIDGES = [
    # Structural org/fleet edges (cross project-boundary by design)
    "BELONGS_TO", "HAS_AGENT", "OVERSEES",
    # Legacy + semantic bridge edges
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
PROVIDED_PARAMS = {"allowed": ALLOWED_BRIDGES}


def _http_cypher(cypher, params):
    body = json.dumps({"statements": [{
        "statement": cypher,
        "parameters": params or {},
        "resultDataContents": ["row"],
    }]}).encode()
    token = base64.b64encode(("neo4j:" + NEO4J_PASS).encode()).decode()
    req = urllib.request.Request(NEO4J_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Basic " + token,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode())
    if resp.get("errors"):
        return {"error": resp["errors"][0]["message"][:400]}
    if not resp.get("results"):
        return {"columns": [], "rows": []}
    res = resp["results"][0]
    return {
        "columns": res.get("columns", []),
        "rows": [d.get("row", []) for d in res.get("data", [])],
    }


def split_row(line):
    """Split a cypher-shell plain line into cells, respecting quoted strings."""
    parts = re.split(r", (?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line)
    return [p.strip() for p in parts]


def norm(v):
    """Normalize a cypher-shell plain cell to a native value."""
    v = v.strip()
    if v == "TRUE":
        return True
    if v == "FALSE":
        return False
    if v in ("NULL", "null"):
        return None
    if v.startswith('"') and v.endswith('"') and len(v) >= 2:
        v = v[1:-1]
    try:
        return int(v)
    except ValueError:
        return v


def _parse_plain(output):
    """Parse cypher-shell plain output into columns/rows of native values."""
    if not output or not output.strip():
        return {"columns": [], "rows": []}
    lines = output.strip().splitlines()
    columns = split_row(lines[0])
    rows = [[norm(v) for v in split_row(l)] for l in lines[1:]]
    return {"columns": columns, "rows": rows}


def _docker_cypher(cypher):
    r = subprocess.run(
        ["docker", "exec", "mycelium-neo4j", "cypher-shell",
         "-u", "neo4j", "-p", NEO4J_PASS, "--format", "plain", cypher],
        capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:400]}
    return _parse_plain(r.stdout)


def run_cypher(cypher, params=None):
    """Run Cypher, returning {'columns': [...], 'rows': [[...], ...]} or
    {'error': msg}. Injects known parameters referenced by the query."""
    params = {k: v for k, v in (params or {}).items()}
    for name in re.findall(r"\$(\w+)", cypher):
        if name in PROVIDED_PARAMS and name not in params:
            params[name] = PROVIDED_PARAMS[name]
    try:
        return _http_cypher(cypher, params)
    except Exception as e:
        if VERBOSE:
            print("  http api failed (%s); falling back to cypher-shell"
                  % str(e)[:80])
        return _docker_cypher(cypher)


def count_violations(rows):
    """Infer violation count from check_cypher result rows.

    Boolean row: false is a violation, true is not. Integer row: the integer
    is the violation count. Entity row (names/objects): one per row.
    """
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


def set_invariant_health(node_id, status):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(node_id)):
        return
    run_cypher(
        "MATCH (i:Invariant {node_id:'%s'}) "
        "SET i.health='%s', i.last_checked_at=datetime()" % (node_id, status)
    )


def set_test_result(node_id, result):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(node_id)):
        return
    run_cypher(
        "MATCH (t:TestCase {node_id:'%s'}) "
        "SET t.last_result='%s', t.last_checked_at=datetime()" % (node_id, result)
    )


def main():
    print("=" * 72)
    print("INVARIANT RUNNER  %s" % TS)
    print("=" * 72)

    res = run_cypher(
        "MATCH (i:Invariant) WHERE i.check_cypher IS NOT NULL "
        "RETURN i.node_id AS node_id, i.label AS label, i.check_cypher AS check_cypher, "
        "i.severity AS severity, i.category AS category, i.project AS project"
    )
    if "error" in res:
        print("FATAL: could not fetch invariants: %s" % res["error"])
        sys.exit(1)
    cols = res["columns"]
    invs = [dict(zip(cols, r)) for r in res["rows"]]

    tres = run_cypher(
        "MATCH (t:TestCase) WHERE t.assertion_cypher IS NOT NULL "
        "RETURN t.node_id AS node_id, t.label AS label, "
        "t.assertion_cypher AS assertion_cypher"
    )
    tests = []
    if "error" in tres:
        print("WARN: could not fetch test cases: %s" % tres["error"])
    else:
        tcols = tres["columns"]
        tests = [dict(zip(tcols, r)) for r in tres["rows"]]

    pres = run_cypher(
        "MATCH (t:TestCase)-[:VALIDATES]->(i:Invariant) "
        "RETURN i.node_id AS inv"
    )
    covered = set()
    if "error" not in pres:
        covered = set(r[0] for r in pres["rows"] if r)

    print("\n--- INVARIANTS (%d) ---" % len(invs))
    inv_pass = inv_fail = inv_error = 0
    for inv in invs:
        nid = inv["node_id"]
        label = inv.get("label") or nid
        res = run_cypher(inv["check_cypher"])
        if "error" in res:
            status = "ERROR"
            detail = res["error"]
            set_invariant_health(nid, "error")
            inv_error += 1
        else:
            count = count_violations(res["rows"])
            if count == 0:
                status = "PASS"
                set_invariant_health(nid, "healthy")
                inv_pass += 1
            else:
                status = "FAIL"
                set_invariant_health(nid, "violated")
                inv_fail += 1
            if VERBOSE and count:
                detail = "violations: " + "; ".join(
                    ", ".join(str(v) for v in r) for r in res["rows"][:5])
            else:
                detail = "%d violation(s)" % count if count else "0 violations"
        covered_mark = "[TESTED]" if nid in covered else "[UNTESTED]"
        print("  %-6s %s %s %s" % (status, covered_mark, nid, label))
        print("          %s" % detail)

    print("\n--- TEST CASES (%d) ---" % len(tests))
    tc_pass = tc_fail = tc_error = 0
    for tc in tests:
        nid = tc["node_id"]
        label = tc.get("label") or nid
        res = run_cypher(tc["assertion_cypher"])
        if "error" in res:
            status = "ERROR"
            detail = res["error"]
            set_test_result(nid, "ERROR")
            tc_error += 1
        else:
            detail = ""
            if res["rows"]:
                d = dict(zip(res["columns"], res["rows"][0]))
                if d.get("pass") is True:
                    status = "PASS"
                    tc_pass += 1
                else:
                    status = "FAIL"
                    tc_fail += 1
                detail = "actual=%s expected=%s" % (d.get("actual", "?"),
                                                    d.get("expected", "?"))
            else:
                status = "ERROR"
                tc_error += 1
                detail = "assertion returned no rows (cannot evaluate pass)"
            set_test_result(nid, status)
        print("  %-6s %s %s" % (status, nid, label))
        if VERBOSE and detail:
            print("          %s" % detail)

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print("  Invariants: %d total, %d PASS, %d FAIL, %d ERROR"
          % (len(invs), inv_pass, inv_fail, inv_error))
    health = (100.0 * inv_pass / len(invs)) if invs else 0.0
    print("  Health score: %.1f%%" % health)
    if tests:
        print("  Test cases: %d total, %d PASS, %d FAIL, %d ERROR"
              % (len(tests), tc_pass, tc_fail, tc_error))
    coverage = (100.0 * len(covered) / len(invs)) if invs else 0.0
    print("  Coverage: %d/%d invariants have a test case (%.1f%%)"
          % (len(covered), len(invs), coverage))
    untested = [i["node_id"] for i in invs if i["node_id"] not in covered]
    if untested and VERBOSE:
        print("  Untested invariants: %s" % ", ".join(untested))
    print("=" * 72)


if __name__ == "__main__":
    main()
