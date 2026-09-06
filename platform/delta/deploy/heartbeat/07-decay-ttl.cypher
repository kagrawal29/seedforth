// Expire transient nodes (single statement)
MATCH (st:SessionTrace)
WHERE st.created_at < datetime() - duration({days:2})
DETACH DELETE st;
