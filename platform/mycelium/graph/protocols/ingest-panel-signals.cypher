// @node_id: protocol-ingest-panel-signals
// @label: "Ingest panel-session signal files into the graph (heartbeat-safe)"
// @kind: protocol
// @fsd_layer: features
//
// The forest panel (scripts/forest-panel.py) emits Cypher files under
// graph/signals/panel/*.cypher on every run. This protocol ingests them in
// batches each heartbeat, then moves them to graph/signals/panel/ingested/.
//
// Writes produced by those signals:
//   :PanelSession nodes
//   :HEARD_FROM edges (PanelSession → node)
//   :FIRED_WITH edges (node ↔ node) with fire_count + strength (Hebbian)
//
// Depends on:
//   apoc.load.directory (directory listing)
//   apoc.cypher.runMany (execute file content)
//   apoc.load.file (read text)
//
// Invocation is done by the heartbeat; this protocol stores the cypher only.
// ============================================================================

CALL apoc.load.directory('*.cypher', 'graph/signals/panel/', {recursive:false})
YIELD value AS path
WITH path
CALL apoc.load.file(path) YIELD line
WITH path, apoc.text.join(collect(line), '\n') AS body
CALL apoc.cypher.runMany(body, {}, {statistics:true}) YIELD row
WITH path, count(row) AS stmts_run
CALL apoc.file.move(path, replace(path, '/panel/', '/panel/ingested/')) YIELD result
RETURN path, stmts_run, result AS moved;
