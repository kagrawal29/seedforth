import json
import asyncio
from pathlib import Path
import socket
import struct
import sys
import threading

import pytest

pytest.importorskip('argon2')
sys.path.insert(0,str(Path(__file__).parents[1]))
from control.identity_runtime import admin_operation, backup_credentials, invalidate_recovered_credentials, deployment_policy, operator_server
from control.human_identity import HumanIdentity, IdentityError
from control.oauth_provider import OAuthStore, DurableOAuthProvider
from test_human_identity import human, enrolled, PASSWORD
from mcp.shared.auth import OAuthClientInformationFull
from test_oauth_provider import tokens


def test_operator_requires_kernel_root_and_cannot_grant_authority(human):
    identity,_,_,_=human
    for body in [{'operation':'invite','principal':'person'},{'operation':'backup'}]:
        with pytest.raises(IdentityError):admin_operation(identity,body,1000)
    with pytest.raises(IdentityError):admin_operation(identity,{'operation':'grant','principal':'person'},0)
    with pytest.raises(IdentityError):admin_operation(identity,{'operation':'invite','principal':'unknown'},0)
    result=admin_operation(identity,{'operation':'invite','principal':'person'},0)
    assert len(result['invitation'])>=32
    assert result['principal']=='person'


def test_backup_restore_cannot_resurrect_sessions_or_factors(human,tmp_path):
    identity,provider,now,_=human
    session,recovery,_=enrolled(human)
    client=OAuthClientInformationFull(client_id='backup-client',token_endpoint_auth_method='none',
        redirect_uris=['http://127.0.0.1:9911/callback'],grant_types=['authorization_code','refresh_token'],
        response_types=['code'],scope='mycelium')
    asyncio.run(provider.register_client(client))
    issued=tokens((provider,client,{}))
    saved=backup_credentials(identity.store)
    path=Path(saved['backup_ref'])
    assert path.stat().st_mode&0o077==0
    restored=OAuthStore(path)
    recovered=HumanIdentity(restored,provider.grants,clock=lambda:now[0])
    recovered_oauth=DurableOAuthProvider(restored,provider.issuer,provider.resource,provider.allowed_projects,provider.grants,clock=lambda:now[0])
    # Demonstrates the real resurrection risk before mandatory sanitization.
    assert recovered.session(session)['principal']=='person'
    assert asyncio.run(recovered_oauth.verify_token(issued.access_token)) is not None
    invalidate_recovered_credentials(restored)
    assert recovered.session(session) is None
    assert asyncio.run(recovered_oauth.verify_token(issued.access_token)) is None
    assert asyncio.run(recovered_oauth.load_refresh_token(client,issued.refresh_token)) is None
    with pytest.raises(IdentityError):recovered.login('operator',PASSWORD,recovery[0],'fixture')
    with restored.transaction() as db:
        assert db.execute('SELECT count(*) FROM human_users').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM human_recovery WHERE used=0').fetchone()[0]==0
    assert admin_operation(recovered,{'operation':'reset','principal':'person'},0)['invitation']


def test_policy_cannot_open_listener_or_widen_scopes():
    approved=dict(issuer='https://185.192.96.100/',resource='https://185.192.96.100/mcp',
        scopes=['seedforth-platform','flowing-indian','cajon-sensei'],host='127.0.0.1',port=8788,public=False)
    class Graph:
        def query(self,_):return [self.policy]
    graph=Graph();graph.policy=approved
    assert deployment_policy(graph)==approved
    for change in [{'host':'0.0.0.0'},{'public':True},{'scopes':['another']},{'issuer':'https://evil.example/'}]:
        graph.policy={**approved,**change}
        with pytest.raises(ValueError):deployment_policy(graph)


@pytest.mark.skipif(not hasattr(socket,'SO_PEERCRED'),reason='Linux kernel credential socket test')
def test_actual_unix_kernel_peer_credentials(human,tmp_path):
    import os
    identity,_,_,_=human
    tmp_path.chmod(0o700)
    path=tmp_path/'operator.sock'
    server=operator_server(path,identity)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as conn:
            conn.connect(str(path));conn.sendall(b'{"operation":"backup"}\n')
            response=json.loads(conn.recv(8192))
            if os.geteuid()==0:assert 'backup_ref' in response
            else:assert response=={'error':'root_operator_required'}
        assert path.stat().st_mode&0o077==0
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)
