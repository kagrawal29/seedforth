#!/usr/bin/env python3
"""Trace-aware graph query tool for agents.

Every query the agent runs through this tool:
1. Creates/updates a :Query node (keyed by sha256 of the cypher) — fire_count++
2. Creates a :QueryTrace node (agent, timestamp, cypher)
3. Runs the query, returns results
4. Links the trace to touched nodes where possible

This is the Hebbian layer: frequently-asked paths strengthen, never-asked paths decay.

Usage (called by opencode graph tool):
  python3 graph-tool.py "MATCH (n) RETURN count(n)"
  GRAPH_AGENT=subagent-seedforthing python3 graph-tool.py "..."
"""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.request

NEO4J_URL = "http://127.0.0.1:7474/db/neo4j/tx/commit"
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "")
if not NEO4J_PASS:
    raise RuntimeError("NEO4J_PASSWORD must be provided at runtime")
AGENT = os.environ.get("GRAPH_AGENT", "unknown-agent")


def _post(statements):
    body = json.dumps({"statements": statements}).encode()
    auth = base64.b64encode(f"neo4j:{NEO4J_PASS}".encode()).decode()
    req = urllib.request.Request(NEO4J_URL, data=body, headers={
        "Content-Type": "application/json", "Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def record_trace(cypher):
    """Write Query node (fire_count++) + QueryTrace node."""
    cypher_hash = hashlib.sha256(cypher.encode()).hexdigest()[:24]
    ts = int(time.time() * 1000)
    trace_id = f"qt-{ts}"
    try:
        _post([
            {
                "statement": (
                    "MERGE (q:Query {cypher_hash:$h}) "
                    "SET q.text=$t, q.last_command='graph-tool', q.project='system' "
                    "SET q.fire_count = coalesce(q.fire_count, 0) + 1 "
                    "RETURN q.fire_count"
                ),
                "parameters": {"h": cypher_hash, "t": cypher[:500]},
            },
            {
                "statement": (
                    "CREATE (qt:QueryTrace {node_id:$tid, agent:$ag, "
                    "cypher_hash:$h, cypher:$c, created_at:datetime(), project:'system'}) "
                    "RETURN qt.node_id"
                ),
                "parameters": {"tid": trace_id, "ag": AGENT,
                               "h": cypher_hash, "c": cypher[:500]},
            },
        ])
        return cypher_hash, trace_id
    except Exception as e:
        print(f"[graph-tool] trace write failed (non-fatal): {e}", file=sys.stderr)
        return None, None


def write_knowledge(label, content, file_type="learning", scope="seedforth",
                    project="system", tags=None):
    """Record a Knowledge node. This is the agent's write path into the graph.

    Agents call this after discovering something reusable:
      graph-tool.py write "How to fix X" "When Y happens, do Z" learning <project>

    The node becomes part of the knowledge layer: connect/converge/dream
    atoms wire it to SessionTraces and other knowledge over time.
    """
    ts = int(time.time() * 1000)
    node_id = f"kn-{ts}-{AGENT}"
    _post([
        {
            "statement": (
                "MERGE (k:Knowledge {scope:$scope, label:$label}) "
                "SET k.content=$content, k.file_type=$ft, k.project=$project, "
                "k.source=$ag, k.tags=$tags, k.updated_at=datetime() "
                "ON CREATE SET k.created_at=datetime(), k.node_id=$nid "
                "RETURN k.node_id"
            ),
            "parameters": {
                "scope": scope, "label": label, "content": content,
                "ft": file_type, "project": project, "ag": AGENT,
                "tags": tags or [], "nid": node_id,
            },
        },
    ])
    print(f"knowledge recorded: {scope}:{label} [{file_type}]")
    return True


def run(cypher):
    cypher_hash, trace_id = record_trace(cypher)
    try:
        data = _post([{"statement": cypher}])
        if data.get("errors"):
            return {"error": data["errors"][0]["message"][:300]}
        results = []
        touched_ids = []
        for res in data.get("results", []):
            cols = res.get("columns", [])
            for row in res.get("data", []):
                r = dict(zip(cols, row.get("row", [])))
                results.append(r)
                # Hebbian: collect node_id-ish values so we can link the trace.
                # Column names like "n.node_id" / "g.node_id" signal identity.
                for col, v in r.items():
                    if isinstance(v, dict):
                        nid = v.get("node_id") or v.get("name") or v.get("id")
                        if nid:
                            touched_ids.append(str(nid))
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                nid = item.get("node_id") or item.get("name") or item.get("id")
                                if nid:
                                    touched_ids.append(str(nid))
                    elif col.split(".")[-1] in ("node_id", "name", "id") and v:
                        touched_ids.append(str(v))
        _link_trace(trace_id, touched_ids)
        return {"results": results, "trace": trace_id, "query_hash": cypher_hash}
    except Exception as e:
        return {"error": str(e)}


def _link_trace(trace_id, node_ids):
    """Hebbian: link QueryTrace -> touched nodes with READS edges.

    Frequently-touched nodes accumulate READS, and the weekly strengthen/decay
    atom turns that frequency into edge-weight reinforcement.
    """
    if not trace_id or not node_ids:
        return
    seen = set()
    for nid in node_ids[:50]:
        if nid in seen or len(nid) > 200:
            continue
        seen.add(nid)
        try:
            _post([{"statement":
                "MATCH (qt:QueryTrace {node_id:$tid}) "
                "MATCH (n) WHERE n.node_id = $nid "
                "MERGE (qt)-[:READS {decay_protected:true}]->(n)",
                "parameters": {"tid": trace_id, "nid": nid}}])
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: graph-tool.py <cypher> | graph-tool.py write <label> <content> [type] [project]"}))
        sys.exit(1)
    if sys.argv[1] == "write":
        label = sys.argv[2] if len(sys.argv) > 2 else ""
        content = sys.argv[3] if len(sys.argv) > 3 else ""
        ftype = sys.argv[4] if len(sys.argv) > 4 else "learning"
        project = sys.argv[5] if len(sys.argv) > 5 else "system"
        if not label or not content:
            print(json.dumps({"error": "write requires <label> <content>"}))
            sys.exit(1)
        write_knowledge(label, content, ftype, project=project)
        return
    cypher = " ".join(sys.argv[1:]).strip()
    out = run(cypher)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
