// @node_id: knowledge-awareness-event-contract-v1
// @label: "Awareness event contract v1"
//
// Canonical event substrate for code, graph, runtime, conversation, and
// external observations. The contract is descriptive and validation-oriented;
// it does not grant authority or promote an observation into execution state.
MERGE (c:AwarenessEventContract {node_id:'awareness-event-contract-v1'})
ON CREATE SET c.created_at=datetime(), c.version=1
SET c.name='Canonical awareness event contract',
    c.version=1,
    c.status='active',
    c.authority='observation_only',
    c.scope_id='seedforth-platform',
    c.source='platform/mycelium/graph/knowledge/awareness-event-contract-v1.cypher',
    c.updated_at=datetime()
WITH c
UNWIND [
  {name:'event_id', required:true, semantic:'stable idempotency key'},
  {name:'event_type', required:true, semantic:'normalized observation type'},
  {name:'source_kind', required:true, semantic:'code, graph, runtime, conversation, or external'},
  {name:'source_id', required:true, semantic:'origin adapter, node, process, or repository'},
  {name:'observed_at', required:true, semantic:'time observation occurred'},
  {name:'ingested_at', required:true, semantic:'time graph accepted observation'},
  {name:'observed_by', required:true, semantic:'principal or sensor identity'},
  {name:'scope_id', required:true, semantic:'authorization and tenancy boundary'},
  {name:'lineage', required:true, semantic:'parent event, revision, attempt, or conversation lineage'},
  {name:'freshness_seconds', required:true, semantic:'age at evaluation time'},
  {name:'uncertainty', required:true, semantic:'explicit confidence or unknown state'},
  {name:'payload_ref', required:true, semantic:'content reference without authority implication'}
] AS field
MERGE (f:AwarenessEventField {node_id:'awareness-event-v1-'+field.name})
SET f.name=field.name, f.required=field.required, f.semantic=field.semantic,
    f.version=1, f.updated_at=datetime()
MERGE (c)-[:REQUIRES_FIELD]->(f)
RETURN c.node_id AS contract, count(*) AS fields;
