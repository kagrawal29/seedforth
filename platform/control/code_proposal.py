"""Produce bounded candidate code artifacts. Never apply, run, commit or deploy.

Edits are untrusted worker suggestions. Each old string must uniquely match the
specified immutable source. Tests and review are separate graph-governed actions.
"""
import hashlib
import json
from pathlib import Path

from control.broker import InvocationDenied, digest
from control.code_snapshot import CodeSnapshot


class CodeProposal(CodeSnapshot):
    def __init__(self, repositories, allowed_paths, artifact_root):
        super().__init__(repositories, allowed_paths, artifact_root)
        self.generation = digest({'snapshot_generation': self.generation,
            'proposal_source': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})

    def validate(self, scope, arguments):
        if type(arguments) is not dict or set(arguments) != {'revision', 'changes'}:
            raise InvocationDenied('invalid_proposal_fields')
        changes = arguments['changes']
        if type(changes) is not list or not 1 <= len(changes) <= 8:
            raise InvocationDenied('invalid_proposal_changes')
        for change in changes:
            if (type(change) is not dict or set(change) != {'path', 'old', 'new'}
                    or any(type(change[k]) is not str for k in change)
                    or not change['old'] or change['old'] == change['new']
                    or len(change['old']) > 8192 or len(change['new']) > 8192
                    or '\0' in change['new']):
                raise InvocationDenied('invalid_proposal_change')
        if len(json.dumps(arguments).encode()) > 28000:
            raise InvocationDenied('proposal_request_too_large')
        snapshot = super().validate(scope, {'revision': arguments['revision'],
            'paths': sorted({change['path'] for change in changes})})
        return {**snapshot, 'changes': changes}

    def run(self, invocation, arguments):
        args = self.validate(arguments['scope'], {k: arguments[k] for k in ['revision', 'changes']})
        snapshot = self.read_snapshot(args)
        files = {item['path']: dict(item) for item in snapshot['files']}
        for change in args['changes']:
            item = files[change['path']]
            if item['content'].count(change['old']) != 1:
                raise ValueError('proposal_base_match_not_unique')
            item['content'] = item['content'].replace(change['old'], change['new'], 1)
        total = 0
        for item in files.values():
            raw = item['content'].encode()
            total += len(raw)
            if len(raw) > self.max_file_bytes or total > self.max_total_bytes:
                raise ValueError('proposal_result_too_large')
            item['base_sha256'] = item['sha256']
            item['sha256'] = hashlib.sha256(raw).hexdigest()
        report = {'kind': 'code_change_proposal', 'scope': args['scope'],
            'base_revision': args['revision'], 'files': list(files.values()),
            'changes_hash': digest(args['changes']), 'adapter_generation': self.generation,
            'trust': 'untrusted_candidate_code', 'verification_status': 'not_run',
            'applied': False, 'bytes': total}
        return self.persist_report(invocation, report)
