// @node_id: protocol-density-map
// @label: "Density Map"
// ============================================================================
// DENSITY MAP PROTOCOL - Section 1: Per-label density
// ============================================================================

MATCH (n)
WHERE labels(n)[0] IS NOT NULL AND labels(n)[0] <> 'GraphNode'
WITH labels(n)[0] as label, count(n) as node_count
MATCH (a)-[r]->(b)
WHERE labels(a)[0] = label
  AND type(r) <> 'INFERRED_SIMILAR' AND type(r) <> 'SEEMS_LIKE'
WITH label, node_count, count(r) as typed_edges
WITH 'SECTION_1_PER_LABEL_DENSITY' as section, label as key,
     toString(node_count) as val1, toString(typed_edges) as val2,
     CASE WHEN node_count > 0 THEN typed_edges / toFloat(node_count) ELSE 0.0 END as typed_edges_avg
WHERE node_count >= 5
RETURN section, key, val1 as node_count, val2 as typed_edges,
       round(typed_edges_avg * 1000) / 1000.0 as avg_per_node
ORDER BY typed_edges_avg DESC
LIMIT 30
