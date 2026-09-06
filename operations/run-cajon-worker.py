"""Launch the explicitly reviewed single Cajon pilot in an isolated container.

Graph admission and readiness precede launch. Uncertain launch outcomes must be
reconciled using the exact container/attempt; this adapter never restarts them.
"""
import grp
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'platform'))
sys.path.insert(0,str(ROOT/'platform/integration-tests/fixtures'))
from control.graph import Graph
from cajon_candidate import CHANGES, REVISION

IMAGE='python@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254'
JOB={'scope':'cajon-sensei','work':'wi-cajon-partial-loop-credit',
     'attempt':'attempt-cajon-pilot-v1','invocation':'invocation-cajon-pilot-v1'}


def main():
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896': raise RuntimeError('invalid_pilot_target')
    graph=Graph()
    if graph.query('MATCH (e:ExecutionSession {node_id:$attempt}) RETURN count(e) AS n',JOB)!=[{'n':0}]:
        raise RuntimeError('existing_attempt_reconcile_only')
    if subprocess.run(['docker','inspect','sf-cajon-pilot-v1'],capture_output=True).returncode==0:
        raise RuntimeError('existing_container_reconcile_only')
    folder=Path('/opt/seedforth/shared/backups/cajon-pilot-launch-v1')
    folder.mkdir(mode=0o700)
    token=folder/'worker-token'
    fd=os.open(token,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
    with os.fdopen(fd,'w') as out: out.write(Path('/opt/seedforth/shared/env/worker-pilot-token').read_text())
    os.chown(token,65534,65534)
    job=folder/'job.json'
    fd=os.open(job,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
    with os.fdopen(fd,'w') as out: json.dump(JOB,out)
    params=dict(revision=REVISION,expected_hash='dad62bbc229af2cb827326608660bb23ef64381caa7a48909cddc000ffc53a85',
        arguments=json.dumps({'revision':REVISION,'changes':[dict(path='app/index.html',old=a,new=b) for a,b in CHANGES]}))
    source=ROOT/'platform/mycelium/graph/control/admit-cajon-reviewed-proposal.cypher'
    statement='\n'.join(l for l in source.read_text().splitlines() if not l.startswith('//'))
    admitted=graph.query(statement,params)
    if len(admitted)!=1: raise RuntimeError('pilot_admission_denied')
    ready=graph.operation('ready-work','principal-seedforth-owner','cajon-sensei',
        id=JOB['work'],version=admitted[0]['version'],event_id='transition-cajon-pilot-ready-v1')
    if len(ready)!=1: raise RuntimeError('pilot_ready_denied')
    gid=grp.getgrnam('seedforth-workers').gr_gid
    command=['docker','run','--rm','--name','sf-cajon-pilot-v1','--network=none','--read-only',
        '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=32','--memory=128m',
        '--cpus=0.5','--user=65534:65534','--group-add',str(gid),
        '--mount','type=bind,src=/run/seedforth-worker/broker.sock,dst=/run/broker.sock,readonly',
        '--mount',f'type=bind,src={token},dst=/run/worker-token,readonly',
        '--mount',f'type=bind,src={job},dst=/run/job.json,readonly',
        '--mount',f'type=bind,src={ROOT}/platform/control/isolated_worker.py,dst=/worker.py,readonly',
        IMAGE,'python','-B','/worker.py']
    result=subprocess.run(command,capture_output=True,text=True,timeout=75)
    if result.returncode!=0: raise RuntimeError('worker_failed_inspect_attempt_before_retry')
    outcome=json.loads(result.stdout)
    if outcome.get('status')!='review': raise RuntimeError('review_not_confirmed')
    fd=os.open(folder/'result.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out: json.dump(outcome,out)
    print(json.dumps(outcome))


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('pilot_launch_stopped:'+type(exc).__name__,flush=True)
        raise SystemExit(1) from None
