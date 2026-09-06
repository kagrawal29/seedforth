#!/usr/bin/env python3
"""
enforce-indexes.py — read IndexDecl nodes, issue CREATE INDEX IF NOT EXISTS.

Part of v2 piece 1 (wi-v2-01-indexdecl). Runs after bootstrap MERGEs the
IndexDecl nodes from graph/protocols/indexes.cypher. Idempotent.

Why Python: CREATE INDEX is DDL and apoc.cypher.doIt is sandbox-restricted
for DDL in Neo4j Community. Python can issue DDL directly over the HTTP
tx endpoint. The graph remains the source of truth — Python is thin I/O.

Outputs one line per IndexDecl: "[ok] idx-foo-node_id RANGE Foo(node_id)"
or "[err] <id> <kind> <detail>". Exit 0 if all decls enforced, 1 if any
errored.
"""
import base64
import json
import os
import sys
import urllib.request
import urllib.error


NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")


def cypher(statement, params=None, timeout=30):
    body = {"statements": [{"statement": statement, "parameters": params or {}}]}
    req = urllib.request.Request(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode())
    if result.get("errors"):
        raise RuntimeError(result["errors"])
    return result.get("results", [])


def fetch_decls():
    result = cypher(
        "MATCH (d:IndexDecl) "
        "RETURN d.node_id AS id, d.label AS label, d.property AS property, "
        "       d.kind AS kind, coalesce(d.index_name, '') AS index_name, "
        "       coalesce(d.dimensions, 0) AS dimensions, "
        "       coalesce(d.similarity, '') AS similarity "
        "ORDER BY d.node_id"
    )
    data = result[0].get("data", []) if result else []
    rows = []
    for row in data:
        cols = row.get("row", [])
        rows.append({
            "id": cols[0],
            "label": cols[1],
            "property": cols[2],
            "kind": cols[3],
            "index_name": cols[4],
            "dimensions": cols[5],
            "similarity": cols[6],
        })
    return rows


def enforce(decl):
    kind = decl["kind"]
    label = decl["label"]
    prop = decl["property"]

    if kind == "RANGE":
        index_name = decl["index_name"] or f"idx_{label.lower()}_{prop}"
        stmt = (
            f"CREATE INDEX {index_name} IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.{prop})"
        )
    elif kind == "VECTOR":
        index_name = decl["index_name"] or f"vec_{label.lower()}_{prop}"
        dims = int(decl["dimensions"])
        sim = decl["similarity"] or "cosine"
        stmt = (
            f"CREATE VECTOR INDEX {index_name} IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.{prop}) "
            f"OPTIONS {{indexConfig: {{`vector.dimensions`: {dims}, "
            f"`vector.similarity_function`: '{sim}'}}}}"
        )
    else:
        return False, f"unknown kind: {kind}"

    try:
        cypher(stmt)
        cypher(
            "MATCH (d:IndexDecl {node_id: $id}) "
            "SET d.index_name = $name, d.last_enforced_at = toString(datetime())",
            {"id": decl["id"], "name": index_name},
        )
        return True, index_name
    except Exception as exc:
        return False, str(exc)[:200]


def main():
    decls = fetch_decls()
    if not decls:
        print("[enforce-indexes] no IndexDecl nodes found — did you bootstrap indexes.cypher?")
        return 1

    errors = 0
    for d in decls:
        ok, detail = enforce(d)
        flag = "ok " if ok else "err"
        print(f"[{flag}] {d['id']:<40} {d['kind']:<6} {d['label']}({d['property']}) -> {detail}")
        if not ok:
            errors += 1

    print(f"[enforce-indexes] declared={len(decls)} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
