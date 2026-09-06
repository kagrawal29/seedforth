"""Loopback-only control gateway. Remote publication requires a TLS/auth proxy.

Credentials are external, per-principal opaque bearer secrets stored as SHA-256
digests. Graph grants are checked on every request. No arbitrary Cypher surface.
This bootstrap transport is not OAuth and does not claim universal MCP support.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit
from uuid import uuid4

from control.graph import Graph, GraphError

WEB = Path(__file__).parent / 'web'
FIELDS = {
    'read-scope': {}, 'read-work': {}, 'read-timeline': {'id':str},
    'create-work': {'id':str,'milestone':str,'title':str,'acceptance':str},
    'ready-work': {'id':str,'version':int},
    'hold-work': {'id':str,'version':int,'hold':bool},
    'review-work': {'id':str,'version':int,'receipt':str,'artifact_hash':str,
                    'test_run':(str,type(None)),'accept':bool},
}


class RequestError(Exception):
    def __init__(self, status, code):
        self.status,self.code=status,code


class Boundary:
    def __init__(self, graph, credentials):
        self.graph,self.credentials=graph,Path(credentials)

    def authenticate(self, header):
        if not header or not header.startswith('Bearer ') or len(header)>1024:
            raise RequestError(401,'authentication_required')
        token=header[7:]
        if len(token)<32:
            raise RequestError(401,'invalid_credentials')
        digest=hashlib.sha256(token.encode()).hexdigest()
        # Reload on each request so external revocation is immediately effective.
        try:
            if self.credentials.stat().st_mode & 0o007:
                raise ValueError('world_accessible_credentials')
            entries=json.loads(self.credentials.read_text())
            for entry in entries:
                if secrets.compare_digest(digest,entry['sha256']):
                    expiry=datetime.fromisoformat(entry['expires_at'])
                    if expiry.tzinfo is None or expiry<=datetime.now(timezone.utc):
                        break
                    return entry['principal'],entry['scopes']
        except (OSError,ValueError,KeyError,TypeError):
            raise RequestError(503,'authentication_unavailable') from None
        raise RequestError(401,'invalid_credentials')

    def dispatch(self, header, body):
        actor,scopes=self.authenticate(header)
        if not isinstance(body,dict) or set(body)!={'operation','scope','params'}:
            raise RequestError(400,'invalid_envelope')
        name,scope,params=body['operation'],body['scope'],body['params']
        if not isinstance(name,str) or name not in FIELDS:
            raise RequestError(400,'unknown_operation')
        if not isinstance(scope,str) or scope not in scopes:
            raise RequestError(403,'scope_denied')
        if not isinstance(params,dict) or set(params)!=set(FIELDS[name]):
            raise RequestError(400,'invalid_parameters')
        for key,expected in FIELDS[name].items():
            value=params[key]
            allowed=expected if isinstance(expected,tuple) else (expected,)
            if type(value) not in allowed or (isinstance(value,str) and len(value)>8000):
                raise RequestError(400,'invalid_parameter_type')
            if key=='version' and value<0:
                raise RequestError(400,'invalid_version')
        permitted=self.graph.query(
            "MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(g:Grant {scope:$scope,revoked:false}) "
            "WHERE 'read' IN g.permissions AND (g.expires_at IS NULL OR g.expires_at>datetime()) "
            "RETURN count(g)>0 AS permitted",{'actor':actor,'scope':scope})
        if not permitted or not permitted[0]['permitted']:
            raise RequestError(403,'scope_denied')
        bound=dict(params)
        if name=='create-work':
            bound['request_hash']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if name in {'ready-work','hold-work','review-work'}:
            bound['event_id']=str(uuid4())
        rows=self.graph.operation(name,actor,scope,**bound)
        if not name.startswith('read-') and not rows:
            raise RequestError(409,'transition_denied_or_version_conflict')
        return {'data':rows,'scope':scope,'as_of':datetime.now(timezone.utc).isoformat(),
                'projection_version':'control-v2','evidence_status':'graph_read_succeeded'}


class Handler(BaseHTTPRequestHandler):
    server_version='SeedForthControl'

    def log_message(self,*args):
        # Do not log request headers, tokens, query strings, or graph content.
        pass

    def reply(self,status,payload,content_type='application/json'):
        data=json.dumps(payload).encode() if content_type=='application/json' else payload
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path=urlsplit(self.path).path
        names={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
        if path not in names:
            return self.reply(404,{'error':'not_found'})
        file=WEB/names[path]
        content_type={'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[file.suffix[1:]]
        self.reply(200,file.read_bytes(),content_type)

    def do_POST(self):
        try:
            if self.path!='/api/operation':
                raise RequestError(404,'not_found')
            if self.headers.get('Origin') and self.headers['Origin'] not in self.server.allowed_origins:
                raise RequestError(403,'origin_denied')
            if self.headers.get('Content-Type')!='application/json' or self.headers.get('Transfer-Encoding'):
                raise RequestError(400,'invalid_content_type')
            length=self.headers.get('Content-Length','')
            if not re.fullmatch(r'[0-9]{1,6}',length) or not 1<=int(length)<=32768:
                raise RequestError(413,'invalid_body_size')
            self.connection.settimeout(10)
            body=json.loads(self.rfile.read(int(length)))
            self.reply(200,self.server.boundary.dispatch(self.headers.get('Authorization'),body))
        except RequestError as exc:
            self.reply(exc.status,{'error':exc.code})
        except (ValueError,TimeoutError):
            self.reply(400,{'error':'invalid_body'})
        except GraphError:
            self.reply(503,{'error':'graph_unavailable_or_generation_mismatch'})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8787)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.boundary=Boundary(Graph(),os.environ['CONTROL_CREDENTIALS_FILE'])
    server.allowed_origins=set(os.environ.get('CONTROL_ALLOWED_ORIGINS',f'http://127.0.0.1:{args.port}').split(','))
    server.serve_forever()


if __name__=='__main__':
    main()
