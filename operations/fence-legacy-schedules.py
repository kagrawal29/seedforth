"""Apply the exact graph-approved root-crontab fence; preserve all other entries.

No script, user, source file, log, protocol or customer transport is deleted.
Raw crontab backups remain root-private. Never print command/environment contents.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'platform'))
from control.graph import Graph

DECISION='decision-legacy-schedule-fence-20260906'
MARKER='# seedforth fenced '+DECISION+' '


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def transform(raw, expected_hash, targets):
    if sha(raw)!=expected_hash or len(targets)!=4 or len(set(targets))!=4:
        raise ValueError('configuration_precondition_failed')
    lines=raw.decode().splitlines(keepends=True)
    found=[]
    result=[]
    for line in lines:
        digest=sha(line.rstrip('\r\n').encode())
        if digest in targets:
            if line.lstrip().startswith('#'):
                raise ValueError('target_is_not_active')
            found.append(digest)
            result.append(MARKER+line)
        else:
            result.append(line)
    if sorted(found)!=sorted(targets):
        raise ValueError('target_set_mismatch')
    return ''.join(result).encode()


def main():
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896':
        raise RuntimeError('invalid_target')
    graph=Graph()
    rows=graph.query("MATCH (d:Decision {node_id:$id,status:'accepted',target:'root-crontab'}) "
                     "RETURN d.expected_before_hash AS before,d.line_hashes AS targets,d.applied_hash AS applied",{'id':DECISION})
    if len(rows)!=1 or rows[0]['applied']:
        raise RuntimeError('decision_missing_or_already_applied_inspect_state')
    approved=rows[0]
    before=subprocess.check_output(['crontab','-l'],timeout=5)
    after=transform(before,approved['before'],approved['targets'])
    for unit in ['seedforth-mycelium-heartbeat.timer','seedforth-delta.service','whatsapp-webhook.service']:
        subprocess.run(['systemctl','is-active','--quiet',unit],check=True,timeout=5)
    root=Path('/opt/seedforth/shared/backups')/('legacy-schedule-fence-'+uuid4().hex)
    root.mkdir(mode=0o700)
    for name,raw in [('before.crontab',before),('after.crontab',after)]:
        fd=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    # A failed observation after installation must be reconciled, not rerun.
    if subprocess.check_output(['crontab','-l'],timeout=5)!=before:
        raise RuntimeError('crontab_changed_after_preflight')
    subprocess.run(['crontab','-'],input=after,check=True,timeout=5)
    actual=subprocess.check_output(['crontab','-l'],timeout=5)
    if actual!=after:
        raise RuntimeError('readback_mismatch_inspect_private_backup')
    rows=graph.operation('record-legacy-schedule-fence','principal-seedforth-owner','seedforth-platform',
                         before_hash=sha(before),after_hash=sha(after),removed_count=4,backup=str(root/'before.crontab'))
    if len(rows)!=1 or rows[0]['schedules']!=4:
        raise RuntimeError('fence_applied_evidence_pending_inspect_before_retry')
    print(json.dumps(dict(status='verified_fenced',before_hash=sha(before),after_hash=sha(after),
                          backup=str(root/'before.crontab'),**rows[0])))


if __name__=='__main__':
    main()
