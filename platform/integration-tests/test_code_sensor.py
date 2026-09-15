from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import os
import subprocess
import sys
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control import sense_code


@pytest.fixture
def repo(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    (tmp_path/'app').mkdir()
    (tmp_path/'app/index.html').write_text('baseline')
    subprocess.run(['git', '-C', str(tmp_path), 'add', 'app/index.html'], check=True)
    subprocess.run(['git', '-C', str(tmp_path), '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
    return tmp_path


def test_exact_commit_and_working_hashes(repo):
    result = sense_code.probe(str(repo), 'app/index.html')
    assert result['committed_hash'] == result['working_hash'] == hashlib.sha256(b'baseline').hexdigest()
    (repo/'app/index.html').write_text('changed')
    result2 = sense_code.probe(str(repo), 'app/index.html')
    assert result2['revision'] == result['revision']
    assert result2['committed_hash'] == result['committed_hash']
    assert result2['working_hash'] == hashlib.sha256(b'changed').hexdigest()
    (repo/'app/index.html').unlink()
    assert sense_code.probe(str(repo), 'app/index.html')['working_hash'] is None


def test_probe_rejects_symlinks_and_oversized_files(repo):
    (repo/'app/index.html').unlink()
    (repo/'app/index.html').symlink_to('/etc/passwd')
    with pytest.raises(OSError):
        sense_code.probe(str(repo), 'app/index.html')
    (repo/'app/index.html').unlink()
    (repo/'app/index.html').write_bytes(b'x'*(sense_code.LIMIT+1))
    with pytest.raises(ValueError, match='unsupported_file'):
        sense_code.probe(str(repo), 'app/index.html')


def test_probe_rejects_directory_symlink_and_traversal(repo):
    (repo/'alias').symlink_to(repo/'app', target_is_directory=True)
    with pytest.raises(OSError):
        sense_code.working_hash(str(repo), 'alias/index.html')
    with pytest.raises(ValueError, match='invalid_path'):
        sense_code.probe(str(repo), '../secret')


def test_missing_parent_is_absent_not_collection_failure(repo):
    result = sense_code.probe(str(repo), 'app/missing/route.ts')
    assert result['committed_hash'] is None and result['working_hash'] is None
    assert len(result['revision']) == 40


def test_collector_preserves_failure_and_rejects_unapproved_binding(monkeypatch):
    def failed(*args):
        raise subprocess.TimeoutExpired('probe', 22)
    monkeypatch.setattr(sense_code, 'isolated_probe', failed)
    class Graph:
        path = 'app/index.html'
        def query(self, *args):
            return [dict(id='fixture', scope='cajon-sensei', path=self.path)]
        def operation(self, *args, **params):
            assert params['status'] == 'collection_failed'
            assert params['revision'] is None and params['working_hash'] is None
            return [dict(status='collection_failed')]
    g = Graph()
    assert sense_code.collect(g, 'fixture')[0]['status'] == 'collection_failed'
    g.path = '.env'
    with pytest.raises(ValueError, match='unapproved_source_binding'):
        sense_code.collect(g, 'fixture')


def test_probe_drops_identity_environment_and_descriptors(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(sense_code.pwd, 'getpwnam', lambda _: SimpleNamespace(pw_uid=1234, pw_gid=1235))
    def run(*args, **kwargs):
        assert kwargs['user'] == 1234 and kwargs['group'] == 1235 and kwargs['extra_groups'] == []
        assert kwargs['close_fds'] is True and kwargs['cwd'] == '/'
        assert set(kwargs['env']) == {'PATH', 'PYTHONPATH'}
        return SimpleNamespace(stdout=b'{"revision":"'+b'a'*40+b'","committed_hash":null,"working_hash":null}')
    monkeypatch.setattr(subprocess, 'run', run)
    assert sense_code.isolated_probe('cajon-sensei', 'app/index.html')['revision'] == 'a'*40


def test_project_probe_refuses_retained_capabilities(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(sense_code.pwd, 'getpwnam', lambda _: SimpleNamespace(pw_uid=1234))
    monkeypatch.setattr(os, 'getuid', lambda: 1234)
    monkeypatch.setattr(os, 'getgroups', lambda: [])
    monkeypatch.setattr(Path, 'read_text', lambda _: 'CapEff:\t0000000000000080\nCapAmb:\t0000000000000000\n')
    with pytest.raises(ValueError, match='privileged_probe_denied'):
        sense_code.check_probe_identity('fixture')
    monkeypatch.setattr(Path, 'read_text', lambda _: 'CapEff:\t0000000000000000\nCapAmb:\t0000000000000000\n')
    sense_code.check_probe_identity('fixture')
    monkeypatch.setattr(os, 'getgroups', lambda: [1234])
    with pytest.raises(ValueError, match='probe_identity_denied'):
        sense_code.check_probe_identity('fixture')


def test_graph_reducer_order_replay_freshness_and_scope():
    url = os.environ.get('CONTROL_TEST_URL')
    if not url:
        pytest.skip('explicit disposable endpoint required')
    assert url == 'http://127.0.0.1:27474'
    from control.graph import Graph
    g = Graph(url, user='', password='')
    g.promote()
    scope = 'fixture-code-'+uuid4().hex
    g.query("CREATE (:Principal {node_id:$s,enabled:true})-[:HAS_GRANT]->"
            "(:Grant {scope:$s,revoked:false,permissions:['read','source.observe']}) "
            "CREATE (:SourceStream {node_id:$s,scope_id:$s,path:'app/index.html',enabled:true,"
            "adapter:'local-git-file-hash-v1',freshness_seconds:900})", {'s':scope})
    now = datetime.now(timezone.utc)
    def observe(offset, event, **changes):
        payload = dict(source=scope, path='app/index.html', observed_at=(now+timedelta(seconds=offset)).isoformat(),
                       status='collected', revision='a'*40, committed_hash='b'*64, working_hash='c'*64,
                       adapter_revision='fixture', event_id=scope+event, payload_hash=event)
        payload.update(changes)
        return g.operation('record-code-observation', scope, scope, **payload)
    assert observe(0, 'new')[0]['status'] == 'diverged_from_commit'
    assert observe(-20, 'old', working_hash='b'*64)[0]['status'] == 'matches_commit'
    assert observe(0, 'new')[0]['id'] == scope+'new'
    assert observe(0, 'new', payload_hash='collision') == []
    rows = g.operation('read-sources', scope, scope)
    assert rows[0]['code_status'] == 'diverged_from_commit' and rows[0]['evidence_status'] == 'fresh'
    assert observe(1, 'failure', status='collection_failed', revision=None, committed_hash=None, working_hash=None)
    rows = g.operation('read-sources', scope, scope)
    assert rows[0]['evidence_status'] == 'degraded' and rows[0]['working_hash'] == 'c'*64
    assert observe(2, 'recovered', working_hash='b'*64)[0]['status'] == 'matches_commit'
    assert g.operation('read-sources', scope, scope)[0]['evidence_status'] == 'fresh'
    assert observe(3, 'absent', committed_hash=None, working_hash=None)[0]['status'] == 'missing'
    assert observe(4, 'added', committed_hash=None)[0]['status'] == 'not_in_commit'
    assert observe(5, 'deleted', working_hash=None)[0]['status'] == 'missing_working_file'
    assert observe(120, 'future') == []
    assert observe(6, 'invalid', revision='not-a-revision') == []
    assert observe(6, 'wrong-path', path='.env') == []
    assert g.operation('read-sources', scope, 'different-scope') == []
    g.query("MATCH (s:SourceStream {node_id:$s}) SET s.last_success_at=datetime()-duration('PT1H')", {'s':scope})
    rows = g.operation('read-sources', scope, scope)
    assert rows[0]['evidence_status'] == 'stale' and rows[0]['code_status'] == 'unknown'
    g.query("MATCH (:Principal {node_id:$s})-[:HAS_GRANT]->(g) SET g.revoked=true", {'s':scope})
    assert observe(7, 'revoked') == []
