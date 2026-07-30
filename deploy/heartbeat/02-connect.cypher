// Wire unprocessed SessionTraces to Knowledge by project tag overlap
MATCH (st:SessionTrace)
WHERE NOT exists(st.digested)
MATCH (k:Knowledge {project: st.project})
MERGE (st)-[:TOUCHES]->(k)
SET st.digested = true;
