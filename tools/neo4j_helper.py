"""Fast Neo4j helper using the HTTP transaction API.

cypher-shell spawns a fresh JVM per call (~5s). The HTTP API (port 7474)
answers in ~0.03s — 160x faster. All graph tools should use this.

Usage:
    from neo4j_helper import q, ql
    rows = q("MATCH (n) RETURN count(n)")
    for row in ql("MATCH (n) RETURN n.name"):
        print(row)
"""
import base64
import json
import os
import subprocess
import urllib.request
import urllib.error

NEO4J_HOST = "127.0.0.1"
NEO4J_HTTP_PORT = "7474"
NEO4J_USER = "neo4j"
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "9aac5c811e6d4f4f64a00c65666f3528")

_AUTH = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()


def _tx_endpoint():
    return f"http://{NEO4J_HOST}:{NEO4J_HTTP_PORT}/db/neo4j/tx/commit"


def _post(statements):
    body = json.dumps({"statements": statements}).encode()
    req = urllib.request.Request(
        _tx_endpoint(),
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {_AUTH}",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def q(cypher, params=None):
    """Run a Cypher query, return list of row dicts (or empty list on error)."""
    stmt = {"statement": cypher}
    if params:
        stmt["parameters"] = params
    try:
        data = _post([stmt])
    except urllib.error.HTTPError as e:
        body = e.read().decode() if hasattr(e, "read") else str(e)
        print(f"  [neo4j HTTP {e.code}] {body[:300]}")
        return []
    except Exception as e:
        print(f"  [neo4j error] {e}")
        return []

    if data.get("errors"):
        for err in data["errors"]:
            print(f"  [neo4j error] {err.get('message', err)[:300]}")
        return []

    rows = []
    for result in data.get("results", []):
        cols = result.get("columns", [])
        for row in result.get("data", []):
            rows.append(dict(zip(cols, row.get("row", []))))
    return rows


def ql(cypher, params=None):
    """Like q() but returns list of lists (raw rows) — useful for tabular output."""
    stmt = {"statement": cypher}
    if params:
        stmt["parameters"] = params
    try:
        data = _post([stmt])
    except Exception as e:
        print(f"  [neo4j error] {e}")
        return []

    if data.get("errors"):
        for err in data["errors"]:
            print(f"  [neo4j error] {err.get('message', err)[:300]}")
        return []

    rows = []
    for result in data.get("results", []):
        for row in result.get("data", []):
            rows.append(row.get("row", []))
    return rows


def q_strict(cypher, params=None):
    """Run Cypher and raise RuntimeError on error, else return raw rows.

    Unlike q()/ql(), which swallow errors and return [], this surfaces the
    error so callers can tell a failed query apart from an empty result.
    """
    stmt = {"statement": cypher}
    if params:
        stmt["parameters"] = params
    data = _post([stmt])
    if data.get("errors"):
        raise RuntimeError(data["errors"][0].get("message", "neo4j error"))
    rows = []
    for result in data.get("results", []):
        for row in result.get("data", []):
            rows.append(row.get("row", []))
    return rows


def scalar(cypher, params=None, default=None):
    """Run a query returning a single scalar value."""
    rows = ql(cypher, params)
    if rows and rows[0]:
        return rows[0][0]
    return default


def health():
    """Check Neo4j connectivity."""
    rows = ql("RETURN 1")
    return bool(rows and rows[0][0] == 1)
