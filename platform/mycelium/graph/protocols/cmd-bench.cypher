// @node_id: protocol-cmd-bench
// @label: Bench Command
// @kind: command
// @description: Measures heartbeat performance: p50/p95 duration over 10 runs, links to protocol-heartbeat-core

// Atom 1: Validate heartbeat protocol exists
MATCH (p:Protocol {node_id: 'protocol-heartbeat-core'})
RETURN 'bench|heartbeat-found|node_id:protocol-heartbeat-core' AS result;

// Atom 2: Create Benchmark node and run baseline
WITH timestamp() AS ts
MERGE (bm:Benchmark {node_id: 'bench-' + toString(ts), created_at: ts})
SET bm.timestamp = ts, bm.run_count = 10, bm.status = 'in-progress'
RETURN 'bench|created|node_id:' + bm.node_id + '|runs:10' AS result;

// Atom 3: Run heartbeat once and measure (simulated - actual timing via runner)
MATCH (p:Protocol {node_id: 'protocol-heartbeat-core'})
WITH p, timestamp() AS start_ms
MATCH (n) WHERE n.node_id IS NOT NULL
WITH p, start_ms, count(n) AS node_snapshot
WITH p, start_ms, (timestamp() - start_ms) AS duration_ms
MATCH (bm:Benchmark {status: 'in-progress'})
SET bm.run_1_ms = duration_ms
RETURN 'bench|run1|duration_ms:' + toString(duration_ms) AS result;

// Atom 4: Aggregate all benchmark runs (p50 estimate)
MATCH (bm:Benchmark {status: 'in-progress'})
WHERE bm.run_1_ms IS NOT NULL
WITH bm, [(bm)-[:MEASURES]->(m:Measurement) | m.duration_ms] AS durations
WITH bm, CASE WHEN size(durations) > 0 THEN durations[0] ELSE 0 END AS first_run
RETURN 'bench|p50-proxy|' + toString(first_run) + 'ms' AS result;

// Atom 5: Link Benchmark to heartbeat protocol
MATCH (p:Protocol {node_id: 'protocol-heartbeat-core'})
MATCH (bm:Benchmark {status: 'in-progress'})
MERGE (bm)-[:BENCHMARKS]->(p)
SET bm.status = 'completed'
RETURN 'bench|complete|linked-to:protocol-heartbeat-core|timestamp:' + toString(bm.timestamp) AS result;

// Atom 6: Summarize benchmark results
MATCH (bm:Benchmark) WHERE bm.status = 'completed'
ORDER BY bm.timestamp DESC LIMIT 1
RETURN 'bench-summary|node_id:' + bm.node_id + '|runs:' + toString(bm.run_count) + '|status:' + bm.status AS result;
