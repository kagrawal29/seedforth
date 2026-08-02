#!/usr/bin/env python3
"""SuperAgent steering executor — acts on graph ActionProposals.

The graph generates :ActionProposal nodes (ConfirmLifecycle, system_health,
invariant_failure, immune_escalation). The SuperAgent's steering loop:
  SENSE  -> read pending proposals
  ASSESS -> classify: real vs stale, below-gate vs above-gate
  ACT    -> execute below-gate actions (hibernate stalled, resolve stale)
  LEARN  -> write Decision nodes for every action

Below-gate actions the executor may take autonomously:
  - ConfirmLifecycle (stalled) -> hibernate the runtime agent, mark proposal done
  - system_health / invariant_failure / immune_escalation that are ALREADY
    resolved in reality -> mark proposal done (stale)

Above-gate (human) actions are only flagged, never executed:
  - ConfirmLifecycle (complete/archive) with real customers/money
  - SeedEntity, MergeEntities

Usage: python3 steering-executor.py [--dry-run]
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from neo4j_helper import q, ql

REGISTRY_PATH = "/opt/delta/delta-registry.json"
DRY_RUN = "--dry-run" in sys.argv


def load_registry():
    return json.load(open(REGISTRY_PATH))


def save_registry(registry):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def hibernate_agent(project_name, registry):
    """Stop the supervisor program for a project. Keep config for restore."""
    prog = f"proj-{project_name}"
    subprocess.run(["supervisorctl", "stop", prog], capture_output=True, timeout=15)
    # Update registry
    if project_name in registry.get("projects", {}):
        registry["projects"][project_name]["status"] = "hibernated"
        save_registry(registry)
    print(f"    HIBERNATED agent for {project_name}")


def resolve_proposal(proposal_id, resolution, note=""):
    """Mark a proposal as resolved/done with a Decision node."""
    q(
        "MATCH (ap:ActionProposal {node_id:$pid}) SET ap.status='resolved', ap.resolved_at=datetime()",
        {"pid": proposal_id},
    )
    decision_id = f"dec-steer-{int(time.time()*1000)}"
    q(
        "CREATE (d:Decision {node_id:$did, type:'steering', topic:$topic, "
        "rationale:$note, status:'executed', created_at:datetime(), project:'system'})",
        {"did": decision_id, "topic": f"resolved {proposal_id}", "note": note or resolution},
    )
    print(f"    RESOLVED {proposal_id} ({resolution})")


def is_invariant_actually_healthy(proposal_id):
    """For invariant_failure proposals, check if the failure still exists."""
    # Look at the latest InvariantRun health
    rows = ql(
        "MATCH (ir:InvariantRun) RETURN ir.health_score ORDER BY ir.timestamp DESC LIMIT 1"
    )
    if rows and rows[0][0] == 100.0:
        return True
    return False


def main():
    print(f"=== STEERING EXECUTOR {time.strftime('%Y-%m-%d %H:%M:%S')} "
          f"({'DRY RUN' if DRY_RUN else 'EXECUTING'}) ===")
    registry = load_registry()

    pending = ql(
        "MATCH (ap:ActionProposal {status:'pending'}) "
        "RETURN ap.node_id, ap.type, ap.entity, ap.description, ap.confidence"
    )

    for pid, ptype, entity, desc, conf in pending:
        print(f"\n[{ptype}] {entity or 'system'}: {(desc or '')[:60]}")

        # ASSESS + ACT per type
        if ptype == "ConfirmLifecycle" and "stalled" in (desc or ""):
            # Below gate: hibernate the stalled project's agent
            if entity and entity not in ("mycelium", "tetrahedron", "delta", "audioworld",
                                          "flowing-indian", "website"):
                if DRY_RUN:
                    print(f"    would hibernate {entity}")
                else:
                    hibernate_agent(entity, registry)
                    resolve_proposal(pid, "stalled confirmed, agent hibernated")
            else:
                # Ecosystem repo, not a delta agent — just resolve
                if not DRY_RUN:
                    resolve_proposal(pid, "ecosystem repo, no runtime agent to hibernate")

        elif ptype in ("invariant_failure", "immune_escalation"):
            # Check if already healthy in reality
            if is_invariant_actually_healthy(pid):
                if not DRY_RUN:
                    resolve_proposal(pid, "invariant already healthy, stale proposal")
            else:
                print(f"    ESCALATE (still failing)")

        elif ptype == "system_health":
            # Check current load
            rows = ql(
                "MATCH (h:SystemHealth) RETURN h.load_15min ORDER BY h.updated_at DESC LIMIT 1"
            )
            current_load = rows[0][0] if rows else 0
            if current_load < 20:
                if not DRY_RUN:
                    resolve_proposal(pid, f"load recovered to {current_load}")
            else:
                print(f"    ESCALATE (load still {current_load})")

        else:
            print(f"    ABOVE-GATE (needs human)")

    print("\n=== COMPLETE ===")


if __name__ == "__main__":
    main()
