"""Loopback-only synthetic human + real disposable graph fixture for Playwright.

Test clock/seed endpoints exist ONLY here, never in production application routes.
No owner credentials. Requires SSH forwarding of the dedicated test graph27474.
"""
import asyncio
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import threading
import time
from uuid import uuid4

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

sys.path.insert(0,str(Path(__file__).parents[1]))
from control.graph import Graph, GraphError
from control.oauth_provider import OAuthStore, DurableOAuthProvider, GraphIdentityGrants
from control.human_identity import HumanIdentity
from control.identity_web import create_identity_app


if __name__ == '__main__':
    graph = Graph('http://127.0.0.1:27474',user='',password='')
    assert graph.endpoint == 'http://127.0.0.1:27474'
    if os.environ.get('CONTROL_FIXTURE_REUSE_PROMOTION') == '1':
        graph.operation('read-identity-scopes','nonexistent-fixture','seedforth-platform')
    else:
        graph.promote()
    suffix = uuid4().hex
    scope,other = 'fixture-human-cajon-'+suffix,'fixture-human-flowing-'+suffix
    principal = 'fixture-human-'+suffix
    graph.query("CREATE (p:Principal {node_id:$principal,enabled:true})-[:HAS_GRANT]->"
        "(:Grant {node_id:$principal+'-read',scope:$scope,revoked:false,permissions:['read','conversation.send','conversation.read']}) "
        "CREATE (:ControlScope {node_id:$scope,name:'Cajon fixture'}) CREATE (:ControlScope {node_id:$other,name:'Flowing fixture'}) "
        "CREATE (:WorkItem {node_id:$scope+'-work',scope_id:$scope,title:'Synthetic human scoped work',status:'proposed',state_version:0})",
        dict(principal=principal,scope=scope,other=other))
    now = [time.time()]
    with TemporaryDirectory(prefix='seedforth-human-fixture-') as directory:
        store = OAuthStore(Path(directory)/'identity.db')
        graph_grants = GraphIdentityGrants(graph)
        outage = [False]
        def grants(principal):
            if outage[0]:
                raise GraphError('synthetic_graph_outage')
            return graph_grants(principal)
        provider = DurableOAuthProvider(store,'http://localhost:18789','http://localhost:18789/mcp',
            [scope,other],grants,clock=lambda:now[0])
        identity = HumanIdentity(store,grants,clock=lambda:now[0])
        invite = identity.issue_invite(principal)
        app = create_identity_app(identity,provider,graph)
        async def state(request):
            return JSONResponse(dict(invite=invite,scope=scope,other=other,now=now[0]))
        async def advance(request):
            now[0] += 31
            return JSONResponse(dict(now=now[0]))
        async def revoke(request):
            await asyncio.to_thread(graph.query,'MATCH (:Principal {node_id:$id})-[:HAS_GRANT]->(g:Grant) SET g.revoked=true',{'id':principal})
            return JSONResponse(dict(revoked=True))
        async def fail_graph(request):
            outage[0] = True
            return JSONResponse(dict(outage=True))
        async def callback(request):
            return PlainTextResponse('Synthetic client callback received')
        app.app.app.router.routes[0:0] = [Route('/__fixture/state',state),
            Route('/__fixture/advance',advance,methods=['POST']),Route('/__fixture/revoke',revoke,methods=['POST']),
            Route('/__fixture/outage',fail_graph,methods=['POST'])]
        callback_server = uvicorn.Server(uvicorn.Config(Starlette(routes=[Route('/callback',callback)]),
            host='127.0.0.1',port=18790,access_log=False,log_level='critical',proxy_headers=False))
        callback_thread = threading.Thread(target=callback_server.run,daemon=True)
        callback_thread.start()
        for _ in range(100):
            if callback_server.started:
                break
            time.sleep(.02)
        assert callback_server.started
        print('Synthetic identity fixture ready on localhost:18789',flush=True)
        try:
            uvicorn.run(app,host='127.0.0.1',port=18789,access_log=False,log_level='critical',proxy_headers=False)
        finally:
            callback_server.should_exit = True
            callback_thread.join(timeout=10)
