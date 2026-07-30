// The Dream Round: close triangles
MATCH (a:Knowledge)-[:TOUCHES]-(bridge)
MATCH (bridge)-[:TOUCHES]-(c:Knowledge)
WHERE a <> c
  AND NOT (a)-[:CONCEPTUALLY_RELATED_TO]-(c)
  AND (a.updated_at > datetime() - duration({days:7})
       OR c.updated_at > datetime() - duration({days:7}))
MERGE (a)-[r:CONCEPTUALLY_RELATED_TO {inferred:true}]->(c)
SET r.dream_round = datetime();
