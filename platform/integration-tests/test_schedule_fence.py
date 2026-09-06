import importlib.util
import os
from pathlib import Path

import pytest

path=Path(__file__).parents[2]/'operations/fence-legacy-schedules.py'
spec=importlib.util.spec_from_file_location('schedule_fence',path)
fence=importlib.util.module_from_spec(spec)
spec.loader.exec_module(fence)


def fixture():
    target=[f'0 {n} * * * python3 /fixture/job{n}.py' for n in range(4)]
    preserved='# Header\nSHELL=/bin/sh\n*/5 * * * * /fixture/ingest\n'
    before=(preserved+'\n'.join(target)+'\n').encode()
    return before,[fence.sha(line.encode()) for line in target],preserved.encode()


def test_exact_targets_disabled_without_removing_any_content():
    before,targets,preserved=fixture()
    result=fence.transform(before,fence.sha(before),targets)
    assert result.startswith(preserved)
    assert result.count(fence.MARKER.encode())==4
    assert result.replace(fence.MARKER.encode(),b'')==before


def test_changed_configuration_and_missing_or_duplicate_targets_fail_closed():
    before,targets,_=fixture()
    with pytest.raises(ValueError,match='precondition'):
        fence.transform(before+b'# changed\n',fence.sha(before),targets)
    with pytest.raises(ValueError,match='target_set_mismatch'):
        fence.transform(before,fence.sha(before),targets[:3]+['a'*64])
    with pytest.raises(ValueError,match='precondition'):
        fence.transform(before,fence.sha(before),targets[:3]+targets[:1])


def test_already_fenced_state_cannot_be_applied_again():
    before,targets,_=fixture()
    result=fence.transform(before,fence.sha(before),targets)
    with pytest.raises(ValueError,match='precondition'):
        fence.transform(result,fence.sha(before),targets)


def test_graph_admission_and_verified_fence_are_scoped_and_idempotent():
    url=os.environ.get('CONTROL_TEST_URL')
    if not url:
        pytest.skip('explicit disposable endpoint required')
    assert url=='http://127.0.0.1:27474'
    graph=fence.Graph(url,user='',password='')
    graph.promote()
    source=Path(__file__).parents[1]/'mycelium/graph/knowledge/seedforth-legacy-schedule-fence.cypher'
    for _ in range(2):
        for statement in source.read_text().split(';'):
            if statement.strip():graph.query(statement)
    decision=graph.query("MATCH (d:Decision {node_id:$id}) RETURN d.expected_before_hash AS hash",{'id':fence.DECISION})[0]
    params=dict(before_hash=decision['hash'],after_hash='d'*64,removed_count=4,
                backup='/opt/seedforth/shared/backups/legacy-schedule-fence-fixture/before.crontab')
    assert graph.operation('record-legacy-schedule-fence','untrusted','seedforth-platform',**params)==[]
    assert graph.operation('record-legacy-schedule-fence','principal-seedforth-owner','cajon-sensei',**params)==[]
    assert graph.operation('record-legacy-schedule-fence','principal-seedforth-owner','seedforth-platform',**{**params,'removed_count':3})==[]
    for _ in range(2):
        result=graph.operation('record-legacy-schedule-fence','principal-seedforth-owner','seedforth-platform',**params)
        assert result==[dict(id='observation-legacy-schedule-fence-20260906',schedules=4)]
    assert graph.operation('record-legacy-schedule-fence','principal-seedforth-owner','seedforth-platform',**{**params,'after_hash':'e'*64})==[]
