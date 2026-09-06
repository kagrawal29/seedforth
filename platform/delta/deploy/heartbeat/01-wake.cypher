// Check if there's new data since last heartbeat
MATCH (n) WHERE n.created_at > datetime() - duration({hours:1}) RETURN count(n) > 0 AS hasWork;
