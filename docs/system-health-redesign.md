# System Health Redesign — Self-Awareness for the Fleet

## Problem

1. **Load spike** — 21 opencode serve processes boot simultaneously on Delta restart, each scanning project + loading LSP. 4-core server overloaded (318% CPU on opencode alone).
2. **No self-awareness** — the graph knows the fleet structure but not its own health. No CPU/memory/load data. The SuperAgent cannot answer "why is the system slow?"
3. **Snapshot noise** — 611 append-only FleetSnapshots from a 5-min timer. This is a log, not a map. 75% of the graph is snapshots.

## Fix 1: Staggered Agent Boot

Problem: `_restore_active_projects()` starts all 21 supervisor programs at once.

Fix: Stagger starts. Instead of `supervisorctl start` all simultaneously, start them 2-3 at a time with a delay.

```python
# In app.py _restore_active_projects, for opencode projects:
import time
boot_queue = [p for p in active_projects if p.runtime == "opencode"]
for i, proj in enumerate(boot_queue):
    runner.start(proj)
    if i % 3 == 2:
        await asyncio.sleep(5)  # stagger 3 at a time, 5s apart
```

Also: disable LSP servers in opencode config to reduce per-agent boot cost:
```jsonc
// /root/.config/opencode/opencode.jsonc
"lsp": { "disable": true }
```

## Fix 2: System Health as First-Class Graph Data

New node type: `SystemHealth` — one mutable node, updated in place.

```
(:SystemHealth {
  node_id: "system-health",
  load_1min: 19.8,
  load_5min: 26.7,
  load_15min: 31.2,
  cpu_pct: 78,
  mem_used_gb: 3.6,
  mem_total_gb: 7.8,
  active_agents: 18,
  stopped_agents: 3,
  fatal_agents: 0,
  errors_5min: 2,
  updated_at: datetime()
})
```

Update script: `tools/ingest-fleet-state.py` — MERGE this node instead of CREATE.

New invariant: `invariant-system-health`
```cypher
MATCH (h:SystemHealth)
WHERE h.load_15min > 20 OR h.cpu_pct > 90
RETURN h.updated_at, h.load_15min, h.cpu_pct
```
→ creates an `ActionProposal` when the system is unhealthy.

## Fix 3: Replace Append-Only Snapshots

Current: `CREATE (:FleetSnapshot {...})` every 5 min → 611 nodes.

New model:
1. **`FleetState`** — one mutable node, current truth. MERGE on `node_id: "fleet-state"`. Updated every 5 min.
2. **`SystemHealth`** — one mutable node, health metrics. MERGE on `node_id: "system-health"`. Updated every 5 min.
3. **`FleetEvent`** — only when state CHANGES. E.g. agent went down, agent came up, error spike. Not a timer — an event.
4. **`DailySummary`** — one per day, folded from the day's events. For trend analysis.

The graph stays lean: ~10-20 nodes instead of 288/day.

## Fix 4: SuperAgent Reads Health

Update HUB_CLAUDE.md:
```
Every cycle, check system health:
- `graph MATCH (h:SystemHealth) RETURN h.load_15min, h.cpu_pct, h.active_agents`
- `graph MATCH (ap:ActionProposal {status:"pending"}) RETURN ap.type, ap.description`
If load > 20 or an ActionProposal is pending, report it and propose action.
```

## Expected Result

- Boot spike reduced (staggered)
- Graph lean (~100 nodes, not 800+)
- SuperAgent can answer "why is the system slow?" from graph data
- Unhealthy system → Invariant fires → ActionProposal → SuperAgent reads → reports/acts
