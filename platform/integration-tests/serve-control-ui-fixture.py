"""Real HTTP gateway against the dedicated disposable graph only.

Forward delta2's synthetic Neo4j port to localhost:27474 first. This adapter
creates an expiring synthetic browser identity file, not production access.
Run the integration suite first to seed the three scopes and upgrade plan.
"""
from datetime import datetime, timedelta, timezone
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parents[1]))
from control.graph import Graph
from control.server import Boundary, Handler


if __name__ == '__main__':
    graph = Graph('http://127.0.0.1:27474', user='', password='')
    assert graph.query("MATCH (w:WorkItem {node_id:'wi-upgrade-W00'}) RETURN count(w) AS n") == [{'n': 1}]
    # Re-promote only to the dedicated test graph so source hash enforcement
    # covers the exact local checkout used by this browser qualification.
    graph.promote()
    graph.query("MERGE (p:Principal {node_id:'principal-ui-fixture-sensor'}) SET p.enabled=true "
                "MERGE (g:Grant {node_id:'grant-ui-fixture-sensor'}) "
                "SET g.scope='seedforth-platform',g.revoked=false,g.permissions=['source.observe'] "
                "MERGE (p)-[:HAS_GRANT]->(g) "
                "MERGE (s:SourceStream {node_id:'source-ui-fixture-code'}) "
                "SET s.scope_id='seedforth-platform',s.path='fixture/app.html',s.enabled=true,"
                "s.adapter='local-git-file-hash-v1',s.freshness_seconds=900")
    event = uuid4().hex
    assert graph.operation('record-code-observation', 'principal-ui-fixture-sensor', 'seedforth-platform',
        source='source-ui-fixture-code', path='fixture/app.html', observed_at=datetime.now(timezone.utc).isoformat(),
        status='collected', revision='a'*40, committed_hash='b'*64, working_hash='c'*64,
        adapter_revision='synthetic-browser-fixture', event_id=event, payload_hash=event)
    with TemporaryDirectory(prefix='seedforth-ui-fixture-') as directory:
        credentials = Path(directory) / 'access.json'
        credentials.touch(mode=0o600)
        credentials.write_text(json.dumps([{
            'principal': 'principal-seedforth-owner',
            'scopes': ['seedforth-platform'],
            'sha256': hashlib.sha256(b'synthetic-browser-credential-not-a-secret').hexdigest(),
            'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }]))
        server = ThreadingHTTPServer(('127.0.0.1', 18788), Handler)
        server.allowed_origins = {'http://127.0.0.1:18788'}
        server.boundary = Boundary(graph, credentials)
        print('Disposable graph UI gateway ready on 127.0.0.1:18788', flush=True)
        try:
            server.serve_forever()
        finally:
            server.server_close()
