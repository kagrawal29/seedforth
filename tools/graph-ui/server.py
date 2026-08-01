#!/usr/bin/env python3
"""Mycelium graph web UI server.

Serves a single-page frontend (index.html) plus JSON APIs backed by the
mycelium Neo4j knowledge graph:

  GET  /api/health    graph stats (nodes, edges, density, label breakdown)
  GET  /api/topology  all nodes + edges for force-directed rendering
  POST /api/cypher    run raw Cypher, returns columns + rows
  POST /api/nl        natural language -> DeepSeek Cypher -> result -> DeepSeek answer

Transport: Neo4j HTTP transaction API (stdlib urllib, no DB driver) which is
~0.4s faster than cypher-shell, with a `docker exec mycelium-neo4j cypher-shell`
fallback if the HTTP API is unreachable. The DeepSeek API key is read from
/opt/delta/delta.env (DEEPSEEK_API_KEY).

Usage: python3 server.py [--port 8890] [--host 0.0.0.0]
"""
import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NEO4J_USER = "neo4j"
NEO4J_PASS = os.environ.get("NEO4J_PASS", "9aac5c811e6d4f4f64a00c65666f3528")
NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474/db/neo4j/tx/commit")
ENV_PATH = os.environ.get("DELTA_ENV_PATH", "/opt/delta/delta.env")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOST = os.environ.get("GRAPH_UI_HOST", "0.0.0.0")
PORT = int(os.environ.get("GRAPH_UI_PORT", "8890"))
SCHEMA_TTL = 600
TOPOLOGY_TTL = 15

_lock = threading.Lock()
_schema = {"ts": 0, "data": None}
_topology = {"ts": 0, "data": None}


# ---------------------------------------------------------------- neo4j http

def _auth_header():
    token = base64.b64encode(("%s:%s" % (NEO4J_USER, NEO4J_PASS)).encode()).decode()
    return "Basic " + token


def _tx(statements):
    """POST a statements array to the Neo4j HTTP tx endpoint.

    Returns a list of per-statement {"columns": [...], "rows": [...]} dicts or
    raises RuntimeError on transport/HTTP failure.
    """
    body = json.dumps({"statements": statements}).encode()
    req = urllib.request.Request(NEO4J_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": _auth_header(),
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise RuntimeError("Neo4j HTTP %s: %s" % (e.code, detail))
    except Exception as e:
        raise RuntimeError("Neo4j HTTP request failed: %s" % str(e)[:400])

    if resp.get("errors"):
        msg = resp["errors"][0].get("message", "unknown error")
        raise RuntimeError("Neo4j error: %s" % msg[:400])
    results = []
    for res in resp.get("results", []):
        results.append({
            "columns": res.get("columns", []),
            "rows": [d.get("row", []) for d in res.get("data", [])],
        })
    return results


def http_cypher(cypher, params=None):
    """Run a single Cypher statement. Returns {"columns", "rows", "error"}."""
    statements = [{
        "statement": cypher,
        "parameters": params or {},
        "resultDataContents": ["row"],
    }]
    try:
        res = _tx(statements)[0]
    except RuntimeError as e:
        return {"columns": [], "rows": [], "error": str(e)}
    return {"columns": res["columns"], "rows": res["rows"], "error": None}


def _split_row(line):
    parts = re.split(r", (?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", line)
    return [p.strip() for p in parts]


def _norm(v):
    v = v.strip()
    if v == "TRUE":
        return True
    if v == "FALSE":
        return False
    if v in ("NULL", "null"):
        return None
    if v.startswith('"') and v.endswith('"') and len(v) >= 2:
        v = v[1:-1]
    try:
        return int(v)
    except ValueError:
        return v


def _parse_plain(output):
    if not output or not output.strip():
        return {"columns": [], "rows": []}
    lines = output.strip().splitlines()
    columns = _split_row(lines[0])
    rows = [[_norm(v) for v in _split_row(l)] for l in lines[1:]]
    return {"columns": columns, "rows": rows}


def docker_cypher(cypher):
    """Fallback transport via cypher-shell inside the mycelium-neo4j container."""
    r = subprocess.run(
        ["docker", "exec", "mycelium-neo4j", "cypher-shell",
         "-u", NEO4J_USER, "-p", NEO4J_PASS, "--format", "plain", cypher],
        capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return {"columns": [], "rows": [], "error": r.stderr.strip()[:400]}
    res = _parse_plain(r.stdout)
    return {"columns": res["columns"], "rows": res["rows"], "error": None}


def run_cypher(cypher, params=None):
    res = http_cypher(cypher, params)
    if res["error"]:
        fb = docker_cypher(cypher)
        if not fb["error"]:
            return fb
        return res
    return res


# ---------------------------------------------------------------- deepseek

def get_deepseek_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key.strip()
    if not os.path.exists(ENV_PATH):
        return ""
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def llm(prompt, system=""):
    """Call the DeepSeek chat API. Raises on network/API failure."""
    key = get_deepseek_key()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not found in %s" % ENV_PATH)
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system or
             "You convert natural language to Cypher queries for a Neo4j knowledge graph."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 700,
    }).encode()
    req = urllib.request.Request(DEEPSEEK_URL, data=body, headers={
        "Authorization": "Bearer %s" % key,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read().decode())
        return resp["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise RuntimeError("DeepSeek HTTP %s: %s" % (e.code, detail))
    except Exception as e:
        raise RuntimeError("DeepSeek request failed: %s" % str(e)[:400])


def extract_cypher(text):
    """Strip markdown fences and prose from an LLM Cypher response."""
    text = text.strip()
    if text.startswith("```"):
        blocks = text.split("```")
        if len(blocks) >= 2:
            text = blocks[1].strip()
    joined = text.strip().rstrip(";").strip()
    if joined.lower().startswith("cypher"):
        joined = joined[len("cypher"):].strip()
    return joined


WRITE_KEYWORDS = ("CREATE", "MERGE", "DELETE", "DETACH", "SET ", "REMOVE",
                  "DROP", "LOAD CSV", "CALL apoc.import", "FOREACH")


def is_read_only(cypher):
    head = re.sub(r"//[^\n]*", "", cypher).strip().upper()
    head = re.sub(r"/\*.*?\*/", "", head, flags=re.S).strip()
    for kw in WRITE_KEYWORDS:
        if head.startswith(kw):
            return False
    return True


# ---------------------------------------------------------------- schema

def discover_schema():
    """Pull live labels, relationship types, properties, and edge patterns."""
    statements = [
        {"statement": "CALL db.labels() YIELD label RETURN label ORDER BY label",
         "resultDataContents": ["row"]},
        {"statement": "CALL db.relationshipTypes() YIELD relationshipType "
                      "RETURN relationshipType ORDER BY relationshipType",
         "resultDataContents": ["row"]},
        {"statement": "MATCH (n) WHERE size(labels(n)) > 0 "
                      "WITH labels(n)[0] AS label, keys(n) AS props "
                      "WITH label, collect(props)[0] AS props "
                      "RETURN label, props ORDER BY label",
         "resultDataContents": ["row"]},
        {"statement": "MATCH ()-[r]->() "
                      "WITH type(r) AS t, keys(r) AS props "
                      "WITH t, collect(props)[0] AS props "
                      "RETURN t, props ORDER BY t",
         "resultDataContents": ["row"]},
        {"statement": "MATCH (a)-[r]->(b) "
                      "WITH labels(a)[0] AS src, type(r) AS t, labels(b)[0] AS dst, count(*) AS c "
                      "RETURN src, t, dst, c ORDER BY c DESC LIMIT 30",
         "resultDataContents": ["row"]},
    ]
    results = _tx(statements)
    return {
        "labels": [r[0] for r in results[0]["rows"]],
        "relationships": [r[0] for r in results[1]["rows"]],
        "node_props": {r[0]: r[1] for r in results[2]["rows"]},
        "edge_props": {r[0]: r[1] for r in results[3]["rows"]},
        "patterns": results[4]["rows"],
    }


def get_schema():
    now = time.time()
    with _lock:
        if _schema["data"] and now - _schema["ts"] < SCHEMA_TTL:
            return _schema["data"]
        try:
            data = discover_schema()
            _schema.update({"ts": now, "data": data})
            return data
        except RuntimeError:
            if _schema["data"]:
                return _schema["data"]
            raise


def build_schema_prompt(schema):
    lines = ["The Neo4j knowledge graph (mycelium) has these node labels with typical properties:"]
    for label in schema["labels"]:
        props = schema["node_props"].get(label, [])
        lines.append("- %s: %s" % (label, ", ".join(props) if props else "(no properties)"))
    lines.append("\nRelationship types available:")
    lines.append(", ".join(schema["relationships"]))
    if schema["patterns"]:
        lines.append("\nObserved source -[relationship]-> target patterns (by count):")
        for src, t, dst, c in schema["patterns"]:
            lines.append("- (%s)-[:%s]->(%s) x%d" % (src or "?", t, dst or "?", c))
    return "\n".join(lines)


def nl_to_cypher_prompt(question, schema):
    return (
        "You write Cypher queries for a Neo4j knowledge graph.\n\n"
        "%s\n\n"
        "Write a READ-ONLY Cypher query (MATCH/RETURN only, no CREATE/MERGE/SET/DELETE) "
        "for this question. Use node_id strings for node identifiers. "
        "Return ONLY the Cypher, no explanation, no markdown fences.\n\n"
        "Question: %s" % (build_schema_prompt(schema), question)
    )


def result_to_text(res, max_rows=25, cell_max=120):
    if res.get("error"):
        return "ERROR: %s" % res["error"]
    cols = res["columns"]
    rows = res["rows"]
    if not rows:
        return "(empty result)"
    lines = [" | ".join(cols)]
    for row in rows[:max_rows]:
        lines.append(" | ".join(
            "" if v is None else str(v)[:cell_max] for v in row))
    if len(rows) > max_rows:
        lines.append("... and %d more rows" % (len(rows) - max_rows))
    return "\n".join(lines)


def answer_summary(res, question):
    text = result_to_text(res, max_rows=25)
    n_rows = len(res["rows"]) if not res.get("error") else 0
    prompt = (
        "The graph query returned %d data row(s):\n%s\n\n"
        "Answer the original question '%s' in 2-3 natural sentences. "
        "Base every count on the data below exactly - never invent numbers. "
        "If the data is empty, say so plainly." % (n_rows, text, question)
    )
    return llm(prompt, "You summarize graph query results in natural language. "
                       "You are precise with counts and never fabricate data.")


# ---------------------------------------------------------------- handlers

def handle_health():
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stmts = [
        {"statement": "MATCH (n) RETURN count(n) AS nodes", "resultDataContents": ["row"]},
        {"statement": "MATCH ()-[r]->() RETURN count(r) AS edges", "resultDataContents": ["row"]},
        {"statement": "MATCH (n) WHERE size(labels(n)) > 0 "
                      "RETURN labels(n)[0] AS label, count(*) AS c ORDER BY c DESC",
         "resultDataContents": ["row"]},
        {"statement": "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c "
                      "ORDER BY c DESC", "resultDataContents": ["row"]},
    ]
    results = _tx(stmts)
    nodes = results[0]["rows"][0][0] if results[0]["rows"] else 0
    edges = results[1]["rows"][0][0] if results[1]["rows"] else 0
    labels = [{"label": r[0], "count": r[1]} for r in results[2]["rows"]]
    relationships = [{"type": r[0], "count": r[1]} for r in results[3]["rows"]]
    density = 0.0
    avg_degree = 0.0
    if nodes > 1:
        density = edges / float(nodes * (nodes - 1))
        avg_degree = (2.0 * edges) / nodes
    return {
        "nodes": nodes,
        "edges": edges,
        "density": round(density, 6),
        "avg_degree": round(avg_degree, 2),
        "labels": labels,
        "relationships": relationships,
        "ts": now,
    }


def handle_topology():
    now = time.time()
    with _lock:
        if _topology["data"] and now - _topology["ts"] < TOPOLOGY_TTL:
            return _topology["data"]

    cypher = (
        "MATCH (n) OPTIONAL MATCH (n)-[r]->(m) "
        "RETURN COALESCE(n.node_id, elementId(n)) AS nid, n.name AS name, "
        "labels(n)[0] AS lbl, type(r) AS rel, "
        "COALESCE(m.node_id, elementId(m)) AS mid, m.name AS mname"
    )
    res = http_cypher(cypher)
    if res["error"]:
        return {"error": res["error"]}

    nodes = {}
    edges = []
    for nid, name, lbl, rel, mid, mname in res["rows"]:
        group = lbl or "Unlabeled"
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": name or nid, "group": group}
        if rel and mid is not None:
            edges.append({"source": nid, "target": mid, "type": rel})

    data = {"nodes": list(nodes.values()), "edges": edges}
    with _lock:
        _topology.update({"ts": time.time(), "data": data})
    return data


def handle_cypher(query):
    cypher = (query or "").strip()
    if not cypher:
        return {"columns": [], "rows": [], "error": "Empty query"}
    res = run_cypher(cypher)
    return res


def handle_nl(question):
    question = (question or "").strip()
    if not question:
        return {"error": "Empty question"}

    schema = get_schema()
    cypher = extract_cypher(llm(nl_to_cypher_prompt(question, schema)))
    if not cypher:
        return {"error": "DeepSeek did not generate a Cypher query."}
    if not is_read_only(cypher):
        return {"error": "Refused to run a non-read-only query.", "cypher": cypher}

    res = run_cypher(cypher)
    resp = {
        "cypher": cypher,
        "columns": res["columns"],
        "rows": res["rows"],
        "error": res["error"],
        "answer": None,
    }
    if not res["error"]:
        try:
            resp["answer"] = answer_summary(res, question)
        except Exception as e:
            resp["summary_error"] = "summary failed: %s" % str(e)[:300]
    return resp


# ---------------------------------------------------------------- http server

class Handler(BaseHTTPRequestHandler):
    server_version = "GraphUI/1.0"

    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, data):
        body = json.dumps(data, default=str).encode()
        self._send(code, body, "application/json; charset=utf-8")

    def _text(self, code, text):
        self._send(code, text.encode(), "text/plain; charset=utf-8")

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 4 * 1024 * 1024:
            return None
        return self.rfile.read(length)

    def _get_json(self):
        raw = self._read_body()
        if not raw:
            return None
        try:
            return json.loads(raw.decode())
        except Exception:
            return None

    def do_GET(self):
        path = self.path.split("?")[0]
        try:
            if path in ("/", "/index.html"):
                with open(os.path.join(BASE_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            elif path == "/favicon.ico":
                self._send(204, b"", "image/x-icon")
            elif path == "/api/health":
                self._json(200, handle_health())
            elif path == "/api/topology":
                self._json(200, handle_topology())
            else:
                self._json(404, {"error": "not found"})
        except RuntimeError as e:
            self._json(500, {"error": str(e)})
        except Exception as e:
            self._json(500, {"error": "internal error: %s" % str(e)[:300]})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            if path == "/api/cypher":
                data = self._get_json()
                if not data or not data.get("query"):
                    self._json(400, {"error": "body must be {\"query\": \"...\"}"})
                else:
                    self._json(200, handle_cypher(data.get("query")))
            elif path == "/api/nl":
                data = self._get_json()
                if not data or not data.get("question"):
                    self._json(400, {"error": "body must be {\"question\": \"...\"}"})
                else:
                    self._json(200, handle_nl(data.get("question")))
            else:
                self._json(404, {"error": "not found"})
        except RuntimeError as e:
            self._json(500, {"error": str(e)})
        except Exception as e:
            self._json(500, {"error": "internal error: %s" % str(e)[:300]})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (time.strftime("%H:%M:%S"), fmt % args))


def main():
    host, port = HOST, PORT
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        else:
            i += 1

    server = ThreadingHTTPServer((host, port), Handler)
    print("Graph UI listening on http://%s:%d" % (host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
