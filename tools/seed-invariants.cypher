// Seed fleet invariants into Neo4j
// Run: docker exec -i mycelium-neo4j cypher-shell -u neo4j -p $PASS < seed-invariants.cypher

// I1 — Rooted tree: every SubAgent must have a BELONGS_TO path to an Organization
MERGE (i1:Invariant {node_id:"invariant-rooted-tree"})
SET i1.label="I1: Rooted tree — no orphan SubAgents",
    i1.check_cypher="MATCH (sa:SubAgent) WHERE NOT (sa)-[:BELONGS_TO*1..5]->(:Organization) RETURN sa.name AS orphan",
    i1.heal_protocol="MATCH (sa:SubAgent) WHERE NOT (sa)-[:BELONGS_TO*1..5]->(:Organization) SET sa.status='orphan'",
    i1.severity="high",
    i1.category="structural",
    i1.health="healthy",
    i1.created_at=datetime();

// I2 — Scope boundary: agent must only write within its own organization
MERGE (i2:Invariant {node_id:"invariant-scope-boundary"})
SET i2.label="I2: Scope boundary — agents write within their org",
    i2.check_cypher="MATCH (k:Knowledge) WHERE k.agent IS NOT NULL AND k.scope IS NOT NULL MATCH (o:Organization) WHERE o.name = k.scope RETURN count(*) = count(k) AS valid",
    i2.severity="critical",
    i2.category="security",
    i2.health="healthy",
    i2.created_at=datetime();

// I3 — Decay protection: structural edges must be protected from heartbeat decay
MERGE (i3:Invariant {node_id:"invariant-decay-protection"})
SET i3.label="I3: Decay protection — structural edges are protected",
    i3.check_cypher="MATCH ()-[r:BELONGS_TO]->() WHERE NOT r.decay_protected RETURN count(r) AS unprotected",
    i3.heal_protocol="MATCH ()-[r:BELONGS_TO]->() WHERE NOT r.decay_protected SET r.decay_protected=true",
    i3.severity="medium",
    i3.category="integrity",
    i3.health="healthy",
    i3.created_at=datetime();

// I4 — Project liveness: every project must have activity within 48h
MERGE (i4:Invariant {node_id:"invariant-project-liveness"})
SET i4.label="I4: Project liveness — activity within 48h",
    i4.check_cypher="MATCH (p:Project) WHERE p.last_activity < datetime() - duration({hours:48}) RETURN p.name AS stale_project, p.last_activity",
    i4.severity="medium",
    i4.category="operational",
    i4.health="healthy",
    i4.created_at=datetime();

// I5 — SubAgent liveness: every SubAgent must have reported within 24h
MERGE (i5:Invariant {node_id:"invariant-agent-liveness"})
SET i5.label="I5: Agent liveness — SubAgent heartbeat within 24h",
    i5.check_cypher="MATCH (sa:SubAgent) WHERE sa.status='active' AND (sa.updated_at IS NULL OR sa.updated_at < datetime() - duration({hours:24})) RETURN sa.name AS dead_agent",
    i5.severity="high",
    i5.category="operational",
    i5.health="healthy",
    i5.created_at=datetime();

// I6 — No stale FleetSnapshots: at least one snapshot per day
MERGE (i6:Invariant {node_id:"invariant-fresh-snapshot"})
SET i6.label="I6: Fresh snapshot — at least one FleetSnapshot per day",
    i6.check_cypher="MATCH (fs:FleetSnapshot) WHERE fs.created_at > datetime() - duration({hours:24}) RETURN count(fs) >= 1 AS has_fresh_snapshot",
    i6.severity="medium",
    i6.category="observability",
    i6.health="healthy",
    i6.created_at=datetime();

return "Seeded " + count(*) + " invariants" as result;
