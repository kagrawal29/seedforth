"""Protected broker process: external I/O wiring, never scheduling authority.

Systemd owns the listening socket across process restarts. Deployment supplies
repository bindings and separate broker/worker credentials. Graph policy still
authorizes every invocation. No runtime config can import an arbitrary adapter.
"""
import json
import os
from pathlib import Path
import socket
import threading

from control.broker import Broker
from control.git_inspection import GitInspection
from control.graph import Graph
from control.receipt_journal import ReceiptJournal
from control.worker_transport import WorkerBoundary, WorkerServer


class RecoveringBroker:
    """Serialize external dispatch with receipt recovery; never replay an effect."""
    def __init__(self, broker):
        self.broker = broker
        self.lock = threading.Lock()

    def recover(self):
        with self.lock:
            # Drain all batches before accepting another external action. A
            # persistent conflict fails closed instead of bypassing lost evidence.
            total = 0
            while True:
                recovered = self.broker.recover_receipts()
                total += len(recovered)
                if len(recovered) < 100:
                    return total

    def invoke(self, **params):
        with self.lock:
            while len(self.broker.recover_receipts()) == 100:
                pass
            return self.broker.invoke(**params)


def activated_listener(path):
    if os.environ.get('LISTEN_PID') != str(os.getpid()) or os.environ.get('LISTEN_FDS') != '1':
        raise RuntimeError('exactly_one_systemd_listener_required')
    listener = socket.socket(fileno=3)
    listener.set_inheritable(False)
    for key in ('LISTEN_PID', 'LISTEN_FDS', 'LISTEN_FDNAMES'):
        os.environ.pop(key, None)
    if (listener.family != socket.AF_UNIX or listener.type != socket.SOCK_STREAM
            or listener.getsockname() != str(path)
            or not listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN)):
        listener.close()
        raise RuntimeError('invalid_activated_listener')
    return listener


def bindings(path):
    source = Path(path)
    if source.stat().st_mode & 0o022 or source.stat().st_size > 32768:
        raise ValueError('unsafe_broker_bindings')
    value = json.loads(source.read_text())
    if not isinstance(value, dict) or set(value) != {'repositories'} or not isinstance(value['repositories'], dict):
        raise ValueError('invalid_broker_bindings')
    for scope, repository in value['repositories'].items():
        if (not isinstance(scope, str) or scope not in ['flowing-indian', 'cajon-sensei', 'seedforth-platform']
                or not isinstance(repository, str) or not Path(repository).is_absolute()
                or not Path(repository).is_dir()):
            raise ValueError('invalid_repository_binding')
    return value['repositories']


def main():
    path = '/run/seedforth-worker/broker.sock'
    state = Path(os.environ['STATE_DIRECTORY'])
    graph = Graph()
    adapter = GitInspection(bindings(os.environ['CONTROL_BROKER_BINDINGS']), state/'artifacts')
    broker = RecoveringBroker(Broker(graph, 'principal-capability-broker',
        {'capability-git-inspection-v1': adapter}, ReceiptJournal(state/'receipts')))
    listener = activated_listener(path)
    # No source promotion, grant creation, mandate admission or worker activation.
    # Recovery must succeed before this process consumes queued worker requests.
    broker.recover()
    boundary = WorkerBoundary(graph, os.environ['CONTROL_WORKER_CREDENTIALS'], broker)
    with listener, WorkerServer(path, boundary, listener=listener) as server:
        server.serve_forever()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # External credentials/graph errors must not enter service logs.
        print('worker_service_failed:' + type(exc).__name__, flush=True)
        raise SystemExit(1) from None
