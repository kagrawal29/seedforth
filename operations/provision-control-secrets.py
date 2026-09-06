"""One-time external credential provisioning on the authorized delta2 host.

Run with the existing production secret environment loaded. Never prints secrets.
Existing files are refused rather than overwritten. Public OAuth is not provided.
"""
from datetime import datetime,timedelta,timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket


def provision():
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896':
        raise RuntimeError('wrong_provisioning_target')
    root=Path('/opt/seedforth/shared/env')
    names=['control-neo4j.json','control-access.json','control-owner-bootstrap-token']
    if any((root/name).exists() for name in names):
        raise RuntimeError('existing_credentials_require_explicit_rotation')
    password=os.environ['NEO4J_PASSWORD']
    if not password:
        raise RuntimeError('missing_graph_password')
    token=secrets.token_urlsafe(48)
    values={
        'control-neo4j.json':json.dumps(dict(endpoint='http://127.0.0.1:7474',user='neo4j',password=password)),
        'control-access.json':json.dumps([dict(principal='principal-seedforth-owner',
            scopes=['flowing-indian','cajon-sensei','seedforth-platform'],sha256=hashlib.sha256(token.encode()).hexdigest(),
            expires_at=(datetime.now(timezone.utc)+timedelta(days=7)).isoformat())]),
        'control-owner-bootstrap-token':token,
    }
    for name,value in values.items():
        fd=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as stream:
            stream.write(value+'\n')
            stream.flush()
            os.fsync(stream.fileno())
    print('Provisioned root-only control credentials. Bootstrap token expires in seven days.')


if __name__=='__main__':
    provision()
