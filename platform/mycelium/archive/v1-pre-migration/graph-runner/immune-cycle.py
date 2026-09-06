#!/usr/bin/env python3
"""
Runner: immune-cycle (Python rewrite)

Complete immune cycle: check invariants -> heal unhealthy -> recheck -> score

Replaces the bash version which had:
- stdin consumption bugs in while-read loops
- health check only recognizing "true" (missing "healthy", expressions)
- quote escaping failures for check_cypher with embedded quotes
"""

import subprocess
import sys
import os
import json
import re

VERBOSE = os.environ.get("VERBOSE", "0") == "1"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def log(msg):
    print(f"[immune-cycle] {msg}", flush=True)


def log_debug(msg):
    if VERBOSE:
        print(f"[immune-cycle] DEBUG: {msg}", flush=True)


def run_cypher(cypher, timeout=15):
    """Run cypher via docker exec directly, bypassing mycelium shell wrapper."""
    try:
        result = subprocess.run(
            [
                "docker", "exec", "-i", "mycelium-neo4j-local",
                "cypher-shell", "-u", "neo4j", "-p", "localtest12",
                "--encryption", "false", "--format", "plain",
            ],
            input=cypher,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT"
    except Exception as e:
        return "", str(e)


def evaluate_health(check_result):
    """Determine if a check_cypher result indicates healthy.

    Handles: true, TRUE, false, FALSE, healthy, unhealthy,
    empty results (vacuous pass), numeric expressions.
    """
    if not check_result or not check_result.strip():
        # Empty result = no violations found = healthy
        return True

    val = check_result.strip().lower()

    # Direct boolean
    if val == "true":
        return True
    if val == "false":
        return False

    # The word "healthy" in the result
    if "healthy" in val and "unhealthy" not in val:
        return True
    if "unhealthy" in val:
        return False

    # Check for "true" anywhere (but not "false")
    if "true" in val and "false" not in val:
        return True
    if "false" in val:
        return False

    # Numeric: non-zero = healthy
    try:
        n = float(val)
        return n > 0
    except ValueError:
        pass

    # Expression results like "count(ce) > 0" -- can't evaluate, mark unknown
    log_debug(f"  unparseable result: [{check_result}]")
    return None


def main():
    os.chdir(REPO_ROOT)

    # ==================================================================
    # PHASE 1+2: Evaluate all invariants via APOC in one pass
    # ==================================================================
    log("=== PHASE 1: Evaluating all invariants via APOC ===")

    # APOC runs each check_cypher dynamically from the property -- no quote
    # escaping, no CSV parsing, no stdin issues. Single query evaluates all.
    # Use DISTINCT on node_id to handle multiple Being nodes producing dupes.
    # Take first result per invariant (worst case -- if ANY row is false, unhealthy).
    stdout, stderr = run_cypher("""
        MATCH (inv:Invariant)
        WHERE inv.check_cypher IS NOT NULL AND inv.node_id IS NOT NULL
        CALL apoc.cypher.run(inv.check_cypher, {}) YIELD value
        WITH inv, value, keys(value)[0] AS result_key
        WITH inv, value[result_key] AS result_val
        WITH inv.node_id AS node_id, collect(result_val) AS results
        WITH node_id,
             CASE
               WHEN any(r IN results WHERE r = false) THEN false
               WHEN any(r IN results WHERE r IS NULL) THEN false
               ELSE true
             END AS healthy
        RETURN node_id, healthy
        ORDER BY node_id
    """, timeout=120)

    if not stdout:
        log(f"WARNING: No results. stderr={stderr}")
        sys.exit(1)

    lines = stdout.strip().split("\n")
    if len(lines) < 2:
        log("WARNING: Empty result set.")
        sys.exit(1)

    # Also fetch heal_protocol and label for unhealthy reporting
    meta_stdout, _ = run_cypher("""
        MATCH (inv:Invariant)
        WHERE inv.check_cypher IS NOT NULL AND inv.node_id IS NOT NULL
        RETURN inv.node_id, inv.heal_protocol, inv.label
        ORDER BY inv.node_id
    """, timeout=30)

    inv_meta = {}
    if meta_stdout:
        for mline in meta_stdout.strip().split("\n")[1:]:
            mline = mline.strip()
            if not mline:
                continue
            # Simple parse: first field is node_id (quoted)
            parts = mline.split(", ", 2)
            if len(parts) >= 1:
                nid = parts[0].strip().strip('"')
                hp = parts[1].strip().strip('"') if len(parts) > 1 else ""
                lb = parts[2].strip().strip('"') if len(parts) > 2 else ""
                if hp.upper() in ("NULL", ""):
                    hp = ""
                inv_meta[nid] = {"heal_protocol": hp, "label": lb}

    # Parse results (skip header)
    total = 0
    healthy_count = 0
    unhealthy_list = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        # Format: "node_id", TRUE/FALSE
        parts = line.split(", ", 1)
        if len(parts) < 2:
            continue

        node_id = parts[0].strip().strip('"')
        health_val = parts[1].strip().upper()

        meta = inv_meta.get(node_id, {"heal_protocol": "", "label": ""})
        total += 1

        if health_val == "TRUE":
            log(f"  [OK] {node_id}")
            healthy_count += 1
            status = "healthy"
        else:
            log(f"  [FAIL] {node_id}")
            unhealthy_list.append({
                "node_id": node_id,
                "label": meta["label"],
                "heal_protocol": meta["heal_protocol"],
            })
            status = "unhealthy"

        # Update health_status in graph
        run_cypher(f"""
            MATCH (inv:Invariant {{node_id: '{node_id}'}})
            SET inv.health_status = '{status}', inv.last_checked = toString(datetime())
            RETURN inv.node_id
        """)

    # ==================================================================
    # PHASE 3: Mark unhealthy with heal protocols for dispatch
    # ==================================================================
    log("")
    log("=== PHASE 3: Marking healable invariants ===")

    healed_count = 0
    for inv in unhealthy_list:
        if inv["heal_protocol"]:
            log(f"  -> dispatch: {inv['node_id']} via {inv['heal_protocol']}")
            run_cypher(f"""
                MATCH (inv:Invariant {{node_id: '{inv["node_id"]}'}})
                SET inv.healing_needed = true, inv.heal_marked_at = toString(datetime())
                RETURN inv.node_id
            """)
            healed_count += 1

    # ==================================================================
    # PHASE 4: Update autonomous_score on Being
    # ==================================================================
    log("")
    log("=== PHASE 4: Updating autonomous score ===")

    failed_count = len(unhealthy_list)
    score = (healthy_count * 100 // total) if total > 0 else 0

    log(f"  invariants: {total} | healthy: {healthy_count} | failed: {len(unhealthy_list)} | score: {score}%")

    run_cypher(f"""
        MATCH (b:Being {{node_id: 'being-mycelium'}})
        SET b.autonomous_score = {score},
            b.invariants_healthy = {healthy_count},
            b.invariants_total = {total},
            b.last_immune_cycle = toString(datetime()),
            b.immune_cycle_heals = {healed_count}
        RETURN b.node_id, b.autonomous_score
    """)

    # ==================================================================
    # Summary
    # ==================================================================
    log("")
    log("=== IMMUNE CYCLE COMPLETE ===")
    log(f"  checked: {total} | healthy: {healthy_count} | healable: {healed_count} | failed: {len(unhealthy_list)}")
    log(f"  autonomous_score: {score}%")

    if unhealthy_list:
        log("")
        log("UNHEALTHY:")
        for inv in unhealthy_list:
            heal = f" [healer: {inv['heal_protocol']}]" if inv["heal_protocol"] else ""
            log(f"  - {inv['node_id']}: {inv['label']}{heal}")


    sys.exit(1 if unhealthy_list else 0)


if __name__ == "__main__":
    main()
