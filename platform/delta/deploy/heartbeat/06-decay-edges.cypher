// Prune unused inferred edges where neither endpoint has recent activity
MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b)
WHERE a.updated_at IS NULL AND b.updated_at IS NULL
  AND (a.created_at IS NULL OR a.created_at < datetime() - duration({days:30}))
DELETE r;
