#!/usr/bin/env python3
"""
breathe.py — Tiered breath for the graph.

Three cadences, one loop:
  HOT  (100ms): reflex — update Being heartbeat, run hot protocols
  WARM   (5s): digestion — wire new signals, run priority tests
  COOL  (60s): deep — full protocols, tests, invariants, DNA, external polls

The graph decides what tier each Protocol/TestCase/Invariant runs in
via its `cadence` property. This loop is pure muscle.

    python3 scripts/breathe.py           # breathe until killed
    python3 scripts/breathe.py --once    # one cycle of all tiers
"""

import hashlib
import json
import os
import sys
import time
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))

_graph = None


def graph():
    global _graph
    if _graph is None:
        from falkordb import FalkorDB
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        _graph = db.select_graph("asgard")
    return _graph


def now():
    return datetime.now(timezone.utc).isoformat()


def now_ms():
    return int(time.time() * 1000)


def esc(s):
    return str(s).replace("\\", "\\\\").replace("'", "\\'")[:3000]


def resolve(cypher):
    n = datetime.now(timezone.utc)
    return (
        cypher
        .replace("$TODAY", date.today().isoformat())
        .replace("$NOW", n.isoformat())
        .replace("$CUTOFF_2D", (n - timedelta(days=2)).isoformat())
        .replace("$CUTOFF_7D", (n - timedelta(days=7)).isoformat())
        .replace("$CUTOFF_14D", (n - timedelta(days=14)).isoformat())
    )


# ─── HOT breath (100ms) ──────────────────────────────────────────────────────
def breathe_hot():
    """Heartbeat. Runs every 100ms. Minimal work — just the pulse."""
    g = graph()

    # Bump heartbeat counter
    g.query(
        "MERGE (b:Being {node_id: 'being-mycelium'}) "
        "SET b.heartbeat_count = coalesce(b.heartbeat_count, 0) + 1, "
        "b.last_heartbeat = timestamp(), "
        "b.alive = true"
    )

    # Execute hot protocols
    protocols = g.query(
        "MATCH (p:Protocol) WHERE p.cadence = 'hot' "
        "AND (p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL) "
        "RETURN p.node_id, "
        "CASE WHEN p.cypher_execute IS NOT NULL THEN p.cypher_execute ELSE p.cypher END, "
        "p.protocol_type"
    )
    for row in protocols.result_set:
        pid, cypher, ptype = row
        if ptype == "template":
            cypher = resolve(cypher)
        try:
            g.query(cypher)
        except Exception:
            pass

    # Run hot invariants (single alive check)
    invs = g.query(
        "MATCH (inv:Invariant) WHERE inv.cadence = 'hot' "
        "AND inv.cypher_check IS NOT NULL "
        "RETURN inv.cypher_check"
    )
    for row in invs.result_set:
        try:
            g.query(row[0])
        except Exception:
            pass


# ─── WARM breath (5s) ────────────────────────────────────────────────────────
def breathe_warm():
    """Digestion. Runs every 5s. Wire new signals, run priority tests."""
    g = graph()
    t0 = time.time()

    # 1. Execute warm protocols
    proto_ok = proto_fail = 0
    protocols = g.query(
        "MATCH (p:Protocol) WHERE p.cadence = 'warm' "
        "AND (p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL) "
        "RETURN p.node_id, "
        "CASE WHEN p.cypher_execute IS NOT NULL THEN p.cypher_execute ELSE p.cypher END, "
        "p.protocol_type "
        "ORDER BY p.protocol_order"
    )
    for row in protocols.result_set:
        pid, cypher, ptype = row
        if ptype == "template":
            cypher = resolve(cypher)
        try:
            g.query(cypher)
            proto_ok += 1
        except Exception:
            proto_fail += 1

    # 2. Manual signal ingestion (fast, local disk)
    manual_count = ingest_manual(g)

    # 3. Warm tests (auth tests — small, critical)
    tests = g.query(
        "MATCH (tc:TestCase) WHERE tc.cadence = 'warm' "
        "AND (tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL) "
        "RETURN tc.node_id, "
        "CASE WHEN tc.assertion_query IS NOT NULL THEN tc.assertion_query ELSE tc.cypher END, "
        "coalesce(tc.expected, 'true')"
    )
    test_pass = test_fail = 0
    for row in tests.result_set:
        tid, cypher, expected = row
        try:
            r = g.query(cypher)
            actual = str(r.result_set[0][0]).lower() if r.result_set else "null"
            ok = actual == str(expected).lower()
            status = "pass" if ok else "fail"
            if ok:
                test_pass += 1
            else:
                test_fail += 1
            g.query(
                f"MATCH (tc:TestCase {{node_id: '{tid}'}}) "
                f"SET tc.last_result = '{status}', tc.last_run = timestamp()"
            )
        except Exception:
            test_fail += 1

    # 4. Warm invariants
    inv_ok = inv_total = 0
    invs = g.query(
        "MATCH (inv:Invariant) WHERE inv.cadence = 'warm' "
        "AND inv.cypher_check IS NOT NULL "
        "RETURN inv.node_id, inv.cypher_check"
    )
    for row in invs.result_set:
        iid, cypher = row
        inv_total += 1
        try:
            r = g.query(cypher)
            if r.result_set and r.result_set[0][0]:
                inv_ok += 1
        except Exception:
            pass

    elapsed = (time.time() - t0) * 1000
    return {
        "proto": f"{proto_ok}/{proto_ok + proto_fail}",
        "manual": manual_count,
        "tests": f"{test_pass}/{test_pass + test_fail}",
        "inv": f"{inv_ok}/{inv_total}",
        "ms": int(elapsed),
    }


# ─── COOL breath (60s) ───────────────────────────────────────────────────────
def breathe_cool():
    """Deep work. Runs every 60s. Full protocols, tests, invariants, DNA, external polls."""
    g = graph()
    t0 = time.time()

    # 1. External ingestion (rate-limited inside each function)
    ls_count = ingest_langsmith(g)
    gh_count = ingest_github(g)

    # 2. Execute cool protocols
    proto_ok = proto_fail = 0
    protocols = g.query(
        "MATCH (p:Protocol) WHERE p.cadence = 'cool' "
        "AND (p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL) "
        "RETURN p.node_id, "
        "CASE WHEN p.cypher_execute IS NOT NULL THEN p.cypher_execute ELSE p.cypher END, "
        "p.protocol_type "
        "ORDER BY p.protocol_order"
    )
    for row in protocols.result_set:
        pid, cypher, ptype = row
        if ptype == "template":
            cypher = resolve(cypher)
        try:
            g.query(cypher)
            proto_ok += 1
        except Exception:
            proto_fail += 1

    # 3. Cool tests (full suite)
    tests = g.query(
        "MATCH (tc:TestCase) WHERE tc.cadence = 'cool' "
        "AND (tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL) "
        "RETURN tc.node_id, "
        "CASE WHEN tc.assertion_query IS NOT NULL THEN tc.assertion_query ELSE tc.cypher END, "
        "coalesce(tc.expected, 'true')"
    )
    test_pass = test_fail = 0
    for row in tests.result_set:
        tid, cypher, expected = row
        try:
            r = g.query(cypher)
            actual = str(r.result_set[0][0]).lower() if r.result_set else "null"
            ok = actual == str(expected).lower()
            if ok:
                test_pass += 1
            else:
                test_fail += 1
            g.query(
                f"MATCH (tc:TestCase {{node_id: '{tid}'}}) "
                f"SET tc.last_result = '{'pass' if ok else 'fail'}', tc.last_run = timestamp()"
            )
        except Exception:
            test_fail += 1

    # 4. Cool invariants
    inv_ok = inv_total = 0
    invs = g.query(
        "MATCH (inv:Invariant) WHERE inv.cadence = 'cool' "
        "AND inv.cypher_check IS NOT NULL "
        "RETURN inv.node_id, inv.cypher_check"
    )
    for row in invs.result_set:
        iid, cypher = row
        inv_total += 1
        try:
            r = g.query(cypher)
            healthy = bool(r.result_set[0][0]) if r.result_set else False
            if healthy:
                inv_ok += 1
            g.query(
                f"MATCH (inv:Invariant {{node_id: '{iid}'}}) "
                f"SET inv.last_check = timestamp(), inv.last_healthy = {str(healthy).lower()}"
            )
        except Exception:
            pass

    # 5. DNA fingerprint (graph-native protocol if exists, else inline)
    r = g.query(
        "MATCH (p:Protocol {node_id: 'protocol-dna-fingerprint'}) RETURN p.cypher"
    )
    if r.result_set and r.result_set[0][0]:
        try:
            dr = g.query(r.result_set[0][0])
            if dr.result_set:
                row = dr.result_set[0]
                nodes, edges, tp, tt, dna_str = row[0], row[1], row[2], row[3], row[4]
                dna_hash = hashlib.sha256(dna_str.encode()).hexdigest()[:16]
                g.query(
                    f"MATCH (b:Being) SET b.dna_hash = '{dna_hash}', "
                    f"b.nodes = {nodes}, b.edges = {edges}, "
                    f"b.breath_count = coalesce(b.breath_count, 0) + 1, "
                    f"b.last_breath = timestamp()"
                )
        except Exception:
            pass

    elapsed = (time.time() - t0) * 1000
    return {
        "proto": f"{proto_ok}/{proto_ok + proto_fail}",
        "langsmith": ls_count,
        "github": gh_count,
        "tests": f"{test_pass}/{test_pass + test_fail}",
        "inv": f"{inv_ok}/{inv_total}",
        "ms": int(elapsed),
    }


# ─── INGESTION ───────────────────────────────────────────────────────────────
def ingest_manual(g):
    manual_dir = Path("/opt/maverick-meta/signals/manual")
    if not manual_dir.exists():
        manual_dir = Path(__file__).parent.parent / "signals" / "manual"
    if not manual_dir.exists():
        return 0
    count = 0
    for f in manual_dir.glob("*.md"):
        node_id = f"manual-{f.stem}"
        r = g.query(f"MATCH (n:ManualReport {{node_id: '{node_id}'}}) RETURN n")
        if r.result_set:
            continue
        content = esc(f.read_text().replace("\n", " "))
        g.query(
            f"MERGE (n:ManualReport {{node_id: '{node_id}'}}) "
            f"SET n.label = '{f.stem}', n.content = '{content}', "
            f"n.ingested_at = timestamp(), n.file_type = 'manual'"
        )
        count += 1
    return count


def ingest_langsmith(g):
    import urllib.request
    api_key = os.environ.get("CC_LANGSMITH_API_KEY", "")
    if not api_key:
        return 0

    team = {
        "Mycelium":  "ce70362b-3f8f-499b-b90c-a09f45bb000b",
        "Banyan":    "7d991519-fad6-4ede-bed1-9be395152ebe",
        "Sequoia":   "3473bc94-aa22-40ab-80bd-8588c9b00861",
        "Birch":     "f6b7d95f-ebda-48e6-81f9-9cfdbe28294c",
        "Oak":       "43265e84-4cad-452b-b2d2-65859553e043",
        "Willow":    "bf63ca28-62c6-4466-9c3b-97e6f6bbc32a",
    }
    count = 0
    for alias, uuid in team.items():
        src_id = f"signalsource-langsmith-{alias.lower()}"
        r = g.query(
            f"MATCH (ss:SignalSource {{node_id: '{src_id}'}}) RETURN ss.last_polled"
        )
        last_polled = (r.result_set[0][0] or 0) if r.result_set else 0
        if (now_ms() - last_polled) < 300_000:
            continue
        try:
            body = json.dumps({
                "session": [uuid], "limit": 3, "is_root": True,
                "select": ["id", "status", "start_time", "inputs"],
            }).encode()
            req = urllib.request.Request(
                "https://api.smith.langchain.com/api/v1/runs/query",
                data=body,
                headers={"x-api-key": api_key, "Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=10)
            data = json.loads(resp.read())
            for run in data.get("runs", []):
                run_id = run.get("id", "")
                if not run_id:
                    continue
                msgs = (run.get("inputs") or {}).get("messages", [])
                user_msg = ""
                for m in reversed(msgs):
                    if m.get("role") == "user":
                        c = m.get("content", "")
                        if isinstance(c, list):
                            c = " ".join(p.get("text", "") for p in c if p.get("type") == "text")
                        user_msg = c[:500]
                        break
                q = esc(user_msg)
                g.query(
                    f"MERGE (t:Trace {{node_id: 'trace-{run_id}'}}) "
                    f"SET t.label = '{esc(user_msg[:80])}', "
                    f"t.question = '{q}', t.person = '{alias}', "
                    f"t.timestamp = '{run.get('start_time', '')}', "
                    f"t.ingested_at = timestamp(), t.file_type = 'trace'"
                )
                count += 1
            g.query(
                f"MERGE (ss:SignalSource {{node_id: '{src_id}'}}) "
                f"SET ss.source_type = 'langsmith-trace', "
                f"ss.label = 'LangSmith traces for {alias}', "
                f"ss.last_polled = timestamp()"
            )
        except Exception:
            pass
    return count


def ingest_github(g):
    import subprocess
    src_id = "signalsource-github-polled"
    r = g.query(f"MATCH (ss:SignalSource {{node_id: '{src_id}'}}) RETURN ss.last_polled")
    last_polled = (r.result_set[0][0] or 0) if r.result_set else 0
    if (now_ms() - last_polled) < 120_000:
        return 0
    repos = [
        "Qubit-Capital/maverick-meta",
        "Qubit-Capital/VC-AI-Assoicate",
        "Qubit-Capital/maverick-market-research",
    ]
    count = 0
    for repo in repos:
        try:
            r_cmd = subprocess.run(
                ["gh", "api", f"repos/{repo}/commits?per_page=5"],
                capture_output=True, text=True, timeout=10,
            )
            if r_cmd.returncode != 0:
                continue
            commits = json.loads(r_cmd.stdout)
            for c in commits:
                sha = c.get("sha", "")
                if not sha:
                    continue
                msg = esc(c.get("commit", {}).get("message", "").split("\n")[0][:300])
                author = esc(c.get("commit", {}).get("author", {}).get("name", ""))
                date_str = c.get("commit", {}).get("author", {}).get("date", "")
                exist = g.query(f"MATCH (c:Commit {{node_id: 'commit-{sha}'}}) RETURN c")
                if exist.result_set:
                    continue
                g.query(
                    f"MERGE (c:Commit {{node_id: 'commit-{sha}'}}) "
                    f"SET c.label = '{msg}', c.sha = '{sha}', c.repo = '{repo}', "
                    f"c.author = '{author}', c.timestamp = '{date_str}', "
                    f"c.ingested_at = timestamp(), c.file_type = 'commit'"
                )
                count += 1
        except Exception:
            pass
    g.query(
        f"MERGE (ss:SignalSource {{node_id: '{src_id}'}}) "
        f"SET ss.source_type = 'github-commit', ss.last_polled = timestamp()"
    )
    return count


# ─── MAIN LOOP ───────────────────────────────────────────────────────────────
def main():
    once = "--once" in sys.argv

    # Read tier intervals from Being (graph controls cadence)
    g = graph()
    r = g.query(
        "MATCH (b:Being) "
        "RETURN coalesce(b.hot_interval_ms, 100), "
        "coalesce(b.warm_interval_ms, 5000), "
        "coalesce(b.cool_interval_ms, 60000)"
    )
    if r.result_set:
        hot_ms, warm_ms, cool_ms = r.result_set[0]
    else:
        hot_ms, warm_ms, cool_ms = 100, 5000, 60000

    print(
        f"[{now()}] breathing"
        f" | hot={hot_ms}ms warm={warm_ms}ms cool={cool_ms}ms"
    )

    if once:
        print(f"[{now()}] HOT:")
        breathe_hot()
        print(f"[{now()}] WARM: {breathe_warm()}")
        print(f"[{now()}] COOL: {breathe_cool()}")
        return

    last_hot = 0
    last_warm = 0
    last_cool = 0
    hot_count = 0

    while True:
        try:
            t_ms = now_ms()

            if t_ms - last_hot >= hot_ms:
                breathe_hot()
                last_hot = t_ms
                hot_count += 1

            if t_ms - last_warm >= warm_ms:
                w = breathe_warm()
                print(f"[{now()}] WARM #{hot_count}: {w}")
                last_warm = t_ms

            if t_ms - last_cool >= cool_ms:
                c = breathe_cool()
                print(f"[{now()}] COOL #{hot_count}: {c}")
                last_cool = t_ms

            # Sleep just enough to hit the next deadline
            next_deadline = min(
                last_hot + hot_ms,
                last_warm + warm_ms,
                last_cool + cool_ms,
            )
            sleep_ms = max(0, next_deadline - now_ms())
            time.sleep(min(sleep_ms, 50) / 1000.0)

        except KeyboardInterrupt:
            print(f"\n[{now()}] breath stopped")
            break
        except Exception as e:
            print(f"[{now()}] error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
