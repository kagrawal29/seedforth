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
                "CREATE (b)-[:REPRESENTS]->(:SubAgent {node_id:$worker,project:$scope}) "
                "CREATE (:Mandate {node_id:$scope+'-mandate',scope_id:$scope,enabled:true,version:1,budget_id:$scope+'-budget',"
                "expires_at:datetime()+duration('PT1H'),allowed_capabilities:[$scope+'-cap']})"
                "-[:HAS_BUDGET]->(:Budget {node_id:$scope+'-budget',scope_id:$scope,total_units:2,reserved_units:0,spent_units:0}) "
                "CREATE (:Capability {node_id:$scope+'-cap',enabled:true,policy_generation:'fixture-policy',cost_units:1,max_seconds:30}) "
                "CREATE (broker:Principal {node_id:$scope+'-broker',enabled:true})"
                "-[:HAS_GRANT]->(:Grant {scope:$scope,revoked:false,permissions:['invocation.settle']})",
                dict(scope=scope, actor=actor, worker=worker))
    return dict(scope=scope, actor=actor, worker=worker, id=scope+'-work', milestone=scope+'-m')


def create(graph, c):
    rows=graph.operation('create-work', c['actor'], c['scope'], id=c['id'],
                           milestone=c['milestone'], title='Verify staged artifact',
                           acceptance='Independent checker accepts exact hash',request_hash='request-a')
    graph.query("MATCH (w:WorkItem {node_id:$id}),(m:Mandate {node_id:$scope+'-mandate'}) SET w.mandate_id=m.node_id MERGE (w)-[:AUTHORIZED_BY]->(m)",c)
    return rows


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
    evidence=graph.operation('read-evidence',case['actor'],case['scope'],id=case['id'])
    assert evidence[0]['id']==receipt and evidence[0]['kind']=='execution_receipt'
    assert graph.operation('read-evidence',case['actor'],'another-scope',id=case['id'])==[]


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


def test_dependency_is_checked_at_schedule_and_claim(graph, case):
    create(graph,case)
    graph.query("MATCH (w:WorkItem {node_id:$id}) CREATE (w)-[:DEPENDS_ON]->(:WorkItem {node_id:$id+'-dependency',scope_id:$scope,status:'proposed'})",case)
    assert graph.operation('ready-work',case['actor'],case['scope'],id=case['id'],version=0,event_id=uuid4().hex)==[]
    graph.query("MATCH (d:WorkItem {node_id:$id+'-dependency'}) SET d.status='done'",case)
    assert graph.operation('ready-work',case['actor'],case['scope'],id=case['id'],version=0,event_id=uuid4().hex)
    graph.query("MATCH (d:WorkItem {node_id:$id+'-dependency'}) SET d.status='blocked'",case)
    assert claim(graph,case)==[]


def test_legacy_done_is_not_governed_verified_work(graph, case):
    graph.query("CREATE (:WorkItem {node_id:$id+'-legacy',project:$scope,status:'done',title:'Historical output'})",case)
    row=graph.operation('read-legacy-work',case['actor'],case['scope'])[0]
    assert row['legacy_status']=='done' and row['status']=='legacy_needs_triage'
    assert graph.operation('read-work',case['actor'],case['scope'])==[]
    assert graph.operation('read-legacy-work',case['actor'],'another-scope')==[]
    graph.query("CREATE (:Project {node_id:$scope+'-ambiguous',name:$scope})",case)
    assert graph.operation('read-legacy-work',case['actor'],case['scope'])==[]


def test_full_migration_and_upgrade_plan_are_idempotent(graph):
    from control.migrate import migrate
    for node_id,name in [('proj-mycelium','mycelium'),('project-cajon-sensei','cajon-sensei'),('project-flowing-indian','flowing-indian')]:
        graph.query("MERGE (p:Project {node_id:$id}) SET p.name=$name",{'id':node_id,'name':name})
    first=migrate(graph,'fixture-release')
    second=migrate(graph,'fixture-release')
    assert first==second
    assert graph.query("MATCH (w:WorkItem {scope_id:'seedforth-platform'}) RETURN count(w) AS n")[0]['n']==22
    assert graph.query("MATCH (:ControlScope {node_id:'seedforth-platform'})-[:MAPS_PROJECT]->(p:Project) RETURN p.node_id AS id")==[{'id':'proj-mycelium'}]
    assert graph.query("MATCH (w:WorkItem {scope_id:'seedforth-platform'}) WHERE w.status<>'proposed' RETURN count(w) AS n")[0]['n']==0


def invocation_params(graph,case):
    ready(graph,case)
    attempt=claim(graph,case)[0]
    return dict(attempt=attempt['attempt'],fence=attempt['fence'],invocation=uuid4().hex,
        capability=case['scope']+'-cap',generation='fixture-policy',params_hash='fixture-arguments',cost_units=1,max_seconds=30)


def test_invocation_budget_idempotency_and_exhaustion(graph,case):
    params=invocation_params(graph,case)
    admit=lambda p:graph.operation('admit-invocation',case['worker'],case['scope'],**p)
    assert admit(params)[0]['status']=='admitted'
    assert admit(params)[0]['status']=='admitted'
    assert admit({**params,'params_hash':'changed-intent'})==[]
    assert admit({**params,'invocation':uuid4().hex})
    assert admit({**params,'invocation':uuid4().hex})==[]
    budget=graph.query("MATCH (b:Budget {node_id:$scope+'-budget'}) RETURN b.reserved_units AS reserved,b.spent_units AS spent",case)[0]
    assert budget==dict(reserved=2,spent=0)


@pytest.mark.parametrize('change', [
    "MATCH (g:Grant {node_id:$worker+'-grant'}) SET g.revoked=true",
    "MATCH (p:Principal {node_id:$worker}) SET p.enabled=false",
    "MATCH (s:ControlScope {node_id:$scope}) SET s.work_enabled=false",
    "MATCH (w:WorkItem {node_id:$id}) SET w.lease_until=datetime()+duration('PT10S')",
    "MATCH (m:Mandate {node_id:$scope+'-mandate'}) SET m.expires_at=datetime()+duration('PT10S')",
    "MATCH (m:Mandate {node_id:$scope+'-mandate'}) SET m.version=m.version+1",
    "MATCH (m:Mandate {node_id:$scope+'-mandate'}) SET m.allowed_capabilities=[]",
    "MATCH (c:Capability {node_id:$scope+'-cap'}) SET c.policy_generation='changed'",
])
def test_admission_and_dispatch_recheck_authority_and_full_deadline(graph,case,change):
    params=invocation_params(graph,case)
    assert graph.operation('admit-invocation',case['worker'],case['scope'],**params)
    graph.query(change,case)
    assert graph.operation('admit-invocation',case['worker'],case['scope'],
                           **{**params,'invocation':uuid4().hex})==[]
    assert graph.operation('dispatch-invocation',case['worker'],case['scope'],
        invocation=params['invocation'],params_hash=params['params_hash'])==[]
    assert graph.query("MATCH (i:Invocation {node_id:$id}) RETURN i.status AS status",
                       {'id':params['invocation']})==[{'status':'admitted'}]
    # The separate broker can release a never-dispatched reservation after revoke.
    result=graph.operation('settle-invocation',case['scope']+'-broker',case['scope'],
        invocation=params['invocation'],outcome='cancelled',result_hash='authority-changed',
        artifact_hash=None,artifact_ref=None,event_id=uuid4().hex)
    assert result[0]['budget_reserved']==0 and result[0]['budget_spent']==0


def test_concurrent_invocations_conserve_budget_and_dispatch_once(graph,case):
    params=invocation_params(graph,case)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(lambda _:graph.operation('admit-invocation',case['worker'],
            case['scope'],**{**params,'invocation':uuid4().hex}),range(6)))
    admitted=[rows[0]['id'] for rows in results if rows]
    assert len(admitted)==2
    assert graph.query("MATCH (b:Budget {node_id:$scope+'-budget'}) RETURN b.reserved_units AS reserved,b.spent_units AS spent",case)==[{'reserved':2,'spent':0}]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        dispatched=list(pool.map(lambda _:graph.operation('dispatch-invocation',
            case['worker'],case['scope'],invocation=admitted[0],params_hash=params['params_hash']),range(2)))
    assert sum(bool(rows) for rows in dispatched)==1


def test_dispatch_rechecks_hold_and_broker_can_release_admission(graph,case):
    params=invocation_params(graph,case)
    graph.operation('admit-invocation',case['worker'],case['scope'],**params)
    graph.operation('hold-work',case['actor'],case['scope'],id=case['id'],version=2,hold=True,event_id=uuid4().hex)
    assert graph.operation('dispatch-invocation',case['worker'],case['scope'],invocation=params['invocation'],params_hash=params['params_hash'])==[]
    settled=graph.operation('settle-invocation',case['scope']+'-broker',case['scope'],invocation=params['invocation'],
        outcome='cancelled',result_hash='cancelled',artifact_hash=None,artifact_ref=None,event_id=uuid4().hex)
    assert settled[0]['budget_reserved']==0 and settled[0]['budget_spent']==0


def test_unknown_result_holds_budget_and_worker_cannot_forge_settlement(graph,case):
    params=invocation_params(graph,case)
    graph.operation('admit-invocation',case['worker'],case['scope'],**params)
    assert graph.operation('dispatch-invocation',case['worker'],case['scope'],invocation=params['invocation'],params_hash=params['params_hash'])
    settle=dict(invocation=params['invocation'],outcome='unknown',result_hash='timeout',artifact_hash=None,artifact_ref=None,event_id=uuid4().hex)
    assert graph.operation('settle-invocation',case['worker'],case['scope'],**settle)==[]
    unknown=graph.operation('settle-invocation',case['scope']+'-broker',case['scope'],**settle)[0]
    assert unknown['budget_reserved']==1 and unknown['budget_spent']==0
    graph.query("MATCH (g:Grant {node_id:$id}) SET g.revoked=true",{'id':case['worker']+'-grant'})
    final=graph.operation('settle-invocation',case['scope']+'-broker',case['scope'],**{**settle,'outcome':'succeeded','event_id':uuid4().hex})[0]
    assert final['budget_reserved']==0 and final['budget_spent']==1
    assert graph.operation('settle-invocation',case['scope']+'-broker',case['scope'],**{**settle,'outcome':'succeeded','event_id':uuid4().hex})==[]


@pytest.mark.parametrize('lost_after_commit',[False,True])
def test_broker_runs_real_git_inspection_once(graph,case,tmp_path,lost_after_commit):
    import subprocess
    from control.broker import Broker
    from control.git_inspection import GitInspection
    from control.receipt_journal import ReceiptJournal
    repository=tmp_path/'repo';repository.mkdir()
    subprocess.run(['git','init','-q',str(repository)],check=True)
    (repository/'fixture.txt').write_text('fixture content\n')
    subprocess.run(['git','-C',str(repository),'add','fixture.txt'],check=True)
    subprocess.run(['git','-C',str(repository),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    '-c','commit.gpgsign=false','commit','-qm','fixture'],check=True)
    revision=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip()
    adapter=GitInspection({case['scope']:repository},tmp_path/'artifacts')
    graph.query("MATCH (c:Capability {node_id:$id}) SET c.policy_generation=$generation",
                dict(id=case['scope']+'-cap',generation=adapter.generation))
    params=invocation_params(graph,case)
    class LossyGraph:
        lost=False
        def query(self,*a,**k): return graph.query(*a,**k)
        def operation(self,name,*a,**k):
            if name=='settle-invocation' and not self.lost:
                self.lost=True
                if lost_after_commit:
                    graph.operation(name,*a,**k)
                raise ConnectionError('simulated settlement connection loss')
            return graph.operation(name,*a,**k)
    broker=Broker(LossyGraph(),case['scope']+'-broker',{case['scope']+'-cap':adapter},ReceiptJournal(tmp_path/'receipts'))
    args=dict(actor=case['worker'],scope=case['scope'],attempt=params['attempt'],fence=params['fence'],
              invocation=params['invocation'],capability=params['capability'],arguments={'revision':revision})
    with pytest.raises(ConnectionError): broker.invoke(**args)
    assert broker.recover_receipts()==[params['invocation']]
    assert broker.recover_receipts()==[]
    assert broker.invoke(**args)['status']=='succeeded'
    assert len(list((tmp_path/'artifacts').glob('*.json')))==1
    artifact=broker.read_artifact(case['worker'],case['scope'],params['invocation'])
    assert artifact['content']['commit']==revision
    assert artifact['trust']=='untrusted_artifact_data' and 'artifact_ref' not in artifact
    assert graph.operation('read-invocation-artifact',case['actor'],case['scope'],invocation=params['invocation'])==[]
    assert graph.operation('read-invocation-artifact',case['worker'],'wrong-scope',invocation=params['invocation'])==[]
    result=graph.operation('complete-invocation-work',case['worker'],case['scope'],attempt=params['attempt'],
        invocation=params['invocation'],fence=params['fence'],event_id=uuid4().hex)
    assert result[0]['status']=='review'
    assert graph.query("MATCH (p:ProgressEvent {scope_id:$scope}) RETURN count(p) AS n",case)[0]['n']==0
    graph.query("MATCH (g:Grant {node_id:$worker+'-grant'}) SET g.revoked=true",case)
    from control.broker import InvocationDenied
    with pytest.raises(InvocationDenied):
        broker.read_artifact(case['worker'],case['scope'],params['invocation'])


def test_worker_completion_without_broker_evidence_is_denied(graph,case):
    params=invocation_params(graph,case)
    assert graph.operation('complete-invocation-work',case['worker'],case['scope'],attempt=params['attempt'],
        invocation='does-not-exist',fence=params['fence'],event_id=uuid4().hex)==[]
    assert graph.operation('read-attempt',case['worker'],case['scope'],attempt=params['attempt'])[0]['status']=='running'
    assert graph.operation('read-attempt',case['actor'],case['scope'],attempt=params['attempt'])==[]


def test_governed_code_proposal_can_be_read_but_not_self_accepted(graph,case,tmp_path):
    import subprocess
    from control.broker import Broker
    from control.code_proposal import CodeProposal
    from control.receipt_journal import ReceiptJournal
    repo=tmp_path/'code';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    (repo/'counter.js').write_text('const completed = step === 0;\n')
    subprocess.run(['git','-C',str(repo),'add','counter.js'],check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    '-c','commit.gpgsign=false','commit','-qm','fixture'],check=True)
    revision=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    adapter=CodeProposal({case['scope']:repo},{case['scope']:['counter.js']},tmp_path/'artifacts')
    graph.query("MATCH (c:Capability {node_id:$id}) SET c.policy_generation=$generation",
                dict(id=case['scope']+'-cap',generation=adapter.generation))
    params=invocation_params(graph,case)
    broker=Broker(graph,case['scope']+'-broker',{case['scope']+'-cap':adapter},ReceiptJournal(tmp_path/'receipts'))
    result=broker.invoke(case['worker'],case['scope'],params['attempt'],params['fence'],
        params['invocation'],params['capability'],{'revision':revision,
            'changes':[{'path':'counter.js','old':'step === 0','new':'previousStep === 15'}]})
    assert result['status']=='succeeded'
    report=broker.read_artifact(case['worker'],case['scope'],params['invocation'])['content']
    assert report['files'][0]['content']=='const completed = previousStep === 15;\n'
    assert not report['applied'] and report['verification_status']=='not_run'
    assert (repo/'counter.js').read_text()=='const completed = step === 0;\n'
    reviewed=graph.operation('complete-invocation-work',case['worker'],case['scope'],
        attempt=params['attempt'],fence=params['fence'],invocation=params['invocation'],event_id=uuid4().hex)
    assert reviewed[0]['status']=='review'
    assert graph.query("MATCH (p:ProgressEvent {scope_id:$scope}) RETURN count(p) AS n",case)==[{'n':0}]


def test_distinct_tasks_share_atomic_scope_concurrency_limit(graph,case):
    other={**case,'id':case['id']+'-second'}
    ready(graph,case);ready(graph,other)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda c:claim(graph,c),[case,other]))
    assert sum(bool(r) for r in results)==1


@pytest.mark.skipif(not os.environ.get('CONTROL_WORKER_TEST_IMAGE'),reason='explicit pinned disposable Docker image required')
def test_networkless_worker_completes_broker_path_without_graph_credentials(graph,case,tmp_path):
    import hashlib,json,subprocess,threading
    from datetime import datetime,timedelta,timezone
    from control.broker import Broker
    from control.git_inspection import GitInspection
    from control.receipt_journal import ReceiptJournal
    from control.worker_transport import WorkerBoundary,WorkerServer
    image=os.environ['CONTROL_WORKER_TEST_IMAGE']
    if not image.startswith('python@sha256:') or len(image)!=len('python@sha256:')+64:
        pytest.fail('a pinned official Python image digest is required')
    repository=tmp_path/'repo';repository.mkdir()
    subprocess.run(['git','init','-q',str(repository)],check=True)
    (repository/'fixture.txt').write_text('isolated worker fixture\n')
    subprocess.run(['git','-C',str(repository),'add','fixture.txt'],check=True)
    subprocess.run(['git','-C',str(repository),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    '-c','commit.gpgsign=false','commit','-qm','fixture'],check=True)
    revision=subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip()
    adapter=GitInspection({case['scope']:repository},tmp_path/'artifacts')
    graph.query("MATCH (c:Capability {node_id:$id}) SET c.policy_generation=$generation",
                dict(id=case['scope']+'-cap',generation=adapter.generation))
    ready(graph,case)
    token='fixture-isolation-token-'+uuid4().hex
    credentials=tmp_path/'credentials.json'
    credentials.write_text(json.dumps([dict(principal=case['worker'],scopes=[case['scope']],
        sha256=hashlib.sha256(token.encode()).hexdigest(),expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())]))
    credentials.chmod(0o600)
    worker_token=tmp_path/'worker-token';worker_token.write_text(token);worker_token.chmod(0o444)
    job=tmp_path/'job.json'
    invocation=uuid4().hex
    job.write_text(json.dumps(dict(scope=case['scope'],work=case['id'],attempt=uuid4().hex,
        invocation=invocation,capability=case['scope']+'-cap',revision=revision)))
    job.chmod(0o444)
    broker=Broker(graph,case['scope']+'-broker',{case['scope']+'-cap':adapter},ReceiptJournal(tmp_path/'receipts'))
    socket_path=tmp_path/'worker.sock'
    server=WorkerServer(socket_path,WorkerBoundary(graph,credentials,broker))
    os.chown(socket_path,-1,65534)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    probe=Path(__file__).parent/'fixtures/isolated-worker-probe.py'
    container='sf-worker-fixture-'+uuid4().hex[:12]
    try:
        command=['docker','run','--rm','--name',container,'--network=none','--read-only','--cap-drop=ALL',
            '--security-opt=no-new-privileges','--pids-limit=32','--memory=128m','--cpus=0.5','--user=65534:65534',
            '--mount',f'type=bind,src={socket_path},dst=/run/broker.sock,readonly',
            '--mount',f'type=bind,src={worker_token},dst=/run/worker-token,readonly',
            '--mount',f'type=bind,src={job},dst=/run/job.json,readonly',
            '--mount',f'type=bind,src={probe},dst=/probe.py,readonly',image,'python','-B','/probe.py']
        result=subprocess.run(command,check=True,capture_output=True,text=True,timeout=60)
        assert json.loads(result.stdout)['isolation_checks']=='passed'
    finally:
        subprocess.run(['docker','rm','-f',container],capture_output=True,check=False)
        server.shutdown();server.server_close();thread.join(timeout=5)
    artifact=json.loads((tmp_path/'artifacts'/(invocation+'.json')).read_text())
    assert artifact['commit']==revision
    assert graph.query("MATCH (w:WorkItem {node_id:$id}) RETURN w.status AS status",case)[0]['status']=='review'
    assert graph.query("MATCH (p:ProgressEvent {scope_id:$scope}) RETURN count(p) AS n",case)[0]['n']==0
