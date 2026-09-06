"""Bounded external Git/file observations. No source contents leave the probe.

The credential-bearing parent never opens project-controlled paths. Each probe
runs as the project account with a clean environment and no inherited descriptors.
Graph reducers own classification, freshness and current-state projection.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys
from uuid import uuid4

from control.graph import Graph

BINDINGS = {
    'cajon-sensei': ('proj-cajon-sensei', '/home/proj-cajon-sensei/cajon-sensei', ('app/index.html',)),
    'flowing-indian': ('proj-flowing-indian', '/home/proj-flowing-indian/flowing-indian',
                       ('app/api/order/route.ts', 'app/api/verify/route.ts')),
}
LIMIT = 1024 * 1024


def git(repo, *args):
    result = subprocess.run(
        ['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
         '-c', 'safe.directory='+repo, '-C', repo, *args],
        env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1',
             'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1',
             'GIT_LITERAL_PATHSPECS': '1', 'GIT_TERMINAL_PROMPT': '0'},
        capture_output=True, check=True, timeout=3)
    if len(result.stdout) > LIMIT:
        raise ValueError('oversized_git_output')
    return result.stdout


def working_hash(repo, path):
    # Refuse directory and file symlinks, devices, oversized files, unstable reads.
    parts = Path(repo, path).parts
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        try:
            file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        except FileNotFoundError:
            return None
        try:
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > LIMIT:
                raise ValueError('unsupported_file')
            with os.fdopen(os.dup(file_fd), 'rb') as stream:
                content = stream.read(LIMIT+1)
            after = os.fstat(file_fd)
            named = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if len(content) > LIMIT or identity(before) != identity(after) or identity(after) != identity(named):
                raise ValueError('source_changed_during_read')
            return hashlib.sha256(content).hexdigest()
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def probe(repo, path):
    if not Path(repo).is_absolute() or Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError('invalid_path')
    revision = git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    if not re.fullmatch('[a-f0-9]{40}', revision):
        raise ValueError('invalid_revision')
    tree = git(repo, 'ls-tree', '-z', revision, '--', path)
    committed = None
    if tree:
        match = re.fullmatch(rb'(100644|100755) blob ([a-f0-9]{40})\t'+re.escape(path.encode())+b'\x00', tree)
        if not match:
            raise ValueError('unsupported_git_entry')
        blob = match[2].decode()
        size = int(git(repo, 'cat-file', '-s', blob))
        if not 0 <= size <= LIMIT:
            raise ValueError('oversized_blob')
        content = git(repo, 'cat-file', 'blob', blob)
        if len(content) != size:
            raise ValueError('blob_size_mismatch')
        committed = hashlib.sha256(content).hexdigest()
    working = working_hash(repo, path)
    if git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip() != revision:
        raise ValueError('revision_changed_during_read')
    return dict(revision=revision, committed_hash=committed, working_hash=working)


def isolated_probe(scope, path):
    account, repo, paths = BINDINGS[scope]
    if path not in paths:
        raise ValueError('unapproved_path')
    user = pwd.getpwnam(account)
    if user.pw_uid == 0:
        raise ValueError('root_probe_forbidden')
    result = subprocess.run(
        ['/usr/bin/python3', '-m', 'control.sense_code', '--probe', scope, path],
        cwd='/', user=user.pw_uid, group=user.pw_gid, extra_groups=[],
        env={'PATH': '/usr/bin:/bin', 'PYTHONPATH': str(Path(__file__).resolve().parents[1])},
        close_fds=True, capture_output=True, check=True, timeout=22)
    if len(result.stdout) > 512:
        raise ValueError('oversized_probe_result')
    data = json.loads(result.stdout)
    if not isinstance(data, dict) or set(data) != {'revision', 'committed_hash', 'working_hash'}:
        raise ValueError('invalid_probe_result')
    if not isinstance(data['revision'], str) or not re.fullmatch('[a-f0-9]{40}', data['revision']):
        raise ValueError('invalid_probe_revision')
    for key in ('committed_hash', 'working_hash'):
        if data[key] is not None and (not isinstance(data[key], str) or not re.fullmatch('[a-f0-9]{64}', data[key])):
            raise ValueError('invalid_probe_hash')
    return data


def collect(graph, adapter_revision):
    sources = graph.query("MATCH (s:SourceStream {adapter:'local-git-file-hash-v1',enabled:true}) "
                          "RETURN s.node_id AS id,s.scope_id AS scope,s.path AS path")
    outcomes = []
    for source in sources:
        scope, path = source['scope'], source['path']
        if scope not in BINDINGS or path not in BINDINGS[scope][2]:
            raise ValueError('unapproved_source_binding')
        observed_at = datetime.now(timezone.utc).isoformat()
        data = dict(revision=None, committed_hash=None, working_hash=None)
        status = 'collected'
        try:
            data = isolated_probe(scope, path)
        except (OSError, ValueError, subprocess.SubprocessError):
            status = 'collection_failed'
        payload = dict(source=source['id'], path=path, observed_at=observed_at,
                       status=status, adapter_revision=adapter_revision, **data)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        rows = graph.operation('record-code-observation', 'principal-code-sensor', scope,
                               **payload, event_id='obs-'+str(uuid4()), payload_hash=digest)
        if len(rows) != 1:
            raise RuntimeError('observation_not_persisted')
        outcomes.append(dict(scope=scope, path=path, status=rows[0]['status']))
    if not sources:
        raise RuntimeError('no_registered_sources')
    return outcomes


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--probe':
        scope, path = sys.argv[2:]
        account, repo, paths = BINDINGS[scope]
        if os.getuid() == 0 or os.getuid() != pwd.getpwnam(account).pw_uid or path not in paths:
            raise SystemExit('probe_identity_or_path_denied')
        try:
            print(json.dumps(probe(repo, path)))
        except (OSError, ValueError, subprocess.SubprocessError):
            raise SystemExit('probe_collection_failed') from None
    else:
        print(json.dumps(collect(Graph(), os.environ['SEEDFORTH_RELEASE_SHA'])))
