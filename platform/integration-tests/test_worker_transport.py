from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from control.server import RequestError
from control.worker_transport import WorkerBoundary,WorkerServer,WorkerClient

TOKEN='fixture-worker-only-token-not-a-real-secret-12345'


@pytest.fixture
def service():
    with tempfile.TemporaryDirectory(prefix='sfw-',dir='/tmp') as directory:
        root=Path(directory)
        credentials=root/'credentials.json'
        credentials.write_text(json.dumps([dict(principal='worker-fixture',scopes=['fixture'],
            sha256=hashlib.sha256(TOKEN.encode()).hexdigest(),
            expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())]))
        credentials.chmod(0o600)
        class Graph:
            calls=[]
            def operation(self,name,actor,scope,**params):
                self.calls.append((name,actor,scope,params))
                return [dict(id='fixture-work')]
        class Broker:
            def invoke(self,**params):
                assert params['actor']=='worker-fixture' and params['scope']=='fixture'
                return dict(status='succeeded')
            def read_artifact(self,**params):
                assert params==dict(actor='worker-fixture',scope='fixture',invocation='fixture-invocation')
                return dict(trust='untrusted_artifact_data',content={'source':'fixture'})
        graph=Graph()
        server=WorkerServer(root/'worker.sock',WorkerBoundary(graph,credentials,Broker()))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            yield WorkerClient(root/'worker.sock',TOKEN,'fixture'),graph,root
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)


def test_real_unix_transport_binds_identity_and_scope(service):
    client,graph,root=service
    assert client.request('read-work')==[dict(id='fixture-work')]
    assert graph.calls[0][1:3]==('worker-fixture','fixture')
    assert (root/'worker.sock').stat().st_mode & 0o777 == 0o660
    other=WorkerClient(root/'worker.sock',TOKEN,'another-project')
    with pytest.raises(RequestError) as exc: other.request('read-work')
    assert exc.value.status==403


@pytest.mark.parametrize('operation',['promote','settle-invocation','ready-work','review-work','finish-work','create-work'])
def test_worker_has_no_policy_or_verification_authority(service,operation):
    client,graph,_=service
    with pytest.raises(RequestError) as exc: client.request(operation)
    assert exc.value.status==400 and not graph.calls


def test_worker_cannot_supply_actor_or_broker_identity(service):
    client,graph,_=service
    with pytest.raises(RequestError): client.request('read-work',actor='owner')
    assert not graph.calls


def test_private_gateway_requires_current_credential(service):
    client,_,root=service
    (root/'credentials.json').write_text('[]')
    with pytest.raises(RequestError) as exc: client.request('read-work')
    assert exc.value.status==401


def test_worker_dispatch_reaches_broker_with_bound_actor(service):
    client,_,_=service
    result=client.request('invoke',attempt='fixture-attempt',fence=1,
        invocation='fixture-invocation',capability='fixture',arguments={})
    assert result==[dict(status='succeeded')]


def test_worker_artifact_read_binds_identity_without_host_path(service):
    client,_,_=service
    assert client.request('read-artifact',invocation='fixture-invocation')==[
        dict(trust='untrusted_artifact_data',content={'source':'fixture'})]
    with pytest.raises(RequestError):
        client.request('read-artifact',invocation='fixture-invocation',path='/etc/passwd')
