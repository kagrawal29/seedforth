"""Add the authored platform scope to the existing bootstrap owner credential.

Preserves token digest and expiry. Does not alter teammate credentials. Restart
the control service after this change because systemd credentials are snapshots.
"""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import socket
from uuid import uuid4


def extend():
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896':
        raise RuntimeError('wrong_scope_migration_target')
    path=Path('/opt/seedforth/shared/env/control-access.json')
    entries=json.loads(path.read_text())
    owners=[e for e in entries if e.get('principal')=='principal-seedforth-owner']
    if len(owners)!=1:
        raise RuntimeError('ambiguous_owner_credential')
    owner=owners[0]
    if datetime.fromisoformat(owner['expires_at'])<=datetime.now(timezone.utc):
        raise RuntimeError('expired_credential_requires_rotation')
    if not set(owner['scopes'])<= {'flowing-indian','cajon-sensei','seedforth-platform'}:
        raise RuntimeError('unexpected_existing_scopes')
    if 'seedforth-platform' in owner['scopes']:
        print('Owner platform scope already present.')
        return
    backup=Path('/opt/seedforth/shared/backups')/('control-access-before-'+uuid4().hex+'.json')
    fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(entries,stream)
    owner['scopes'].append('seedforth-platform')
    candidate=path.parent/('control-access-candidate-'+uuid4().hex)
    fd=os.open(candidate,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(entries,stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(candidate,path)
    print('Added platform scope to bootstrap owner. Token and expiry unchanged.')


if __name__=='__main__':
    extend()
