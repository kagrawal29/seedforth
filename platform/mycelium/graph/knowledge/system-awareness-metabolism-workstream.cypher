// @node_id: knowledge-system-awareness-metabolism-workstream
// @label: "System Awareness & Metabolism workstream admission"
//
// Governed admission for the graph-native System Awareness & Metabolism workstream.
// Everything starts proposed so this workstream cannot pre-empt active work.
MATCH (p:Project {node_id:'proj-mycelium'})
MATCH (parent_goal:Goal {node_id:'goal-seedforth-upgrade-20260906'})
MERGE (goal:Goal {node_id:'goal-system-awareness-metabolism'})
ON CREATE SET goal.name='System Awareness & Metabolism',
  goal.project='mycelium',
  goal.scope_id='seedforth-platform',
  goal.status='active',
  goal.owner='principal-seedforth-owner',
  goal.version=1,
  goal.created_by='principal-seedforth-owner',
  goal.created_at=datetime()
SET goal.acceptance='The system correlates canonical code, runtime, graph, semantic, and learning observations into provenance-bearing advisory context and reviewable improvement proposals without silently changing authority, active execution, or external commitments.',
  goal:EntityGoal,
  goal.source='owner-session-2026-09-16',
  goal.updated_at=datetime()
MERGE (p)-[:HAS_GOAL]->(goal)
MERGE (goal)-[:SUBGOAL_OF]->(parent_goal)
MERGE (ws:Workstream {node_id:'workstream-system-awareness-metabolism'})
ON CREATE SET ws.name='System Awareness & Metabolism',
  ws.project='mycelium',
  ws.scope_id='seedforth-platform',
  ws.status='active',
  ws.created_by='principal-seedforth-owner',
  ws.created_at=datetime()
SET ws.acceptance='Canonical code, runtime, graph, semantic, and learning observations improve agent context and system diagnosis while preserving authority boundaries, provenance, bounded execution, and human review.',
  ws.mode='advisory',
  ws.updated_at=datetime()
MERGE (p)-[:HAS_WORKSTREAM]->(ws)
MERGE (ws)-[:SERVES]->(goal)
MERGE (m:Milestone {node_id:'milestone-system-awareness-metabolism'})
ON CREATE SET m.name='System Awareness & Metabolism foundation',
  m.project='mycelium',
  m.scope_id='seedforth-platform',
  m.status='planned',
  m.created_at=datetime()
MERGE (ws)-[:HAS_MILESTONE]->(m)
MERGE (m)-[:SERVES]->(goal)
WITH goal,ws,m
UNWIND [
  {id:'W01',title:'Define the canonical awareness event substrate',deliverable:'A versioned awareness event contract and graph-native validation fixtures covering code, graph, runtime, conversation, and external observations.',acceptance:'Code, graph, runtime, conversation, and external observations have one versioned event contract with source, timestamp, identity, scope, lineage, freshness, and uncertainty.'},
  {id:'W02',title:'Map repository history into the system graph',acceptance:'Every in-scope repository commit and file change can be ingested idempotently with author, parent, branch, diff lineage, and provenance without treating history as accepted progress.'},
  {id:'W03',title:'Map agent runtime and provider lifecycle',acceptance:'Agent processes, leases, attempts, provider events, heartbeats, failures, and graph state are correlated with freshness and explicit mismatch evidence.'},
  {id:'W04',title:'Build connectome activation and Hebbian evidence',acceptance:'Useful node and relationship traversals record observed activation and reinforcement evidence with decay, provenance, and no authority escalation.'},
  {id:'W05',title:'Persist shadow cross-workstream constraint advisories',acceptance:'Repeated system constraints become queryable advisory GapSignals and improve worker context without changing WorkItem status, leases, provider choice, or execution eligibility.'},
  {id:'W06',title:'Enable governed agent priority proposals',acceptance:'Agents can submit evidence-backed priority proposals linked to goals and work items; proposals are reviewable and cannot silently reprioritize or interrupt active work.'},
  {id:'W07',title:'Add semantic metabolism and retrieval',acceptance:'Graph observations can be normalized, deduplicated, embedded, retrieved, and linked with model/version/cost/provenance metadata; vector similarity never replaces graph authority.'},
  {id:'W08',title:'Add dream consolidation and self-evolution review',acceptance:'Bounded offline synthesis produces hypotheses, contradictions, and candidate changes for review, with replayable inputs, budget limits, and protected promotion gates.'}
] AS item
MERGE (w:WorkItem {node_id:'wi-awareness-metabolism-'+item.id})
ON CREATE SET w.created_at=datetime(),
  w.created_by='principal-seedforth-owner',
  w.request_hash='authored-awareness-metabolism-20260916-'+item.id,
  w.state_version=0,
  w.verification_status='unverified'
SET w.title=item.title,
  w.objective=item.title,
  w.deliverable=item.deliverable,
  w.acceptance=item.acceptance,
  w.success_criteria=[item.acceptance],
  w.project='mycelium',
  w.scope_id='seedforth-platform',
  w.program='mycelium.autonomy_control_plane.v2',
  w.workstream_id=ws.node_id,
  w.status='proposed',
  w.hold=false,
  w.execution_eligible=false,
  w.hold_reason='requires_explicit_priority_admission',
  w.source='platform/mycelium/graph/knowledge/system-awareness-metabolism-workstream.cypher',
  w.updated_at=datetime()
MERGE (m)-[:HAS_WORK_ITEM]->(w)
MERGE (w)-[:SERVES]->(goal)
MERGE (w)-[:PART_OF]->(ws);

UNWIND [
  {id:'W02',deps:['W01']},
  {id:'W03',deps:['W01']},
  {id:'W04',deps:['W01','W02','W03']},
  {id:'W05',deps:['W03']},
  {id:'W06',deps:['W01','W05']},
  {id:'W07',deps:['W01','W02','W03']},
  {id:'W08',deps:['W04','W06','W07']}
] AS item
MATCH (w:WorkItem {node_id:'wi-awareness-metabolism-'+item.id})
UNWIND item.deps AS dependency
MATCH (d:WorkItem {node_id:'wi-awareness-metabolism-'+dependency})
MERGE (w)-[:DEPENDS_ON]->(d);
