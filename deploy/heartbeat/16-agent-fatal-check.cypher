// Check for fatal agents (via FleetState), create ActionProposal
MATCH (f:FleetState)
WHERE f.fatal_agents > 0
WITH f
MERGE (ap:ActionProposal {
  node_id: "ap-fatal-" + toString(date({timezone: "UTC"}))
})
ON CREATE SET
  ap.type = "agent_fatal",
  ap.description = "Fatal agents: " + f.fatal_agents,
  ap.status = "pending",
  ap.confidence = 0.95,
  ap.generated_at = datetime();
