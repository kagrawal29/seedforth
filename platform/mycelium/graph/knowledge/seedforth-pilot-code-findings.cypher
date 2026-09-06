// Explicit observed local-checkout baseline, not a claim about remote app revision.
// This source is separately admitted by the upgrade operator, not worker startup.
MATCH (p:Project {node_id:'project-cajon-sensei'})
MERGE (ws:Workstream {node_id:'workstream-cajon-practice-reliability'})
ON CREATE SET ws.name='Cajon practice reliability',ws.scope_id='cajon-sensei',ws.status='active'
MERGE (p)-[:HAS_WORKSTREAM]->(ws)
MERGE (m:Milestone {node_id:'milestone-cajon-accurate-practice-tracking'})
ON CREATE SET m.name='Accurate practice tracking',m.scope_id='cajon-sensei',m.status='planned'
MERGE (ws)-[:HAS_MILESTONE]->(m)
MERGE (w:WorkItem {node_id:'wi-cajon-partial-loop-credit'})
ON CREATE SET w.title='Do not credit a full groove on the first beat',w.scope_id='cajon-sensei',
w.project='cajon-sensei',w.status='proposed',w.state_version=0,w.hold=true,
w.verification_status='baseline_failure_observed',w.created_at=datetime(),w.updated_at=datetime(),
w.acceptance='At 80 bpm, 200ms of playback records zero complete grooves. A full cycle records exactly one. Stop/restart and tempo changes cannot create partial-cycle credits. Verify through Playwright CLI against exact artifact.',
w.authority='owner-upgrade-pilot-delegation-20260906',w.source_revision='498b17acbd832b37744b9138abf3e4d52bc81f57'
MERGE (m)-[:HAS_WORK_ITEM]->(w)
MERGE (r:TestRun {node_id:'baseline-cajon-partial-loop-20260906T154646'})
ON CREATE SET r.scope_id='cajon-sensei',r.status='failed',r.runner='playwright-cli-0.1.19',
r.source_revision='498b17acbd832b37744b9138abf3e4d52bc81f57',r.source_path='app/index.html',
r.source_kind='local_clean_checkout',r.expected_loops=0,r.actual_loops=1,r.simulated_ms=200,r.tempo_bpm=80,
r.evidence_kind='independent_baseline_reproduction',r.recorded_at=datetime(),
r.observation='Browser reproduced one credited loop after first subdivision. Full cycle at this tempo is 3000ms. No musical performance was measured.'
MERGE (r)-[:INFORMS]->(w);
