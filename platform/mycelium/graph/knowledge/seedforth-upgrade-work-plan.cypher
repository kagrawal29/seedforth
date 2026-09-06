// Plan admission only. No historical activity is converted into accepted progress.
MATCH (p:Project {node_id:'proj-mycelium'})
MERGE (s:ControlScope {node_id:'seedforth-platform'})
ON CREATE SET s.name='SeedForth Platform',s.portfolio_state='active',s.work_enabled=false,
s.hold_reason='capability_broker_not_yet_promoted',s.state_version=0,s.created_at=datetime(),s.updated_at=datetime()
MERGE (s)-[:MAPS_PROJECT]->(p)
MERGE (goal:Goal {node_id:'goal-seedforth-upgrade-20260906'})
ON CREATE SET goal.name='Truthful, remotely steerable, useful autonomous work',goal.project='mycelium',
goal.scope_id=s.node_id,goal.status='active',goal.owner='principal-seedforth-owner',goal.version=1,
goal.acceptance='Both active products demonstrate scoped direction-to-execution-to-independent-evidence loops. Humans can inspect, steer, and reconnect remotely. Authority, outage, replay, recovery, and honest soak tests pass.',
goal.source='owner-session-2026-09-06',goal.created_at=datetime()
MERGE (p)-[:HAS_GOAL]->(goal)
MERGE (ws:Workstream {node_id:'workstream-seedforth-upgrade-20260906'})
ON CREATE SET ws.name='SeedForth system upgrade',ws.project='mycelium',ws.scope_id=s.node_id,ws.status='active'
MERGE (p)-[:HAS_WORKSTREAM]->(ws)
MERGE (ws)-[:SERVES]->(goal)
WITH p,s,goal,ws
UNWIND [
{id:'W00',phase:0,title:'Verify current baseline and writer census',acceptance:'Current target, release, streams, writers, privilege boundaries, and unknowns have source evidence.'},
{id:'W01',phase:0,title:'Reconcile every audit finding',acceptance:'A01–A17 map to applicable source/runtime findings and concrete disposition.'},
{id:'W02',phase:1,title:'Qualify human operating journeys',acceptance:'U01–U16 are covered, including failure, mobile, deep work, and unattended return.'},
{id:'W03',phase:1,title:'Map portfolio and bounded mandates',acceptance:'Active product priorities, retained service obligations, archive dispositions, and bounded grants are explicit.'},
{id:'W04',phase:2,title:'Establish canonical graph contracts',acceptance:'D01–D15 and S01–S10 have implemented or explicitly pending compatibility and migration contracts.'},
{id:'W05',phase:2,title:'Qualify access and threat model',acceptance:'Authority roots, isolation, prompt injection, confused-deputy, and remote-client tests are specified and executable.'},
{id:'W06',phase:2,title:'Establish migration and verification gates',acceptance:'Batches have scoped changes, source versions, independent checks, rollback, and observation windows.'},
{id:'W07',phase:3,title:'Deploy trustworthy runner evidence',acceptance:'Known failures fail, dependencies stop, and actual runs record source, generation, atom attempts, and uncertainty.'},
{id:'W08',phase:3,title:'Migrate identity, scope, and evidence foundation',acceptance:'Identity preflight, preserved aliases, twice-run schema, isolated restore, and deployed source receipts pass.'},
{id:'W09',phase:4,title:'Connect runtime and work sensing',acceptance:'Sources expose freshness, coverage, attempts, ordering, lineage, and divergence without inferring portfolio authority.'},
{id:'W10',phase:4,title:'Integrate bounded Graphify source sensing',acceptance:'Pinned extractor and source snapshots reproduce tested discrepancies with coverage and inference provenance.'},
{id:'W11',phase:4,title:'Deliver truthful scoped board',acceptance:'Humans can inspect useful current state and evidence on desktop/mobile with honest stale, legacy, and unavailable states.'},
{id:'W12',phase:5,title:'Enforce capabilities and protected policy',acceptance:'Grant, revocation, budget, destination, scope, prompt-injection, and policy-promotion denial tests pass.'},
{id:'W13',phase:5,title:'Close the governed execution loop',acceptance:'Pilot intent, claim, invocation, artifact, independent verification, review, and observed outcome form a causal chain.'},
{id:'W14',phase:5,title:'Deliver controls, timelines, and evidence review',acceptance:'Versioned controls and exact-artifact review work through the UI, including combined failure scenario C01.'},
{id:'W15',phase:6,title:'Deliver remote MCP and teammate access',acceptance:'Scoped graph and Delta conversation survive disconnect and pass authorized desktop/client and mobile workflows.'},
{id:'W16',phase:7,title:'Qualify both products and agent lifecycle',acceptance:'Both projects support isolated useful work, provisioning, bounded delegation, and independent Charlie/Delta coordination.'},
{id:'W17',phase:7,title:'Archive nonpriority work safely',acceptance:'New work is held, attempts reconciled, history preserved, services retained, and reactivation prevention tested.'},
{id:'W18',phase:7,title:'Demonstrate useful unattended operation',acceptance:'Bounded unattended runs produce verified outputs, preserve budgets, use fallback work, and yield an honest return report.'},
{id:'W19',phase:8,title:'Close healing and incident loops',acceptance:'Repairs have independent postconditions, bounded attempts, safe rollback, and explicit unresolved incidents.'},
{id:'W20',phase:8,title:'Govern learning and self-modification',acceptance:'Knowledge correction and policy evolution preserve provenance, measured usefulness, budget conservation, and protected promotion.'},
{id:'W21',phase:9,title:'Qualify reliability and continuity',acceptance:'Restore, outage, replay, revocation, and observed soak evidence meet the declared release gates without claiming unelapsed time.'}
] AS package
MERGE (m:Milestone {node_id:'milestone-upgrade-phase-'+toString(package.phase)})
ON CREATE SET m.name='Upgrade phase '+toString(package.phase),m.scope_id=s.node_id,m.project='mycelium',m.status='planned'
MERGE (ws)-[:HAS_MILESTONE]->(m)
MERGE (m)-[:SERVES]->(goal)
MERGE (w:WorkItem {node_id:'wi-upgrade-'+package.id})
ON CREATE SET w.title=package.title,w.acceptance=package.acceptance,w.scope_id=s.node_id,
w.project='mycelium',w.status='proposed',w.state_version=0,w.hold=false,
w.verification_status='unverified',w.created_by='principal-seedforth-owner',
w.request_hash='authored-upgrade-plan-20260906-'+package.id,w.created_at=datetime(),w.updated_at=datetime(),
w.source='architecture/upgrade/migration-and-operations.md',w.package_id=package.id
MERGE (m)-[:HAS_WORK_ITEM]->(w);

UNWIND [
{id:'W01',deps:['W00']},{id:'W02',deps:['W00']},{id:'W03',deps:['W00']},
{id:'W04',deps:['W01','W02','W03']},{id:'W05',deps:['W02','W04']},
{id:'W06',deps:['W01','W04','W05']},{id:'W07',deps:['W04','W05','W06']},
{id:'W08',deps:['W07']},{id:'W09',deps:['W08']},{id:'W10',deps:['W08']},
{id:'W11',deps:['W02','W09']},{id:'W12',deps:['W05','W08']},
{id:'W13',deps:['W07','W09','W12']},{id:'W14',deps:['W11','W13']},
{id:'W15',deps:['W12','W13','W14']},{id:'W16',deps:['W13','W15']},
{id:'W17',deps:['W03','W08','W16']},{id:'W18',deps:['W14','W15','W16']},
{id:'W19',deps:['W07','W12','W13']},{id:'W20',deps:['W09','W13','W19']},
{id:'W21',deps:['W17','W18','W19','W20']}
] AS item
MATCH (w:WorkItem {node_id:'wi-upgrade-'+item.id})
UNWIND item.deps AS dependency
MATCH (d:WorkItem {node_id:'wi-upgrade-'+dependency})
MERGE (w)-[:DEPENDS_ON]->(d);
