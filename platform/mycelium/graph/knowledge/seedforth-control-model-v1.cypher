// @node_id: schema-seedforth-control-v1
// @label: SchemaContract
// SeedForth canonical work, agent, execution, decision, and evidence model.
// Idempotent: safe to bootstrap repeatedly after review.

CREATE CONSTRAINT seedforth_workstream_node_id IF NOT EXISTS
FOR (n:Workstream) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_workitem_node_id IF NOT EXISTS
FOR (n:WorkItem) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_execution_session_node_id IF NOT EXISTS
FOR (n:ExecutionSession) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_agent_process_node_id IF NOT EXISTS
FOR (n:AgentProcess) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_signal_node_id IF NOT EXISTS
FOR (n:Signal) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_decision_request_node_id IF NOT EXISTS
FOR (n:DecisionRequest) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_activity_log_node_id IF NOT EXISTS
FOR (n:ActivityLog) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_code_change_node_id IF NOT EXISTS
FOR (n:CodeChange) REQUIRE n.node_id IS UNIQUE;

MERGE (s:SchemaContract {node_id: 'schema-seedforth-control-v1'})
SET s.name = 'SeedForth canonical control model',
    s.version = '1.0.0',
    s.status = 'active',
    s.project = 'system',
    s.source = 'platform/contracts',
    s.updated_at = datetime();

UNWIND [
  {name:'Workstream', purpose:'bounded outcome or area of work', owner:'mycelium'},
  {name:'WorkItem', purpose:'actionable unit within a workstream', owner:'mycelium'},
  {name:'ExecutionSession', purpose:'bounded attempt with evidence', owner:'mycelium'},
  {name:'SubAgent', purpose:'durable agent identity and capabilities', owner:'mycelium'},
  {name:'AgentProcess', purpose:'supervised runtime process observation', owner:'delta'},
  {name:'Signal', purpose:'external observation or request', owner:'mycelium'},
  {name:'DecisionRequest', purpose:'explicit human or policy decision needed', owner:'mycelium'},
  {name:'ActivityLog', purpose:'durable execution evidence summary', owner:'mycelium'},
  {name:'CodeChange', purpose:'Git-backed change evidence', owner:'git'}
] AS spec
MERGE (t:ControlType {node_id: 'control-type-' + toLower(spec.name)})
SET t.name = spec.name, t.purpose = spec.purpose, t.authority = spec.owner,
    t.schema_version = '1.0.0', t.project = 'system'
WITH t
MATCH (s:SchemaContract {node_id: 'schema-seedforth-control-v1'})
MERGE (s)-[:DECLARES]->(t);
