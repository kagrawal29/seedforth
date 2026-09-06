// @node_id: protocol-anchor-orphan-couplings
// @label: "Anchor orphan CrossProjectCoupling nodes to real source/target nodes"
// @kind: protocol
// @fsd_layer: features
//
// Context: detect-cross-couplings.cypher writes :CrossProjectCoupling metadata
// nodes but never anchors them to the nodes they couple. As of forest-state-v1
// on pulse-dev, 9 couplings exist with zero edges. The forest cannot traverse
// across subgraphs because the bridges are floating.
//
// This protocol maps each coupling to its two endpoints using the hint in its
// node_id (the `manual-coup-<hint>` suffix) and materializes [:COUPLES_WITH]
// edges — the bridge type already allowed by the Forest Promise.
// ============================================================================

// ----------------------------------------------------------------------------
// Each entry: coupling_id → (left_match, right_match)
// left_match / right_match are Cypher fragments matching a single node.
// Keep idempotent via MERGE.
// ----------------------------------------------------------------------------

// manual-coup-auth: auth pattern across friend ↔ mycelium
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-auth'})
MATCH (a:Protocol {project: 'mycelium'}) WHERE a.node_id CONTAINS 'auth'
MATCH (b) WHERE b.project = 'maverick-dev-friend' AND (b.node_id CONTAINS 'auth' OR coalesce(b.label,'') CONTAINS 'auth')
WITH c, a, b LIMIT 1
MERGE (c)-[:ANCHORS_LEFT]->(a)
MERGE (c)-[:ANCHORS_RIGHT]->(b)
MERGE (a)-[:COUPLES_WITH {via: c.node_id, kind: 'auth'}]->(b);

// manual-coup-being-maverick-dev: Being ↔ Being
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-being-maverick-dev'})
MATCH (a:Being {project: 'mycelium'})
MATCH (b:Being {project: 'maverick-dev'})
MERGE (c)-[:ANCHORS_LEFT]->(a)
MERGE (c)-[:ANCHORS_RIGHT]->(b)
MERGE (a)-[:COUPLES_WITH {via: c.node_id, kind: 'being-kinship'}]->(b);

// manual-coup-claudeagent-being: :ClaudeAgent in friend ↔ :Being in mycelium
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-claudeagent-being'})
MATCH (a:Being {project: 'mycelium'})
MATCH (b:ClaudeAgent) WHERE b.project = 'maverick-dev-friend'
WITH c, a, b LIMIT 5
MERGE (c)-[:ANCHORS_LEFT]->(a)
MERGE (c)-[:ANCHORS_RIGHT]->(b)
MERGE (a)-[:COUPLES_WITH {via: c.node_id, kind: 'agent-is-being'}]->(b);

// manual-coup-testcase-drift: the external-vs-internal inversion
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-testcase-drift'})
MATCH (i:Inversion {node_id: 'inv-testcase-semantic-drift'})
MERGE (c)-[:REALIZES]->(i);

// manual-coup-cli-commands: mycelium CLI ↔ friend dispatch surfaces
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-cli-commands'})
MATCH (a) WHERE a.project='mycelium' AND coalesce(a.node_id,'') CONTAINS 'cli-commands'
MATCH (b) WHERE b.project='maverick-dev-friend' AND (labels(b)[0] IN ['CodeFunction','Protocol']) AND coalesce(b.node_id,'') =~ '(?i).*(dispatch|command|cli).*'
WITH c, a, b LIMIT 1
MERGE (c)-[:ANCHORS_LEFT]->(a)
MERGE (c)-[:ANCHORS_RIGHT]->(b)
MERGE (a)-[:COUPLES_WITH {via: c.node_id, kind: 'dispatch-surface'}]->(b);

// manual-coup-ingestion: ingestion pipelines
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-ingestion'})
MATCH (a:Protocol {project: 'mycelium'}) WHERE a.node_id CONTAINS 'ingest'
MATCH (b) WHERE b.project='maverick-dev-friend' AND coalesce(b.node_id,'') =~ '(?i).*(ingest|pipeline|fetch).*'
WITH c, a, b LIMIT 1
MERGE (c)-[:ANCHORS_LEFT]->(a)
MERGE (c)-[:ANCHORS_RIGHT]->(b)
MERGE (a)-[:COUPLES_WITH {via: c.node_id, kind: 'ingestion-pipeline'}]->(b);

// manual-coup-protocol-feature: Protocol ↔ Feature (the core inversion concrete-vs-abstract)
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-protocol-feature'})
MATCH (i:Inversion {node_id: 'inv-codefunc-vs-protocol'})
MERGE (c)-[:REALIZES]->(i);

// manual-coup-scaffolding: structural parallel
MATCH (c:CrossProjectCoupling {node_id: 'manual-coup-scaffolding'})
MATCH (a:ForestPromise {node_id: 'forest-promise-sovereignty'})
MERGE (c)-[:ANCHORS_LEFT]->(a);

RETURN 'Orphan couplings anchored; [:COUPLES_WITH] edges materialized between subgraphs.' AS checkpoint;
