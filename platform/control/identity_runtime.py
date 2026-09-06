"""Private production identity runtime and root-only external credential I/O."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import sqlite3
import stat
import struct
import threading
from uuid import uuid4

import uvicorn

from control.graph import Graph
from control.oauth_provider import OAuthStore, DurableOAuthProvider, GraphIdentityGrants
from control.human_identity import HumanIdentity, IdentityError
from control.identity_web import create_identity_app


def deployment_policy(graph):
    rows = graph.query("MATCH (p:DeploymentPolicy {node_id:'deployment-policy-human-identity-v1',status:'approved'}) "
        "RETURN p.issuer AS issuer,p.resource AS resource,p.project_scopes AS scopes,"
        "p.bind_host AS host,p.bind_port AS port,p.public_ingress_enabled AS public")
    if len(rows) != 1:
        raise ValueError('identity_deployment_policy_missing')
    p = rows[0]
    if (p['issuer'] != 'https://185.192.96.100/' or p['resource'] != 'https://185.192.96.100/mcp'
            or p['host'] != '127.0.0.1' or p['port'] != 8788 or p['public'] is not False
            or set(p['scopes']) != {'seedforth-platform','flowing-indian','cajon-sensei'}):
        raise ValueError('identity_deployment_policy_outside_qualified_envelope')
    return p


def backup_credentials(store):
    directory = store.path.parent/'snapshots'
    directory.mkdir(mode=0o700,exist_ok=True)
    if directory.is_symlink() or directory.stat().st_mode & 0o077:
        raise ValueError('insecure_snapshot_directory')
    target = directory/('identity-'+uuid4().hex+'.sqlite')
    fd = os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.close(fd)
    source = sqlite3.connect(store.path)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
        if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('snapshot_integrity_failed')
    finally:
        destination.close(); source.close()
    return dict(backup_ref=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest())


def invalidate_recovered_credentials(store):
    """Offline recovery step, never an HTTP or agent tool. Retains identity maps."""
    with store.transaction() as db:
        db.execute('UPDATE families SET revoked=1')
        db.execute('UPDATE human_sessions SET revoked=1')
        db.execute('UPDATE human_users SET enabled=0')
        db.execute('UPDATE human_recovery SET used=1')
        db.execute('UPDATE human_invites SET used=1')
        db.execute('UPDATE human_pending SET expires=0')
        db.execute('UPDATE requests SET used=1')
        db.execute('UPDATE codes SET used=1')


def admin_operation(identity, body, peer_uid):
    if peer_uid != 0:
        raise IdentityError('root_operator_required',403)
    if not isinstance(body,dict):
        raise IdentityError('invalid_operator_request')
    if body == {'operation':'backup'}:
        return backup_credentials(identity.store)
    if (set(body) != {'operation','principal'} or body['operation'] not in {'invite','reset'}
            or not isinstance(body['principal'],str) or not re.fullmatch('[a-zA-Z0-9_-]{3,128}',body['principal'])):
        raise IdentityError('invalid_operator_request')
    value = identity.issue_invite(body['principal'],reset=body['operation']=='reset')
    return {'invitation':value,'expires_in':86400,'principal':body['principal']}


class OperatorHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(5)
        try:
            _,uid,_ = struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid != 0:
                raise IdentityError('root_operator_required',403)
            data = bytearray()
            while len(data) <= 4096:
                chunk = self.request.recv(min(4097-len(data),1024))
                if not chunk:
                    break
                data.extend(chunk)
                if b'\n' in data:
                    break
            if len(data)>4096 or not data.endswith(b'\n'):
                raise IdentityError('invalid_operator_request')
            response = admin_operation(self.server.identity,json.loads(data),uid)
        except IdentityError as exc:
            response = {'error':exc.code}
        except Exception:
            response = {'error':'operator_request_failed'}
        self.request.sendall(json.dumps(response).encode()+b'\n')


class OperatorServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    request_queue_size = 4


def operator_server(path,identity):
    path = Path(path)
    if (path.parent.is_symlink() or path.parent.stat().st_uid != os.geteuid()
            or path.parent.stat().st_mode & 0o077):
        raise ValueError('insecure_operator_socket_directory')
    # systemd owns the runtime directory lifecycle. Never unlink an unknown path.
    if path.exists() or path.is_symlink():
        raise ValueError('operator_socket_exists')
    server = OperatorServer(str(path),OperatorHandler)
    server.identity = identity
    os.chmod(path,0o600)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',default='/var/lib/seedforth-identity/identity.db')
    parser.add_argument('--operator-socket',default='/run/seedforth-identity/operator.sock')
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise ValueError('identity_runtime_must_not_run_as_root')
    graph = Graph()
    p = deployment_policy(graph)
    grants = GraphIdentityGrants(graph)
    # Fail startup if the reviewed identity-scope atom has not been promoted.
    grants('nonexistent-identity-startup-probe')
    store = OAuthStore(args.state)
    provider = DurableOAuthProvider(store,p['issuer'],p['resource'],p['scopes'],grants)
    identity = HumanIdentity(store,grants)
    operator = operator_server(args.operator_socket,identity)
    thread = threading.Thread(target=operator.serve_forever,daemon=True)
    thread.start()
    try:
        uvicorn.run(create_identity_app(identity,provider,graph),host=p['host'],port=p['port'],
                    proxy_headers=False,access_log=False,log_level='warning')
    finally:
        operator.shutdown(); operator.server_close(); thread.join(timeout=5)


if __name__=='__main__':
    main()
