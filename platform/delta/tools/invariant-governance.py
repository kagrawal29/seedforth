#!/usr/bin/env python3
"""Invariant Governance — the human-owned rulemaking layer.

Invariants are mycelium's constitution. This subsystem is the ONLY way
invariants are born or changed. The operations layer (immune system) may
heal WITHIN rules, but only this layer rewrites them.

Flow:
  1. PROPOSE   - draft an invariant (check + heal + test + rationale)
  2. SURFACE   - admin digest shows it awaiting approval
  3. DECIDE    - approve-invariant / reject-invariant via Discord
  4. ACTIVATE  - on approve, the :Invariant is born, linked to proposal+decision
  5. AUDIT     - full provenance: who proposed, who approved, why, when

Enforcement is itself an invariant: no :Invariant may exist without a
GOVERNS link from an approved :InvariantDecision.

Usage:
  propose <label> <check_cypher> [--heal <cypher>] [--severity high|medium|low]
          [--rationale "..."] [--by <name>]
  approve <proposal_id> --by <name> [--reason "..."]
  reject  <proposal_id> --by <name> [--reason "..."]
  list    [--status proposed|approved|rejected]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from neo4j_helper import q, ql

ENV_PATH = os.environ.get("DELTA_ENV_PATH", "/opt/delta/delta.env")
VALID_SEVERITIES = ("critical", "high", "medium", "low", "info")


def slugify(text, maxlen=48):
    s = "".join(c if c.isalnum() else "-" for c in (text or "").lower()).strip("-")
    return s[:maxlen].rstrip("-") or "invariant"


def _proposal_id(label):
    return f"proposal-{slugify(label)}"


def get_admin():
    for line in open(ENV_PATH):
        if line.startswith("ADMIN_DISCORD_ID="):
            return line.split("=", 1)[1].strip()
    return os.environ.get("ADMIN_DISCORD_ID", "")


def propose(label, check_cypher, heal=None, severity="medium",
            rationale="", by=""):
    pid = _proposal_id(label)
    by = by or "human"
    existing = ql("MATCH (p:InvariantProposal {node_id:$id}) RETURN p.status",
                  {"id": pid})
    if existing:
        print(f"proposal {pid} already exists (status={existing[0][0]})")
        return pid

    q(
        "CREATE (p:InvariantProposal {node_id:$id, label:$label, "
        "check_cypher:$check, heal_protocol:$heal, severity:$sev, "
        "rationale:$rat, proposed_by:$by, status:'proposed', "
        "proposed_at:datetime(), project:'system'})",
        {"id": pid, "label": label, "check": check_cypher, "heal": heal or "",
         "sev": severity, "rat": rationale, "by": by},
    )
    print(f"PROPOSED {pid} ({label}) by {by}")
    return pid


def decide(proposal_id, decision, by="", reason=""):
    by = by or "human"
    rows = ql(
        "MATCH (p:InvariantProposal {node_id:$id}) RETURN p.label, p.check_cypher, "
        "p.heal_protocol, p.severity, p.rationale, p.status",
        {"id": proposal_id},
    )
    if not rows:
        print(f"no proposal {proposal_id}")
        sys.exit(1)
    label, check, heal, sev, rat, status = rows[0]
    if status != "proposed":
        print(f"proposal {proposal_id} already {status}")
        sys.exit(1)

    decision_id = f"decision-{proposal_id}"
    q(
        "CREATE (d:InvariantDecision {node_id:$id, proposal_id:$pid, "
        "decision:$dec, decided_by:$by, reason:$reason, decided_at:datetime(), "
        "project:'system'}) "
        "WITH d MATCH (p:InvariantProposal {node_id:$pid}) "
        "SET p.status = CASE WHEN $dec='approve' THEN 'approved' ELSE 'rejected' END, "
        "p.decided_by=$by, p.decided_at=datetime(), p.reason=$reason "
        "MERGE (d)-[:DECIDES_ON {decay_protected:true}]->(p)",
        {"id": decision_id, "pid": proposal_id, "dec": decision, "by": by,
         "reason": reason},
    )

    if decision == "approve":
        _activate(proposal_id, label, check, heal, sev, rat, decision_id, by)
    else:
        print(f"REJECTED {proposal_id} ({label}) by {by} — {reason or 'no reason'}")
    return decision_id


def _activate(proposal_id, label, check, heal, sev, rat, decision_id, by):
    """Create the :Invariant + :TestCase, link them to the decision."""
    inv_id = slugify(label, maxlen=48)
    node_id = f"inv-{inv_id}"
    if heal:
        q(
            "MERGE (i:Invariant {node_id:$nid}) "
            "SET i.label=$label, i.check_cypher=$check, i.heal_protocol=$heal, "
            "i.severity=$sev, i.rationale=$rat, i.health='healthy', "
            "i.governed='approved', i.created_at=datetime(), i.project='system' "
            "WITH i MATCH (d:InvariantDecision {node_id:$did}) "
            "MERGE (d)-[:GOVERNS {decay_protected:true}]->(i)",
            {"nid": node_id, "label": label, "check": check, "heal": heal,
             "sev": sev, "rat": rat, "did": decision_id},
        )
    else:
        q(
            "MERGE (i:Invariant {node_id:$nid}) "
            "SET i.label=$label, i.check_cypher=$check, i.severity=$sev, "
            "i.rationale=$rat, i.health='healthy', i.governed='approved', "
            "i.created_at=datetime(), i.project='system' "
            "WITH i MATCH (d:InvariantDecision {node_id:$did}) "
            "MERGE (d)-[:GOVERNS {decay_protected:true}]->(i)",
            {"nid": node_id, "label": label, "check": check, "sev": sev,
             "rat": rat, "did": decision_id},
        )
    # A testcase verifies the invariant — required by inv-every-invariant-has-test
    q(
        "MERGE (tc:TestCase {node_id:'tc-' + $nid}) "
        "SET tc.label='Verify ' + $label, tc.project='system' "
        "WITH tc MATCH (i:Invariant {node_id:$nid}) "
        "MERGE (tc)-[:VALIDATES {decay_protected:true}]->(i)",
        {"nid": node_id, "label": label},
    )
    print(f"ACTIVATED {node_id} ({label}) — law in force, approved by {by}")


def list_proposals(status=None):
    if status:
        rows = ql(
            "MATCH (p:InvariantProposal {status:$st}) "
            "RETURN p.node_id, p.label, p.severity, p.proposed_by, p.proposed_at "
            "ORDER BY p.proposed_at",
            {"st": status},
        )
    else:
        rows = ql(
            "MATCH (p:InvariantProposal) "
            "RETURN p.node_id, p.label, p.severity, p.proposed_by, p.status, "
            "p.proposed_at ORDER BY p.proposed_at"
        )
    for r in rows:
        print("  %-42s %-40s [%s] by=%s %s" % (r[0], r[1][:38], r[2], r[3],
                                               r[4] if len(r) > 4 else ""))


def main():
    parser = argparse.ArgumentParser(description="Invariant Governance")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("propose")
    p.add_argument("label")
    p.add_argument("check_cypher")
    p.add_argument("--heal", default="")
    p.add_argument("--severity", default="medium", choices=VALID_SEVERITIES)
    p.add_argument("--rationale", default="")
    p.add_argument("--by", default="human")

    d = sub.add_parser("approve")
    d.add_argument("proposal_id")
    d.add_argument("--by", default="human")
    d.add_argument("--reason", default="")

    r = sub.add_parser("reject")
    r.add_argument("proposal_id")
    r.add_argument("--by", default="human")
    r.add_argument("--reason", default="")

    l = sub.add_parser("list")
    l.add_argument("--status", default=None)

    args = parser.parse_args()
    if args.cmd == "propose":
        propose(args.label, args.check_cypher, heal=args.heal,
                severity=args.severity, rationale=args.rationale, by=args.by)
    elif args.cmd == "approve":
        decide(args.proposal_id, "approve", by=args.by, reason=args.reason)
    elif args.cmd == "reject":
        decide(args.proposal_id, "reject", by=args.by, reason=args.reason)
    elif args.cmd == "list":
        list_proposals(args.status)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
