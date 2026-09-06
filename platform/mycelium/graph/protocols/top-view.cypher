// @node_id: protocol-top
// @label: "Top View — hottest atoms + queries by fire_count"

// Rows tagged (section, content)
RETURN 'header' AS section, 'HOTTEST ATOMS' AS content
UNION ALL
MATCH (a:CypherAtom) WHERE coalesce(a.fire_count, 0) > 0
RETURN 'atom' AS section,
       '  ' + toString(a.fire_count) + '  ' + a.node_id + '  ' + substring(coalesce(a.semantic, ''), 0, 60) AS content
ORDER BY split(content, ' ')[2] DESC LIMIT 10
UNION ALL
RETURN 'header' AS section, 'HOTTEST QUERIES' AS content
UNION ALL
MATCH (q:Query) WHERE coalesce(q.fire_count, 0) > 0
RETURN 'query' AS section,
       '  ' + toString(q.fire_count) + '  ' + coalesce(q.last_command, 'unknown') + '  ' + substring(coalesce(q.cypher_summary, ''), 0, 60) AS content
ORDER BY q.fire_count DESC LIMIT 10
