"""Test-only HTTP proxy for a Host-bound loopback service.

It forwards localhost traffic to an SSH tunnel, rewriting only Host and Origin.
It has no persistence, authentication, or public bind and must not be deployed.
"""
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sys

UPSTREAM_HOST = '127.0.0.1:18789'
PUBLIC_HOST = '185.192.96.100'


class Proxy(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def do_GET(self): self.forward()
    def do_POST(self): self.forward()

    def log_message(self, *_): pass

    def forward(self):
        length = int(self.headers.get('Content-Length', '0') or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in {'host', 'origin', 'connection', 'content-length'}}
        headers['Host'] = PUBLIC_HOST
        if 'Origin' in self.headers:
            headers['Origin'] = 'https://' + PUBLIC_HOST
        connection = HTTPConnection('127.0.0.1', 18789, timeout=15)
        connection.request(self.command, self.path, body=body, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        self.send_response(response.status)
        for key, value in response.getheaders():
            if key.lower() in {'connection', 'transfer-encoding', 'server', 'date', 'content-length'}:
                continue
            if key.lower() == 'location' and value.startswith('https://' + PUBLIC_HOST):
                value = 'http://127.0.0.1:18792' + value[len('https://' + PUBLIC_HOST):]
            self.send_header(key, value)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(payload)
        connection.close()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18792
    server = ThreadingHTTPServer(('127.0.0.1', port), Proxy)
    print(f'Host rewrite proxy ready on localhost:{port}', flush=True)
    server.serve_forever()
