"""Explicit first-pilot broker provisioning. Does not enable scope or launch work.

Run from an immutable reviewed release on delta2. Repository copies, private
credentials and process isolation are external I/O; authority is authored Cypher.
"""
import argparse
from datetime import datetime, timedelta, timezone
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shutil
import socket
import subprocess
import sys

RELEASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELEASE/'platform'))
from control.graph import Graph
from control.worker_service import build_adapters


def run(*args):
    return subprocess.check_output(list(args), text=True, stderr=subprocess.PIPE).strip()


def exclusive_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream)
        stream.flush(); os.fsync(stream.fileno())


def provision(revision):
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896' or not re.fullmatch('[0-9a-f]{40}',revision):
        raise RuntimeError('invalid_worker_provision_target')
    if run('git','-C',str(RELEASE),'rev-parse','HEAD')!=revision or run('git','-C',str(RELEASE),'status','--porcelain'):
        raise RuntimeError('immutable_release_required')
    root=Path('/opt/seedforth')
    env=root/'shared/env'
    graph=Graph()
    if graph.query("MATCH (s:ControlScope {node_id:'cajon-sensei'}) RETURN s.work_enabled AS enabled")!=[{'enabled':False}]:
        raise RuntimeError('pilot_scope_must_remain_held')
    if graph.query("MATCH (p:Principal) WHERE p.node_id IN ['principal-capability-broker','principal-cajon-upgrade-worker'] RETURN count(p) AS n")!=[{'n':0}]:
        raise RuntimeError('pilot_identity_already_exists_inspect_before_resume')
    if any((env/name).exists() for name in ['worker-access.json','worker-bindings.json','worker-pilot-token']):
        raise RuntimeError('worker_already_provisioned_inspect_before_resume')
    for group in ['seedforth-workers','seedforth-source-read']:
        try: grp.getgrnam(group)
        except KeyError: run('groupadd','--system',group)
    try: account=pwd.getpwnam('seedforth-broker')
    except KeyError:
        run('useradd','--system','--user-group','--no-create-home','--shell','/usr/sbin/nologin','seedforth-broker')
        account=pwd.getpwnam('seedforth-broker')
    source='/home/proj-cajon-sensei/cajon-sensei'
    expected='2a518d957bb1fbd39b02a8dcbc3e1f2890630b93'
    if run('git','-c','safe.directory='+source,'-C',source,'rev-parse','HEAD')!=expected:
        raise RuntimeError('pilot_source_changed_requalify')
    repositories=root/'worker-repositories'
    repositories.mkdir(mode=0o750,exist_ok=True)
    read_gid=grp.getgrnam('seedforth-source-read').gr_gid
    os.chown(repositories,0,read_gid);repositories.chmod(0o750)
    repo=repositories/'cajon-2a518d9.git'
    if not repo.exists():
        run('git','-c','safe.directory='+source,'clone','--bare','--no-hardlinks','--depth','1','file://'+source,str(repo))
    if run('git','-C',str(repo),'rev-parse','HEAD')!=expected:
        raise RuntimeError('private_source_copy_mismatch')
    for path in [repo,*repo.rglob('*')]:
        if path.is_symlink(): raise RuntimeError('unexpected_repository_symlink')
        os.chown(path,0,read_gid);path.chmod(0o750 if path.is_dir() else 0o640)
    state=Path('/var/lib/seedforth-worker')
    state.mkdir(mode=0o700,exist_ok=True)
    os.chown(state,account.pw_uid,account.pw_gid);state.chmod(0o700)
    binding={'cajon-sensei':str(repo)}
    token=secrets.token_urlsafe(48)
    expiry=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()
    exclusive_json(env/'worker-access.json',[dict(principal='principal-cajon-upgrade-worker',
        scopes=['cajon-sensei'],sha256=hashlib.sha256(token.encode()).hexdigest(),expires_at=expiry)])
    exclusive_json(env/'worker-bindings.json',{'repositories':binding})
    fd=os.open(env/'worker-pilot-token',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream: stream.write(token)
    adapters=build_adapters(binding,state)
    params=dict(expires_at=expiry,capabilities=[dict(id=name,generation=adapter.generation,
        cost_units=adapter.cost_units,max_seconds=adapter.max_seconds) for name,adapter in adapters.items()])
    source_text=(RELEASE/'platform/mycelium/graph/knowledge/seedforth-worker-pilot-authority.cypher').read_text()
    statements=[s.strip() for s in '\n'.join(l for l in source_text.splitlines() if not l.startswith('//')).split(';') if s.strip()]
    if graph.query("MATCH (s:ControlScope {node_id:'cajon-sensei'}) RETURN s.work_enabled AS enabled")!=[{'enabled':False}]:
        raise RuntimeError('pilot_scope_must_remain_held')
    graph.promote()
    for statement in statements: graph.query(statement,params)
    link=root/'worker-current'
    if link.exists() or link.is_symlink(): raise RuntimeError('worker_component_already_exists')
    link.symlink_to(RELEASE)
    for unit in ['seedforth-worker.socket','seedforth-worker.service']:
        shutil.copyfile(RELEASE/'platform/deployment/systemd'/unit,Path('/etc/systemd/system')/unit)
    run('systemd-analyze','verify','/etc/systemd/system/seedforth-worker.socket','/etc/systemd/system/seedforth-worker.service')
    run('systemctl','daemon-reload')
    run('systemctl','enable','--now','seedforth-worker.socket')
    run('systemctl','start','seedforth-worker.service')
    receipt=dict(revision=revision,source_revision=expected,scope='cajon-sensei',expires_at=expiry,
        capabilities=list(adapters),scope_enabled=False,worker_launched=False)
    exclusive_json(root/'shared/backups'/('worker-provision-'+revision[:7]+'.json'),receipt)
    print(json.dumps(receipt))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True)
    try: provision(parser.parse_args().revision)
    except Exception as exc:
        print('worker_provision_failed:'+type(exc).__name__,flush=True)
        raise SystemExit(1) from None
