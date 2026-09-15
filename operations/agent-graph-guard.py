"""Enforce a graph-approved, offline projection at the host socket boundary.

Narrow containment, not a replacement for credential rotation or isolated workers.
Does not stop agents or change incoming-message delivery.
"""
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess

POLICY = Path('/opt/seedforth/shared/security/agent-graph-guard.json')
COMMENT = 'seedforth-legacy-agent-graph-v1'
ACCOUNTS = {
    1003: 'proj-cajon-sensei', 1004: 'proj-ethos',
    1005: 'proj-flowing-indian', 1006: 'proj-linkedin-himanshu-ghiya',
    1007: 'proj-linkedin-kshitiz-agarwal', 1008: 'proj-seedforthing',
    1009: 'proj-zuuro', 1010: 'proj-delta-hub',
}


def validate(policy):
    if (not isinstance(policy, dict) or
            set(policy) != {'id', 'version', 'uids', 'ports'} or
            policy['id'] != 'network-policy-legacy-agent-graph-v1' or
            type(policy['version']) is not int or policy['version'] != 1 or
            policy['uids'] != list(ACCOUNTS) or policy['ports'] != [7474, 7687] or
            any(type(v) is not int for v in policy['uids'] + policy['ports'])):
        raise ValueError('agent_graph_projection_outside_adapter_envelope')
    return policy


def verify_accounts(lookup=pwd.getpwuid):
    for uid, name in ACCOUNTS.items():
        try:
            account_name = lookup(uid).pw_name
        except KeyError:
            raise ValueError('agent_uid_binding_missing')
        if account_name != name:
            raise ValueError('agent_uid_binding_changed')


def read_policy(path=POLICY):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (info.st_uid != 0 or info.st_mode & 0o077 or
                not stat.S_ISREG(info.st_mode) or info.st_size > 4096):
            raise ValueError('insecure_agent_graph_projection')
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValueError('oversized_agent_graph_projection')
    return validate(json.loads(raw)), hashlib.sha256(raw).hexdigest()


def rules(policy):
    validate(policy)
    # Original destination survives local Docker DNAT. Restrict original direction
    # so an agent's replies to a transport client are not blocked by source port.
    return [['-p', 'tcp', '-m', 'owner', '--uid-owner', str(uid),
             '-m', 'conntrack', '--ctdir', 'ORIGINAL', '--ctorigdstport', str(port),
             '-m', 'comment', '--comment', COMMENT,
             '-j', 'REJECT', '--reject-with', 'tcp-reset']
            for uid in policy['uids'] for port in policy['ports']]


def enforce(policy, run=subprocess.run):
    for binary in ['/usr/sbin/iptables', '/usr/sbin/ip6tables']:
        for rule in rules(policy):
            def command(args, check=True):
                return run([binary, '-w', '5', *args], check=check,
                           capture_output=True, timeout=10)
            if command(['-C', 'OUTPUT', *rule], check=False).returncode:
                command(['-I', 'OUTPUT', '1', *rule])
            command(['-C', 'OUTPUT', *rule])


if __name__ == '__main__':
    if os.geteuid() != 0:
        raise SystemExit('root_kernel_enforcement_required')
    policy, digest = read_policy()
    verify_accounts()
    enforce(policy)
    print(json.dumps(dict(status='kernel_rules_present', policy=policy['id'],
                         projection_hash=digest,
                         coverage='host_uid_original_tcp_graph_ports_only')))
