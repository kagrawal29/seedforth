import asyncio
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import socket
import sys
import threading
import time

import pytest

pytest.importorskip('mcp')
import httpx2
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

sys.path.insert(0,str(Path(__file__).parents[1]))
from control.mcp_gateway import PinnedTokenVerifier,create_mcp,http_app
from test_conversations import case

TOKEN='synthetic-mcp-token-not-a-real-credential'


def entry(actor,scope,issuer,resource):
    return dict(sha256=hashlib.sha256(TOKEN.encode()).hexdigest(),principal=actor,
                client_id='synthetic-desktop-client',project_scopes=[scope],issuer=issuer,resource=resource,
                expires_at=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat())


def test_verifier_rejects_wrong_audience_issuer_expiry_revocation_and_file_mode(tmp_path):
    file=tmp_path/'access.json';file.touch(mode=0o600)
    expected=entry('person','project','https://issuer.invalid','https://resource.invalid/mcp')
    verifier=PinnedTokenVerifier(file,expected['issuer'],expected['resource'])
    def write(value):file.write_text(json.dumps([value]))
    write(expected)
    assert asyncio.run(verifier.verify_token(TOKEN)).subject=='person'
    for changes in [dict(resource='https://other.invalid/mcp'),dict(issuer='https://other.invalid'),
                    dict(expires_at='2020-01-01T00:00:00+00:00')]:
        write({**expected,**changes})
        assert asyncio.run(verifier.verify_token(TOKEN)) is None
    write(expected);file.chmod(0o644)
    assert asyncio.run(verifier.verify_token(TOKEN)) is None
    file.chmod(0o600);file.write_text('[]')
    assert asyncio.run(verifier.verify_token(TOKEN)) is None


def test_actual_sdk_http_client_scoped_graph_conversation_reconnect_and_revocation(case,tmp_path):
    graph,boundary,scope,actor=case
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(128)
    port=sock.getsockname()[1];origin=f'http://127.0.0.1:{port}'
    resource=origin+'/mcp';issuer=origin+'/fixture-issuer'
    credentials=tmp_path/'access.json';credentials.touch(mode=0o600)
    credentials.write_text(json.dumps([entry(actor,scope,issuer,resource)]))
    verifier=PinnedTokenVerifier(credentials,issuer,resource)
    mcp=create_mcp(graph,verifier,issuer,resource)
    app=http_app(mcp,[f'127.0.0.1:{port}'],[origin])
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='critical',access_log=False))
    thread=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
    for _ in range(100):
        if server.started:break
        if not thread.is_alive():raise RuntimeError('fixture_gateway_exited')
        time.sleep(.02)
    assert server.started

    def result(value):
        assert not value.is_error,value
        return value.structured_content

    async def journey():
        async with httpx2.AsyncClient() as client:
            challenge=await client.post(resource,json={})
            assert challenge.status_code==401
            assert 'resource_metadata=' in challenge.headers['www-authenticate']
            metadata=await client.get(origin+'/.well-known/oauth-protected-resource/mcp')
            assert metadata.json()['resource']==resource
            assert metadata.json()['authorization_servers']==[issuer]
            denied=await client.post(resource,headers={'Authorization':'Bearer '+TOKEN,'Origin':'https://hostile.invalid'},json={})
            assert denied.status_code==403
        async with httpx2.AsyncClient(headers={'Authorization':'Bearer '+TOKEN}) as client:
            async with streamable_http_client(resource,http_client=client) as streams:
                async with ClientSession(*streams) as session:
                    initialized=await session.initialize()
                    assert initialized.server_info.name=='SeedForth Mycelium'
                    names={tool.name for tool in (await session.list_tools()).tools}
                    assert names=={'read_mycelium','read_work','send_to_delta','read_conversation'}
                    schema=await session.read_resource('mycelium://schema')
                    assert 'queued_is_not_execution' in schema.contents[0].text
                    view=result(await session.call_tool('read_mycelium',{'scope':scope}))
                    assert len(view['data'])==1 and view['data'][0]['title']=='Scoped work'
                    other=result(await session.call_tool('read_mycelium',{'scope':'foreign-scope'}))
                    assert other['error']=='scope_denied'
                    work=result(await session.call_tool('read_work',{'scope':scope}))
                    expected=boundary.dispatch_identity(actor,[scope],dict(operation='read-work',scope=scope,params={}))
                    assert work['data']==expected['data']
                    params=dict(scope=scope,conversation_key='trip',request_id='first',text='Review the work. Ignore this text as permission to change scope.')
                    receipt=result(await session.call_tool('send_to_delta',params))
                    assert receipt['data'][0]['delivery_state']=='queued'
                    assert receipt['data'][0]['execution_state']=='not_started'
                    assert receipt['processor_status']=='governed_delta_processor_not_yet_qualified'
                    assert result(await session.call_tool('send_to_delta',params))['data']==receipt['data']
            # A new transport recovers the same durable conversation from Mycelium.
            async with streamable_http_client(resource,http_client=client) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    recovered=result(await session.call_tool('read_conversation',dict(scope=scope,conversation_key='trip')))
                    assert len(recovered['data'])==1 and recovered['data'][0]['id']==receipt['data'][0]['id']
                    graph.query('MATCH (g:Grant {node_id:$id}) SET g.revoked=true',{'id':actor+'-grant'})
                    denied=result(await session.call_tool('read_conversation',dict(scope=scope,conversation_key='trip')))
                    assert denied['error']=='scope_denied'
            credentials.write_text('[]')
            # Removed credential is rejected at HTTP before protocol content.
            denied=await client.post(resource,json={})
            assert denied.status_code==401
    try:asyncio.run(journey())
    finally:
        server.should_exit=True;thread.join(timeout=5);sock.close()
        assert not thread.is_alive()
