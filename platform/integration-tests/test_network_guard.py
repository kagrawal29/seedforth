import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

path=Path(__file__).parents[2]/'operations/network-guard.py'
spec=importlib.util.spec_from_file_location('guard',path)
guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
POLICY=dict(id='network-policy-internal-services-v1',version=1,interface='eth0',ports=[6083,7474,7687])


def test_policy_cannot_touch_ssh_other_interfaces_or_inject_commands():
    for changes in [dict(ports=[22,7474,7687]),dict(interface='eth0; bad'),dict(ports=[6083,7474,7687,8900]),dict(version=True)]:
        with pytest.raises(ValueError):guard.validate({**POLICY,**changes})
    assert guard.validate(POLICY)==POLICY


def test_rules_preserve_local_and_reply_direction_and_use_original_ports():
    rules=guard.rules(POLICY)
    assert len(rules)==4
    for chain,args in rules:
        assert args[:4]==['-i','eth0','-p','tcp']
        assert '22' not in args and '8900' not in args
        assert args[-3:]==['REJECT','--reject-with','tcp-reset']
        if chain=='DOCKER-USER':
            assert args[args.index('--ctdir')+1]=='ORIGINAL'
            assert args[args.index('--ctorigdstport')+1] in ['6083','7474','7687']


def test_reapplication_is_idempotent_and_never_flushes_shared_rules():
    installed=set();commands=[]
    def run(args,**kwargs):
        commands.append(args)
        command=args[3:]
        if command[:1]==['-C']:
            return SimpleNamespace(returncode=0 if (args[0],tuple(command[1:])) in installed else 1)
        if command[:1]==['-I']:
            installed.add((args[0],tuple([command[1],*command[3:]])))
        return SimpleNamespace(returncode=0)
    guard.enforce(POLICY,run)
    guard.enforce(POLICY,run)
    assert sum('-I' in c for c in commands)==8
    assert all('-F' not in c and '-D' not in c and '-P' not in c for c in commands)
    assert len(installed)==8


def test_boot_enforcement_precedes_docker_without_graph_dependency():
    root=Path(__file__).parents[1]/'deployment/systemd'
    service=(root/'seedforth-network-guard.service').read_text()
    dependency=(root/'docker-network-guard.conf').read_text()
    assert 'Before=docker.service' in service and 'PartOf=docker.service' in service
    assert 'Requires=seedforth-network-guard.service' in dependency
    assert 'After=seedforth-network-guard.service' in dependency
    assert 'LoadCredential' not in service and 'ExecStop' not in service
