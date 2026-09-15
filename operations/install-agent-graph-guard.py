"""Provision an approved legacy-agent direct graph boundary projection."""
import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
from pathlib import Path
from uuid import uuid4
import shutil
import sys
import importlib.util

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'platform'))
from control.graph import Graph


POLICY_ID = 'network-policy-legacy-agent-graph-v1'


def install(revision):
    if os.geteuid() != 0 or socket.gethostname() != 'vmi3556896' or not re.fullmatch('[a-f0-9]{40}', revision):
        raise RuntimeError('invalid_guard_target')

    release = Path('/opt/seedforth/releases') / revision[:7]
    if not release.is_dir():
        raise RuntimeError('release_directory_missing')
    guard_script = release / 'operations' / 'agent-graph-guard.py'
    unit_source = release / 'platform' / 'deployment' / 'systemd' / 'seedforth-agent-graph-guard.service'
    dropin_source = release / 'platform' / 'deployment' / 'systemd' / 'agent-graph-guard-dependency.conf'
    if not guard_script.is_file() or not unit_source.is_file() or not dropin_source.is_file():
        raise RuntimeError('release_payload_missing')

    if subprocess.check_output(['git', '-C', str(release), 'rev-parse', 'HEAD'], text=True).strip() != revision:
        raise RuntimeError('wrong_release')
    if subprocess.check_output(['git', '-C', str(release), 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('dirty_release')

    for family in ['-4', '-6']:
        routes = json.loads(subprocess.check_output(['ip', '-j', family, 'route', 'show', 'default'], timeout=10))
        if not routes or any(r.get('dev') != 'eth0' for r in routes):
            raise RuntimeError('uplink_preflight_failed')

    graph = Graph()
    rows = graph.query(
        "MATCH (p:NetworkPolicy {node_id:$id, status:'approved'}) "
        "RETURN p.node_id AS id,p.version AS version,p.uids AS uids,p.ports AS ports "
        "ORDER BY p.created_at DESC LIMIT 1",
        {'id': POLICY_ID},
    )
    if len(rows) != 1:
        raise RuntimeError('approved_policy_missing_or_non_unique')

    spec = importlib.util.spec_from_file_location('agent_graph_guard', guard_script)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    policy = dict(rows[0])
    guard.validate(policy)

    raw = json.dumps(policy, sort_keys=True).encode()
    digest = hashlib.sha256(raw).hexdigest()

    security = Path('/opt/seedforth/shared/security')
    security.mkdir(mode=0o700, exist_ok=True)
    if security.is_symlink() or security.stat().st_mode & 0o077:
        raise RuntimeError('insecure_security_directory')

    projection = security / 'agent-graph-guard.json'
    if projection.exists():
        raise RuntimeError('projection_exists_inspect_before_retry')

    backup = Path('/opt/seedforth/shared/backups') / ('agent-graph-guard-' + uuid4().hex)
    backup.mkdir(mode=0o700)
    for binary, name in [('/usr/sbin/iptables-save', 'before.v4'),
                         ('/usr/sbin/ip6tables-save', 'before.v6')]:
        fd = os.open(backup / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(subprocess.check_output([binary], timeout=10))

    fd = os.open(projection, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

    release_link = Path('/opt/seedforth/agent-guard-current')
    if release_link.exists() or release_link.is_symlink():
        raise RuntimeError('agent_guard_release_link_exists_inspect_before_retry')
    release_link.symlink_to(release)

    unit = Path('/etc/systemd/system/seedforth-agent-graph-guard.service')
    dropins = [
        Path('/etc/systemd/system/seedforth-delta.service.d/seedforth-agent-graph-guard-dependency.conf'),
        Path('/etc/systemd/system/supervisor.service.d/seedforth-agent-graph-guard-dependency.conf'),
    ]
    if unit.exists() or any(path.exists() for path in dropins):
        raise RuntimeError('unit_or_dropin_exists_inspect_before_retry')

    shutil.copyfile(unit_source, unit)
    for dropin in dropins:
        dropin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(dropin_source, dropin)

    subprocess.run(
        ['systemd-analyze', 'verify',
         str(unit), '/etc/systemd/system/seedforth-delta.service',
         '/etc/systemd/system/supervisor.service'],
        check=True)
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', 'enable', '--now', 'seedforth-agent-graph-guard.service'], check=True)

    graph.query(
        "MATCH (p:NetworkPolicy {node_id:$id}) "
        "MERGE (o:Observation {node_id:'observation-agent-graph-guard-install-20260906'}) "
        "ON CREATE SET o.scope_id='seedforth-platform', o.observed_at=datetime(), "
        "o.received_at=datetime(), o.status='kernel_rules_present', o.payload_hash=$hash, "
        "o.source_revision=$revision, o.backup_ref=$backup, "
        "o.coverage='host_uid_original_tcp_graph_ports_only' "
        "MERGE (o)-[:OBSERVES_POLICY]->(p) "
        "SET p.projected_hash=$hash, p.projected_at=datetime()",
        {'id': POLICY_ID, 'hash': digest, 'revision': revision, 'backup': str(backup)},
    )

    print(json.dumps({
        'status': 'agent_graph_guard_installed',
        'policy_id': policy['id'],
        'policy_version': policy['version'],
        'policy_uids': len(policy['uids']),
        'policy_ports': policy['ports'],
        'projection_hash': digest,
        'backup': str(backup),
    }))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    install(parser.parse_args().revision)
