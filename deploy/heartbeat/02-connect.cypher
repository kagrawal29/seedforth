// Wire unprocessed SessionTraces to Knowledge by project tag overlap
MATCH (st:SessionTrace)
WHERE st.digested IS NULL
MATCH (k:Knowledge {project: st.project})
MERGE (st)-[:TOUCHES]->(k)
SET st.digested = true;
