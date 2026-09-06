// Capture current state
MATCH (n) WITH count(n) as total_nodes
MATCH ()-[r]->() WITH total_nodes, count(r) as total_edges
MATCH (sa:SubAgent) WHERE sa.status = "active" WITH total_nodes, total_edges, count(sa) as active_agents
CREATE (snap:Snapshot {node_id:"snap-" + toString(timestamp()), created_at:datetime(),
  total_nodes:total_nodes, total_edges:total_edges,
  active_agents:active_agents, project:"system"});
