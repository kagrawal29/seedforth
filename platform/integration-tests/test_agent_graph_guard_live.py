"""Real socket-owner containment in a disposable namespace, never host rules."""
import os
from pathlib import Path
import socket
import subprocess
import time
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(os.environ.get('CONTROL_NETWORK_GUARD_TEST') != '1',
                               reason='explicit namespace qualification required')


def test_all_legacy_uids_denied_both_families_after_dnat_transport_retained():
    assert os.geteuid() == 0 and socket.gethostname() == 'vmi3556896'
    name = 'sfag' + uuid4().hex[:8]
    process = None
    def run(*args):
        return subprocess.run(args, check=True, capture_output=True, text=True, timeout=10)

    def ns(*args):
        return run('ip', 'netns', 'exec', name, *args)

    def probe(uid, host, port):
        code = (
            'import os,socket,sys;'
            'os.setgroups([]);'
            'os.setgid(int(sys.argv[1]));'
            'os.setuid(int(sys.argv[1]));'
            'socket.create_connection((sys.argv[2],int(sys.argv[3])),timeout=1).close()'
        )
        return subprocess.run(['ip', 'netns', 'exec', name, '/usr/bin/python3', '-c',
                               code, str(uid), host, str(port)], capture_output=True,
                              timeout=3).returncode == 0

    run('ip', 'netns', 'add', name)
    try:
        ns('ip', 'link', 'set', 'lo', 'up')
        listener = '''import socket,threading,time
def serve(family,host,port):
 s=socket.socket(family);s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
 if family==socket.AF_INET6:s.setsockopt(socket.IPPROTO_IPV6,socket.IPV6_V6ONLY,1)
 s.bind((host,port));s.listen()
 while True:
 c,_=s.accept();c.sendall(b'ok');c.close()
for port in [17474,7687,7724]:
 for family,host in [(socket.AF_INET,'127.0.0.1'),(socket.AF_INET6,'::1')]:
  threading.Thread(target=serve,args=(family,host,port),daemon=True).start()
time.sleep(60)
'''
        process = subprocess.Popen(['ip', 'netns', 'exec', name, '/usr/bin/python3',
                                    '-c', listener], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        for binary, destination in [('iptables', '127.0.0.1:17474'),
                                    ('ip6tables', '[::1]:17474')]:
            ns(binary, '-t', 'nat', '-A', 'OUTPUT', '-p', 'tcp', '--dport', '7474',
               '-j', 'DNAT', '--to-destination', destination)
            ns(binary, '-t', 'nat', '-A', 'OUTPUT', '-p', 'tcp', '--dport', '7687',
               '-j', 'DNAT', '--to-destination', destination)
        deadline = time.monotonic() + 5
        while not all(probe(0, host, 7474) for host in ['127.0.0.1', '::1']):
            assert process.poll() is None and time.monotonic() < deadline
            time.sleep(.05)
        for uid in range(1003, 1011):
            for host in ['127.0.0.1', '::1']:
                assert all(probe(uid, host, p) for p in [7474, 7687, 7724])
        path = str(Path(__file__).parents[2] / 'operations/agent-graph-guard.py')
        code = ("import importlib.util;s=importlib.util.spec_from_file_location('g'," +
                repr(path) + ");g=importlib.util.module_from_spec(s);s.loader.exec_module(g);"
                "g.enforce(dict(id='network-policy-legacy-agent-graph-v1',version=1,"
                "uids=list(range(1003,1011)),ports=[7474,7687]))")
        ns('/usr/bin/python3', '-c', code)
        ns('/usr/bin/python3', '-c', code)
        for host in ['127.0.0.1', '::1']:
            for uid in range(1003, 1011):
                assert not probe(uid, host, 7474)
                assert not probe(uid, host, 7687)
                assert probe(uid, host, 7724)
            # Privileged collector and Delta transport can still use the graph.
            for uid in [0, 1001]:
                assert all(probe(uid, host, p) for p in [7474, 7687, 7724])
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        run('ip', 'netns', 'delete', name)
