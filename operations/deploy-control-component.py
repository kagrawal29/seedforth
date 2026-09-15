"""Install the control component from a verified immutable release, not Delta.

Requires a successful explicitly invoked graph migration first. Keeps Delta's
current symlink and legacy schedulers unchanged. Existing component target is
recorded in an external deployment receipt for rollback.
"""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
from uuid import uuid4


def deploy(revision):
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896' or not re.fullmatch('[0-9a-f]{40}',revision):
        raise RuntimeError('invalid_deployment_target')
    root=Path('/opt/seedforth')
    release=root/'releases'/revision[:7]
    actual=subprocess.check_output(['git','-C',str(release),'rev-parse','HEAD'],text=True).strip()
    if actual!=revision:
        raise RuntimeError('release_mismatch')
    if subprocess.check_output(['git','-C',str(release),'status','--porcelain'],text=True).strip():
        raise RuntimeError('dirty_release')
    for name in ['control-neo4j.json','control-access.json']:
        path=root/'shared/env'/name
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise RuntimeError('insecure_or_missing_credentials')
    link=root/'control-current'
    previous=str(link.resolve()) if link.is_symlink() else None
    if link.exists() and not link.is_symlink():
        raise RuntimeError('component_target_is_not_symlink')
    temporary=root/('control-candidate-'+uuid4().hex)
    temporary.symlink_to(release)
    os.replace(temporary,link)
    env=root/'shared/env/control-release.env'
    fd=os.open(env,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as stream:
        stream.write('SEEDFORTH_RELEASE_SHA='+revision+'\n')
    units=['seedforth-control.service','seedforth-runtime-sensor.service','seedforth-runtime-sensor.timer',
           'seedforth-code-sensor.service','seedforth-code-sensor.timer']
    for name in units:
        shutil.copyfile(release/'platform/deployment/systemd'/name,Path('/etc/systemd/system')/name)
    subprocess.run(['systemd-analyze','verify',*[str(Path('/etc/systemd/system')/n) for n in units]],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','seedforth-control.service','seedforth-runtime-sensor.timer',
                    'seedforth-code-sensor.timer'],check=True)
    subprocess.run(['systemctl','restart','seedforth-control.service'],check=True)
    subprocess.run(['systemctl','start','seedforth-runtime-sensor.service'],check=True)
    subprocess.run(['systemctl','start','seedforth-code-sensor.service'],check=True)
    receipt=dict(revision=revision,previous_control_target=previous,
        deployed_at=datetime.now(timezone.utc).isoformat(),status='services_started',
        main_platform_target=str((root/'current').resolve()))
    receipt_path=root/'shared/backups'/('control-deploy-'+uuid4().hex+'.json')
    fd=os.open(receipt_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        json.dump(receipt,stream)
    print(json.dumps(receipt))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True)
    deploy(parser.parse_args().revision)
