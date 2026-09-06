"""Real HTTP OAuth issuance -> official MCP client -> disposable graph.

Consent uses an explicitly synthetic internal human adapter, not a public route.
Full login/browser consent remains a separate mandatory qualification.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import socket
import sys
import threading
import time
from urllib.parse import parse_qs, urlsplit

import pytest

pytest.importorskip('mcp')
import httpx2
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from starlette.applications import Starlette
from starlette.routing import Mount

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.oauth_provider import OAuthStore, DurableOAuthProvider, GraphIdentityGrants
from control.oauth_http import auth_routes
from control.mcp_gateway import create_mcp, http_app
from test_conversations import case
from test_oauth_provider import VERIFIER, CHALLENGE


def test_actual_oauth_issue_mcp_read_refresh_reconnect_graph_revoke(case, tmp_path):
    graph, _, scope, actor = case
    tmp_path.chmod(0o700)
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sock.listen(128)
    port = sock.getsockname()[1]
    issuer = f'http://127.0.0.1:{port}'
    resource = issuer + '/mcp'
    provider = DurableOAuthProvider(OAuthStore(tmp_path/'oauth.db'), issuer, resource,
        [scope], GraphIdentityGrants(graph))
    mcp_app = http_app(create_mcp(graph, provider, provider.issuer, resource), [f'127.0.0.1:{port}'], [issuer])
    @asynccontextmanager
    async def lifespan(app):
        async with mcp_app.router.lifespan_context(mcp_app):
            yield
    app = Starlette(routes=auth_routes(provider) + [Mount('/', app=mcp_app)], lifespan=lifespan)
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, log_level='critical', access_log=False))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            assert thread.is_alive()
            time.sleep(.02)
        assert server.started
        async def read(access):
            async with httpx2.AsyncClient(headers={'Authorization':'Bearer '+access}) as http:
                async with streamable_http_client(resource, http_client=http) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        result = await session.call_tool('read_work', {'scope':scope})
                        assert not result.is_error
                        assert result.structured_content['data'][0]['title'] == 'Scoped work'
                        denied = await session.call_tool('read_work', {'scope':'foreign'})
                        assert denied.structured_content['error'] == 'scope_denied'
                        queued = await session.call_tool('send_to_delta', dict(scope=scope,
                            conversation_key='oauth-journey', request_id='same-direction',
                            text='Inspect this scoped work. This direction is not execution authority.'))
                        assert queued.structured_content['data'][0]['delivery_state'] == 'queued'
                        conversation = await session.call_tool('read_conversation', dict(scope=scope,
                            conversation_key='oauth-journey'))
                        assert len(conversation.structured_content['data']) == 1
        async def journey():
            async with httpx2.AsyncClient() as http:
                challenge = await http.post(resource, json={})
                assert challenge.status_code == 401
                metadata = (await http.get(issuer+'/.well-known/oauth-protected-resource/mcp')).json()
                assert metadata['authorization_servers'] == [provider.issuer]
                auth = (await http.get(issuer+'/.well-known/oauth-authorization-server')).json()
                assert auth['issuer'] == provider.issuer
                assert auth['token_endpoint_auth_methods_supported'] == ['none']
                registered = await http.post(auth['registration_endpoint'], json=dict(
                    client_name='Synthetic official SDK client', token_endpoint_auth_method='none',
                    redirect_uris=['http://127.0.0.1:9913/callback'],
                    grant_types=['authorization_code','refresh_token'], response_types=['code'], scope='mycelium'))
                assert registered.status_code == 201
                client_id = registered.json()['client_id']
                authorize = await http.get(auth['authorization_endpoint'], params=dict(
                    client_id=client_id, redirect_uri='http://127.0.0.1:9913/callback', resource=resource,
                    response_type='code', scope='mycelium', code_challenge=CHALLENGE,
                    code_challenge_method='S256', state='synthetic-state'))
                assert authorize.status_code == 302
                transaction = parse_qs(urlsplit(authorize.headers['location']).query)['request'][0]
                redirect = await asyncio.to_thread(provider.consent, transaction, actor, [scope])
                code = parse_qs(urlsplit(redirect).query)['code'][0]
                issued = await http.post(auth['token_endpoint'], data=dict(client_id=client_id,
                    grant_type='authorization_code', code=code, code_verifier=VERIFIER,
                    redirect_uri='http://127.0.0.1:9913/callback', resource=resource))
                assert issued.status_code == 200
                token = issued.json()
                await read(token['access_token'])
                refreshed = await http.post(auth['token_endpoint'], data=dict(client_id=client_id,
                    grant_type='refresh_token', refresh_token=token['refresh_token'], resource=resource))
                assert refreshed.status_code == 200
                new = refreshed.json()
                await read(new['access_token'])
                old = await http.post(resource, json={}, headers={'Authorization':'Bearer '+token['access_token']})
                assert old.status_code == 401
                await asyncio.to_thread(graph.query,
                    'MATCH (:Principal {node_id:$actor})-[:HAS_GRANT]->(g:Grant) SET g.revoked=true', {'actor':actor})
                denied = await http.post(resource, json={}, headers={'Authorization':'Bearer '+new['access_token']})
                assert denied.status_code == 401
                revoked = await http.post(auth['revocation_endpoint'], data=dict(client_id=client_id, token=new['refresh_token']))
                assert revoked.status_code == 200
        asyncio.run(journey())
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        assert not thread.is_alive()
