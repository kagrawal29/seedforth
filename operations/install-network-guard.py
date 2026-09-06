"""Provision approved kernel-policy projection without restarting Docker/services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'platform'))
from control.graph import Graph


def install(revision):
    if os.geteuid()!=0 or socket.gethostname()!='vmi3556896' or not re.fullmatch('[a-f0-9]{40}',revision):
        raise ValueError('invalid_guard_target')
    release=Path('/opt/seedforth/releases')/revision[:7]
    if subprocess.check_output(['git','-C',str(release),'rev-parse','HEAD'],text=True).strip()!=revision:
        raise ValueError('wrong_release')
    if subprocess.check_output(['git','-C',str(release),'status','--porcelain'],text=True).strip():
        raise ValueError('dirty_release')
    for family in ['-4','-6']:
        routes=json.loads(subprocess.check_output(['ip','-j',family,'route','show','default']))
        if not routes or any(r.get('dev')!='eth0' for r in routes):
            raise ValueError('uplink_preflight_failed')
    g=Graph()
    rows=g.query("MATCH (p:NetworkPolicy {node_id:'network-policy-internal-services-v1',status:'approved'}) "
                 "RETURN p.node_id AS id,p.version AS version,p.interface AS interface,p.ports AS ports")
    if len(rows)!=1:
        raise ValueError('approved_network_policy_missing')
    import importlib.util
    spec=importlib.util.spec_from_file_location('guard',release/'operations/network-guard.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    guard.validate(rows[0])
    raw=json.dumps(rows[0],sort_keys=True).encode()
    security=Path('/opt/seedforth/shared/security')
    security.mkdir(mode=0o700,exist_ok=True)
    if security.is_symlink() or security.stat().st_uid!=0 or security.stat().st_mode&0o077:
        raise ValueError('insecure_security_directory')
    projection=security/'network-guard.json'
    if projection.exists():
        raise ValueError('projection_exists_inspect_before_retry')
    backup=Path('/opt/seedforth/shared/backups')/('network-guard-'+uuid4().hex)
    backup.mkdir(mode=0o700)
    for binary,name in [('/usr/sbin/iptables-save','before.v4'),('/usr/sbin/ip6tables-save','before.v6')]:
        saved=subprocess.check_output([binary],timeout=10)
        fd=os.open(backup/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(saved)
    fd=os.open(projection,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    link=Path('/opt/seedforth/security-current')
    if link.exists() or link.is_symlink():
        raise ValueError('security_release_exists_inspect_before_retry')
    link.symlink_to(release)
    unit=Path('/etc/systemd/system/seedforth-network-guard.service')
    dropin=Path('/etc/systemd/system/docker.service.d/seedforth-network-guard.conf')
    if unit.exists() or dropin.exists():
        raise ValueError('unit_exists_inspect_before_retry')
    dropin.parent.mkdir(exist_ok=True)
    shutil.copyfile(release/'platform/deployment/systemd/seedforth-network-guard.service',unit)
    shutil.copyfile(release/'platform/deployment/systemd/docker-network-guard.conf',dropin)
    subprocess.run(['systemd-analyze','verify',str(unit),'docker.service'],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','seedforth-network-guard.service'],check=True)
    digest=hashlib.sha256(raw).hexdigest()
    g.query("MATCH (p:NetworkPolicy {node_id:$id}) "
            "MERGE (o:Observation {node_id:'observation-network-guard-install-20260906'}) "
            "ON CREATE SET o.scope_id='seedforth-platform',o.observed_at=datetime(),o.received_at=datetime(),"
            "o.status='kernel_rules_present',o.payload_hash=$hash,o.source_revision=$revision,o.backup_ref=$backup,"
            "o.coverage='local_rule_readback_external_probe_pending' "
            "MERGE (o)-[:OBSERVES_POLICY]->(p) SET p.projected_hash=$hash,p.projected_at=datetime()",
            {'id':rows[0]['id'],'hash':digest,'revision':revision,'backup':str(backup)})
    print(json.dumps(dict(status='kernel_guard_installed',projection_hash=digest,backup=str(backup))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',required=True)
    install(parser.parse_args().revision)
