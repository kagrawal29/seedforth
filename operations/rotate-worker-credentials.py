"""Rotate scoped worker transport credentials on the reviewed server.

This is external credential I/O only. Graph authority remains in Mycelium and
the operation never enables a scope or creates work.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
from uuid import uuid4

RELEASE = Path(__file__).resolve().parents[1]
ROOT = Path('/opt/seedforth')
ENV = ROOT / 'shared/env'
BACKUPS = ROOT / 'shared/backups'


def run(*args):
    return subprocess.check_output(list(args), text=True, stderr=subprocess.PIPE).strip()


def private_copy(source, target):
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(source.read_bytes())
            stream.flush(); os.fsync(stream.fileno())
    except BaseException:
        try: os.close(fd)
        except OSError: pass
        raise


def atomic_text(target, value):
    temporary = target.with_name('.' + target.name + '.' + uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(value); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    except BaseException:
        try: temporary.unlink()
        except FileNotFoundError: pass
        raise


def rotate(revision, release=RELEASE):
    if os.geteuid() != 0 or socket.gethostname() != 'vmi3556896':
        raise RuntimeError('root_server_required')
    if run('git', '-C', str(release), 'rev-parse', 'HEAD') != revision or run('git', '-C', str(release), 'status', '--porcelain'):
        raise RuntimeError('immutable_release_required')
    access = ENV / 'worker-access.json'
    bindings = ENV / 'worker-bindings.json'
    tokens = {scope: ENV / ('worker-' + scope + '.token') for scope in ['flowing-indian', 'cajon-sensei']}
    if access.is_symlink() or bindings.is_symlink() or any(path.is_symlink() for path in tokens.values()):
        raise RuntimeError('credential_symlink_rejected')
    entries = json.loads(access.read_text())
    by_scope = {scope: next((e for e in entries if e.get('scopes') == [scope]), None) for scope in tokens}
    if any(value is None for value in by_scope.values()):
        raise RuntimeError('expected_worker_scope_missing')
    backup = BACKUPS / ('worker-credential-rotation-' + uuid4().hex)
    backup.mkdir(mode=0o700)
    os.chmod(backup, 0o700)
    private_copy(access, backup / 'worker-access.json')
    for path in tokens.values(): private_copy(path, backup / path.name)
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    rotated = []
    for scope, path in tokens.items():
        token = secrets.token_urlsafe(48)
        by_scope[scope]['sha256'] = hashlib.sha256(token.encode()).hexdigest()
        by_scope[scope]['expires_at'] = expiry
        atomic_text(path, token)
        rotated.append({'scope': scope, 'token_sha256': by_scope[scope]['sha256']})
    atomic_text(access, json.dumps(entries, sort_keys=True, separators=(',', ':')))
    run('systemctl', 'restart', 'seedforth-worker.service')
    if run('systemctl', 'is-active', 'seedforth-worker.service') != 'active':
        raise RuntimeError('worker_restart_failed')
    receipt = {'revision': revision, 'expires_at': expiry, 'backup': str(backup), 'rotated': rotated}
    receipt_path = BACKUPS / ('worker-credential-rotation-' + revision[:7] + '-' + uuid4().hex[:12] + '.json')
    atomic_text(receipt_path, json.dumps(receipt, sort_keys=True))
    print(json.dumps(receipt))


if __name__ == '__main__':
    if len(sys.argv) not in {3, 5} or sys.argv[1] != '--revision':
        raise SystemExit('usage: rotate-worker-credentials.py --revision <immutable-release> [--release <path>]')
    release = Path(sys.argv[4]) if len(sys.argv) == 5 and sys.argv[3] == '--release' else RELEASE
    rotate(sys.argv[2], release)
