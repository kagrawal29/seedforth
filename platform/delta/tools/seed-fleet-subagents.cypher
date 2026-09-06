// Seed SubAgent nodes for all fleet agents
// Run via: docker exec -i mycelium-neo4j cypher-shell -u neo4j -p $PASS < seed-fleet-subagents.cypher

// First: query existing projects from the registry to get the list
// Then for each active project, create a SubAgent node

// Seed the Hub/Delta-Hub subagent
MERGE (hub:SubAgent {node_id:"subagent-delta-hub"})
SET hub.name="Delta Hub",
    hub.role="SuperAgent orchestrator",
    hub.model="deepseek-v4-pro",
    hub.status="active",
    hub.owner="Kshitiz",
    hub.tools=["graph","provision","fleet_status"],
    hub.updated_at=datetime(),
    hub.decay_protected=true;

// Link Hub to Organization
MATCH (hub:SubAgent {node_id:"subagent-delta-hub"})
MATCH (o:Organization {node_id:"org-seedforth"})
MERGE (hub)-[:BELONGS_TO {decay_protected:true}]->(o);

// Link Hub to existing Agent node if it exists
MATCH (hub:SubAgent {node_id:"subagent-delta-hub"})
OPTIONAL MATCH (a:Agent {node_id:"agent-delta-hub"})
FOREACH (agent IN CASE WHEN a IS NOT NULL THEN [a] ELSE [] END |
    MERGE (hub)-[:AGENT_IS {decay_protected:true}]->(agent)
);

// Seed individual project subagents (placeholder — actual list comes from registry)
// Each project will have its own SubAgent created by seed-fleet-graph.py
// This seeds the pattern, the script populates it

CREATE (_:Invariant {node_id:"invariant-schema-bootstrap"})
SET _.label="Schema bootstrap marker",
    _.health="healthy";

RETURN "SubAgent schema seeded";
