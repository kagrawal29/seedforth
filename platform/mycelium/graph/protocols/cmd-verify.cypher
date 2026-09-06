// @node_id: protocol-cmd-verify
// @label: Verify Command
// @kind: command
// @description: Graph integrity check - Merkle root, invariant baseline, edge counts, orphan detection

// Atom 1: Verify Merkle root baseline
MATCH (being:Being {node_id: 'being-mycelium'})
RETURN 'merkle|baseline|' + coalesce(being.merkle_root_baseline, 'not-computed') AS result;

// Atom 2: Compute current node count (baseline check)
MATCH (n) WHERE n.node_id IS NOT NULL
WITH count(n) AS node_count
MATCH (being:Being {node_id: 'being-mycelium'})
WITH node_count, coalesce(being.node_count_baseline, 0) AS baseline
RETURN 'nodecount|current:' + toString(node_count) + '|baseline:' + toString(baseline) + '|drift:' + toString(node_count - baseline) AS result;

// Atom 3: Verify invariant count baseline
MATCH (inv:Invariant) WHERE coalesce(inv.enabled, true) = true
WITH count(inv) AS inv_count
MATCH (being:Being {node_id: 'being-mycelium'})
WITH inv_count, coalesce(being.invariant_count_baseline, 0) AS baseline
RETURN 'invariants|count:' + toString(inv_count) + '|baseline:' + toString(baseline) + '|status:' + CASE WHEN inv_count >= baseline THEN 'ok' ELSE 'drift' END AS result;

// Atom 4: Verify edge count baseline
MATCH (n)-[r]-(m) WHERE n.node_id IS NOT NULL
WITH count(r) AS edge_count
MATCH (being:Being {node_id: 'being-mycelium'})
WITH edge_count, coalesce(being.edge_count_baseline, 0) AS baseline
RETURN 'edges|count:' + toString(edge_count) + '|baseline:' + toString(baseline) + '|drift:' + toString(edge_count - baseline) AS result;

// Atom 5: Detect orphaned nodes (no incoming or outgoing edges)
MATCH (n) WHERE n.node_id IS NOT NULL AND NOT (n)-[]-()
WITH count(n) AS orphan_count
RETURN 'orphans|' + CASE WHEN orphan_count > 0 THEN 'found:' + toString(orphan_count) ELSE 'none' END AS result;

// Atom 6: Summary: all checks passed or failed
MATCH (being:Being {node_id: 'being-mycelium'})
RETURN 'verify-status|' + coalesce(being.verify_status, 'pending') + '|timestamp:' + coalesce(toString(being.verify_timestamp), 'unknown') AS result;
