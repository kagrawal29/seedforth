"""External Neo4j transport and reviewed graph-operation promotion/execution.

Domain transitions live in authored Cypher and promoted ControlOperation atoms.
This module supplies transport, typed bounds, and immutable-release hash checks.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path
import urllib.request

OPERATIONS = Path(__file__).resolve().parents[1] / "mycelium/graph/control"


def operation_sources():
    # macOS archive metadata is not executable source.
    return sorted(p for p in OPERATIONS.glob('*.cypher') if not p.name.startswith('.'))


class GraphError(RuntimeError):
    pass


class Graph:
    def __init__(self, endpoint=None, user=None, password=None):
        supplied = {}
        credential_file = os.environ.get('CONTROL_GRAPH_CREDENTIALS')
        if credential_file:
            supplied = json.loads(Path(credential_file).read_text())
        self.endpoint = endpoint or supplied.get('endpoint') or os.environ.get("CONTROL_NEO4J_URL", "http://127.0.0.1:7474")
        self.user = user if user is not None else supplied.get('user', os.environ.get("NEO4J_USER", "neo4j"))
        self.password = password if password is not None else supplied.get('password', os.environ.get("NEO4J_PASSWORD", ""))

    def query(self, statement, params=None):
        headers = {"Content-Type": "application/json"}
        if self.password:
            headers["Authorization"] = "Basic " + base64.b64encode(
                f"{self.user}:{self.password}".encode()).decode()
        request = urllib.request.Request(self.endpoint.rstrip('/') + "/db/neo4j/tx/commit",
            data=json.dumps({"statements": [{"statement": statement, "parameters": params or {}}]}).encode(),
            headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                data = json.loads(response.read())
        except Exception as exc:
            raise GraphError(type(exc).__name__) from None
        if data.get("errors"):
            raise GraphError(data["errors"][0].get("code", "graph_error"))
        result = data["results"][0]
        return [dict(zip(result["columns"], row["row"])) for row in result["data"]]

    def promote(self):
        """Deployment-only I/O; never expose this through project clients."""
        for path in operation_sources():
            cypher = path.read_text()
            digest = hashlib.sha256(cypher.encode()).hexdigest()
            old=self.query("MATCH (a:ControlOperation {node_id:$id}) RETURN a.cypher AS cypher,a.source_hash AS hash,a.source AS source",
                           {'id':'control-'+path.stem})
            if old and old[0]['hash'] == hashlib.sha256(old[0]['cypher'].encode()).hexdigest():
                self.query("MATCH (a:ControlOperation {node_id:$id}) "
                           "MERGE (v:OperationRevision {node_id:$id+':'+$hash}) "
                           "ON CREATE SET v.cypher=$cypher,v.source_hash=$hash,v.source=$source,v.recorded_at=datetime() "
                           "MERGE (a)-[:HAS_REVISION]->(v)",{'id':'control-'+path.stem,**old[0]})
            self.query("MERGE (a:ControlOperation:CypherAtom {node_id:$id}) "
                       "SET a.cypher=$cypher,a.source_hash=$hash,a.project='system',"
                       "a.semantic=$semantic,a.source=$source,a.promoted_at=datetime(),a.current_revision=$id+':'+$hash "
                       "MERGE (v:OperationRevision {node_id:a.current_revision}) "
                       "ON CREATE SET v.cypher=$cypher,v.source_hash=$hash,v.source=$source,v.recorded_at=datetime() "
                       "MERGE (a)-[:HAS_REVISION]->(v)",
                       {"id": "control-" + path.stem, "cypher": cypher, "hash": digest,
                        "semantic": path.stem.replace('-', ' '),
                        "source": "platform/mycelium/graph/control/" + path.name})

    def operation(self, name, actor, scope, **params):
        # Reject path traversal and operation names outside this immutable release.
        names = {p.stem: p for p in operation_sources()}
        if name not in names:
            raise GraphError("unknown_operation")
        source_hash = hashlib.sha256(names[name].read_bytes()).hexdigest()
        rows = self.query("MATCH (a:ControlOperation {node_id:$id}) "
                          "RETURN a.cypher AS cypher,a.source_hash AS source_hash",
                          {"id": "control-" + name})
        if (len(rows) != 1 or rows[0]["source_hash"] != source_hash or
                hashlib.sha256(rows[0]["cypher"].encode()).hexdigest() != source_hash):
            raise GraphError("operation_generation_mismatch")
        for attempt in range(3):
            try:
                return self.query(rows[0]["cypher"], {**params, "actor": actor, "scope": scope})
            except GraphError as exc:
                # Neo4j explicitly rolls back a deadlocked transaction. Retry
                # only this known rollback; network timeouts may have committed.
                if str(exc) != "Neo.TransientError.Transaction.DeadlockDetected" or attempt == 2:
                    raise
                time.sleep(0.025 * (attempt + 1))
