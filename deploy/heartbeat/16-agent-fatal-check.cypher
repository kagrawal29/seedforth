// Check for fatal agents in the fleet and create an ActionProposal
MATCH (f:FleetState)
WHERE f.fatal_agents > 0
WITH f
MERGE (ap:ActionProposal {
  node_id: "ap-fatal-" + toString(date({timezone: "UTC"})),
  type: "agent_fatal",
  description: "Fatal agents: " + f.fatal_agents,
  status: "pending",
  confidence: 0.95,
  generated_at: datetime()
});
