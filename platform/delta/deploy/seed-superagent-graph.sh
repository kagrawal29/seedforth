#!/bin/bash
# Seed the SuperAgent graph: organizations, agents, project connections
set -euo pipefail
NEO4J_PASS="${NEO4J_PASSWORD:?set NEO4J_PASSWORD in the runtime environment}"

CS="docker exec mycelium-neo4j cypher-shell -u neo4j -p $NEO4J_PASS"

echo "Seeding organizations..."
$CS 'MERGE (:Organization {node_id:"org-seedforth", name:"SeedForth", entity_type:"earner", status:"active"})'
$CS 'MERGE (:Organization {node_id:"org-solveos", name:"SolveOS", entity_type:"earner", status:"active"})'
$CS 'MERGE (:Organization {node_id:"org-flowingindian", name:"FlowingIndian", entity_type:"earner", status:"active"})'
$CS 'MERGE (:Organization {node_id:"org-sceneforthos", name:"SceneforthOS", entity_type:"earner", status:"active"})'
$CS 'MERGE (:Organization {node_id:"org-revti", name:"Revti Digital", entity_type:"client", status:"active"})'

echo "Creating SuperAgent..."
$CS 'MERGE (hub:Agent {node_id:"agent-delta-hub", name:"Delta Hub", role:"SuperAgent orchestrator", model:"deepseek-v4-pro", status:"active", owner:"Kshitiz"})'

echo "Linking projects to organizations..."
for proj in $($CS 'MATCH (p:Project) RETURN p.name' | tail -n +2); do
    $CS "MATCH (p:Project {name:\"$proj\"}) MATCH (o:Organization {name:\"SeedForth\"}) MERGE (p)-[:BELONGS_TO]->(o)"
done

echo "Linking Hub to fleet..."
$CS 'MATCH (hub:Agent {node_id:"agent-delta-hub"}) MATCH (p:Project) MERGE (hub)-[:OVERSEES]->(p)'
$CS 'MATCH (hub:Agent {node_id:"agent-delta-hub"}) MATCH (o:Organization) MERGE (hub)-[:MANAGES]->(o)'

echo "Graph seeded"
