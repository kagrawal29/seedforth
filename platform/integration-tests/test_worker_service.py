import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
from tempfile import TemporaryDirectory

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.worker_service import RecoveringBroker, activated_listener, bindings
from control.worker_transport import WorkerServer, WorkerClient


@pytest.fixture
def socket_directory():
    with TemporaryDirectory(prefix='sfb-', dir='/tmp') as directory:
        yield Path(directory)


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux systemd socket activation contract')
def test_listener_survives_service_restart(socket_directory):
    path = str(socket_directory/'broker.sock')
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(path)
    listener.listen(16)
    class Boundary:
        def dispatch(self, header, body):
            return {'data': [{'scope': body['scope']}]}
    try:
        inode = Path(path).stat().st_ino
        for _ in range(2):
            with WorkerServer(path, Boundary(), listener=listener) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    assert WorkerClient(path, 'fixture', 'fixture').request('read-work') == [{'scope': 'fixture'}]
                finally:
                    server.shutdown()
                    thread.join(timeout=3)
            assert Path(path).stat().st_ino == inode
            assert listener.fileno() >= 0
    finally:
        listener.close()


def test_wrong_activation_owner_is_denied(monkeypatch):
    monkeypatch.setenv('LISTEN_PID', '-1')
    monkeypatch.setenv('LISTEN_FDS', '1')
    with pytest.raises(RuntimeError, match='exactly_one'):
        activated_listener('/unused')


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux systemd socket activation contract')
def test_child_consumes_activation_fd_without_leaking_to_adapters(socket_directory):
    path = str(socket_directory/'activated.sock')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(path)
        listener.listen(16)
        code = '''
import os,sys
sys.path.insert(0,sys.argv[1])
from control.worker_service import activated_listener
original=int(sys.argv[2])
os.dup2(original,3)
os.environ['LISTEN_PID']=str(os.getpid())
os.environ['LISTEN_FDS']='1'
with activated_listener(sys.argv[3]) as inherited:
    assert not inherited.get_inheritable()
    assert 'LISTEN_PID' not in os.environ and 'LISTEN_FDS' not in os.environ
    assert inherited.getsockname()==sys.argv[3]
print('activation-verified')
'''
        result = subprocess.run([sys.executable, '-c', code, str(Path(__file__).parents[1]),
            str(listener.fileno()), path], pass_fds=(listener.fileno(),),
            capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == 'activation-verified'


def test_recovery_precedes_dispatch_and_conflict_denies():
    class Broker:
        calls = []
        conflict = False
        def recover_receipts(self):
            self.calls.append('recover')
            if self.conflict:
                raise RuntimeError('conflict')
            return []
        def invoke(self, **params):
            self.calls.append('invoke')
            return 'result'
    raw = Broker()
    broker = RecoveringBroker(raw)
    assert broker.invoke() == 'result'
    assert raw.calls == ['recover', 'invoke']
    raw.conflict = True
    with pytest.raises(RuntimeError):
        broker.invoke()
    assert raw.calls == ['recover', 'invoke', 'recover']


def test_repository_bindings_cannot_load_code_or_extra_scope(tmp_path):
    path = tmp_path/'bindings.json'
    path.write_text(json.dumps({'repositories': {'flowing-indian': str(tmp_path)}}))
    assert bindings(path) == {'flowing-indian': str(tmp_path)}
    for value in [{'repositories': {}, 'adapter': 'arbitrary.module'},
                  {'repositories': {'another-project': str(tmp_path)}},
                  {'repositories': {'flowing-indian': '../relative'}}]:
        path.write_text(json.dumps(value))
        with pytest.raises(ValueError):
            bindings(path)
    path.write_text('{"repositories":{}}')
    path.chmod(0o666)
    with pytest.raises(ValueError, match='unsafe'):
        bindings(path)
