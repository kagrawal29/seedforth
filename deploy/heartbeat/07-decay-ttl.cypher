// Expire transient nodes
MATCH (st:SessionTrace)
WHERE st.created_at < datetime() - duration({days:2})
DELETE st;

MATCH (fs:FleetSnapshot)
WHERE fs.created_at < datetime() - duration({days:7})
DELETE fs;
