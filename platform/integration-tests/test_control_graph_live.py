"""Actual Cypher tests, only on the dedicated disposable loopback endpoint.

Run with CONTROL_TEST_URL=http://127.0.0.1:27474. No production environment or
Neo4j credentials are used. Every fixture uses an isolated random scope.
"""
import concurrent.futures
import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.graph import Graph, GraphError

URL = os.environ.get("CONTROL_TEST_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="explicit disposable endpoint required")


@pytest.fixture(scope="module")
def graph():
    if URL != "http://127.0.0.1:27474":
        pytest.fail("Only dedicated disposable endpoint is allowed")
    g = Graph(URL, user="", password="")
    for filename in ["seedforth-control-model-v1.cypher", "seedforth-control-model-v2.cypher"]:
        source = Path(__file__).parents[1] / "mycelium/graph/knowledge" / filename
        statements = '\n'.join(line for line in source.read_text().splitlines()
                               if not line.lstrip().startswith('//')).split(';')
        for _ in range(2):
            for statement in statements:
                if statement.strip():
                    g.query(statement)
    g.promote()
    return g


@pytest.fixture
def case(graph):
    scope = 'fixture-' + uuid4().hex
    actor = scope + '-lead'
    worker = scope + '-worker'
    graph.query("CREATE (p:Project {node_id:$scope,name:$scope}) "
                "CREATE (s:ControlScope {node_id:$scope,name:$scope,work_enabled:true}) "
                "CREATE (s)-[:MAPS_PROJECT]->(p) "
                "CREATE (p)-[:HAS_WORKSTREAM]->(:Workstream {node_id:$scope+'-ws'})"
                "-[:HAS_MILESTONE]->(:Milestone {node_id:$scope+'-m'}) "
                "CREATE (a:Principal {node_id:$actor,enabled:true}) "
                "CREATE (a)-[:HAS_GRANT]->(:Grant {node_id:$actor+'-grant',scope:$scope,"
                "revoked:false,permissions:['read','work.create','work.schedule','work.control','work.review','work.reconcile']}) "
                "CREATE (b:Principal {node_id:$worker,enabled:true}) "
                "CREATE (b)-[:HAS_GRANT]->(:Grant {node_id:$worker+'-grant',scope:$scope,"
                "revoked:false,permissions:['read','work.execute']}) "
                "CREATE (b)-[:REPRESENTS]->(:SubAgent {node_id:$worker,project:$scope})",
                dict(scope=scope, actor=actor, worker=worker))
    return dict(scope=scope, actor=actor, worker=worker, id=scope+'-work', milestone=scope+'-m')


def create(graph, c):
    return graph.operation('create-work', c['actor'], c['scope'], id=c['id'],
                           milestone=c['milestone'], title='Verify staged artifact',
                           acceptance='Independent checker accepts exact hash',request_hash='request-a')


def ready(graph, c):
    create(graph, c)
    return graph.operation('ready-work',c['actor'],c['scope'],id=c['id'],version=0,event_id=uuid4().hex)


def claim(graph, c):
    return graph.operation('claim-work',c['worker'],c['scope'],id=c['id'],version=1,
                           attempt=uuid4().hex,event_id=uuid4().hex)


def test_idempotent_creation_and_cross_scope_denial(graph, case):
    assert create(graph, case)[0]['version'] == 0
    assert create(graph, case)[0]['version'] == 0
    assert graph.query("MATCH (w:WorkItem {node_id:$id}) RETURN count(w) AS n",case)[0]['n'] == 1
    assert graph.operation('read-work',case['actor'],'wrong-scope') == []
    assert graph.operation('read-work','unknown-person',case['scope']) == []


def test_concurrent_claim_has_one_winner(graph, case):
    ready(graph,case)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: claim(graph,case), range(2)))
    assert sum(bool(r) for r in results) == 1


def test_hold_blocks_execution_and_version_conflicts(graph, case):
    ready(graph,case)
    assert graph.operation('hold-work',case['actor'],case['scope'],id=case['id'],version=1,
                           hold=True,event_id=uuid4().hex)
    assert claim(graph,case) == []
    assert graph.operation('hold-work',case['actor'],case['scope'],id=case['id'],version=1,
                           hold=False,event_id=uuid4().hex) == []


def test_failure_does_not_create_progress(graph, case):
    ready(graph,case)
    attempt = claim(graph,case)[0]
    rows = graph.operation('finish-work',case['worker'],case['scope'],attempt=attempt['attempt'],
        fence=attempt['fence'],outcome='failed',artifact_ref=None,artifact_hash=None,event_id=uuid4().hex)
    assert rows[0]['status'] == 'blocked'
    assert graph.query("MATCH (p:ProgressEvent {scope_id:$scope}) RETURN count(p) AS n",case)[0]['n'] == 0


def test_revocation_and_expired_lease_prevent_completion(graph, case):
    ready(graph,case)
    attempt = claim(graph,case)[0]
    graph.query("MATCH (g:Grant {node_id:$id}) SET g.revoked=true",{'id':case['worker']+'-grant'})
    params=dict(attempt=attempt['attempt'],fence=attempt['fence'],outcome='succeeded',
                artifact_ref='fixture.txt',artifact_hash='a'*64,event_id=uuid4().hex)
    assert graph.operation('finish-work',case['worker'],case['scope'],**params) == []
    graph.query("MATCH (g:Grant {node_id:$id}) SET g.revoked=false",{'id':case['worker']+'-grant'})
    graph.query("MATCH (w:WorkItem {node_id:$id}) SET w.lease_until=datetime()-duration('PT1S')",case)
    assert graph.operation('finish-work',case['worker'],case['scope'],**params) == []


def test_changed_graph_operation_is_not_executed(graph, case):
    graph.query("MATCH (a:ControlOperation {node_id:'control-read-scope'}) SET a.cypher='RETURN 1'")
    try:
        with pytest.raises(GraphError,match='generation_mismatch'):
            graph.operation('read-scope',case['actor'],case['scope'])
    finally:
        graph.promote()
    import hashlib
    revisions=graph.query("MATCH (:ControlOperation {node_id:'control-read-scope'})-[:HAS_REVISION]->(v:OperationRevision) RETURN v.cypher AS cypher,v.source_hash AS hash")
    assert revisions
    assert all(hashlib.sha256(row['cypher'].encode()).hexdigest()==row['hash'] for row in revisions)


def test_lease_renewal_and_expiry_require_reconciliation(graph, case):
    ready(graph,case)
    attempt=claim(graph,case)[0]
    params=dict(attempt=attempt['attempt'],fence=attempt['fence'])
    assert graph.operation('renew-work',case['worker'],case['scope'],**params)
    graph.query("MATCH (w:WorkItem {node_id:$id}) SET w.lease_until=datetime()-duration('PT1S')",case)
    assert graph.operation('renew-work',case['worker'],case['scope'],**params)==[]
    assert graph.operation('reconcile-expired-work',case['worker'],case['scope'])==[]
    result=graph.operation('reconcile-expired-work',case['actor'],case['scope'])
    assert result[0]['attempt_status']=='unknown'
    assert graph.operation('reconcile-expired-work',case['actor'],case['scope'])==[]
    assert graph.operation('finish-work',case['worker'],case['scope'],**params,
        outcome='succeeded',artifact_ref='late.txt',artifact_hash='c'*64,event_id=uuid4().hex)==[]
    row=graph.query("MATCH (w:WorkItem {node_id:$id}) RETURN w.status AS status,w.hold AS hold,w.fence AS fence",case)[0]
    assert row==dict(status='blocked',hold=True,fence=attempt['fence']+1)


def test_success_requires_independent_verification_and_review(graph, case):
    ready(graph,case)
    attempt = claim(graph,case)[0]
    receipt = uuid4().hex
    graph.operation('finish-work',case['worker'],case['scope'],attempt=attempt['attempt'],
        fence=attempt['fence'],outcome='succeeded',artifact_ref='fixture.txt',
        artifact_hash='a'*64,event_id=receipt)
    params=dict(id=case['id'],version=3,receipt=receipt,artifact_hash='a'*64,
                test_run=uuid4().hex,accept=True,event_id=uuid4().hex)
    assert graph.operation('review-work',case['actor'],case['scope'],**params) == []
    graph.query("MATCH (r:Receipt {node_id:$receipt}) "
                "CREATE (v:TestRun {node_id:$test_run,scope_id:$scope,status:'passed',"
                "artifact_hash:$artifact_hash,runner:'independent-checker',finished_at:datetime()}) "
                "CREATE (v)-[:VERIFIES]->(r)",{**params,'scope':case['scope']})
    assert graph.operation('review-work',case['actor'],case['scope'],**params)[0]['status'] == 'done'
    assert graph.operation('review-work',case['actor'],case['scope'],**params) == []
    assert graph.query("MATCH (p:ProgressEvent {scope_id:$scope}) RETURN count(p) AS n",case)[0]['n'] == 1


def test_reject_without_passing_test_does_not_award_progress(graph, case):
    ready(graph,case)
    attempt=claim(graph,case)[0]
    receipt=uuid4().hex
    graph.operation('finish-work',case['worker'],case['scope'],attempt=attempt['attempt'],
        fence=attempt['fence'],outcome='succeeded',artifact_ref='fixture.txt',
        artifact_hash='b'*64,event_id=receipt)
    result=graph.operation('review-work',case['actor'],case['scope'],id=case['id'],version=3,
        receipt=receipt,artifact_hash='b'*64,test_run=None,accept=False,event_id=uuid4().hex)
    assert result[0]['status']=='proposed'
    assert graph.query("MATCH (p:ProgressEvent {scope_id:$scope}) RETURN count(p) AS n",case)[0]['n']==0


def test_real_runner_records_per_atom_and_stops_failed_chain(graph, monkeypatch):
    import importlib.util
    monkeypatch.setenv('NEO4J_PASSWORD','fixture-only')
    path=Path(__file__).parents[1]/'delta/tools/graph-runner-v2.py'
    spec=importlib.util.spec_from_file_location('live_runner',path)
    runner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    def query(q,p=None):
        return [list(row.values()) for row in graph.query(q,p)]
    monkeypatch.setattr(runner,'q_strict',query)
    pid='fixture-protocol-'+uuid4().hex
    graph.query("CREATE (p:Protocol {node_id:$pid,enabled:true}) "
                "CREATE (a:CypherAtom {node_id:$pid+'-first',cypher:'RETURN 1'}) "
                "CREATE (b:CypherAtom {node_id:$pid+'-fail',cypher:'INVALID QUERY'}) "
                "CREATE (c:CypherAtom {node_id:$pid+'-last',cypher:'CREATE (:MustNotExist)'}) "
                "CREATE (p)-[:FIRST_ATOM]->(a) CREATE (a)-[:FOLLOWS]->(b) "
                "CREATE (b)-[:FOLLOWS]->(c)",{'pid':pid})
    assert runner.execute_protocol(pid) is False
    rows=graph.query("MATCH (r:ProtocolRun {protocol:$pid}) "
                     "OPTIONAL MATCH (r)-[:HAS_ATOM_RUN]->(a:AtomRun) "
                     "RETURN r.status AS status,r.atoms_ok AS ok,count(a) AS attempts",{'pid':pid})
    assert rows==[{'status':'failed','ok':1,'attempts':2}]
    assert graph.query("MATCH (n:MustNotExist) RETURN count(n) AS n")[0]['n']==0


def test_runtime_observations_replay_late_failure_and_staleness(graph, case):
    from datetime import datetime,timedelta,timezone
    graph.query("MATCH (p:Principal {node_id:$actor}) "
        "CREATE (p)-[:HAS_GRANT]->(:Grant {scope:$scope,revoked:false,permissions:['source.observe']}) "
        "CREATE (:SourceStream {node_id:$scope+'-source',scope_id:$scope,enabled:true,"
        "adapter:'local-opencode-process-v1',freshness_seconds:180})",case)
    now=datetime.now(timezone.utc)
    params=dict(source=case['scope']+'-source',observed_at=now.isoformat(),status='running',
        process_count=1,revision='fixture',event_id=uuid4().hex,payload_hash='fixture-hash')
    assert graph.operation('record-runtime-observation',case['actor'],case['scope'],**params)
    assert graph.operation('record-runtime-observation',case['actor'],case['scope'],**params)
    assert graph.query("MATCH (o:Observation {node_id:$event_id}) RETURN count(o) AS n",params)[0]['n']==1
    assert graph.operation('record-runtime-observation',case['worker'],case['scope'],**params)==[]
    late={**params,'event_id':uuid4().hex,'observed_at':(now-timedelta(minutes=1)).isoformat(),
          'status':'stopped','process_count':0,'payload_hash':'late'}
    graph.operation('record-runtime-observation',case['actor'],case['scope'],**late)
    assert graph.operation('read-sources',case['actor'],case['scope'])[0]['process_status']=='running'
    failed={**params,'event_id':uuid4().hex,'observed_at':(now+timedelta(seconds=1)).isoformat(),
            'status':'collection_failed','process_count':0,'payload_hash':'failed'}
    graph.operation('record-runtime-observation',case['actor'],case['scope'],**failed)
    assert graph.operation('read-sources',case['actor'],case['scope'])[0]['evidence_status']=='degraded'
    graph.query("MATCH (s:SourceStream {node_id:$source}) SET s.last_success_at=datetime()-duration('PT4M')",params)
    row=graph.operation('read-sources',case['actor'],case['scope'])[0]
    assert row['evidence_status']=='stale' and row['process_status']=='unknown'
