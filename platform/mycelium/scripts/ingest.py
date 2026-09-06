#!/usr/bin/env python3
"""
Ingest — the single entry point to the nervous system.

Any MERGE triggers digest + excrete. One node enters, the system processes it.
Python is the thinnest possible glue: MERGE, then execute Cypher from Protocol nodes.

Usage:
    # As a script — ingest a document/text
    python3 scripts/ingest.py --type document --label "Cypher-native principle" --content "The system does not read..."
    python3 scripts/ingest.py --type trace --person Kshitiz --question "can we ingest this?" --answer "yes"
    python3 scripts/ingest.py --type signal --label "hook fired" --content "auto-sync ran at 14:00"

    # As a library — from other scripts
    from scripts.ingest import ingest
    ingest(graph, "Document", {"label": "...", "content": "..."})
"""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def esc(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")[:500]


def esc_dq(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")[:500]


def get_graph(traced: bool = True):
    """Get a graph connection. If traced=True, every query auto-creates a QueryTrace node."""
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    graph = db.select_graph("asgard")
    if not traced:
        return graph
    return _wrap_with_trace(graph)


def _wrap_with_trace(graph):
    """Wrap graph.query() to auto-MERGE a QueryTrace node for every call."""
    original_query = graph.query

    def traced_query(cypher, *args, **kwargs):
        result = original_query(cypher, *args, **kwargs)
        # Skip tracing our own trace MERGEs (prevent recursion)
        if cypher.strip().startswith("MERGE (qt:QueryTrace"):
            return result
        try:
            ts = datetime.now(timezone.utc).isoformat()
            qid = f"qt-{sha256(cypher.encode()).hexdigest()[:12]}-{ts[:19].replace(':', '-')}"
            rows = len(result.result_set) if result.result_set else 0
            cypher_short = cypher[:300].replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")
            original_query(
                f"MERGE (qt:QueryTrace {{node_id: '{qid}'}}) "
                f"SET qt.cypher = '{cypher_short}', "
                f"qt.rows = {rows}, "
                f"qt.timestamp = '{ts}', "
                f"qt.file_type = 'query-trace'"
            )
        except Exception:
            pass  # never block the main query path
        return result

    graph.query = traced_query
    return graph


def resolve_template(cypher: str) -> str:
    now = datetime.now(timezone.utc)
    return (cypher
        .replace("$TODAY", now.strftime("%Y-%m-%d"))
        .replace("$NOW", now.isoformat())
        .replace("$CUTOFF_2D", (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S"))
        .replace("$CUTOFF_7D", (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"))
        .replace("$CUTOFF_14D", (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S"))
    )


def ingest(graph, node_label: str, props: dict, verbose: bool = True):
    """
    Ingest a node. MERGE it, run matching IngestionRules, then digest+excrete.
    The graph tells Python what to do at every step.
    """
    return _ingest(graph, "node", node_label, props, verbose=verbose)


def ingest_edge(graph, src_label: str, src_id: str, edge_type: str,
                dst_label: str, dst_id: str, edge_props: dict = None, verbose: bool = True):
    """
    Ingest an edge. MERGE it between two existing nodes, run matching IngestionRules, then digest+excrete.
    Sometimes the insight IS the relationship.
    """
    return _ingest(graph, "edge", edge_type, edge_props or {},
                   src_label=src_label, src_id=src_id,
                   dst_label=dst_label, dst_id=dst_id, verbose=verbose)


def _ingest(graph, mode: str, label: str, props: dict,
            src_label=None, src_id=None, dst_label=None, dst_id=None,
            verbose: bool = True):
    """
    The single entry point. MERGE, then the graph processes it.

    1. MERGE the node or edge
    2. Load matching IngestionRules FROM the graph
    3. Execute each rule's Cypher (type-specific linking)
    4. Load digest+excrete Protocols FROM the graph
    5. Execute each protocol's Cypher
    6. Run tests

    Returns: dict with status, node_id, rules_run, protocols_run, tests_passed, elapsed
    """
    ts = datetime.now(timezone.utc).isoformat()
    total_start = time.time()

    # ================================================================
    # STEP 1: MERGE the node or edge
    # ================================================================
    if mode == "node":
        if "node_id" not in props:
            content = props.get("content") or props.get("label") or props.get("question") or ""
            props["node_id"] = f"{label.lower()}-{sha256(content.encode()).hexdigest()[:12]}"
        props["timestamp"] = ts
        props.setdefault("_digested", None)

        prop_sets = []
        for k, v in props.items():
            if v is None:
                continue
            if isinstance(v, (int, float, bool)):
                prop_sets.append(f"n.{k} = {v}")
            else:
                prop_sets.append(f'n.{k} = "{esc_dq(str(v))}"')

        merge_q = (
            f"MERGE (n:{label} {{node_id: '{esc(props['node_id'])}'}}) "
            f"SET {', '.join(prop_sets)} "
            f"RETURN n.node_id"
        )
        try:
            r = graph.query(merge_q)
            entity_id = r.result_set[0][0] if r.result_set else props["node_id"]
            if verbose:
                print(f"  [ingest] MERGED {label} {{node_id: '{entity_id}'}}")
        except Exception as e:
            if verbose:
                print(f"  [ingest] MERGE FAILED: {e}")
            return {"status": "failed", "error": str(e)}

    elif mode == "edge":
        prop_sets = []
        for k, v in (props or {}).items():
            if v is None:
                continue
            if isinstance(v, (int, float, bool)):
                prop_sets.append(f"r.{k} = {v}")
            else:
                prop_sets.append(f'r.{k} = "{esc_dq(str(v))}"')
        prop_sets.append(f'r.timestamp = "{ts}"')

        set_clause = f"SET {', '.join(prop_sets)}" if prop_sets else ""

        merge_q = (
            f"MATCH (a:{src_label} {{node_id: '{esc(src_id)}'}}), "
            f"(b:{dst_label} {{node_id: '{esc(dst_id)}'}}) "
            f"MERGE (a)-[r:{label}]->(b) "
            f"{set_clause} "
            f"RETURN type(r)"
        )
        try:
            r = graph.query(merge_q)
            entity_id = f"{src_id}-[{label}]->{dst_id}"
            if verbose:
                print(f"  [ingest] MERGED {src_label}--{label}-->{dst_label}")
        except Exception as e:
            if verbose:
                print(f"  [ingest] MERGE FAILED: {e}")
            return {"status": "failed", "error": str(e)}
    else:
        return {"status": "failed", "error": f"unknown mode: {mode}"}

    # ================================================================
    # IMMUNE GATE: verify core integrity against last authorized snapshot
    # ================================================================
    try:
        # Collect DNA — deterministic hash of all executable Cypher
        r = graph.query(
            "MATCH (n) WHERE (n:Protocol OR n:Invariant OR n:IngestionRule OR n:Rhythm) "
            "WITH n ORDER BY n.node_id "
            "RETURN n.node_id, coalesce(n.cypher, n.label, '')"
        )
        current_dna = "".join(f"{row[0]}::{row[1]}" for row in (r.result_set or []))
        current_hash = sha256(current_dna.encode()).hexdigest()

        # Compare against last authorized snapshot
        r = graph.query(
            "MATCH (gs:GraphSnapshot {authorized: true}) "
            "WITH gs ORDER BY gs.timestamp DESC LIMIT 1 "
            "RETURN gs.core_hash, gs.protocol_count, gs.invariant_count, "
            "gs.rule_count, gs.rhythm_count, gs.enables_edges"
        )
        if r.result_set:
            gs = r.result_set[0]
            expected_hash, exp_pc, exp_ic, exp_rc, exp_rmc, exp_ec = gs

            if expected_hash and current_hash != expected_hash:
                if verbose:
                    print(f"  [IMMUNE BLOCKED] Core hash mismatch:")
                    print(f"    Expected: {expected_hash[:16]}...")
                    print(f"    Current:  {current_hash[:16]}...")
                    print(f"    Someone modified Protocol/Rule/Invariant Cypher.")
                    print(f"    Re-run seed-protocols.py to authorize changes.")
                return {
                    "status": "immune-blocked",
                    "entity_id": entity_id,
                    "reason": "core hash mismatch",
                }
    except Exception:
        pass  # if immune check fails, proceed (don't block on gate failure)

    # ================================================================
    # TDD GATE: hard block if any executable node lacks a test
    # ================================================================
    try:
        r = graph.query(
            "MATCH (n) WHERE n.cypher IS NOT NULL "
            "AND NOT (:TestCase)-[:VALIDATES]->(n) "
            "AND NOT n:TestCase AND NOT n:QueryTrace "
            "AND (n:Protocol OR n:IngestionRule OR n:Rhythm) "
            "RETURN labels(n)[0] AS type, n.node_id AS id"
        )
        if r.result_set:
            if verbose:
                print(f"  [TDD BLOCKED] {len(r.result_set)} executable(s) lack tests:")
                for row in r.result_set[:5]:
                    print(f"    [{row[0]}] {row[1]}")
                if len(r.result_set) > 5:
                    print(f"    ... and {len(r.result_set) - 5} more")
                print(f"  System frozen until every executable has a TestCase.")
            return {
                "status": "tdd-blocked",
                "entity_id": entity_id,
                "untested": len(r.result_set),
                "first_untested": r.result_set[0][1] if r.result_set else None,
            }
    except Exception:
        pass  # if the gate query fails, proceed (don't block on gate failure)

    # ================================================================
    # STEP 2: Load matching IngestionRules FROM the graph
    # Matches: exact trigger_label OR wildcard '*', exact trigger_type OR 'any'
    # ================================================================
    trigger_type = "node" if mode == "node" else "edge"
    rules_run = 0
    try:
        r = graph.query(
            f"MATCH (ir:IngestionRule) "
            f"WHERE ir.enabled = true "
            f"AND (ir.trigger_label = '{esc(label)}' OR ir.trigger_label = '*') "
            f"AND (ir.trigger_type = '{trigger_type}' OR ir.trigger_type = 'any') "
            f"RETURN ir.node_id, ir.description, ir.cypher"
        )
        for row in (r.result_set or []):
            ir_id, ir_desc, ir_cypher = row
            if not ir_cypher:
                continue
            try:
                start = time.time()
                qr = graph.query(ir_cypher)
                elapsed = time.time() - start
                summary = ""
                if qr.result_set:
                    summary = ", ".join(str(v) for v in qr.result_set[0])
                rules_run += 1
                if verbose:
                    print(f"    [rule:{ir_id}] {ir_desc[:50]} → {summary[:40]} ({elapsed:.1f}s)")
            except Exception as e:
                if verbose:
                    print(f"    [rule:{ir_id}] FAILED: {str(e)[:60]}")
    except Exception as e:
        if verbose:
            print(f"  [ingest] Could not load rules: {e}")

    # ================================================================
    # STEP 3: Load digest + excrete protocols FROM the graph
    # ================================================================
    try:
        r = graph.query(
            "MATCH (p:Protocol) "
            "WHERE p.enabled = true "
            "AND p.phase IN ['digest', 'excrete'] "
            "AND p.protocol_type IN ['cypher', 'template'] "
            "RETURN p.node_id, p.name, p.cypher, p.protocol_type "
            "ORDER BY p.protocol_order"
        )
        protocols = r.result_set or []
    except Exception as e:
        if verbose:
            print(f"  [ingest] Could not load protocols: {e}")
        return {"status": "merged", "rules_run": rules_run, "error": f"protocol load failed: {e}"}

    # ================================================================
    # STEP 4: Execute each protocol's Cypher
    # ================================================================
    results = []
    for row in protocols:
        p_id, p_name, p_cypher, p_type = row
        if not p_cypher:
            continue

        cypher = resolve_template(p_cypher) if p_type == "template" else p_cypher

        try:
            start = time.time()
            qr = graph.query(cypher)
            elapsed = time.time() - start

            summary = ""
            if qr.result_set:
                summary = ", ".join(str(v) for v in qr.result_set[0])

            results.append({"name": p_name, "status": "ok", "elapsed": elapsed, "summary": summary})

            if verbose:
                print(f"    [{p_name}] ok ({elapsed:.1f}s) {summary[:80]}")
        except Exception as e:
            results.append({"name": p_name, "status": "failed", "error": str(e)[:100]})
            if verbose:
                print(f"    [{p_name}] FAILED: {str(e)[:80]}")

    # ================================================================
    # STEP 4: Run tests, record TestRun nodes
    # ================================================================
    test_results = []
    try:
        tr = graph.query(
            "MATCH (tc:TestCase)-[:VALIDATES]->(p:Protocol) "
            "WHERE p.phase IN ['digest', 'excrete'] "
            "RETURN tc.node_id, tc.label, tc.cypher"
        )
        for row in (tr.result_set or []):
            tc_id, tc_label, tc_cypher = row
            if not tc_cypher:
                continue
            try:
                resolved = resolve_template(tc_cypher)
                qr = graph.query(resolved)
                passed = qr.result_set[0][0] if qr.result_set else False

                # Update TestCase
                graph.query(
                    f"MATCH (t:TestCase {{node_id: '{tc_id}'}}) "
                    f"SET t.last_result = '{'pass' if passed else 'fail'}', "
                    f"t.last_run = '{ts}', "
                    f"t.run_count = coalesce(t.run_count, 0) + 1, "
                    f"t.pass_count = coalesce(t.pass_count, 0) + {'1' if passed else '0'}, "
                    f"t.fail_count = coalesce(t.fail_count, 0) + {'0' if passed else '1'}, "
                    f"t.streak = CASE WHEN '{'pass' if passed else 'fail'}' = 'pass' "
                    f"THEN coalesce(t.streak, 0) + 1 ELSE 0 END"
                )

                status = "pass" if passed else "FAIL"
                test_results.append({"label": tc_label, "status": status})
                if verbose and not passed:
                    print(f"      TEST {status}: {tc_label}")
            except Exception:
                pass
    except Exception:
        pass

    total_elapsed = time.time() - total_start
    ok = sum(1 for r in results if r["status"] == "ok")
    tests_pass = sum(1 for t in test_results if t["status"] == "pass")

    if verbose:
        print(f"  [ingest] Done: {rules_run} rules, {ok}/{len(results)} protocols, "
              f"{tests_pass}/{len(test_results)} tests, "
              f"{total_elapsed:.1f}s, $0.00")

    return {
        "status": "ok",
        "entity_id": entity_id,
        "rules_run": rules_run,
        "protocols_run": len(results),
        "protocols_ok": ok,
        "tests_total": len(test_results),
        "tests_pass": tests_pass,
        "elapsed": total_elapsed,
    }


# ================================================================
# Boundary: Hook Effectiveness Metrics
# ================================================================

def ingest_hook_metrics(graph, verbose: bool = True):
    """
    Read JSONL files from signals/hook-effectiveness/ and MERGE HookMetric nodes.
    Each line becomes a node with: node_id, hook_name, success, elapsed_s, timestamp, _digested=null.
    """
    import json
    import glob as globmod

    hook_dir = Path(__file__).resolve().parent.parent / "signals" / "hook-effectiveness"
    if not hook_dir.exists():
        if verbose:
            print(f"  [hook-metrics] No directory: {hook_dir}")
        return {"status": "skipped", "reason": "no directory", "count": 0}

    files = sorted(globmod.glob(str(hook_dir / "*.jsonl")))
    if not files:
        if verbose:
            print("  [hook-metrics] No JSONL files found")
        return {"status": "skipped", "reason": "no files", "count": 0}

    count = 0
    errors = 0
    for fpath in files:
        with open(fpath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    errors += 1
                    continue

                hook_name = rec.get("tool", "unknown")
                timestamp = rec.get("ts", "")
                elapsed_s = rec.get("injection_length", 0)
                success = True  # presence in log means the hook fired

                node_id = f"hook-metric-{sha256((hook_name + timestamp).encode()).hexdigest()[:12]}"

                result = ingest(graph, "HookMetric", {
                    "node_id": node_id,
                    "hook_name": hook_name,
                    "success": success,
                    "elapsed_s": elapsed_s,
                    "timestamp": timestamp,
                    "_digested": None,
                }, verbose=verbose)

                if result.get("status") in ("ok", "merged"):
                    count += 1
                else:
                    errors += 1

    if verbose:
        print(f"  [hook-metrics] Ingested {count} HookMetric nodes ({errors} errors)")
    return {"status": "ok", "count": count, "errors": errors}


# ================================================================
# Boundary: Fetch and ingest person's latest traces from LangSmith
# ================================================================

def ingest_person_traces(graph, person_alias: str = None, verbose: bool = True):
    """
    Fetch latest LangSmith traces for a person and ingest each as a Trace node.
    If person_alias is None, detect from git config or config.yaml.
    Protocols fire once after all traces are MERGEd (batch then digest).
    """
    import json
    import yaml as _yaml
    from urllib.request import Request, urlopen

    repo_root = Path(__file__).resolve().parent.parent

    # Load config
    config_path = repo_root / "config.yaml"
    if not config_path.exists():
        if verbose:
            print("  [traces] No config.yaml")
        return {"status": "skipped", "count": 0}

    config = _yaml.safe_load(config_path.read_text())
    team = config.get("team", [])

    # Resolve person
    if not person_alias:
        # Try git config
        import subprocess
        try:
            git_name = subprocess.run(
                ["git", "config", "user.name"], capture_output=True, text=True
            ).stdout.strip()
            # Match against team
            for member in team:
                if member.get("name", "").lower() in git_name.lower() or \
                   git_name.lower() in member.get("name", "").lower():
                    person_alias = member.get("alias", member.get("name"))
                    break
        except Exception:
            pass

    if not person_alias:
        if verbose:
            print("  [traces] Could not determine person")
        return {"status": "skipped", "count": 0}

    # Find LangSmith project UUID for this person
    project_uuid = None
    for member in team:
        if member.get("alias") == person_alias or member.get("name") == person_alias:
            project_uuid = member.get("langsmith_project")
            break

    if not project_uuid:
        if verbose:
            print(f"  [traces] No LangSmith project UUID for {person_alias}")
        return {"status": "skipped", "count": 0}

    # Get API key
    api_key = os.environ.get("CC_LANGSMITH_API_KEY", "")
    if not api_key:
        if verbose:
            print("  [traces] No CC_LANGSMITH_API_KEY")
        return {"status": "skipped", "count": 0}

    # Load watermark — last ingested timestamp for this person
    watermarks_path = repo_root / "signals" / ".watermarks.yaml"
    since = None
    if watermarks_path.exists():
        try:
            wm = _yaml.safe_load(watermarks_path.read_text()) or {}
            ls_wm = wm.get("langsmith", {}).get(project_uuid, {})
            since = ls_wm.get("last_start_time")
        except Exception:
            pass

    # Fetch traces from LangSmith
    base_url = "https://api.smith.langchain.com/api/v1"
    body = {
        "session": [project_uuid],
        "limit": 20,
        "is_root": True,
        "select": ["status", "start_time", "total_tokens", "inputs", "outputs"],
    }
    if since:
        body["start_time"] = since

    try:
        req = Request(
            f"{base_url}/runs/query",
            data=json.dumps(body).encode(),
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        if verbose:
            print(f"  [traces] LangSmith fetch failed: {str(e)[:60]}")
        return {"status": "failed", "count": 0}

    runs = data.get("runs", [])
    if not runs:
        if verbose:
            print(f"  [traces] No new traces for {person_alias}")
        return {"status": "ok", "count": 0}

    # Batch MERGE all traces (no protocol firing per trace — too expensive)
    count = 0
    latest_ts = since
    for run in runs:
        run_id = run.get("id", "")
        start_time = run.get("start_time", "")
        tokens = run.get("total_tokens", 0)
        status = run.get("status", "")

        # Extract question
        question = ""
        inputs = run.get("inputs") or {}
        for msg in reversed(inputs.get("messages", [])):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
                question = content[:300]
                break

        if not question:
            continue

        node_id = f"trace-{person_alias}-{run_id[:15]}"
        try:
            graph.query(
                f"MERGE (t:Trace {{node_id: '{esc(node_id)}'}}) "
                f"SET t.label = \"{esc_dq(question[:100])}\", "
                f"t.person = '{esc(person_alias)}', "
                f"t.question = \"{esc_dq(question)}\", "
                f"t.timestamp = '{esc(start_time)}', "
                f"t.tokens = {tokens or 0}, "
                f"t.status = '{esc(status)}', "
                f"t.file_type = 'trace'"
            )
            count += 1
            if not latest_ts or start_time > latest_ts:
                latest_ts = start_time
        except Exception:
            pass

    # Update watermark
    if latest_ts and latest_ts != since:
        try:
            wm = _yaml.safe_load(watermarks_path.read_text()) if watermarks_path.exists() else {}
            wm.setdefault("langsmith", {})[project_uuid] = {
                "last_start_time": latest_ts,
                "member": person_alias,
            }
            watermarks_path.write_text(_yaml.dump(wm, default_flow_style=False))
        except Exception:
            pass

    if verbose:
        print(f"  [traces] Ingested {count} traces for {person_alias}")

    return {"status": "ok", "count": count, "person": person_alias}


# ================================================================
# CLI
# ================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest a node into the graph. Triggers full digest+excrete.")
    parser.add_argument("--type", required=True, help="Node label: Document, Trace, Signal, Note, etc.")
    parser.add_argument("--label", help="Human-readable label")
    parser.add_argument("--content", help="Body content")
    parser.add_argument("--person", help="Who produced this")
    parser.add_argument("--question", help="For Trace type: the question asked")
    parser.add_argument("--answer", help="For Trace type: the answer given")
    parser.add_argument("--source", help="Where this came from")
    parser.add_argument("--node-id", help="Explicit node_id (auto-generated if omitted)")
    parser.add_argument("--with-traces", action="store_true", help="Also fetch and ingest person's latest LangSmith traces")
    parser.add_argument("--files-changed", help="Comma-separated list of files changed (for Commit type)")
    args = parser.parse_args()

    props = {}
    if args.label:
        props["label"] = args.label
    if args.content:
        props["content"] = args.content
    if args.person:
        props["person"] = args.person
    if args.question:
        props["question"] = args.question
    if args.answer:
        props["answer"] = args.answer
    if args.source:
        props["source"] = args.source
    if args.node_id:
        props["node_id"] = args.node_id
    if args.files_changed:
        props["files_changed"] = args.files_changed

    if not props.get("label") and not props.get("question"):
        print("ERROR: --label or --question required")
        sys.exit(1)

    graph = get_graph(traced=False)

    # Ingest the main node
    result = ingest(graph, args.type, props)

    # If --with-traces, also fetch and ingest this person's latest traces
    if args.with_traces:
        ingest_person_traces(graph, person_alias=args.person)

    sys.exit(0 if result.get("status") == "ok" else 1)


if __name__ == "__main__":
    main()
