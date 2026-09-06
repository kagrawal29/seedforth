// @node_id: protocol-watching
// @label: "Watching — recent QueryTraces, last 10s window"

WITH timestamp() - 10000 AS since_ms
MATCH (qt:QueryTrace)
WHERE qt.invoked_epoch_ms >= since_ms
WITH qt ORDER BY qt.invoked_epoch_ms DESC LIMIT 25
RETURN toString(qt.invoked_epoch_ms) + '  ' + coalesce(qt.invoked_by, '?') + '  ' + coalesce(qt.command, '?') + '  ' + substring(coalesce(qt.cypher_summary, ''), 0, 80) AS line
