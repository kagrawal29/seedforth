"""Authentication and transport authority tests; no live secrets or graph."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).parents[1]))
from control.server import Boundary, RequestError

TOKEN='fixture-token-not-a-real-credential-123456789'


class FakeGraph:
    allowed=True
    calls=[]
    def query(self,*args):
        return [{'permitted':self.allowed}]
    def operation(self,name,actor,scope,**params):
        self.calls.append((name,actor,scope,params))
        return [{'id':'fixture'}]


@pytest.fixture
def boundary(tmp_path):
    path=tmp_path/'credentials.json'
    path.write_text(json.dumps([dict(sha256=hashlib.sha256(TOKEN.encode()).hexdigest(),
        principal='fixture-human',scopes=['fixture'],
        expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())]))
    path.chmod(0o600)
    graph=FakeGraph();graph.calls=[]
    return Boundary(graph,path)


def request(boundary,**changes):
    return boundary.dispatch('Bearer '+TOKEN,
        {'operation':'read-work','scope':'fixture','params':{},**changes})


def test_scope_and_actor_are_bound_to_authenticated_context(boundary):
    assert request(boundary)['scope']=='fixture'
    assert boundary.graph.calls[0][1:3]==('fixture-human','fixture')
    with pytest.raises(RequestError) as exc:
        request(boundary,scope='another-project')
    assert exc.value.status==403
    with pytest.raises(RequestError):
        request(boundary,params={'actor':'admin'})


def test_graph_revocation_checked_every_request(boundary):
    request(boundary)
    boundary.graph.allowed=False
    with pytest.raises(RequestError) as exc:
        request(boundary)
    assert exc.value.status==403
    assert len(boundary.graph.calls)==1


def test_credential_rotation_is_immediate(boundary):
    request(boundary)
    boundary.credentials.write_text('[]')
    with pytest.raises(RequestError) as exc:
        request(boundary)
    assert exc.value.status==401


def test_world_readable_credentials_fail_closed(boundary):
    boundary.credentials.chmod(0o604)
    with pytest.raises(RequestError) as exc:
        request(boundary)
    assert exc.value.status==503


@pytest.mark.parametrize('name',['promote','claim-work','finish-work','../read-work','arbitrary-cypher'])
def test_human_gateway_does_not_expose_privileged_execution(boundary,name):
    with pytest.raises(RequestError):
        request(boundary,operation=name)


def test_boolean_cannot_impersonate_integer_version(boundary):
    with pytest.raises(RequestError):
        request(boundary,operation='hold-work',params={'id':'fixture','version':True,'hold':True})


def test_creation_intent_hash_is_server_computed(boundary):
    params=dict(id='fixture',milestone='m',title='Draft',acceptance='Tests pass')
    request(boundary,operation='create-work',params=params)
    first=boundary.graph.calls[-1][3]['request_hash']
    request(boundary,operation='create-work',params=params)
    assert boundary.graph.calls[-1][3]['request_hash']==first
    request(boundary,operation='create-work',params={**params,'title':'Different'})
    assert boundary.graph.calls[-1][3]['request_hash']!=first
