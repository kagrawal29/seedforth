import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.broker import InvocationDenied
from control.code_proposal import CodeProposal
from test_code_snapshot import source


def proposal(source):
    snapshot, repo, revision = source
    return CodeProposal(snapshot.repositories, snapshot.allowed_paths, snapshot.artifact_root), repo, revision


def test_candidate_is_exact_and_does_not_change_repository(source):
    adapter, repo, revision = proposal(source)
    old = (repo/'app.js').read_text()
    args = adapter.validate('fixture', {'revision': revision,
        'changes': [{'path': 'app.js', 'old': 'approved revision', 'new': 'proposed correction'}]})
    result = adapter.run('proposal-fixture-001', args)
    report = json.loads(Path(result['artifact_ref']).read_bytes())
    assert report['files'][0]['content'] == 'console.log("proposed correction");'
    assert report['files'][0]['base_sha256'] != report['files'][0]['sha256']
    assert not report['applied'] and report['verification_status'] == 'not_run'
    assert report['base_revision'] == revision
    assert (repo/'app.js').read_text() == old


def test_nonmatching_edit_leaves_no_candidate(source):
    adapter, _, revision = proposal(source)
    with pytest.raises(ValueError, match='not_unique'):
        adapter.run('proposal-failure-001', {'scope': 'fixture', 'revision': revision,
            'changes': [{'path': 'app.js', 'old': 'missing content', 'new': 'new'}]})
    assert not adapter.artifact_root.exists()


@pytest.mark.parametrize('change', [
    {'path': '.env.local', 'old': 'a', 'new': 'b'},
    {'path': 'app.js', 'old': '', 'new': 'b'},
    {'path': 'app.js', 'old': 'a', 'new': 'a'},
    {'path': 'app.js', 'old': 'a', 'new': 'b', 'command': 'run me'},
])
def test_proposal_cannot_expand_access_or_hide_commands(source, change):
    adapter, _, revision = proposal(source)
    with pytest.raises(InvocationDenied):
        adapter.validate('fixture', {'revision': revision, 'changes': [change]})
