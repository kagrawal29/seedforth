# Reactive Triggers — APOC-Driven Mutation Detection

This directory contains APOC trigger definitions that fire on graph mutations (node creation, property updates) and set dirty flags for the system to react to.

## Architecture

Triggers are the sensing layer of the graph-native autonomy system. When a Protocol, CypherAtom, or Invariant node is created or modified, triggers fire asynchronously and set a `DirtyState` node to indicate that the graph has changed and may need to re-mint a snapshot.

### Design Principle

- **Graph-native**: Triggers live in the graph as reference documentation, installed via APOC
- **Non-blocking**: Triggers fire `afterAsync` — the transaction commits before the trigger body runs
- **Collapsed state**: All mutations collapse to a single `DirtyState` node (not per-mutation), preventing state explosion
- **One-way observation**: Triggers create `DirtyState -[:OBSERVES]-> Being` edge (metadata link, not control flow)

## Files

- `trigger-protocol-mutation-observed.cypher` — APOC trigger that detects mutations and sets dirty flag

## How Triggers Are Loaded

The `./mycelium bootstrap` command:

1. Loads all `graph/protocols/*.cypher` files
2. Loads all `graph/triggers/*.cypher` files via `bootstrap_triggers_and_invariants.py`
3. Loads all `graph/invariants/*.cypher` files via the same script
4. Decomposes Protocols into atoms

Triggers are stored as reference in Trigger nodes. The actual APOC installation can happen separately via `graph/runner/install-triggers.py` (not yet in automated flow due to transaction routing issues on macOS).

## Triggering Protocol: Mutation Detection

### What Fires

Mutations to Protocol, CypherAtom, or Invariant nodes:
- **create** event: New Protocol/CypherAtom/Invariant node
- **set** event on `.cypher` or `.label` properties

### What Happens

When a trigger fires:
1. Check if any createdNodes are Protocol/CypherAtom/Invariant
2. Check if any assignedNodeProperties target `.cypher` or `.label`
3. If either is true: MERGE `DirtyState {node_id: 'dirty-state-mint-trigger'}`
4. Set `dirty = true`, `touched_at = datetime()`
5. Increment mutation_count
6. Link `DirtyState -[:OBSERVES]-> Being`

### Downstream Protocol

The heartbeat runs `protocol-mint-if-dirty` every 10 seconds, which checks:
- Is DirtyState.dirty = true?
- Has the settle window (default 60s) elapsed since touched_at?
- Is the graph healthy (autonomous_score=100, no unhealthy invariants)?

If all pass: mint a new Species, clear the dirty flag.
If not: wait for next heartbeat or for graph to heal.

## Installation & Verification

### Current Status

Triggers are **DESIGNED but NOT INSTALLED** on local macOS Neo4j due to a transaction routing issue with cypher-shell. The blocking issue:

- `apoc.trigger.install()` requires WRITE transactions to route to the PRIMARY
- Neo4j 2026.03.1 via brew (single-node, implicitly PRIMARY)
- But cypher-shell's driver doesn't route correctly
- Error: "writes must pass through leader"
- Workaround: None without restart or driver upgrade

### Production (FalkorDB)

On FalkorDB with native MCP stream support, triggers will install cleanly.

### Manual Installation

To test locally despite the routing issue:

```bash
# Use the native Neo4j driver (not cypher-shell):
python3 graph/runner/install-triggers.py

# Or via direct Java:
cd /opt/homebrew/Cellar/neo4j/2026.03.1/libexec && \
  ./bin/neo4j-admin command exec-in-transaction \
  "CALL apoc.trigger.install(...)"
```

### Verification

Once triggers are installed:

```bash
# List active triggers
./mycelium shell "CALL apoc.trigger.list()"

# Verify a trigger fires (mutate a Protocol's cypher)
./mycelium shell "
  MATCH (p:Protocol {node_id: 'any-protocol'})
  SET p.cypher = 'test change'
"

# Check dirty flag was set
./mycelium shell "
  MATCH (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
  RETURN ds.dirty, ds.touched_at, ds.mutation_count
"
```

## Testing

Four test cases verify the mint trigger behavior end-to-end:

- `graph/protocols/tc-mint-fires-on-protocol-change.cypher` — Dirty flag set within 1 async tick
- `graph/protocols/tc-mint-respects-settle-window.cypher` — No premature mint before window
- `graph/protocols/tc-mint-blocked-by-unhealth.cypher` — Mint blocked if graph unhealthy
- `graph/protocols/tc-mint-clears-dirty.cypher` — Dirty flag cleared after successful mint

Run all tests: `./mycelium test`

## Design Trade-offs

### Why Triggers vs Polling?

- **Triggers**: O(1) latency on mutation, no polling overhead, integrates cleanly with heartbeat
- **Polling**: O(n) cost to scan all nodes, wastes cycles checking unchanged state

Triggers reduce latency from 10s (heartbeat polling) to <100ms (async callback).

### Why Collapse to Single DirtyState?

- **Per-mutation nodes**: Would create unbounded state (one node per mutation), requiring cleanup, polluting the graph
- **Single collapsed node**: Constant space, acts as a dirty bit (already clean/dirty), heartbeat reads it once per cycle

Trade-off: Lose granularity about WHICH mutations happened. Gain: Clean design, bounded state.

### Why AsyncAfter vs Sync?

- **Sync phase**: Blocks the transaction, could hold locks, risks deadlock
- **Async phase**: Commits first, fires callback, non-blocking, safe

Slight latency cost (callback is async), massive stability gain.

## Extending Triggers

To add a new trigger (e.g., on :Concept node changes):

1. Create `graph/triggers/trigger-concept-mutation-observed.cypher` with @node_id and @label headers
2. Write the APOC trigger cypher (unwind createdNodes/assignedNodeProperties, check conditions, MERGE your dirty flag)
3. Run `./mycelium bootstrap` to load it
4. (Optional) Run `python3 graph/runner/install-triggers.py` to activate it in Neo4j

## Debugging

If dirty flags aren't being set:

1. **Verify triggers are installed**: `./mycelium shell "CALL apoc.trigger.list()"`
2. **Verify Being singleton exists**: `./mycelium shell "MATCH (b:Being {node_id: 'being-mycelium'}) RETURN b"`
3. **Try mutation**: `./mycelium shell "MATCH (p:Protocol) SET p.cypher = p.cypher LIMIT 1"`
4. **Check dirty flag**: `./mycelium shell "MATCH (ds:DirtyState {node_id: 'dirty-state-mint-trigger'}) RETURN ds"`
5. **Check heartbeat is running**: `./mycelium status` should show heartbeat scheduled

If mutations set dirty flag but mint doesn't happen:

- Check `autonomous_score`: `./mycelium shell "MATCH (b:Being) RETURN b.autonomous_score"`
- Check unhealthy invariants: `./mycelium health` (will list them)
- Check mint settle window: `./mycelium shell "MATCH (b:Being) RETURN b.mint_settle_window_sec"`
