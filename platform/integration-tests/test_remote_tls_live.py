"""Read-only qualification of the deliberately closed public TLS ingress."""
import os
import socket
import ssl
import time
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get('CONTROL_REMOTE_TLS_TEST') != '1',
    reason='explicit public TLS qualification opt-in required',
)


def request(path, *, scheme='https', host=None):
    req = urllib.request.Request(f'{scheme}://185.192.96.100{path}')
    if host:
        req.add_header('Host', host)
    try:
        response = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, response.headers, response.read(4096)


def test_certificate_trusted_for_ip_and_not_near_expiry():
    context = ssl.create_default_context()
    with socket.create_connection(('185.192.96.100', 443), timeout=10) as raw:
        with context.wrap_socket(raw, server_hostname='185.192.96.100') as tls:
            cert = tls.getpeercert()
            assert ('IP Address', '185.192.96.100') in cert['subjectAltName']
            assert ssl.cert_time_to_seconds(cert['notAfter']) > time.time() + 48 * 3600
            assert tls.version() in ('TLSv1.2', 'TLSv1.3')


@pytest.mark.parametrize('path', ['/', '/mcp', '/api', '/.well-known/oauth-protected-resource', '/.env'])
def test_application_routes_remain_closed(path):
    status, headers, body = request(path)
    assert status == 503
    assert headers['Cache-Control'] == 'no-store'
    assert headers['X-Content-Type-Options'] == 'nosniff'
    assert "frame-ancestors 'none'" in headers['Content-Security-Policy']
    assert not headers.get('Access-Control-Allow-Origin')
    assert not headers.get('Set-Cookie')
    assert b'503 Service Temporarily Unavailable' in body


@pytest.mark.parametrize('path', ['/', '/mcp', '/.well-known/acme-challenge/absent-probe-token'])
def test_http_serves_no_application_or_directory(path):
    assert request(path, scheme='http')[0] == 404


@pytest.mark.parametrize('scheme', ['http', 'https'])
def test_foreign_host_rejected(scheme):
    assert request('/', scheme=scheme, host='untrusted.example')[0] == 421


@pytest.mark.parametrize('port', [6083, 7474, 7687])
def test_internal_service_ingress_still_refused(port):
    with pytest.raises(ConnectionRefusedError):
        socket.create_connection(('185.192.96.100', port), timeout=5)
