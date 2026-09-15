import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location('agent_guard',
    Path(__file__).parents[2] / 'operations/agent-graph-guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
POLICY = dict(id='network-policy-legacy-agent-graph-v1', version=1,
              uids=list(range(1003, 1011)), ports=[7474, 7687])


def test_fixed_scope_rejects_root_transport_and_arbitrary_ports():
    assert guard.validate(POLICY) == POLICY
    for patch in [dict(uids=[0]), dict(uids=[1001]), dict(ports=[22]),
                  dict(uids=[1003]), dict(version=True), dict(extra='bad'),
                  dict(uids='1003:1010'), dict(ports=[7474.0, 7687])]:
        with pytest.raises(ValueError):
            guard.validate({**POLICY, **patch})


def test_account_reuse_is_detected():
    guard.verify_accounts(lambda uid: SimpleNamespace(pw_name=guard.ACCOUNTS[uid]))
    with pytest.raises(ValueError, match='binding_changed'):
        guard.verify_accounts(lambda uid: SimpleNamespace(pw_name='someone-else'))


def test_original_direction_and_exact_uids_only():
    rules = guard.rules(POLICY)
    assert len(rules) == 16
    for rule in rules:
        assert rule[rule.index('--uid-owner') + 1] in map(str, POLICY['uids'])
        assert rule[rule.index('--ctorigdstport') + 1] in ['7474', '7687']
        assert rule[rule.index('--ctdir') + 1] == 'ORIGINAL'
        assert rule[-3:] == ['REJECT', '--reject-with', 'tcp-reset']


def test_idempotent_readback_no_shared_rule_deletion():
    installed = set()
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        cmd = args[3:]
        if cmd[0] == '-C':
            return SimpleNamespace(returncode=int((args[0], tuple(cmd[1:])) not in installed))
        if cmd[0] == '-I':
            installed.add((args[0], tuple([cmd[1], *cmd[3:]])))
        return SimpleNamespace(returncode=0)
    guard.enforce(POLICY, run)
    guard.enforce(POLICY, run)
    assert len(installed) == 32
    assert sum('-I' in c for c in calls) == 32
    assert all(not set(c).intersection({'-F', '-D', '-P'}) for c in calls)


def test_boot_gate_does_not_stop_existing_transports_or_remove_rules():
    root = Path(__file__).parents[1] / 'deployment/systemd'
    unit = (root / 'seedforth-agent-graph-guard.service').read_text()
    dependency = (root / 'agent-graph-guard-dependency.conf').read_text()
    assert 'Before=supervisor.service seedforth-delta.service' in unit
    assert 'Requires=seedforth-agent-graph-guard.service' in dependency
    assert 'ExecStop' not in unit and 'PartOf=' not in unit
