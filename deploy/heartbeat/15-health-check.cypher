// Check system health and create an ActionProposal when unhealthy
MATCH (h:SystemHealth)
WHERE h.load_15min > 20 OR h.cpu_pct > 90 OR h.mem_used_gb > h.mem_total_gb * 0.85
WITH h
MERGE (ap:ActionProposal {
  node_id: "ap-health-" + toString(date({timezone: "UTC"})),
  type: "system_health",
  description: "System under pressure: load=" + h.load_15min + ", cpu=" + h.cpu_pct + "%, mem=" + h.mem_used_gb + "GB",
  status: "pending",
  confidence: 0.9,
  generated_at: datetime()
});
