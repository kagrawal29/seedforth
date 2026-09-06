// @node_id: invariant-heartbeat-writes-seed
// @label: "Heartbeat Writes Invariant — seed"
// @kind: invariant-seed
// @description: Bounded write rate invariant for heartbeat protocol family. Detects unbounded write loops via QueryTrace spike detection.

MERGE (inv:Invariant {node_id: 'invariant-heartbeat-writes-per-tick'})
  SET inv.label = 'Bounded Writes Per Tick',
      inv.description = 'Heartbeat must not write more than ~30 rows per tick sustained. Proxy signal: QueryTrace nodes created in the last 60s by heartbeat-family protocols. High rate => unbounded write loop => risk of dirty-page accumulation.',
      inv.check_cypher = 'MATCH (qt:QueryTrace) WHERE qt.invoked_epoch_ms > timestamp() - 60000 AND qt.protocol_id STARTS WITH \'protocol-heartbeat\' WITH count(qt) AS writes RETURN writes < 200 AS healthy',
      inv.severity = 'block',
      inv.enabled = true,
      inv.heal_protocol = '',
      inv.question_template_id = 'why-is-heartbeat-writing-too-much';
