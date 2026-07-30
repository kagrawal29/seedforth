// Find and remove duplicate edges
MATCH (a)-[r1:TOUCHES]->(b)
MATCH (a)-[r2:TOUCHES]->(b)
WHERE id(r1) < id(r2)
DELETE r2;
