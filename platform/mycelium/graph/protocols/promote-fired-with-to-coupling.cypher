// @node_id: protocol-promote-fired-with-to-coupling
// @label: "Promote strong :FIRED_WITH edges to :COUPLES_WITH (Hebbian crystallization)"
// @kind: protocol
// @fsd_layer: features
//
// Threshold rule: when a :FIRED_WITH edge between two cross-subgraph nodes
// reaches fire_count >= 3 AND strength >= 0.3, it has co-fired enough times
// to be trusted. Crystallize it as a :COUPLES_WITH edge — a Promise-allowed
// bridge — so the forest's real traversal can cross through it.
//
// When a :FIRED_WITH edge touches 3+ distinct subgraphs (counting the nodes
// on both ends across sessions), it becomes a :FractalEcho candidate and we
// emit a seed node that the weaver will later witness at multiple scales.
//
// Runs on heartbeat after protocol-ingest-panel-signals.
// Idempotent: MERGE on edge identity.
// ============================================================================

// Tier 1: strong dyadic co-firing → :COUPLES_WITH
MATCH (a)-[f:FIRED_WITH]->(b)
WHERE f.fire_count >= 3
  AND f.strength >= 0.3
  AND a.project IS NOT NULL AND b.project IS NOT NULL
  AND a.project <> b.project
  AND NOT EXISTS { (a)-[:COUPLES_WITH]->(b) }
MERGE (a)-[c:COUPLES_WITH {via: 'hebbian-panel', kind: 'co-fire-promotion'}]->(b)
SET c.promoted_at = datetime(),
    c.fire_count = f.fire_count,
    c.strength = f.strength,
    c.source_edge = 'FIRED_WITH';

// Tier 2: promoted edge spans 3+ subgraphs (via transitive co-firing) → seed :FractalEcho
MATCH (a)-[:FIRED_WITH]-(b)-[:FIRED_WITH]-(c)
WHERE a.project IS NOT NULL AND b.project IS NOT NULL AND c.project IS NOT NULL
  AND size(apoc.coll.toSet([a.project, b.project, c.project])) = 3
WITH DISTINCT a, b, c
WITH a, b, c,
     apoc.text.base64Encode(a.node_id + '|' + b.node_id + '|' + c.node_id) AS sig
MERGE (echo:FractalEcho {node_id: 'echo-hebbian-' + left(sig, 16)})
ON CREATE SET echo.project = 'mycelium',
              echo.created_at = datetime(),
              echo.source = 'hebbian-triangle',
              echo.scales_observed = [],
              echo.strength = 0.3
ON MATCH SET echo.strength = echo.strength + 0.1
MERGE (echo)-[:ECHOES_AT_SCALE {scale: coalesce(labels(a)[0],'?')}]->(a)
MERGE (echo)-[:ECHOES_AT_SCALE {scale: coalesce(labels(b)[0],'?')}]->(b)
MERGE (echo)-[:ECHOES_AT_SCALE {scale: coalesce(labels(c)[0],'?')}]->(c);

RETURN 'Hebbian promotion complete: strong co-fires → COUPLES_WITH; triangles → FractalEcho seeds.' AS checkpoint;
