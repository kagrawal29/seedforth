// Detect 2+ SubAgents on same graph region via connected SessionTraces
MATCH (st1:SessionTrace)-[:TOUCHES]->(k:Knowledge)<-[:TOUCHES]-(st2:SessionTrace)
WHERE st1.agent <> st2.agent AND st1.created_at > datetime() - duration({days:1})
WITH k, count(DISTINCT st2.agent) AS agents
MERGE (cv:Convergence {topic: coalesce(k.scope, "system") + ":" + coalesce(k.label, k.node_id, "unknown")})
ON CREATE SET cv.created_at = datetime(), cv.status = "detected", cv.project = coalesce(k.project, "system")
SET cv.last_detected = datetime(), cv.agent_count = agents;
