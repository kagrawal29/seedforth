"""Minimal isolated executor. Graph supplies work, broker enforces every action.

Job file supplies identities only, never commands or grants. One bounded
capability invocation produces a review candidate, never an accepted outcome.
"""
import http.client
import json
from pathlib import Path
import socket


def request(job, token, operation, **params):
    connection = http.client.HTTPConnection('localhost', timeout=40)
    connection.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.sock.settimeout(40)
    connection.sock.connect('/run/broker.sock')
    try:
        connection.request('POST', '/api/operation',
            body=json.dumps({'operation':operation,'scope':job['scope'],'params':params}),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
        response = connection.getresponse()
        raw = response.read(1_500_001)
        if response.status != 200 or len(raw) > 1_500_000:
            raise RuntimeError('worker_request_failed_reconcile_before_retry')
        return json.loads(raw)['data']
    finally:
        connection.close()


def execute(job, call):
    if type(job) is not dict or set(job) != {'scope','work','attempt','invocation'}:
        raise ValueError('invalid_identity_job')
    if any(type(value) is not str or not 1 <= len(value) <= 128 for value in job.values()):
        raise ValueError('invalid_job_identity')
    prior = call('read-attempt', attempt=job['attempt'])
    if prior:
        # No attempt restart, redispatch or claim under ambiguity.
        raise RuntimeError('existing_attempt_requires_reconciliation')
    work = [w for w in call('read-work') if w['id'] == job['work']]
    if len(work) != 1 or work[0]['status'] != 'ready' or work[0]['hold']:
        raise RuntimeError('work_not_ready')
    claimed = call('claim-work', id=job['work'], version=work[0]['version'], attempt=job['attempt'])
    if len(claimed) != 1:
        raise RuntimeError('claim_not_confirmed')
    fence = claimed[0]['fence']
    spec = call('read-execution-spec', attempt=job['attempt'])
    if len(spec) != 1 or type(spec[0]['arguments_json']) is not str:
        raise RuntimeError('execution_spec_missing')
    result = call('invoke', attempt=job['attempt'], fence=fence, invocation=job['invocation'],
        capability=spec[0]['capability'], arguments=json.loads(spec[0]['arguments_json']))
    if len(result) != 1 or result[0]['status'] != 'succeeded':
        raise RuntimeError('invocation_not_confirmed')
    receipt = call('complete-invocation-work', attempt=job['attempt'], fence=fence, invocation=job['invocation'])
    if len(receipt) != 1 or receipt[0]['status'] != 'review':
        raise RuntimeError('review_receipt_not_confirmed')
    return {'attempt':job['attempt'],'invocation':job['invocation'],'status':'review',
        'receipt':receipt[0]['receipt'],'accepted':False}


if __name__ == '__main__':
    try:
        job = json.loads(Path('/run/job.json').read_text())
        token = Path('/run/worker-token').read_text().strip()
        print(json.dumps(execute(job, lambda op, **params: request(job, token, op, **params))))
    except Exception as exc:
        print('isolated_worker_failed:' + type(exc).__name__, flush=True)
        raise SystemExit(1) from None
