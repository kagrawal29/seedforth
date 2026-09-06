"""Every 5 min: read fleet + system state, MERGE mutable nodes, emit FleetEvent on change.

Writes two mutable nodes (FleetState, SystemHealth) instead of append-only
FleetSnapshots. A FleetEvent is only created when the fleet state actually
changes (agent down/up, error spike) -- not on every timer tick.
"""
import json, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from neo4j_helper import q_strict

REGISTRY_PATH = "/opt/delta/delta-registry.json"
STATE_FILE = "/opt/delta/delta-fleet-state.json"
timestamp = str(int(time.time()))

def run_cypher(cypher):
    try:
        q_strict(cypher)
    except Exception as exc:
        print(f"  cypher error: {str(exc)[:200]}")

def read_cpu_pct():
    """Sample /proc/stat twice to compute overall CPU usage percent."""
    def _sample():
        with open("/proc/stat") as f:
            parts = f.readline().split()
        idle = int(parts[4]) + int(parts[5])
        total = sum(int(p) for p in parts[1:])
        return idle, total
    idle0, total0 = _sample()
    time.sleep(0.5)
    idle1, total1 = _sample()
    d_total = total1 - total0
    d_idle = idle1 - idle0
    if d_total <= 0:
        return 0
    return round((1 - d_idle / d_total) * 100, 1)

def read_mem_gb():
    """Read /proc/meminfo for total and used memory in GB."""
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, rest = line.split(":", 1)
            mem[k] = int(rest.strip().split()[0])
    total_kb = mem["MemTotal"]
    available_kb = mem.get("MemAvailable", mem["MemFree"])
    used_kb = max(total_kb - available_kb, 0)
    return round(total_kb / 1024 / 1024, 2), round(used_kb / 1024 / 1024, 2)

# Read registry
registry = json.load(open(REGISTRY_PATH))
projects = registry.get("projects", {})
total_projects = len(projects)

# Get supervisor status
sup = subprocess.run(["supervisorctl", "status"], capture_output=True, text=True, timeout=10)
sup_lines = sup.stdout.split("\n")
active_agents = sum(1 for line in sup_lines if "RUNNING" in line)
stopped_agents = sum(1 for line in sup_lines if "STOPPED" in line)
fatal_agents = sum(1 for line in sup_lines if "FATAL" in line)

# Get delta errors
journal = subprocess.run(
    ["journalctl", "-u", "delta", "--since", "5 minutes ago", "--no-pager"],
    capture_output=True, text=True, timeout=10
)
errors_5min = journal.stdout.count("ERROR")

# System health
load_1min, load_5min, load_15min = os.getloadavg()
cpu_pct = read_cpu_pct()
mem_total_gb, mem_used_gb = read_mem_gb()

# MERGE FleetState -- one mutable node, current truth
run_cypher(
    f'MERGE (f:FleetState {{node_id:"fleet-state"}}) '
    f'SET f.total_projects = {total_projects}, '
    f'f.active_agents = {active_agents}, '
    f'f.stopped_agents = {stopped_agents}, '
    f'f.fatal_agents = {fatal_agents}, '
    f'f.errors_5min = {errors_5min}, '
    f'f.updated_at = datetime()'
)

# MERGE SystemHealth -- one mutable node, health metrics
run_cypher(
    f'MERGE (h:SystemHealth {{node_id:"system-health"}}) '
    f'SET h.load_1min = {load_1min}, '
    f'h.load_5min = {load_5min}, '
    f'h.load_15min = {load_15min}, '
    f'h.cpu_pct = {cpu_pct}, '
    f'h.mem_used_gb = {mem_used_gb}, '
    f'h.mem_total_gb = {mem_total_gb}, '
    f'h.active_agents = {active_agents}, '
    f'h.stopped_agents = {stopped_agents}, '
    f'h.fatal_agents = {fatal_agents}, '
    f'h.errors_5min = {errors_5min}, '
    f'h.updated_at = datetime()'
)

# SubAgent heartbeat -- update status + updated_at for each supervisor program
# so the agent-liveness invariant has a real signal (not a stale seed value).
for line in sup_lines:
    line = line.strip()
    if not line or "proj-" not in line:
        continue
    prog = line.split()[0]
    agent_name = prog.replace("proj-", "", 1)
    agent_id = f"subagent-{agent_name}"
    process_status = "ready" if "RUNNING" in line else "stopped"
    run_cypher(
        f'MERGE (ap:AgentProcess {{node_id:"process-{agent_name}"}}) '
        f'SET ap.name = "{agent_name}", ap.supervisor_program = "{prog}", '
        f'ap.status = "{process_status}", ap.project = "system", '
        'ap.source = "supervisor", ap.observed_at = datetime() '
        f'MERGE (sa:SubAgent {{node_id:"{agent_id}"}}) '
        'MERGE (ap)-[:BACKS]->(sa) '
        'WITH ap '
        'MERGE (srv:Server {node_id:"server-delta2"}) '
        'SET srv.name = "delta2", srv.host = "185.192.96.100" '
        'MERGE (ap)-[:RUNS_ON]->(srv)'
    )
    if "RUNNING" in line:
        run_cypher(
            f"MERGE (sa:SubAgent {{node_id:\"{agent_id}\"}}) "
            f"SET sa.name = \"{agent_name}\", sa.status = 'active', "
            f"sa.updated_at = datetime(), sa.project = 'system'"
        )
    elif "STOPPED" in line or "EXITED" in line or "FATAL" in line:
        run_cypher(
            f"MERGE (sa:SubAgent {{node_id:\"{agent_id}\"}}) "
            f"SET sa.name = \"{agent_name}\", sa.status = 'stopped', "
            f"sa.updated_at = datetime(), sa.project = 'system'"
        )

# Emit FleetEvent only when state changes
state = {
    "total_projects": total_projects,
    "active_agents": active_agents,
    "stopped_agents": stopped_agents,
    "fatal_agents": fatal_agents,
    "errors_5min": errors_5min,
}
prev = {}
if os.path.exists(STATE_FILE):
    try:
        prev = json.load(open(STATE_FILE))
    except (ValueError, OSError):
        prev = {}
changed = {k: v for k, v in state.items() if prev.get(k) != v}
if changed:
    changes = ", ".join(f"{k}:{prev.get(k)}->{v}" for k, v in changed.items())
    run_cypher(
        f'CREATE (e:FleetEvent {{'
        f'node_id:"fleet-event-{timestamp}", '
        f'type:"state_change", '
        f'description:"{changes}", '
        f'project:"system", '
        f'created_at:datetime()'
        f'}})'
    )
    print(f"FleetEvent: {changes}")

json.dump(state, open(STATE_FILE, "w"))

print(f"FleetState: {total_projects} projects, {active_agents} active, "
      f"{errors_5min} errors; load_15min={load_15min}, cpu={cpu_pct}%")
