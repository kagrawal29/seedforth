// Detect 2+ SubAgents on same graph region via connected SessionTraces
MATCH (st1:SessionTrace)-[:TOUCHES]->(k:Knowledge)<-[:TOUCHES]-(st2:SessionTrace)
WHERE st1.agent <> st2.agent AND st1.created_at > datetime() - duration({days:1})
MERGE (cv:Convergence {topic: k.scope + ":" + k.label})
SET cv.last_detected = datetime(), cv.agent_count = count(DISTINCT st2.agent)
ON CREATE SET cv.created_at = datetime(), cv.status = "detected";
