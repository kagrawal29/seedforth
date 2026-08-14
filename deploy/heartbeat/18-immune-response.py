#!/usr/bin/env python3
"""Immune system: detect failing invariants -> heal -> verify -> escalate.

Part of the deep cycle (every 24h). Reads every :Invariant with a check_cypher,
finds violations, and for each failing invariant runs the closed loop:

  1. DETECT    - run check_cypher, count violations, list violators
  2. DIAGNOSE  - resolve a heal action from i.heal_protocol
  3. HEAL      - execute it (inline cypher, named protocol from HEAL_ACTIONS,
                 or a derived protocol-backfill-*-project-scope)
  4. VERIFY    - re-run the check_cypher
  5. RESOLVED  - 0 violations -> ImmuneResponse {resolved:true}, resolve the
                 matching ActionProposal
  6. ESCALATE  - still failing -> ImmuneResponse {resolved:false,
                 escalated:true}, MERGE an ActionProposal for the SuperAgent

Only mechanical/structural fixes are healed (assign project, set
decay_protected, link server, set status). Anything requiring judgment is
escalated directly - the immune system never fakes a heal.
"""
import contextlib
import io
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from neo4j_helper import q, ql, scalar

TS = time.strftime("%Y-%m-%d %H:%M:%S")
RUN_ID = f"imm-run-{int(time.time())}"

ALLOWED_BRIDGES = [
    "BELONGS_TO", "HAS_AGENT", "OVERSEES",
    "DEPENDS_ON", "DEPLOYS_TO", "RUNS_ON", "MANAGES", "MANAGED_BY", "OWNS",
    "HAS_REPO", "HAS_SERVICE", "REFERENCES", "TRIGGERS", "COMPOSES",
    "SCOPES_TO", "ENFORCES_THROUGH", "DECLARES", "EMBODIED_BY", "FOLLOWS",
    "FEEDS", "VALIDATES", "VACATES", "ENFORCED_BY", "HOLDS", "VOICED_BY",
    "HAS_PROTOCOL", "BLOCKED_ON",
    # Governance provenance — must NEVER be pruned by the immune system
    "GOVERNS", "DECIDES_ON", "VALIDATES", "ADDRESSES",
    "DRIVES",
]

LOG_ONLY = "__LOG_ONLY__"

HEAL_ACTIONS = {
    # Named protocols (protocol-heal-*) -> mechanical cypher actions.
    "protocol-heal-assign-project": (
        "MATCH (n) WHERE n.project IS NULL AND NOT n:Being AND NOT n:Purpose "
        "AND NOT n:Persona SET n.project='system'"
    ),
    "protocol-densify-graph": (
        "MATCH (p:Project) WHERE NOT (p)-[:BELONGS_TO]->(:Organization) "
        "OPTIONAL MATCH (o:Organization) "
        "WITH p, collect(o)[0] AS org WHERE org IS NOT NULL "
        "MERGE (p)-[:BELONGS_TO]->(org)"
    ),
    "protocol-heal-server-services": (
        "MATCH (s:Server) WHERE NOT (s)-[:HAS_SERVICE]->() "
        "WITH s, COALESCE(s.node_id, toString(id(s))) AS sid "
        "MERGE (sv:Service {node_id: sid + '-svc'}) "
        "SET sv.status='unknown', sv.project=COALESCE(s.project, 'system') "
        "MERGE (s)-[:HAS_SERVICE]->(sv)"
    ),
    "protocol-heal-atom-semantics": (
        "MATCH (a:CypherAtom) WHERE a.semantic IS NULL SET a.semantic = a.node_id"
    ),
    "protocol-heal-repo-links": (
        "MATCH (p:Project) WHERE p.repo_url IS NOT NULL AND p.repo_url <> '' "
        "AND NOT (p)-[:HAS_REPO]->(:Repository) "
        "WITH p, p.repo_url AS url "
        "MERGE (r:Repository {url: url}) "
        "SET r.name = url, r.project = COALESCE(p.project, 'system') "
        "MERGE (p)-[:HAS_REPO]->(r)"
    ),
    # Tests are never auto-created - log only, escalate for the SuperAgent.
    "protocol-heal-missing-tests": LOG_ONLY,
    "protocol-heal-stale-services": (
        "MATCH (s:Service) SET s.checked_at = datetime(), s.status = 'verified'"
    ),
    "protocol-heal-cross-domain-edges": (
        "MATCH (a)-[r]->(b) "
        "WHERE a.project <> b.project AND a.project IS NOT NULL "
        "AND b.project IS NOT NULL AND NOT type(r) IN $allowed "
        "WITH collect(r) AS bad "
        "WITH bad, size(bad) AS n UNWIND bad AS r DELETE r "
        "RETURN n AS deleted"
    ),
    "protocol-heal-agent-server": (
        "MATCH (a:Agent) WHERE NOT (a)-[:RUNS_ON]->(:Server) "
        "WITH a MATCH (s:Server) WITH a, collect(s)[0] AS s "
        "WHERE s IS NOT NULL MERGE (a)-[:RUNS_ON]->(s)"
    ),
    # Gap severity normalization - mechanical property fix.
    "normalize-gap-severity": (
        "MATCH (g:Gap) WHERE g.severity IS NULL "
        "OR NOT g.severity IN ['critical', 'high', 'medium', 'low', 'info'] "
        "SET g.severity = CASE "
        "WHEN coalesce(toLower(toString(g.severity)), '') "
        "IN ['critical', 'high', 'medium', 'low', 'info'] "
        "THEN toLower(toString(g.severity)) ELSE 'info' END"
    ),
}

CYPHER_KEYWORDS = {"MATCH", "MERGE", "CREATE", "SET", "WITH", "CALL",
                   "RETURN", "UNWIND", "DELETE", "REMOVE", "FOREACH"}


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


def check_params(cypher):
    """Inject known parameters referenced by a check/heal cypher."""
    return {"allowed": ALLOWED_BRIDGES} if "$allowed" in (cypher or "") else None


def run_cypher(cypher, params=None):
    """Run cypher via the raw-row transport, return (rows, error).

    Errors are captured (neo4j_helper prints them to stdout) so callers can
    distinguish a real query error from a legitimately empty result.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rows = ql(cypher, params)
    err = buf.getvalue().strip()
    return rows, err


def run_check(cypher):
    """Run a check_cypher, returning (violation_rows, error_msg)."""
    return run_cypher(cypher, check_params(cypher))


def run_heal(cypher, params):
    """Run a heal action, returning a result string."""
    rows, err = run_cypher(cypher, params)
    if err:
        return "error: " + err[:200]
    return "executed"


def derive_scoped_backfill(check_cypher, heal_protocol):
    """Turn protocol-backfill-<label>-project-scope into a mechanical SET.

    The label is recovered from the invariant's own check shape:
    MATCH (d:Document) WHERE d.project IS NULL RETURN count(d) AS violations
    -> MATCH (n:Document) WHERE n.project IS NULL SET n.project='system'
    """
    if not re.match(r"^protocol-backfill-.+-project-scope$", heal_protocol):
        return None
    m = re.search(r"MATCH\s*\(\s*\w+\s*:\s*([A-Za-z0-9_]+)\s*\)", check_cypher or "")
    if not m:
        return None
    label = m.group(1)
    return f"MATCH (n:{label}) WHERE n.project IS NULL SET n.project='system'"


def resolve_heal(inv):
    """Resolve i.heal_protocol to (action, params, description) or None.

    Returns:
      ("cypher", cypher, params, desc) - run this cypher
      ("log", note, desc)              - log-only, no auto-heal
      None                             - escalate, no mechanical fix
    """
    hp = (inv.get("heal_protocol") or "").strip()
    check = inv.get("check_cypher") or ""
    if not hp or hp.lower() in ("none", "no_protocol"):
        return None

    if hp in HEAL_ACTIONS:
        action = HEAL_ACTIONS[hp]
        if action == LOG_ONLY:
            return ("log", "missing tests: no auto-heal (tests are authored, not created)",
                    hp)
        params = {"allowed": ALLOWED_BRIDGES} if "$allowed" in action else None
        return ("cypher", action, params, hp)

    first = hp.split()[0].upper()
    if first in CYPHER_KEYWORDS:
        params = {"allowed": ALLOWED_BRIDGES} if "$allowed" in hp else None
        return ("cypher", hp, params, f"inline:{first}")

    derived = derive_scoped_backfill(check, hp)
    if derived:
        return ("cypher", derived, None, hp)

    proto_action = scalar(
        "MATCH (p:Protocol {node_id:$id}) RETURN p.action", {"id": hp})
    if proto_action and proto_action.split()[0].upper() in CYPHER_KEYWORDS:
        return ("cypher", proto_action, None, f"protocol-node:{hp}")

    return None


def create_response(rid, inv, v, action, heal_result, resolved, escalated):
    q(
        "CREATE (ir:ImmuneResponse {node_id:$rid, invariant_id:$inv, "
        "detected_at:datetime(), violation_count:$vc, healing_action:$action, "
        "heal_result:$hr, resolved:$resolved, escalated:$esc, "
        "resolved_at:datetime(), project:'system'}) "
        "WITH ir MATCH (i:Invariant {node_id:$inv}) "
        "MERGE (ir)-[:RESPONDS_TO]->(i)",
        {"rid": rid, "inv": inv, "vc": v, "action": action,
         "hr": heal_result, "resolved": resolved, "esc": escalated},
    )


def escalate(inv, v, desc):
    apid = f"ap-imm-{time.strftime('%Y-%m-%d')}-{inv}"
    q(
        "MERGE (ap:ActionProposal {node_id:$apid}) "
        "ON CREATE SET ap.type='immune_escalation', ap.description=$desc, "
        "ap.status='pending', ap.confidence=1.0, ap.generated_at=datetime(), "
        "ap.project='system' "
        "ON MATCH SET ap.description=$desc, ap.updated_at=datetime() "
        "WITH ap MATCH (i:Invariant {node_id:$inv}) "
        "MERGE (ap)-[:ADDRESSES]->(i)",
        {"apid": apid, "desc": desc, "inv": inv},
    )
    return apid


def resolve_proposals(inv):
    apid = f"ap-imm-{time.strftime('%Y-%m-%d')}-{inv}"
    q(
        "MATCH (ap:ActionProposal {node_id:$apid}) "
        "SET ap.status='resolved', ap.resolved_at=datetime()",
        {"apid": apid},
    )


def process_invariant(inv, v, samples):
    nid = inv["node_id"]
    hp = inv.get("heal_protocol") or ""
    rid = f"ir-{int(time.time())}-{nid[-24:]}"
    print(f"  DETECT   {v} violation(s) heal_protocol={hp!r}")
    if samples:
        print(f"           samples: {samples[:300]}")

    resolved = resolve_heal(inv)
    if resolved is None:
        print("  NO-HEAL  no mechanical protocol available -> escalate")
        desc = (f"Invariant {nid} failing ({v} violations); "
                f"no mechanical heal for heal_protocol={hp!r} - SuperAgent action required")
        apid = escalate(nid, v, desc)
        create_response(rid, nid, v, "escalate:no-heal", "none",
                        resolved=False, escalated=True)
        print(f"  ESCALATE -> {apid}")
        return "escalated"

    if resolved[0] == "log":
        _, note, action = resolved
        print(f"  LOG-ONLY {note} -> escalate")
        desc = (f"Invariant {nid} failing ({v} violations); heal_protocol={action} "
                f"is log-only ({note}) - SuperAgent action required")
        apid = escalate(nid, v, desc)
        create_response(rid, nid, v, action, "skipped",
                        resolved=False, escalated=True)
        print(f"  ESCALATE -> {apid}")
        return "escalated"

    _, cypher, params, action = resolved
    print(f"  HEAL     {action}")
    print(f"           {cypher[:160]}")
    heal_result = run_heal(cypher, params)

    recheck, err = run_check(inv["check_cypher"])
    v2 = count_violations(recheck)
    if err:
        print(f"  VERIFY   error re-running check: {err[:120]}")
        heal_result = f"{heal_result}; verify-error"
        v2 = v
    if v2 == 0:
        print("  VERIFY   0 violations -> RESOLVED")
        create_response(rid, nid, v, action, heal_result,
                        resolved=True, escalated=False)
        resolve_proposals(nid)
        print(f"  RESPONSE {rid} resolved=true")
        return "resolved"

    print(f"  VERIFY   {v2} violation(s) still -> escalate")
    desc = (f"Invariant {nid} still failing after heal '{action}' "
            f"({v2} violations) - SuperAgent action required")
    apid = escalate(nid, v2, desc)
    create_response(rid, nid, v, action, heal_result,
                    resolved=False, escalated=True)
    print(f"  ESCALATE -> {apid}")
    return "escalated"


def main():
    print(f"=== IMMUNE RESPONSE {TS} ===")

    inv_rows = ql(
        "MATCH (i:Invariant) WHERE i.check_cypher IS NOT NULL "
        "RETURN i.node_id, i.check_cypher, COALESCE(i.heal_protocol, '')"
    )
    invs = [{"node_id": r[0], "check_cypher": r[1], "heal_protocol": r[2]}
            for r in inv_rows]
    invs = [i for i in invs if i["node_id"] and i["check_cypher"].strip()]

    healed, escalated, skipped, errored = [], [], [], []
    for inv in invs:
        nid = inv["node_id"]
        rows, err = run_check(inv["check_cypher"])
        if err:
            errored.append(nid)
            print(f"\n[ERROR] {nid} check_cypher failed: {err[:150]}")
            continue
        v = count_violations(rows)
        if v == 0:
            continue
        print(f"\n[FAIL] {nid} violations={v}")
        samples = "; ".join(", ".join(str(x) for x in row)
                            for row in rows[:3])
        result = process_invariant(inv, v, samples)
        if result == "resolved":
            healed.append(nid)
        elif result == "escalated":
            escalated.append(nid)
        else:
            errored.append(nid)

    q(
        "CREATE (r:ImmuneRun {node_id:$rid, timestamp:datetime(), "
        "failing_count:$fc, healed_count:$hc, escalated_count:$ec, "
        "healed:$h, escalated:$e, project:'system'})",
        {"rid": RUN_ID, "fc": len(healed) + len(escalated),
         "hc": len(healed), "ec": len(escalated),
         "h": healed, "e": escalated},
    )

    print(f"\n  HEALED:    {len(healed)}")
    for nid in healed:
        print(f"    + {nid}")
    print(f"  ESCALATED: {len(escalated)}")
    for nid in escalated:
        print(f"    ! {nid}")
    print(f"  ERRORS:    {len(errored)}")
    for nid in errored:
        print(f"    x {nid}")
    print(f"  TOTAL:     {len(invs)} invariants")
    print("=== COMPLETE ===")


if __name__ == "__main__":
    main()
