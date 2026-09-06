#!/usr/bin/env python3
# Fast shell: HTTP-transport cypher executor (replaces JVM cypher-shell).
# Target: <500ms per call. cypher-shell's JVM startup alone is ~1000ms.
import os, sys, json, base64, urllib.request, urllib.error

URL = os.environ.get("NEO4J_HTTP", "http://127.0.0.1:7474") + "/db/neo4j/tx/commit"
USER = os.environ.get("NEO4J_USER", "neo4j")
PASS = os.environ.get("NEO4J_PASS", "localtest12")
AUTH = "Basic " + base64.b64encode(f"{USER}:{PASS}".encode()).decode()

query = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
if not query.strip():
    sys.exit(0)

body = json.dumps({"statements": [{"statement": query}]}).encode()
req = urllib.request.Request(URL, data=body, method="POST",
    headers={"Content-Type": "application/json", "Authorization": AUTH})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        resp = json.loads(r.read())
except urllib.error.HTTPError as e:
    print(e.read().decode(), file=sys.stderr); sys.exit(1)

errs = resp.get("errors", [])
if errs:
    for e in errs: print(f"{e.get('code','')}: {e.get('message','')}", file=sys.stderr)
    sys.exit(1)

for res in resp.get("results", []):
    cols = res.get("columns", [])
    print(", ".join(cols))
    for row in res.get("data", []):
        vals = row.get("row", [])
        print(", ".join(json.dumps(v) if not isinstance(v, str) else f'"{v}"' for v in vals))
