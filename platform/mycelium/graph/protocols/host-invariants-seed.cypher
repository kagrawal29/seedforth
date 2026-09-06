// @node_id: protocol-host-invariants-seed
// @label: "Host Invariants Seed — Graph's Body Sensors (RAM, Disk, GC, Load)"
// ============================================================================
// Seeds the graph with host-level invariants that measure the machine
// running Neo4j. Without host sensors, the graph cannot perceive its own
// suffocation — Phase 4 (health-gated heartbeat) depends on this.
//
// Creates 8 :HostInvariant nodes (sampled by out-of-process tools/host-sensor.sh
// every 30s) and 4 :Invariant nodes that check host health using those values.
//
// Reference: graph/docs/proprioception-plan.md (phase 3 — host sensors).
//
// IDEMPOTENT: Uses MERGE on node_id. Safe to re-run.
// ============================================================================

// --- Phase 1: Register 8 SkipKeys for HostInvariant properties ----
// HostInvariant values change frequently (sampled every 30s) and must not
// drift the Merkle root_hash. The root stays stable while sensor data
// accumulates.

MERGE (sk:SkipKey {node_id: 'skipkey-value'})
  SET sk.key = 'value',
      sk.category = 'host-sensor',
      sk.reason = 'Sensor reading (float or string); changes every 30s; excluded from Merkle';

MERGE (sk:SkipKey {node_id: 'skipkey-sampled_at'})
  SET sk.key = 'sampled_at',
      sk.category = 'host-sensor',
      sk.reason = 'ISO datetime of sensor sample; excluded from Merkle for freshness checks';

MERGE (sk:SkipKey {node_id: 'skipkey-sampled_ms'})
  SET sk.key = 'sampled_ms',
      sk.category = 'host-sensor',
      sk.reason = 'Epoch ms of sensor sample; excluded from Merkle for temporal checks';

// --- Phase 2: Create 8 HostInvariant nodes as data sources ----
// Each node has: node_id, label, description, unit, threshold_warn, threshold_critical
// Values (value, sampled_at, sampled_ms) populated by tools/host-sensor.sh

// 1. Host RAM Free (MB)
MERGE (h1:HostInvariant:GraphNode {node_id: 'host-ram-free-mb'})
  SET h1.label = 'Host RAM Free (MB)',
      h1.description = 'Free physical RAM in megabytes. Used by host-ram-ok invariant to detect memory pressure.',
      h1.unit = 'MB',
      h1.threshold_warn = 1500,
      h1.threshold_critical = 500,
      h1.value = NULL,
      h1.sampled_at = NULL,
      h1.sampled_ms = NULL;

// 2. Host RAM Pressure (enum: normal|warn|critical)
MERGE (h2:HostInvariant:GraphNode {node_id: 'host-ram-pressure'})
  SET h2.label = 'Host RAM Pressure',
      h2.description = 'Derived pressure level: normal (>1500 MB free), warn (500-1500 MB), critical (<500 MB). Input for Phase 4 backpressure.',
      h2.unit = 'enum',
      h2.threshold_warn = NULL,
      h2.threshold_critical = NULL,
      h2.value = 'normal',
      h2.sampled_at = NULL,
      h2.sampled_ms = NULL;

// 3. Host Disk Writes per Second
MERGE (h3:HostInvariant:GraphNode {node_id: 'host-disk-writes-per-sec'})
  SET h3.label = 'Host Disk Writes/sec',
      h3.description = 'Disk write rate in operations per second. Neo4j tx-log rotations spike this.',
      h3.unit = 'ops/sec',
      h3.threshold_warn = 1000,
      h3.threshold_critical = 5000,
      h3.value = NULL,
      h3.sampled_at = NULL,
      h3.sampled_ms = NULL;

// 4. Host GC Pause p99 (ms)
MERGE (h4:HostInvariant:GraphNode {node_id: 'host-gc-pause-p99-ms'})
  SET h4.label = 'Host GC Pause p99 (ms)',
      h4.description = '99th percentile GC pause latency. Collected from JMX if available.',
      h4.unit = 'ms',
      h4.threshold_warn = 1000,
      h4.threshold_critical = 2000,
      h4.value = NULL,
      h4.sampled_at = NULL,
      h4.sampled_ms = NULL;

// 5. Host GC Pause Max (last minute, ms)
MERGE (h5:HostInvariant:GraphNode {node_id: 'host-gc-pause-max-ms-last-min'})
  SET h5.label = 'Host GC Pause Max/min (ms)',
      h5.description = 'Maximum GC pause observed in the last 60 seconds. Checked by host-gc-ok invariant. Threshold 2000ms = hard backpressure line for Phase 4.',
      h5.unit = 'ms',
      h5.threshold_warn = 1000,
      h5.threshold_critical = 2000,
      h5.value = NULL,
      h5.sampled_at = NULL,
      h5.sampled_ms = NULL;

// 6. Host TX Log Size (MB)
MERGE (h6:HostInvariant:GraphNode {node_id: 'host-tx-log-size-mb'})
  SET h6.label = 'Host TX Log Size (MB)',
      h6.description = 'Size of Neo4j transaction log. Rapid growth indicates high write rate.',
      h6.unit = 'MB',
      h6.threshold_warn = 200,
      h6.threshold_critical = 500,
      h6.value = NULL,
      h6.sampled_at = NULL,
      h6.sampled_ms = NULL;

// 7. Host Neo4j RSS (MB)
MERGE (h7:HostInvariant:GraphNode {node_id: 'host-neo4j-rss-mb'})
  SET h7.label = 'Host Neo4j RSS (MB)',
      h7.description = 'Resident set size (physical memory) used by Neo4j process. Watch for unbounded growth.',
      h7.unit = 'MB',
      h7.threshold_warn = 1200,
      h7.threshold_critical = 1500,
      h7.value = NULL,
      h7.sampled_at = NULL,
      h7.sampled_ms = NULL;

// 8. Host Load Average (1-minute)
MERGE (h8:HostInvariant:GraphNode {node_id: 'host-load-avg-1m'})
  SET h8.label = 'Host Load Average (1m)',
      h8.description = '1-minute load average. On 8 GB 4-core Mac, >4 indicates contention.',
      h8.unit = 'ratio',
      h8.threshold_warn = 3.0,
      h8.threshold_critical = 4.5,
      h8.value = NULL,
      h8.sampled_at = NULL,
      h8.sampled_ms = NULL;

// --- Phase 3: Create 4 Invariants that check host health ----
// Each invariant uses check_cypher to query the HostInvariant nodes and
// report health status.

// 1. Host RAM OK — ram pressure must not be critical
MERGE (inv1:Invariant {node_id: 'host-ram-ok'})
  SET inv1.label = 'Host RAM OK',
      inv1.description = 'host-ram-pressure value must not equal "critical". Critical pressure triggers Phase 4 backpressure.',
      inv1.check_cypher = 'MATCH (h:HostInvariant {node_id:"host-ram-pressure"}) RETURN h.value <> "critical" AS healthy',
      inv1.severity = 'block',
      inv1.heal_protocol = '',
      inv1.question_template_id = 'why-is-host-ram-critical';

// 2. Host GC OK — max pause in last minute must be < 2000ms
MERGE (inv2:Invariant {node_id: 'host-gc-ok'})
  SET inv2.label = 'Host GC OK',
      inv2.description = 'host-gc-pause-max-ms-last-min.value must be < 2000. Breaches trigger Phase 4 backpressure.',
      inv2.check_cypher = 'MATCH (h:HostInvariant {node_id:"host-gc-pause-max-ms-last-min"}) RETURN coalesce(h.value, 0) < 2000 AS healthy',
      inv2.severity = 'block',
      inv2.heal_protocol = '',
      inv2.question_template_id = 'why-are-gc-pauses-long';

// 3. Host Disk OK — write rate must be below critical threshold
MERGE (inv3:Invariant {node_id: 'host-disk-ok'})
  SET inv3.label = 'Host Disk OK',
      inv3.description = 'host-disk-writes-per-sec.value must be below host-disk-writes-per-sec.threshold_critical (5000 ops/s).',
      inv3.check_cypher = 'MATCH (h:HostInvariant {node_id:"host-disk-writes-per-sec"}) RETURN coalesce(h.value, 0) < coalesce(h.threshold_critical, 5000) AS healthy',
      inv3.severity = 'warn',
      inv3.heal_protocol = '',
      inv3.question_template_id = 'why-is-disk-write-rate-high';

// 4. Host Sensor Fresh — all 8 HostInvariants must have sampled_ms within last 90 seconds
MERGE (inv4:Invariant {node_id: 'host-sensor-fresh'})
  SET inv4.label = 'Host Sensor Fresh',
      inv4.description = 'All 8 HostInvariant nodes must have sampled_ms > timestamp() - 90000. Detects host-sensor.sh failures.',
      inv4.check_cypher = 'MATCH (h:HostInvariant) WHERE h.node_id IN ["host-ram-free-mb","host-ram-pressure","host-disk-writes-per-sec","host-gc-pause-p99-ms","host-gc-pause-max-ms-last-min","host-tx-log-size-mb","host-neo4j-rss-mb","host-load-avg-1m"] WITH collect(h.sampled_ms) AS sampled_times WITH coalesce(min(sampled_times), timestamp()) AS oldest_sample RETURN oldest_sample > timestamp() - 90000 AS healthy',
      inv4.severity = 'block',
      inv4.heal_protocol = '',
      inv4.question_template_id = 'why-are-host-sensors-stale';

// --- Final Summary Report ---

MATCH (h:HostInvariant)
WITH collect(h.node_id) AS host_invariants, count(h) AS h_count
MATCH (inv:Invariant) WHERE inv.node_id IN ['host-ram-ok', 'host-gc-ok', 'host-disk-ok', 'host-sensor-fresh']
WITH host_invariants, h_count, collect(inv.node_id) AS invariants, count(inv) AS inv_count
RETURN
  h_count AS host_invariants_created,
  host_invariants AS host_invariant_node_ids,
  inv_count AS invariants_created,
  invariants AS invariant_node_ids,
  'host-invariants-seed seeded' AS status;
