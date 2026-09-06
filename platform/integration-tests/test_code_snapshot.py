import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.broker import InvocationDenied
from control.code_snapshot import CodeSnapshot


@pytest.fixture
def source(tmp_path):
    repo = tmp_path/'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    (repo/'app.js').write_text('console.log("approved revision");')
    (repo/'large.js').write_text('x' * 65537)
    (repo/'link.js').symlink_to('app.js')
    (repo/'bad.js').write_text('const token="ghp_' + 'x'*24 + '";')
    subprocess.run(['git', '-C', str(repo), 'add', 'app.js', 'large.js', 'link.js', 'bad.js'], check=True)
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture'], check=True)
    revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    adapter = CodeSnapshot({'fixture': repo}, {'fixture': ['app.js', 'large.js', 'link.js', 'bad.js']}, tmp_path/'artifacts')
    return adapter, repo, revision


def test_exact_committed_source_not_worktree_or_history(source):
    adapter, repo, revision = source
    (repo/'app.js').write_text('dirty source must never be included')
    (repo/'.env.local').write_text('FIXTURE_SECRET=not-a-real-secret')
    args = adapter.validate('fixture', {'revision': revision, 'paths': ['app.js']})
    result = adapter.run('snapshot-fixture-001', args)
    raw = Path(result['artifact_ref']).read_bytes()
    report = json.loads(raw)
    assert hashlib.sha256(raw).hexdigest() == result['artifact_hash']
    assert report['files'][0]['content'] == 'console.log("approved revision");'
    assert report['trust'] == 'untrusted_source_data'
    assert len(report['files']) == 1 and 'FIXTURE_SECRET' not in raw.decode()


@pytest.mark.parametrize('path', ['../app.js', '/app.js', '.env.local', '.git/config', 'other.js', 'app.js\n', 'dir//app.js'])
def test_path_escape_and_unpromoted_coverage_denied(source, path):
    adapter, _, revision = source
    with pytest.raises(InvocationDenied):
        adapter.validate('fixture', {'revision': revision, 'paths': [path]})


@pytest.mark.parametrize('path', ['large.js', 'link.js', 'bad.js'])
def test_size_symlink_and_secret_fail_without_artifact(source, path):
    adapter, _, revision = source
    with pytest.raises(ValueError):
        adapter.run('snapshot-denied-001', adapter.validate('fixture', {'revision': revision, 'paths': [path]}))
    assert not adapter.artifact_root.exists()


def test_scope_and_mutable_revision_denied(source):
    adapter, _, revision = source
    with pytest.raises(InvocationDenied):
        adapter.validate('other', {'revision': revision, 'paths': ['app.js']})
    with pytest.raises(InvocationDenied):
        adapter.validate('fixture', {'revision': 'HEAD', 'paths': ['app.js']})
