"""Deploy the identity/MCP component from one immutable SeedForth release."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
from uuid import uuid4


def deploy(revision):
    if os.geteuid() != 0 or socket.gethostname() != 'vmi3556896':
        raise RuntimeError('invalid_deployment_context')
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise RuntimeError('invalid_deployment_target')
    root = Path('/opt/seedforth')
    release = root / 'releases' / revision[:7]
    actual = subprocess.check_output(['git', '-C', str(release), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != revision or subprocess.check_output(['git', '-C', str(release), 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('release_mismatch_or_dirty')
    for name in ['control-neo4j.json']:
        path = root / 'shared/env' / name
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise RuntimeError('insecure_or_missing_credentials')
    link = root / 'identity-current'
    previous = str(link.resolve()) if link.is_symlink() else None
    if link.exists() and not link.is_symlink():
        raise RuntimeError('component_target_is_not_symlink')
    temporary = root / ('identity-candidate-' + uuid4().hex)
    temporary.symlink_to(release)
    os.replace(temporary, link)
    unit = release / 'platform/deployment/systemd/seedforth-identity.service'
    target = Path('/etc/systemd/system/seedforth-identity.service')
    shutil.copyfile(unit, target)
    subprocess.run(['systemd-analyze', 'verify', str(target)], check=True)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'seedforth-identity.service'], check=True)
    subprocess.run(['systemctl', 'restart', 'seedforth-identity.service'], check=True)
    receipt = {'revision': revision, 'previous_identity_target': previous,
               'deployed_at': datetime.now(timezone.utc).isoformat(), 'status': 'service_started'}
    destination = root / 'shared/backups' / ('identity-deploy-' + uuid4().hex + '.json')
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(receipt, stream)
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    deploy(parser.parse_args().revision)
