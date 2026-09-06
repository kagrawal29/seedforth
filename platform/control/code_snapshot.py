"""Bounded immutable source input for code workers and source sensing.

Reads regular Git blobs only, not the working tree, symlinks, submodules or full
history. Deployment fixes the scope/path allowlist. Never runs repository code.
Snapshot content remains untrusted data and conveys no execution authority.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import time

from control.broker import InvocationDenied, digest


class CodeSnapshot:
    cost_units = 1
    max_seconds = 30
    max_file_bytes = 262144
    max_total_bytes = 524288

    def __init__(self, repositories, allowed_paths, artifact_root):
        self.repositories = {scope: Path(path).resolve() for scope, path in repositories.items()}
        self.allowed_paths = {scope: frozenset(paths) for scope, paths in allowed_paths.items()}
        self.artifact_root = Path(artifact_root).resolve()
        if set(self.repositories) != set(self.allowed_paths):
            raise ValueError('snapshot_scope_bindings_mismatch')
        for paths in self.allowed_paths.values():
            for path in paths:
                self.check_path(path)
        self.generation = digest({'source': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'repositories': {s: str(p) for s, p in self.repositories.items()},
            'allowed_paths': {s: sorted(p) for s, p in self.allowed_paths.items()},
            'artifact_root': str(self.artifact_root)})

    @staticmethod
    def check_path(path):
        if (not isinstance(path, str) or not path or len(path) > 256 or '\\' in path
                or any(ord(c) < 32 for c in path) or path.startswith('/')
                or str(PurePosixPath(path)) != path
                or any(p in {'.', '..'} or p.startswith('.') for p in path.split('/'))
                or any(part in path.lower() for part in ['credential', 'secret', 'private-key'])
                or PurePosixPath(path).suffix.lower() not in {'.py', '.js', '.mjs', '.ts', '.tsx', '.jsx', '.html', '.css', '.json'}):
            raise InvocationDenied('source_path_not_permitted')

    def validate(self, scope, arguments):
        if scope not in self.repositories or type(arguments) is not dict or set(arguments) != {'revision', 'paths'}:
            raise InvocationDenied('invalid_snapshot_scope_or_fields')
        revision, paths = arguments['revision'], arguments['paths']
        if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
            raise InvocationDenied('immutable_revision_required')
        if type(paths) is not list or not 1 <= len(paths) <= 8 or any(type(p) is not str for p in paths):
            raise InvocationDenied('invalid_source_paths')
        for path in paths:
            self.check_path(path)
            if path not in self.allowed_paths[scope]:
                raise InvocationDenied('source_outside_promoted_coverage')
        if len(set(paths)) != len(paths):
            raise InvocationDenied('duplicate_source_paths')
        return {'scope': scope, 'revision': revision, 'paths': sorted(paths)}

    def run(self, invocation, arguments):
        return self.persist_report(invocation, self.read_snapshot(arguments))

    def read_snapshot(self, arguments):
        args = CodeSnapshot.validate(self, arguments['scope'], {k: arguments[k] for k in ['revision', 'paths']})
        environment = {'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_REPLACE_OBJECTS': '1',
            'GIT_LITERAL_PATHSPECS': '1'}
        command = ['git', '-c', 'core.hooksPath=/dev/null', '-C', str(self.repositories[args['scope']])]
        deadline = time.monotonic() + 25
        def git(*parts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('snapshot_deadline_exceeded')
            return subprocess.run(command + list(parts), env=environment, check=True,
                capture_output=True, timeout=min(2, remaining)).stdout
        # An exact commit object is required, not a tag object that happens to peel.
        if git('cat-file', '-t', args['revision']).strip() != b'commit':
            raise ValueError('snapshot_revision_is_not_commit')
        entries = git('ls-tree', '-z', args['revision'], '--', *args['paths']).split(b'\0')
        blobs = {}
        for entry in filter(None, entries):
            metadata, raw_path = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode('ascii').split(' ')
            path = raw_path.decode('utf-8')
            if mode not in {'100644', '100755'} or kind != 'blob' or path not in args['paths']:
                raise ValueError('snapshot_requires_regular_source_blobs')
            blobs[path] = oid
        if set(blobs) != set(args['paths']):
            raise ValueError('snapshot_source_missing')
        files, total = [], 0
        for path, oid in sorted(blobs.items()):
            size = int(git('cat-file', '-s', oid))
            total += size
            if size > self.max_file_bytes or total > self.max_total_bytes:
                raise ValueError('snapshot_source_too_large')
            raw = git('cat-file', 'blob', oid)
            if len(raw) != size or b'\0' in raw:
                raise ValueError('invalid_source_blob')
            content = raw.decode('utf-8')
            # Defense-in-depth tripwires, not a claim of exhaustive secret detection.
            if re.search(r'-----BEGIN .*PRIVATE KEY-----|(?:sk_live_|rzp_live_|ghp_|github_pat_|sk-ant-)[A-Za-z0-9_-]{12,}', content):
                raise ValueError('possible_secret_in_snapshot')
            files.append({'path': path, 'git_blob': oid,
                'sha256': hashlib.sha256(raw).hexdigest(), 'content': content})
        return {'kind': 'scoped_code_snapshot', **args, 'files': files,
            'adapter_generation': self.generation, 'trust': 'untrusted_source_data',
            'coverage': 'explicit_paths_only', 'bytes': total}

    def persist_report(self, invocation, report):
        if not re.fullmatch('[a-zA-Z0-9_-]{8,128}', invocation):
            raise ValueError('invalid_snapshot_identity')
        raw = json.dumps(report, sort_keys=True).encode()
        if len(raw) > 1_200_000:
            raise ValueError('serialized_source_report_too_large')
        self.artifact_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self.artifact_root / (invocation + '.json')
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        return {'outcome': 'succeeded', 'artifact_ref': str(target),
            'artifact_hash': hashlib.sha256(raw).hexdigest()}
