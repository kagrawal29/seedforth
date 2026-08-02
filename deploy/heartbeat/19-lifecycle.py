#!/usr/bin/env python3
"""Lifecycle detection — uses ProgressEvents to auto-transition entity states.

Rules (from master-spec Part 5 / progress-and-direction.md):
- active + no real progress (weight>=0.5) for stall_days (default 7) -> stalled
- stalled + real progress -> back to active
- active + all goals complete + no open work -> complete/maintenance
- stale system nodes get project='system'

Writes :LifecycleEvent nodes + :ActionProposal (ConfirmLifecycle) for
SuperAgent ratification. Auto-rules only change the graph lifecycle, never
runtime status directly.

Usage: python3 19-lifecycle.py [--all]
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
from neo4j_helper import q, ql


def set_lifecycle(entity, new_state, reason, triggered_by="auto-rule"):
    """Write LifecycleEvent + update project node."""
    le_id = f"le-{entity}-{int(time.time())}"
    q(
        "CREATE (le:LifecycleEvent {node_id:$lid, entity:$ent, from_state:$frm, "
        "to_state:$to, reason:$reason, triggered_by:$trig, created_at:datetime(), project:$ent})",
        {"lid": le_id, "ent": entity, "frm": "active", "to": new_state,
         "reason": reason, "trig": triggered_by},
    )
    q(
        "MATCH (p:Project {node_id:$pid}) SET p.lifecycle_state=$st, p.updated_at=datetime()",
        {"pid": f"project-{entity}", "st": new_state},
    )

    # Create ConfirmLifecycle proposal for SuperAgent
    q(
        "MERGE (ap:ActionProposal {node_id:$apid}) "
        "ON CREATE SET ap.type='ConfirmLifecycle', ap.entity=$ent, "
        "ap.description=$reason, ap.status='pending', ap.confidence=0.85, "
        "ap.generated_at=datetime(), ap.project=$ent",
        {"apid": f"ap-lifecycle-{entity}-{time.strftime('%Y-%m-%d')}",
         "ent": entity, "reason": reason},
    )


def get_runtime_status(entity):
    """Get the runtime status from delta-registry."""
    import json
    try:
        registry = json.load(open("/opt/delta/delta-registry.json"))
        proj = registry.get("projects", {}).get(entity, {})
        return proj.get("status", "unknown")
    except (json.JSONDecodeError, OSError):
        return "unknown"


def get_recent_progress(entity, days=7):
    """Return max ProgressEvent weight in last N days."""
    rows = ql(
        "MATCH (pe:ProgressEvent {entity:$ent}) "
        "WHERE pe.created_at > datetime() - duration({days:$days}) "
        "RETURN coalesce(max(pe.weight), 0.0)",
        {"ent": entity, "days": days},
    )
    return rows[0][0] if rows else 0.0


def main():
    print(f"=== LIFECYCLE DETECTION {time.strftime('%Y-%m-%d %H:%M:%S')} ===")

    # Get all projects
    rows = ql("MATCH (p:Project) RETURN p.name, p.node_id, p.lifecycle_state")
    projects = [{"name": r[0], "node_id": r[1], "state": r[2] or "seed"} for r in rows]

    transitions = 0
    for proj in projects:
        name = proj["name"]
        weight = get_recent_progress(name, days=7)

        # Only consider delta-managed active entities (skip ecosystem repos)
        if name in ("mycelium", "tetrahedron", "delta", "audioworld", "website"):
            continue

        current = proj["state"]

        # Initial seeding: assign lifecycle from runtime status if none set
        if current == "seed":
            runtime_status = get_runtime_status(name)
            if runtime_status in ("hibernated", "hibernating"):
                # Not running — check if it has goals/work (dormant vs archived)
                has_context = ql(
                    "MATCH (g:EntityGoal {project:$p}) RETURN count(g)",
                    {"p": name})[0][0] if ql(
                        "MATCH (g:EntityGoal {project:$p}) RETURN count(g)",
                        {"p": name}) else 0
                seed_state = "dormant" if has_context else "seed"
            elif runtime_status in ("config-only", "built"):
                seed_state = "complete" if runtime_status == "built" else "dormant"
            else:
                seed_state = "active" if weight >= 0.3 else "seed"

            q(
                "MATCH (p:Project {node_id:$pid}) SET p.lifecycle_state=$st, p.updated_at=datetime()",
                {"pid": proj["node_id"], "st": seed_state},
            )
            if seed_state != "seed":
                transitions += 1
                print(f"  {name}: seeded lifecycle={seed_state} (status={runtime_status}, weight={weight})")
            continue

        if current == "active" and weight < 0.5:
            set_lifecycle(name, "stalled",
                          f"No real progress in 7 days (weight={weight}). "
                          f"Either blocked (dormant) or finished (complete).")
            transitions += 1
            print(f"  {name}: active -> stalled (weight={weight})")
        elif current == "stalled" and weight >= 0.5:
            set_lifecycle(name, "active", f"Real progress resumed (weight={weight}).")
            transitions += 1
            print(f"  {name}: stalled -> active (weight={weight})")

    print(f"\n  {transitions} lifecycle transitions proposed")


if __name__ == "__main__":
    main()
