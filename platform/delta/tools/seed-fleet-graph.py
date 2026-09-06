"""Seed SubAgent → Project → Organization graph mapping in Neo4j.
Reads delta-registry.json and supervisor status, maintains accurate fleet state.
Run on every systemd delta restart and after any project lifecycle change.
"""
import json
import os
import subprocess
import sys
import time

NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "")
if not NEO4J_PASS:
    raise RuntimeError("NEO4J_PASSWORD must be provided at runtime")
REGISTRY_PATH = os.environ.get("DELTA_REGISTRY_PATH", "/opt/delta/delta-registry.json")


def run_cypher(cypher):
    """Run a Cypher statement via docker exec."""
    cmd = [
        "docker", "exec", "mycelium-neo4j",
        "cypher-shell", "-u", "neo4j", "-p", NEO4J_PASS,
        "--format", "plain", cypher,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  cypher error: {result.stderr.strip()[:200]}")
        return None
    return result.stdout.strip()


def seed_fleet():
    registry = json.load(open(REGISTRY_PATH))
    projects = registry.get("projects", {})

    # Get supervisor status
    sup_result = subprocess.run(
        ["supervisorctl", "status"], capture_output=True, text=True, timeout=10
    )
    sup_status = {}
    for line in sup_result.stdout.strip().split("\n"):
        parts = line.split()
        if len(parts) >= 2:
            sup_status[parts[0]] = parts[1]

    print(f"Seeding fleet graph: {len(projects)} projects...")

    # Seed organizations
    orgs = {
        "org-seedforth": "SeedForth",
        "org-solveos": "SolveOS",
        "org-flowingindian": "FlowingIndian",
        "org-sceneforthos": "SceneforthOS",
        "org-revti": "Revti Digital",
    }
    for node_id, name in orgs.items():
        r = run_cypher(
            f'MERGE (o:Organization {{node_id:"{node_id}"}}) '
            f'SET o.name="{name}", o.status="active"'
        )
        if r:
            print(f"  Org: {name}")

    # Seed SubAgent for each active project
    hubs = {"proj-delta-hub": "agent-delta-hub"}
    for name, proj in sorted(projects.items()):
        prog_name = f"proj-{name}"
        agent_id = f"subagent-{name}"
        status = sup_status.get(prog_name, "STOPPED")
        run_status = "active" if status == "RUNNING" else status.lower()

        r = run_cypher(
            f'MERGE (sa:SubAgent {{node_id:"{agent_id}"}}) '
            f'SET sa.name="{name}", sa.role="project agent", '
            f'sa.model="deepseek-v4-pro", sa.status="{run_status}", '
            f'sa.owner="delta", sa.updated_at=datetime()'
        )

        if r is not None:
            print(f"  SubAgent: {name} ({run_status})")

        # Stable runtime identity: a supervised process is distinct from the
        # durable SubAgent identity it backs.
        process_status = "ready" if status == "RUNNING" else "stopped"
        run_cypher(
            f'MERGE (ap:AgentProcess {{node_id:"process-{name}"}}) '
            f'SET ap.name="{name}", ap.supervisor_program="{prog_name}", '
            f'ap.status="{process_status}", ap.project="{name}", '
            'ap.source="supervisor", ap.observed_at=datetime()'
        )
        run_cypher(
            f'MERGE (sa:SubAgent {{node_id:"subagent-{name}"}}) '
            f'MERGE (ap:AgentProcess {{node_id:"process-{name}"}}) '
            'MERGE (ap)-[:BACKS]->(sa)'
        )
        run_cypher(
            f'MERGE (srv:Server {{node_id:"server-delta2"}}) '
            f'SET srv.name="delta2", srv.host="185.192.96.100" '
            f'MERGE (ap:AgentProcess {{node_id:"process-{name}"}}) '
            'MERGE (ap)-[:RUNS_ON]->(srv)'
        )

    # Seed Hub SubAgent — name must match the fleet-ingest heartbeat name
    # ("delta-hub") so MERGE collapses into ONE node, not a duplicate.
    run_cypher(
        'MERGE (sa:SubAgent {name:"delta-hub"}) '
        'SET sa.node_id="subagent-delta-hub", sa.role="SuperAgent orchestrator", '
        'sa.model="deepseek-v4-pro", sa.status="active", sa.owner="Kshitiz", '
        'sa.project="system"'
    )
    print("  SubAgent: delta-hub")

    # Link Hub → Project (OVERSEES)
    run_cypher(
        'MATCH (hub:SubAgent {name:"delta-hub"}) '
        'MATCH (p:Project) '
        'WHERE p.name <> "__hub__" '
        'MERGE (hub)-[:OVERSEES]->(p)'
    )
    print("  Hub OVERSEES all projects")

    # Link Project → SubAgent (HAS_AGENT) — ensure project mapping
    for name in projects:
        run_cypher(
            f'MATCH (p:Project {{name:"{name}"}}) '
            f'MATCH (sa:SubAgent {{node_id:"subagent-{name}"}}) '
            f'MERGE (p)-[:HAS_AGENT]->(sa)'
        )

    # Tetrahedron is retained as historical reference and must never appear
    # as an active SeedForth project during fleet reconciliation.
    run_cypher(
        'MATCH (p:Project {name:"tetrahedron"}) '
        'SET p.status="reference-only", p.architecture_role="reference", '
        'p.active=false, p.updated_at=datetime()'
    )
    run_cypher(
        'MATCH (sa:SubAgent {name:"tetrahedron"}) '
        'SET sa.status="reference-only", sa.architecture_role="reference", '
        'sa.updated_at=datetime()'
    )

    # Create a FleetSnapshot
    active_count = sum(1 for p in sup_status.values() if p == "RUNNING")
    run_cypher(
        'CREATE (fs:FleetSnapshot {node_id:"snapshot-' + str(int(time.time())) + '", '
        f'total_projects:{len(projects)}, active_agents:{active_count}, '
        'total_subagents:' + str(len(projects)) + ', '
        "project:'system', "
        'created_at:datetime()})'
    )
    print(f"  FleetSnapshot: {len(projects)} projects, {active_count} active")

    print("Fleet graph seeded successfully")


if __name__ == "__main__":
    seed_fleet()
