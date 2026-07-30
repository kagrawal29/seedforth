// Delete transient nodes with zero edges
MATCH (st:SessionTrace)
WHERE NOT (st)-[]-()
  AND st.created_at < datetime() - duration({hours:24})
DELETE st;
