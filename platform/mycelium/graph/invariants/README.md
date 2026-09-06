# Invariants — Graph Health Constraints

This directory contains invariant definitions that enforce structural constraints on the graph. Invariants are checked every heartbeat and produce health signals for the immune cycle.

## Architecture

Invariants are boolean claims about system health. Each invariant has:

- **check_cypher**: A Cypher query that returns `{healthy: bool, reason: string, ...}` 
- **heal_protocol** (optional): A Protocol node_id that fixes the unhealthy condition
- **severity**: 'critical' or 'warning'
- **category**: Domain tag (e.g., 'ethics', 'lifecycle')

The immune cycle runs every heartbeat, checks all invariants, and if unhealthy:
- If heal_protocol exists: invokes it to auto-heal
- If not: creates an ActionProposal for human review

## Files

- `invariant-mint-not-stale.cypher` — Detects if dirty flag has persisted >10 minutes without clearing

## How Invariants Are Loaded

The `./mycelium bootstrap` command loads all `graph/invariants/*.cypher` files via `bootstrap_triggers_and_invariants.py`. Each file is expected to be executable Cypher that MERGE's the Invariant node with all properties.

## Invariant: Mint Not Stale

### Purpose

Monitors the mutation dirty flag to ensure it doesn't linger for >10 minutes without being cleared by the mint cycle.

### Healthy When

- DirtyState does not exist, OR
- DirtyState.dirty = false (cleared by mint or other process), OR
- DirtyState.dirty = true AND <10 minutes have elapsed

### Unhealthy When

- DirtyState.dirty = true AND >=10 minutes since touched_at

### Semantics

This is a **soft signal** invariant (severity='warning'). When unhealthy:

- Creates an ActionProposal for human investigation
- Does NOT auto-fail the graph
- Suggests the mint cycle is blocked or slow

### No Auto-Heal

This invariant has no heal_protocol. The blockage might be:
- Autonomous score low (immune cycle healing something else)
- Many unhealthy invariants (queue of heals)
- Graph degradation (query performance, memory pressure)

The human needs to investigate the root cause.

### Metrics

- **stale_duration_sec**: How long the dirty flag has persisted since touched_at
- **threshold**: 600 seconds (10 minutes)

If stale_duration_sec > 600, the invariant is unhealthy.

## Testing

To verify the invariant:

```bash
# Manual check
./mycelium shell "
  OPTIONAL MATCH (ds:DirtyState {node_id: 'dirty-state-mint-trigger', dirty: true})
  WITH duration.inSeconds(ds.touched_at, datetime()).seconds AS elapsed
  RETURN elapsed > 600 AS is_stale, elapsed AS seconds_since_touched
"

# Via immune cycle
./mycelium health
# Look for: invariant-mint-not-stale unhealthy (if dirty flag is stale)
```

## Extending Invariants

To add a new invariant:

1. Create `graph/invariants/invariant-<name>.cypher`
2. Include headers: `// @node_id: invariant-<name>` and `// @label: "Human readable"`
3. Write Cypher that MERGE's the Invariant node with properties:
   - `label`: display name
   - `description`: what it checks
   - `severity`: 'critical' or 'warning'
   - `category`: domain (e.g., 'lifecycle')
   - `check_cypher`: the actual check query (as a string property)
   - `heal_protocol_id` (optional): which protocol to invoke if unhealthy
4. Optionally wire relationships to Rhythm, Purpose, Ontology, Being
5. Run `./mycelium bootstrap` to load it

Example check_cypher:

```cypher
OPTIONAL MATCH (bad:SomeNode {invalid_property: null})
RETURN
  COUNT(bad) = 0 AS healthy,
  CASE WHEN COUNT(bad) > 0
    THEN "found " + toString(COUNT(bad)) + " nodes with invalid_property"
    ELSE "all nodes valid"
  END AS reason
```

The check_cypher is executed by the immune cycle like this:

```cypher
CALL apoc.cypher.run(invariant.check_cypher, {}) YIELD value
// value is {healthy: bool, reason: string, ...}
```

## Design Principles

- **Invariants are facts, not diagnostics.** They assert truth, not explain why. Explanation is in the check's reason string.
- **Invariants should be fast (<100ms).** They run every heartbeat. Use indexes, avoid full scans.
- **Invariants with heal_protocol must be deterministic.** If healing is non-deterministic, create an ActionProposal instead.
- **Soft invariants prefer proposals over auto-failure.** If you're unsure whether to heal, surface as a proposal.

## Current Invariants

Run this to see all invariants:

```bash
./mycelium shell "MATCH (inv:Invariant) RETURN inv.node_id, inv.label, inv.severity, inv.category"
```

## Debugging

If an invariant is stuck unhealthy:

1. **Check the invariant directly**: `./mycelium shell "CALL apoc.cypher.run(inv.check_cypher, {}) YIELD value RETURN value"`
2. **Check if heal_protocol is running**: Look at recent ActionProposal nodes
3. **Check immune cycle logs**: Run `./mycelium status` to see last heartbeat time
4. **Manually invoke heal**: `./mycelium ask "heal <invariant-name>"`

## Integration with Mint Cycle

The mint cycle uses the invariant system as a gate:

1. Dirty flag set by mutation trigger
2. Settle window elapses
3. Mint protocol checks: `invariant-mint-not-stale` healthy?
4. If unhealthy: DO NOT mint, propose ActionProposal
5. If healthy AND no other unhealthy invariants: proceed to mint

This ensures minting only happens when the system is in a known-good state.
