"""Private Unix-socket worker surface. Identity never comes from model parameters.

Workers receive one expiring scoped credential, not Neo4j credentials. This
transport does not itself establish OS isolation; worker launch must enforce it.
"""
from datetime import datetime,timezone
import http.client
import json
import os
import socket
from socketserver import ThreadingMixIn,UnixStreamServer
from uuid import uuid4

from control.broker import InvocationDenied
from control.server import Boundary,Handler,RequestError

FIELDS={
    'read-work':{},'read-attempt':{'attempt':str},
    'claim-work':{'id':str,'version':int,'attempt':str},
    'renew-work':{'attempt':str,'fence':int},
    'invoke':{'attempt':str,'fence':int,'invocation':str,'capability':str,'arguments':dict},
    'complete-invocation-work':{'attempt':str,'fence':int,'invocation':str},
}


class WorkerBoundary(Boundary):
    def __init__(self,graph,credentials,broker):
        super().__init__(graph,credentials)
        self.broker=broker

    def dispatch(self,header,body):
        actor,scopes=self.authenticate(header)
        if not isinstance(body,dict) or set(body)!={'operation','scope','params'}:
            raise RequestError(400,'invalid_envelope')
        name,scope,params=body['operation'],body['scope'],body['params']
        if type(name) is not str or name not in FIELDS:
            raise RequestError(400,'worker_operation_not_exposed')
        if type(scope) is not str or scope not in scopes:
            raise RequestError(403,'scope_denied')
        if not isinstance(params,dict) or set(params)!=set(FIELDS[name]):
            raise RequestError(400,'invalid_worker_parameters')
        for key,expected in FIELDS[name].items():
            if type(params[key]) is not expected or (type(params[key]) is str and len(params[key])>512):
                raise RequestError(400,'invalid_worker_parameter_type')
            if expected is int and params[key]<0:
                raise RequestError(400,'invalid_worker_version')
        bound=dict(params)
        if name=='invoke':
            try:
                rows=[self.broker.invoke(actor=actor,scope=scope,**bound)]
            except InvocationDenied:
                raise RequestError(409,'invocation_denied_or_reconciliation_required') from None
        else:
            if name in {'claim-work','complete-invocation-work'}:
                bound['event_id']=str(uuid4())
            rows=self.graph.operation(name,actor,scope,**bound)
        if not name.startswith('read-') and not rows:
            raise RequestError(409,'worker_transition_denied_or_version_conflict')
        return dict(data=rows,scope=scope,as_of=datetime.now(timezone.utc).isoformat())


class WorkerHandler(Handler):
    def do_GET(self):
        self.reply(404,{'error':'not_found'})

    def do_POST(self):
        try:
            super().do_POST()
        except (RuntimeError,OSError):
            self.reply(503,{'error':'worker_service_unavailable_do_not_redispatch'})


class WorkerServer(ThreadingMixIn,UnixStreamServer):
    daemon_threads=True
    request_queue_size=16

    def __init__(self,path,boundary):
        # Existing paths are not unlinked: an occupied/stale socket is an explicit
        # lifecycle issue, never evidence that another process can be replaced.
        super().__init__(str(path),WorkerHandler)
        os.chmod(path,0o660)
        self.boundary=boundary
        self.allowed_origins=set()


class WorkerClient:
    def __init__(self,socket_path,token,scope):
        self.socket_path,self.token,self.scope=str(socket_path),token,scope

    def request(self,operation,**params):
        connection=http.client.HTTPConnection('localhost',timeout=40)
        connection.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        connection.sock.settimeout(40)
        connection.sock.connect(self.socket_path)
        try:
            connection.request('POST','/api/operation',body=json.dumps(dict(operation=operation,scope=self.scope,params=params)),
                headers={'Content-Type':'application/json','Authorization':'Bearer '+self.token})
            response=connection.getresponse()
            result=json.loads(response.read(65536))
            if response.status!=200:
                raise RequestError(response.status,result.get('error','worker_request_failed'))
            return result['data']
        finally:
            connection.close()
