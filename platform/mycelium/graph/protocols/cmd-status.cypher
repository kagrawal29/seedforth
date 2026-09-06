// @node_id: protocol-cmd-status
// @label: Status Command
// @kind: command
// @description: Graph-native status view shows autonomous score, invariants, proposals

// Atom 1: Fetch system identity and autonomous score
MATCH (being:Being {node_id: 'being-mycelium'})
RETURN 'identity|' + being.node_id + '|autonomous_score:' + toString(round(coalesce(being.autonomous_score, 0) * 1000) / 1000) AS result;

// Atom 2: Count active invariants
MATCH (inv:Invariant) WHERE coalesce(inv.enabled, true) = true
RETURN 'invariants|active:' + toString(count(inv)) AS result;

// Atom 3: Count unhealthy invariants (active only, canonical field: health_status)
MATCH (inv:Invariant)
WHERE coalesce(inv.enabled, true) = true
  AND coalesce(inv.health_status, inv.health) = 'unhealthy'
RETURN 'invariants|unhealthy:' + toString(count(inv)) AS result;

// Atom 4: Count pending action proposals
MATCH (ap:ActionProposal {status: 'pending'})
RETURN 'proposals|pending:' + toString(count(ap)) AS result;

// Atom 5: Check heartbeat schedule
MATCH (being:Being {node_id: 'being-mycelium'})
RETURN 'heartbeat|scheduled:' + coalesce(being.heartbeat_scheduled_at, 'not scheduled') AS result;

// Atom 6: Check dirty flag status (mint trigger)
OPTIONAL MATCH (ds:DirtyState {node_id: 'dirty-state-mint-trigger'})
RETURN 'mint|dirty:' + CASE
  WHEN ds IS NULL THEN 'false'
  ELSE toString(coalesce(ds.dirty, false))
END + '|touched_at:' + CASE
  WHEN ds IS NULL OR ds.touched_at IS NULL THEN 'never'
  ELSE toString(ds.touched_at)
END AS result;
