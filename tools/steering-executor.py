#!/usr/bin/env python3
"""SuperAgent steering executor — acts on graph ActionProposals.

The graph generates :ActionProposal nodes (ConfirmLifecycle, system_health,
invariant_failure, immune_escalation). The SuperAgent's steering loop:
  SENSE  -> read pending proposals
  ASSESS -> classify: real vs stale, below-gate vs above-gate
  ACT    -> execute below-gate actions (hibernate stalled, resolve stale)
  LEARN  -> write Decision nodes for every action

Safety (P2.2):
  - Hibernation goes through provisioner.hibernate() (git_save + bridge
    shutdown + registry update), NOT a raw registry write.
  - A fcntl file lock guards the registry against concurrent writers
    (the Discord bot and this cron executor are separate processes).
  - Every action is recorded as a Decision node in the graph.

Below-gate actions the executor may take autonomously:
  - ConfirmLifecycle (stalled) -> hibernate the runtime agent, mark proposal done
  - system_health / invariant_failure / immune_escalation that are ALREADY
    resolved in reality -> mark proposal done (stale)

Above-gate (human) actions are only flagged, never executed:
  - ConfirmLifecycle (complete/archive) with real customers/money
  - SeedEntity, MergeEntities

Usage: python3 steering-executor.py [--dry-run]
"""
import fcntl
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from neo4j_helper import q, ql

REGISTRY_PATH = "/opt/delta/delta-registry.json"
DRY_RUN = "--dry-run" in sys.argv


def _registry_lock():
    """Exclusive file lock so the bot process and this cron don't collide."""
    lock_path = REGISTRY_PATH + ".lock"
    f = open(lock_path, "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX)
    except (OSError, ImportError):
        pass  # best-effort on platforms without flock
    return f


def hibernate_via_provisioner(project_name):
    """Hibernate through provisioner.hibernate() — git_save + stop + bridge shutdown."""
    from delta.provisioner import hibernate as provisioner_hibernate
    from delta.registry import Registry

    lock_file = _registry_lock()
    try:
        registry = Registry(REGISTRY_PATH)
        ok = provisioner_hibernate(project_name, registry, bridges={})
        return ok
    finally:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        except (OSError, ImportError):
            pass
        lock_file.close()


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
    rows = ql(
        "MATCH (ir:InvariantRun) RETURN ir.health_score ORDER BY ir.timestamp DESC LIMIT 1"
    )
    if rows and rows[0][0] == 100.0:
        return True
    return False


def main():
    print(f"=== STEERING EXECUTOR {time.strftime('%Y-%m-%d %H:%M:%S')} "
          f"({'DRY RUN' if DRY_RUN else 'EXECUTING'}) ===")

    pending = ql(
        "MATCH (ap:ActionProposal {status:'pending'}) "
        "RETURN ap.node_id, ap.type, ap.entity, ap.description, ap.confidence"
    )

    for pid, ptype, entity, desc, conf in pending:
        print(f"\n[{ptype}] {entity or 'system'}: {(desc or '')[:60]}")

        if ptype == "ConfirmLifecycle" and "stalled" in (desc or ""):
            # Below gate: hibernate the stalled project's agent
            if entity and entity not in ("mycelium", "tetrahedron", "delta", "audioworld",
                                          "flowing-indian", "website"):
                if DRY_RUN:
                    print(f"    would hibernate {entity}")
                else:
                    ok = hibernate_via_provisioner(entity)
                    resolve_proposal(pid, "stalled confirmed, agent hibernated" if ok
                                     else "stalled confirmed, hibernate FAILED")
            else:
                # Ecosystem repo, not a delta agent — just resolve
                if not DRY_RUN:
                    resolve_proposal(pid, "ecosystem repo, no runtime agent to hibernate")

        elif ptype in ("invariant_failure", "immune_escalation"):
            if is_invariant_actually_healthy(pid):
                if not DRY_RUN:
                    resolve_proposal(pid, "invariant already healthy, stale proposal")
            else:
                print(f"    ESCALATE (still failing)")

        elif ptype == "agent_fatal":
            # Fatal agent = crash-loop. If it has been FATAL for 2+ days,
            # quarantine it: stop the supervisor program, mark quarantined in
            # the graph, escalate ONCE and resolve the daily repeat.
            # Quarantine keeps the config so the agent can be revived after fix.
            age_days = None
            try:
                age_rows = ql(
                    "MATCH (ap:ActionProposal {node_id:$pid}) "
                    "RETURN duration.between(ap.generated_at, datetime()).days",
                    {"pid": pid},
                )
                if age_rows and age_rows[0][0] is not None:
                    age_days = age_rows[0][0]
            except Exception:
                pass
            if age_days is None:
                age_days = 0
            if age_days < 2:
                print(f"    fresh fatal (<2d), leaving for observation")
                continue

            # Find which agent is fatal
            fatal_agent = None
            try:
                import subprocess as _sp
                r = _sp.run(["supervisorctl", "status"], capture_output=True,
                            text=True, timeout=15)
                for line in r.stdout.split("\n"):
                    if "FATAL" in line:
                        fatal_agent = line.split()[0].replace("proj-", "", 1)
                        break
            except Exception:
                pass
            if not fatal_agent:
                print(f"    no FATAL agent in supervisor, resolving stale proposal")
                if not DRY_RUN:
                    resolve_proposal(pid, "no FATAL agent found, stale proposal")
                continue
            if DRY_RUN:
                print(f"    would quarantine {fatal_agent}")
                continue
            _sp = __import__("subprocess")
            _sp.run(["supervisorctl", "stop", f"proj-{fatal_agent}"],
                    capture_output=True, timeout=15)
            try:
                q(
                    "MATCH (p:Project {node_id:'project-' + $n}) "
                    "SET p.status='quarantined', p.lifecycle_state='dormant', "
                    "p.quarantined_at=datetime(), p.updated_at=datetime()",
                    {"n": fatal_agent},
                )
            except Exception:
                pass
            resolve_proposal(
                pid,
                f"quarantined crash-looping agent {fatal_agent} (fatal {age_days}d+) — revive after fix",
            )

        elif ptype == "system_health":
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
