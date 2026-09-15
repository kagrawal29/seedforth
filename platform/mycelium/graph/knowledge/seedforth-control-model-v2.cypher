// Additive constraints only; duplicate/identity preflight must pass before live use.
CREATE CONSTRAINT seedforth_atomrun_id IF NOT EXISTS FOR (n:AtomRun) REQUIRE n.node_id IS UNIQUE;
// Historical ProtocolRun IDs collide; preserve them and constrain only v2 runs.
CREATE CONSTRAINT seedforth_versioned_protocolrun_id IF NOT EXISTS FOR (n:VersionedProtocolRun) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_testrun_id IF NOT EXISTS FOR (n:TestRun) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_invocation_id IF NOT EXISTS FOR (n:Invocation) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_invocation_result_id IF NOT EXISTS FOR (n:InvocationResult) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_mandate_id IF NOT EXISTS FOR (n:Mandate) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_budget_id IF NOT EXISTS FOR (n:Budget) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_capability_id IF NOT EXISTS FOR (n:Capability) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_receipt_id IF NOT EXISTS FOR (n:Receipt) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_transition_id IF NOT EXISTS FOR (n:StateTransition) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_observation_id IF NOT EXISTS FOR (n:Observation) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_principal_id IF NOT EXISTS FOR (n:Principal) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_grant_id IF NOT EXISTS FOR (n:Grant) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_scope_id IF NOT EXISTS FOR (n:ControlScope) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_operation_id IF NOT EXISTS FOR (n:ControlOperation) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT seedforth_operation_revision_id IF NOT EXISTS FOR (n:OperationRevision) REQUIRE n.node_id IS UNIQUE;
MERGE (s:SchemaContract {node_id:'schema-seedforth-control-v2'})
ON CREATE SET s.version='2.0.0',s.project='system',s.created_at=datetime()
SET s.source='platform/mycelium/graph/knowledge/seedforth-control-model-v2.cypher';
