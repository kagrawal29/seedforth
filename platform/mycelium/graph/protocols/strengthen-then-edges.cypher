// @node_id: protocol-strengthen-then-edges
// @label: "Strengthen Then Edges"
// Strengthen THEN edges by incrementing traversal count
// Called after protocol sequences fire to record THEN edge usage
// This closes the "output never connects to input" fractal root

MATCH (p:Protocol)-[t:THEN]->(q:Protocol)
SET t.count = coalesce(t.count, 0) + 1,
    t.last_traversed = toString(datetime())
RETURN
  p.name AS from_protocol,
  q.name AS to_protocol,
  t.count AS updated_count,
  t.last_traversed
