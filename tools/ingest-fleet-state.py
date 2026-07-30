"""Every 5 min: read fleet state and write FleetSnapshot to Neo4j."""
import json, os, subprocess, time

NEO4J_PASS = "9aac5c811e6d4f4f64a00c65666f3528"
REGISTRY_PATH = "/opt/delta/delta-registry.json"
timestamp = str(int(time.time()))

def run_cypher(cypher):
    subprocess.run(
        ["docker", "exec", "mycelium-neo4j", "cypher-shell",
         "-u", "neo4j", "-p", NEO4J_PASS,
         "--format", "plain", cypher],
        capture_output=True, text=True, timeout=15
    )

# Read registry
registry = json.load(open(REGISTRY_PATH))
projects = registry.get("projects", {})

# Get supervisor status
sup = subprocess.run(["supervisorctl", "status"], capture_output=True, text=True, timeout=10)
active = sum(1 for line in sup.stdout.split("\n") if "RUNNING" in line)
stopped = sum(1 for line in sup.stdout.split("\n") if "STOPPED" in line)

# Get delta errors
journal = subprocess.run(
    ["journalctl", "-u", "delta", "--since", "5 minutes ago", "--no-pager"],
    capture_output=True, text=True, timeout=10
)
error_count = journal.stdout.count("ERROR")

# Write FleetSnapshot
run_cypher(
    f'CREATE (fs:FleetSnapshot {{'
    f'node_id:"snapshot-{timestamp}", '
    f'total_projects:{len(projects)}, '
    f'active_agents:{active}, '
    f'stopped_agents:{stopped}, '
    f'errors_5min:{error_count}, '
    f'created_at:datetime()'
    f'}})'
)
print(f"FleetSnapshot: {len(projects)} projects, {active} active, {error_count} errors")
