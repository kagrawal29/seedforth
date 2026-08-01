// Remove old append-only snapshots (one-time migration)
MATCH (fs:FleetSnapshot) DELETE fs;

// Expire transient nodes
MATCH (st:SessionTrace)
WHERE st.created_at < datetime() - duration({days:2})
DELETE st;
