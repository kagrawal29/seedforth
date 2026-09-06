#!/usr/bin/env python3
"""
Heartbeat — the system's fast metabolism. Every 30 min during work hours. $0.

Three metabolic speeds:
  Real-time:  MCP coupling (every query) — 5 Cypher steps
  Heartbeat:  This script (every 30 min) — free stages + L7 + pulse sync
  Full breath: 14-stage pipeline (2x/day) — LLM stages + distribution

The heartbeat runs the FREE stages that don't need LLM:
  1. Graph Ingest — traces, commits, issues → FalkorDB
  2. Convergence — 3-signal check from Intent nodes
  3. Dream — sense, heal, propose, learn
  4. Integrity — decay, contradictions, effectiveness
  5. L7 Execute — act on ready proposals
  6. Sync to pulse — team sees latest

All Cypher + Python I/O. No LLM. No tokens. $0.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
PULSE_HOST = os.environ.get("PULSE_HOST", "5.78.206.137")
PULSE_PORT = int(os.environ.get("PULSE_PORT", "6380"))


def run_step(script, label, timeout=60):
    """Run a script and report result."""
    start = time.time()
    try:
        result = subprocess.run(
            ["python3", script],
            capture_output=True, text=True, timeout=timeout, cwd=REPO_ROOT
        )
        elapsed = time.time() - start
        # Print last 3 lines of output
        lines = result.stdout.strip().split("\n") if result.stdout else []
        for line in lines[-3:]:
            print(f"    {line}")
        return result.returncode == 0, elapsed
    except subprocess.TimeoutExpired:
        return False, time.time() - start
    except Exception as e:
        return False, time.time() - start


def sync_to_pulse():
    """Redis DUMP/RESTORE to pulse server."""
    try:
        import redis
        src = redis.Redis(host=FALKORDB_HOST, port=int(FALKORDB_PORT))
        dst = redis.Redis(host=PULSE_HOST, port=int(PULSE_PORT))

        for key in src.keys("*"):
            ttl = src.pttl(key)
            if ttl < 0: ttl = 0
            dump = src.dump(key)
            if dump:
                dst.delete(key)
                dst.restore(key, ttl, dump, replace=True)

        from falkordb import FalkorDB
        db = FalkorDB(host=PULSE_HOST, port=int(PULSE_PORT))
        g = db.select_graph("asgard")
        n = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
        print(f"    Pulse: {n} nodes")
        return True
    except Exception as e:
        print(f"    Pulse sync failed: {str(e)[:50]}")
        return False


def execute_proposals():
    """L7 — execute ready ActionProposals through graph."""
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=FALKORDB_HOST, port=int(FALKORDB_PORT))
        g = db.select_graph("asgard")

        ts = datetime.now(timezone.utc).isoformat()

        # Find proposals ready to execute — ONLY those with provenance
        # Invariant 1: proposals must have created_by (from dream round) and
        # a PROPOSED edge from a Dream node. Rejects injected proposals.
        r = g.query(
            "MATCH (d:Dream)-[:PROPOSED]->(ap:ActionProposal {status: 'proposed'})-[:RESOLVES_WITH]->(k:Knowledge) "
            "WHERE ap.created_by IS NOT NULL "
            "RETURN ap.node_id, ap.person, k.label, k.node_id"
        )

        executed = 0
        for row in (r.result_set or []):
            prop_id, person, k_label, k_id = row
            if not person or not k_id:
                continue

            # Route knowledge to person's context
            def esc(s):
                if s is None: return ""
                return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:300]

            g.query(
                f"MERGE (pc:PersonContext {{node_id: 'context-{esc(person)}'}}) "
                f"SET pc.person = '{esc(person)}', pc.file_type = 'person-context'"
            )
            g.query(
                f"MATCH (k:Knowledge {{node_id: '{esc(k_id)}'}}), "
                f"(pc:PersonContext {{node_id: 'context-{esc(person)}'}}) "
                f"MERGE (k)-[:ROUTED_TO {{routed_at: '{esc(ts)}', source: 'heartbeat'}}]->(pc)"
            )
            g.query(
                f"MATCH (ap:ActionProposal {{node_id: '{esc(prop_id)}'}}) "
                f"SET ap.status = 'executed', ap.executed_at = '{esc(ts)}'"
            )
            executed += 1

        if executed:
            print(f"    L7: {executed} proposals executed")
        return executed
    except Exception:
        return 0


def _load_team_config():
    """Load team members from config.yaml. Returns list of dicts with name, alias, langsmith_project."""
    cfg_path = REPO_ROOT / "config.yaml"
    if not cfg_path.exists():
        return []
    text = cfg_path.read_text()
    # Lightweight YAML parse — team section only. Avoids PyYAML dependency.
    members = []
    in_team = False
    current = {}
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == "team:":
            in_team = True
            continue
        if in_team and stripped.startswith("- name:"):
            if current:
                members.append(current)
            current = {"name": stripped.split(":", 1)[1].strip()}
        elif in_team and stripped.startswith("alias:"):
            current["alias"] = stripped.split(":", 1)[1].strip()
        elif in_team and stripped.startswith("langsmith_project:"):
            current["langsmith_project"] = stripped.split(":", 1)[1].strip()
        elif in_team and not stripped.startswith("-") and not stripped.startswith("alias") and not stripped.startswith("langsmith") and stripped and not stripped.startswith("#"):
            # Hit next top-level key — done with team section
            if current:
                members.append(current)
            break
    else:
        if current:
            members.append(current)
    return members


def _get_distributed_rules():
    """Read the last distribution manifest — what rules were pushed and when."""
    manifest = {}
    # Check synthesis manifest for last cycle timestamp
    manifest_path = REPO_ROOT / "signals" / ".synthesis-manifest.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text())
            manifest["last_cycle_ts"] = data.get("last_cycle_ts", "unknown")
        except (json.JSONDecodeError, KeyError):
            manifest["last_cycle_ts"] = "unknown"
    else:
        manifest["last_cycle_ts"] = "unknown"

    # List the actual shared rules that get pushed
    rules_dir = REPO_ROOT / "distribution" / "shared-rules"
    rules = []
    if rules_dir.is_dir():
        for f in sorted(rules_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                rules.append({"file": f.name, "mtime": mtime.isoformat()})
    manifest["rules"] = rules
    return manifest


def _query_rules_loaded(uuid, api_key, base_url):
    """Query LangSmith for a member's latest rules-loaded trace. Returns dict or None."""
    url = f"{base_url}/runs/query"
    body = json.dumps({
        "session": [uuid],
        "limit": 1,
        "is_root": True,
        "filter": 'eq(name, "rules-loaded")',
        "select": ["start_time", "inputs", "name"]
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            runs = data.get("runs", [])
            if runs:
                return runs[0]
            return None
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
        return None


def verify_distribution():
    """Check which team members received the latest distributed rules.

    Queries LangSmith for each member's latest rules-loaded trace, compares
    against the distribution manifest, and writes a delivery status file.
    Returns a summary string for heartbeat output.
    """
    api_key = os.environ.get("CC_LANGSMITH_API_KEY", "")
    if not api_key:
        return "skipped (no CC_LANGSMITH_API_KEY)"

    base_url = "https://api.smith.langchain.com/api/v1"
    members = _load_team_config()
    if not members:
        return "skipped (no team in config.yaml)"

    manifest = _get_distributed_rules()
    last_cycle = manifest.get("last_cycle_ts", "unknown")
    rules = manifest.get("rules", [])

    now = datetime.now(timezone.utc)
    stale_threshold_hours = 6
    results = []  # list of (name, alias, status, trace_time, detail)

    for member in members:
        name = member.get("name", "?")
        alias = member.get("alias", "?")
        uuid = member.get("langsmith_project", "")
        if not uuid:
            results.append((name, alias, "NO UUID", None, "no langsmith_project in config"))
            continue

        trace = _query_rules_loaded(uuid, api_key, base_url)
        if trace is None:
            results.append((name, alias, "NO DATA", None, "no rules-loaded trace found"))
            continue

        trace_time_str = trace.get("start_time", "")
        if not trace_time_str:
            results.append((name, alias, "NO DATA", None, "trace missing start_time"))
            continue

        # Parse ISO timestamp — handle various formats
        try:
            # Strip trailing Z and fractional timezone for simple parsing
            clean = trace_time_str.replace("Z", "+00:00")
            # Python 3.7+ fromisoformat handles most ISO formats
            trace_time = datetime.fromisoformat(clean)
            if trace_time.tzinfo is None:
                trace_time = trace_time.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            results.append((name, alias, "PARSE ERR", None, f"bad timestamp: {trace_time_str[:30]}"))
            continue

        age_hours = (now - trace_time).total_seconds() / 3600

        # Extract loaded rules from trace inputs if available
        loaded_rules = []
        inputs = trace.get("inputs") or {}
        messages = inputs.get("messages", [])
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
            # Look for rule file names in the content
            for rule in rules:
                if rule["file"].replace(".md", "") in content:
                    loaded_rules.append(rule["file"])

        if age_hours < stale_threshold_hours:
            status = "CURRENT"
        else:
            status = "STALE"

        detail = f"age={age_hours:.1f}h"
        if loaded_rules:
            detail += f", loaded={len(loaded_rules)}/{len(rules)} rules"

        results.append((name, alias, status, trace_time_str, detail))

    # MERGE DeliveryEvent nodes into graph
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=FALKORDB_HOST, port=int(FALKORDB_PORT))
        g = db.select_graph("asgard")
        ts_now = datetime.now(timezone.utc).isoformat()

        def esc(s):
            if s is None: return ""
            return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:300]

        for name, alias, status, trace_time, detail in results:
            # Count rules loaded from detail string (e.g. "loaded=3/5 rules")
            rules_loaded = 0
            if "loaded=" in (detail or ""):
                try:
                    rules_loaded = int(detail.split("loaded=")[1].split("/")[0])
                except (IndexError, ValueError):
                    pass
            node_id = f"delivery-{alias}-{today}"

            g.query(
                f"MERGE (d:DeliveryEvent {{node_id: '{esc(node_id)}'}}) "
                f"SET d.person = '{esc(alias)}', d.status = '{esc(status)}', "
                f"d.timestamp = '{esc(ts_now)}', d.rules_loaded = {rules_loaded}, "
                f"d._digested = null"
            )
    except Exception as e:
        print(f"    DeliveryEvent graph merge failed: {str(e)[:60]}")

    # Build summary counts
    current = sum(1 for r in results if r[2] == "CURRENT")
    stale = sum(1 for r in results if r[2] == "STALE")
    no_data = sum(1 for r in results if r[2] in ("NO DATA", "NO UUID", "PARSE ERR"))

    # Write delivery status file
    delivery_dir = REPO_ROOT / "signals" / "delivery"
    delivery_dir.mkdir(parents=True, exist_ok=True)
    delivery_path = delivery_dir / f"{today}.md"

    lines = [
        f"# Distribution Delivery Status — {today}",
        f"",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M UTC')} (heartbeat)",
        f"Last distribution cycle: {last_cycle}",
        f"Rules in manifest: {len(rules)}",
        f"",
        f"## Status",
        f"",
        f"| Member | Alias | Status | Last rules-loaded | Detail |",
        f"|--------|-------|--------|-------------------|--------|",
    ]
    for name, alias, status, trace_time, detail in results:
        t = trace_time[:19] if trace_time else "—"
        lines.append(f"| {name} | {alias} | {status} | {t} | {detail} |")

    lines.extend([
        f"",
        f"## Summary",
        f"",
        f"- Current (< {stale_threshold_hours}h): {current}",
        f"- Stale (> {stale_threshold_hours}h): {stale}",
        f"- No data: {no_data}",
    ])

    if rules:
        lines.extend([
            f"",
            f"## Distributed Rules",
            f"",
        ])
        for rule in rules:
            lines.append(f"- `{rule['file']}` (modified: {rule['mtime'][:19]})")

    lines.append("")
    delivery_path.write_text("\n".join(lines))

    summary = f"{current} current, {stale} stale, {no_data} no-data"
    return summary


def main():
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
    print(f"[heartbeat] {ts} — fast metabolism, $0")

    total_start = time.time()

    # ================================================================
    # PROTOCOL PIPELINE — reads structure from graph, executes Cypher
    # Replaces: ingest-to-graph, convergence-detect, dream-round,
    #           integrity-rules, self-test (all now Protocol nodes)
    # ================================================================
    print(f"  Protocol Pipeline:")
    ok, elapsed = run_step("scripts/pipeline.py", "protocol-pipeline", 600)
    if not ok:
        print(f"    Pipeline had failures — check Protocol nodes")

    # ================================================================
    # HEARTBEAT-ONLY FUNCTIONS (not yet migrated to protocols)
    # These remain as Python until they become Protocol/IngestionRule nodes
    # ================================================================

    # Hook metrics — ingest JSONL from hook executions
    print(f"  Hook Metrics:")
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from scripts.ingest import ingest_hook_metrics, get_graph
        graph = get_graph(traced=False)
        hm_result = ingest_hook_metrics(graph, verbose=False)
        print(f"    {hm_result.get('count', 0)} metrics ingested")
    except Exception as e:
        print(f"    Hook metrics failed: {str(e)[:60]}")

    # L7 Execute — act on ready ActionProposals
    print(f"  L7 Agency:")
    executed = execute_proposals()

    # Security invariants — the system's immune system
    print(f"  Invariants:")
    try:
        from scripts.lib.invariants import check_all, remediate, report
        violations = check_all()
        if violations:
            print(report(violations))
            remediated = remediate(violations)
            if remediated:
                print(f"    Auto-remediated: {remediated}")
            critical = [v for v in violations if v.get("severity") == "critical"]
            if critical:
                print(f"    *** {len(critical)} CRITICAL violations — see issue #49 ***")
        else:
            print(f"    All 5 invariants hold.")
    except Exception as e:
        print(f"    Invariant check failed: {str(e)[:60]}")

    # Distribution verification
    print(f"  Delivery Check:")
    try:
        summary = verify_distribution()
        print(f"    {summary}")
    except Exception as e:
        print(f"    Delivery check failed: {str(e)[:60]}")

    # Graph versioning — export state and commit to git
    print(f"  Graph Version:")
    try:
        ok_v, elapsed_v = run_step("scripts/graph-export-state.py", "graph-export", 60)
        if ok_v:
            import subprocess
            subprocess.run(
                ["git", "add", "graph-state.cypher"],
                cwd=REPO_ROOT, capture_output=True, timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", "graph-state: auto-snapshot"],
                cwd=REPO_ROOT, capture_output=True, timeout=10
            )
            print(f"    Committed graph-state.cypher")
    except Exception as e:
        print(f"    Graph version failed: {str(e)[:60]}")

    # Sync to pulse server
    print(f"  Pulse Sync:")
    sync_to_pulse()

    total_elapsed = time.time() - total_start
    print(f"\n[heartbeat] done in {total_elapsed:.0f}s. $0.")


if __name__ == "__main__":
    main()
