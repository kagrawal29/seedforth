// Check if the system is alive
OPTIONAL MATCH (st:SessionTrace) WHERE st.created_at > datetime() - duration({hours:1})
WITH count(st) as recent_traces
OPTIONAL MATCH (fs:FleetSnapshot) WHERE fs.created_at > datetime() - duration({hours:1})
WITH recent_traces, count(fs) as recent_snapshots
WHERE recent_traces = 0 AND recent_snapshots = 0
CREATE (:LivenessAlert {node_id:"alert-" + toString(timestamp()), detected_at:datetime(),
  severity:"warning", message:"No activity detected in the last hour", project:"system"});
