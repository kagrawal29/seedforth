"""Reconcile delta registry into graph as single source of truth.

Uses the fast Neo4j HTTP API (not cypher-shell — that's 160x slower).
Creates Project + SubAgent nodes, links to orgs, refreshes statuses.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q, ql

REGISTRY_PATH = "/opt/delta/delta-registry.json"


def infer_org(name):
    l = name.lower()
    if "solve" in l:
        return "SolveOS"
    if "flow" in l:
        return "FlowingIndian"
    if "sceneforth" in l:
        return "SceneforthOS"
    if "revti" in l or "charlie" in l:
        return "Revti Digital"
    return "SeedForth"


def reconcile():
    registry = json.load(open(REGISTRY_PATH))
    projects = registry.get("projects", {})

    sup = subprocess.run(["supervisorctl", "status"], capture_output=True,
                         text=True, timeout=10)
    sup_map = {}
    for line in sup.stdout.split("\n"):
        parts = line.split()
        if len(parts) >= 2:
            sup_map[parts[0]] = parts[1]

    print(f"Reconciling {len(projects)} projects...")

    # Clean stale delta-* project nodes
    deleted = ql("MATCH (p:Project) WHERE p.name STARTS WITH 'delta-' "
                 "DETACH DELETE p RETURN count(p)")
    if deleted:
        print(f"  Cleaned {deleted[0][0]} stale delta-* projects")

    # Ensure organizations exist
    orgs = {"SeedForth": "earner", "SolveOS": "earner", "FlowingIndian": "earner",
            "SceneforthOS": "earner", "Revti Digital": "client"}
    for name, etype in orgs.items():
        q(
            "MERGE (o:Organization {name:$name}) "
            "SET o.entity_type=$etype, o.status='active'",
            {"name": name, "etype": etype},
        )

    # Create/update each project + agent in batched transactions
    for name, proj in sorted(projects.items()):
        org = infer_org(name)
        prog = f"proj-{name}"
        state = sup_map.get(prog, "STOPPED")
        agent_status = "active" if state == "RUNNING" else state.lower()

        q(
            "MERGE (p:Project {node_id:$pid}) SET p.name=$name, p.status=$pstatus, p.project=$name "
            "WITH p MATCH (o:Organization {name:$org}) MERGE (p)-[:BELONGS_TO {decay_protected:true}]->(o)",
            {"pid": f"project-{name}", "name": name,
             "pstatus": proj.get("status", "active"), "org": org},
        )

        q(
            "MERGE (sa:SubAgent {node_id:$aid}) SET sa.name=$name, sa.status=$status, "
            "sa.project=$name, sa.updated_at=datetime() "
            "WITH sa MATCH (p:Project {node_id:$pid}) "
            "MERGE (p)-[:HAS_AGENT {decay_protected:true}]->(sa) "
            "WITH sa, p MATCH (hub:SubAgent {node_id:'subagent-delta-hub'}) "
            "MERGE (hub)-[:OVERSEES {decay_protected:true}]->(p)",
            {"aid": f"subagent-{name}", "name": name, "status": agent_status,
             "pid": f"project-{name}"},
        )

    # Ensure hub exists + links to org + server
    q(
        "MERGE (hub:SubAgent {node_id:'subagent-delta-hub'}) "
        "SET hub.name='Delta Hub', hub.role='SuperAgent orchestrator', "
        "hub.status='active', hub.owner='Kshitiz', hub.project='seedforth', hub.updated_at=datetime() "
        "WITH hub MATCH (o:Organization {name:'SeedForth'}) "
        "MERGE (hub)-[:BELONGS_TO {decay_protected:true}]->(o) "
        "WITH hub MERGE (s:Server {name:'delta-server'}) "
        "MERGE (hub)-[:RUNS_ON {decay_protected:true}]->(s)"
    )

    print("Reconcile complete.")


if __name__ == "__main__":
    reconcile()
