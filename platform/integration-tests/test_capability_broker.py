from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from control.broker import Broker,InvocationDenied
from control.git_inspection import GitInspection
from control.receipt_journal import ReceiptJournal


@pytest.mark.parametrize('mutation',['hash','path','symlink','fifo'])
def test_artifact_reader_rejects_corruption_and_nonregular_files(tmp_path,mutation):
    import hashlib,os
    artifact=tmp_path/'fixture-invocation.json'
    artifact.write_text('{"safe":"fixture"}')
    row=dict(capability='fixture',artifact_ref=str(artifact),artifact_hash=hashlib.sha256(artifact.read_bytes()).hexdigest())
    class Adapter:
        artifact_root=tmp_path
    class Graph:
        def operation(self,name,actor,scope,**params):
            assert name=='read-invocation-artifact' and actor=='worker' and scope=='scope'
            return [row]
    if mutation=='hash': artifact.write_text('{"changed":true}')
    if mutation=='path': row['artifact_ref']=str(tmp_path/'different.json')
    if mutation in ['symlink','fifo']:
        artifact.unlink()
        if mutation=='symlink': artifact.symlink_to(tmp_path/'outside')
        else: os.mkfifo(artifact)
    broker=Broker(Graph(),'broker',{'fixture':Adapter()},ReceiptJournal(tmp_path/'receipts'))
    with pytest.raises((InvocationDenied,OSError)):
        broker.read_artifact('worker','scope','fixture-invocation')


def test_unpromoted_capability_cannot_touch_graph(tmp_path):
    class Graph:
        def operation(self,*a,**k):
            pytest.fail('must not access graph')
    with pytest.raises(InvocationDenied):
        Broker(Graph(),'broker',{},ReceiptJournal(tmp_path/'receipts')).invoke('worker','scope','attempt',1,'fixture-invocation','shell',{'command':'anything'})


def test_git_scope_arguments_and_revision_are_bounded(tmp_path):
    adapter=GitInspection({'allowed':tmp_path/'repo'},tmp_path/'artifacts')
    for scope,args in [('other',{'revision':'a'*40}),('allowed',{'revision':'HEAD'}),
                       ('allowed',{'revision':'a'*40,'command':'anything'})]:
        with pytest.raises(InvocationDenied): adapter.validate(scope,args)


def test_no_execution_if_admission_evidence_is_unavailable(tmp_path):
    class Graph:
        def operation(self,*a,**k): raise ConnectionError('unavailable')
    class Adapter:
        generation='fixture'
        cost_units=1
        max_seconds=30
        def validate(self,*a): return {}
        def run(self,*a): pytest.fail('must not execute')
    with pytest.raises(ConnectionError):
        Broker(Graph(),'broker',{'fixture':Adapter()},ReceiptJournal(tmp_path/'receipts')).invoke('worker','scope','attempt',1,'fixture-invocation','fixture',{})


def test_adapter_exception_is_uncertain_and_redacted(tmp_path):
    captured=[]
    class Graph:
        def operation(self,name,*a,**params):
            captured.append((name,params))
            return [{'status':{'admit-invocation':'admitted','dispatch-invocation':'dispatching','settle-invocation':'unknown'}[name]}]
    class Adapter:
        generation='fixture'
        cost_units=1
        max_seconds=30
        def validate(self,*a): return {}
        def run(self,*a): raise TimeoutError('private-output-must-not-leak')
    result=Broker(Graph(),'broker',{'fixture':Adapter()},ReceiptJournal(tmp_path/'receipts')).invoke('worker','scope','attempt',1,'fixture-invocation','fixture',{})
    assert result['status']=='unknown'
    assert 'private-output-must-not-leak' not in str(captured)
