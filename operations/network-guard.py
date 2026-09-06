"""External kernel enforcement of an approved, root-protected graph projection.

Available before Neo4j/Docker starts. Never fetch authority from an unavailable
database at boot, flush shared firewall rules, or remove protection on stop.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

POLICY=Path('/opt/seedforth/shared/security/network-guard.json')
COMMENT='seedforth-internal-services-v1'


def validate(policy):
    if not isinstance(policy,dict) or set(policy)!={'id','version','interface','ports'}:
        raise ValueError('invalid_network_projection')
    # Safety envelope for this reviewed adapter, not arbitrary firewall execution.
    if (policy['id']!='network-policy-internal-services-v1' or type(policy['version']) is not int
            or policy['version']!=1 or policy['interface']!='eth0'
            or policy['ports']!=[6083,7474,7687]
            or any(type(p) is not int for p in policy['ports'])):
        raise ValueError('network_projection_outside_adapter_envelope')
    return policy


def read_policy(path=POLICY):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if info.st_uid!=0 or info.st_mode&0o077 or not stat.S_ISREG(info.st_mode) or info.st_size>4096:
            raise ValueError('insecure_network_projection')
        raw=stream.read(4097)
    if len(raw)>4096:
        raise ValueError('oversized_network_projection')
    return validate(json.loads(raw)),hashlib.sha256(raw).hexdigest()


def rules(policy):
    validate(policy)
    common=['-i',policy['interface'],'-p','tcp']
    ending=['-m','comment','--comment',COMMENT,'-j','REJECT','--reject-with','tcp-reset']
    result=[('INPUT',common+['-m','multiport','--dports',','.join(map(str,policy['ports']))]+ending)]
    # Original-direction match does not block replies to container-originated
    # connections. Original destination port remains correct after Docker DNAT.
    for port in policy['ports']:
        result.append(('DOCKER-USER',common+['-m','conntrack','--ctdir','ORIGINAL',
                                           '--ctorigdstport',str(port)]+ending))
    return result


def enforce(policy,run=subprocess.run):
    for binary in ['/usr/sbin/iptables','/usr/sbin/ip6tables']:
        def command(args,check=True):
            return run([binary,'-w','5',*args],check=check,capture_output=True,timeout=10)
        # Docker's supported policy chain may not exist yet on a fresh boot.
        if command(['-S','DOCKER-USER'],check=False).returncode:
            command(['-N','DOCKER-USER'])
        for chain,rule in rules(policy):
            if command(['-C',chain,*rule],check=False).returncode:
                command(['-I',chain,'1',*rule])
            command(['-C',chain,*rule])


if __name__=='__main__':
    if os.geteuid()!=0:
        raise SystemExit('root_kernel_enforcement_required')
    policy,digest=read_policy()
    enforce(policy)
    print(json.dumps(dict(status='kernel_rules_present',policy=policy['id'],projection_hash=digest,
                          coverage='ipv4_ipv6_input_and_docker_user_not_external_probe')))
