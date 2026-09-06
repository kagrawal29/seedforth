"""Adversarial worker qualification, run only with disposable fixture credentials."""
import http.client
import json
import os
from pathlib import Path
import socket

job=json.loads(Path('/run/job.json').read_text())
token=Path('/run/worker-token').read_text().strip()


def call(operation,params=None,scope=None):
    client=http.client.HTTPConnection('localhost',timeout=30)
    client.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    client.sock.settimeout(30);client.sock.connect('/run/broker.sock')
    try:
        client.request('POST','/api/operation',body=json.dumps(dict(operation=operation,
            scope=scope or job['scope'],params=params or {})),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        response=client.getresponse()
        return response.status,json.loads(response.read())
    finally:
        client.close()


assert os.getuid()!=0
assert not Path('/opt/seedforth/shared/env/control-neo4j.json').exists()
assert not Path('/var/run/docker.sock').exists()
assert not any('NEO4J' in key or 'OPENROUTER' in key or 'ANTHROPIC' in key for key in os.environ)
network=socket.socket();network.settimeout(1)
try:
    network.connect(('172.17.0.1',7474))
except OSError:
    pass
else:
    raise AssertionError('worker unexpectedly reached host network')
finally:
    network.close()
try:
    Path('/run/job.json').write_text('tampered')
except OSError:
    pass
else:
    raise AssertionError('immutable input unexpectedly writable')

assert call('review-work')[0]==400
assert call('settle-invocation')[0]==400
assert call('promote')[0]==400
assert call('read-work',scope='another-project')[0]==403
assert call('read-work',{'actor':'principal-seedforth-owner'})[0]==400
status,result=call('claim-work',dict(id=job['work'],version=1,attempt=job['attempt']))
assert status==200
fence=result['data'][0]['fence']
status,result=call('invoke',dict(attempt=job['attempt'],fence=fence,invocation=job['invocation'],
    capability=job['capability'],arguments={'revision':job['revision']}))
assert status==200 and result['data'][0]['status']=='succeeded'
status,result=call('complete-invocation-work',dict(attempt=job['attempt'],fence=fence,invocation=job['invocation']))
assert status==200 and result['data'][0]['status']=='review'
print(json.dumps(dict(isolation_checks='passed',work_state='review',independent_review='still_required')))
