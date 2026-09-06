#!/usr/bin/env python3
"""Natural language query interface for the mycelium graph.
Usage: python3 nl-query.py "what projects are active right now?"
Reads DEEPSEEK_API_KEY from /opt/delta/delta.env

Transport: Neo4j HTTP transaction API (stdlib urllib, no driver needed) for
speed - cypher-shell costs ~15s per invocation on this box. Falls back to
`docker exec mycelium-neo4j cypher-shell` if the HTTP API is unreachable.
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request

NEO4J_PASS = "9aac5c811e6d4f4f64a00c65666f3528"
NEO4J_URL = "http://127.0.0.1:7474/db/neo4j/tx/commit"
ENV_PATH = os.environ.get("DELTA_ENV_PATH", "/opt/delta/delta.env")


def get_deepseek_key():
    if not os.path.exists(ENV_PATH):
        return ""
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def llm(prompt, system=""):
    """Call DeepSeek API. Raises on network/API failure."""
    key = get_deepseek_key()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not found in %s" % ENV_PATH)
    body = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system or
             "You convert natural language to Cypher queries for a Neo4j knowledge graph."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500
    }).encode()
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=body,
        headers={"Authorization": "Bearer %s" % key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def extract_cypher(text):
    """Strip markdown fences and any prose from the LLM's Cypher response."""
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


def _http_cypher(cypher):
    body = json.dumps({"statements": [{
        "statement": cypher,
        "resultDataContents": ["row"],
    }]}).encode()
    token = base64.b64encode(("neo4j:" + NEO4J_PASS).encode()).decode()
    req = urllib.request.Request(NEO4J_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": "Basic " + token,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode())
    if resp.get("errors"):
        return "ERROR: %s" % resp["errors"][0]["message"][:400]
    if not resp.get("results"):
        return "(empty result)"
    res = resp["results"][0]
    columns = res.get("columns", [])
    rows = [d.get("row", []) for d in res.get("data", [])]
    if not rows:
        return "(empty result)"
    return " | ".join(columns) + "\n" + "\n".join(
        " | ".join("" if v is None else str(v) for v in row) for row in rows)


def _docker_cypher(cypher):
    r = subprocess.run(
        ["docker", "exec", "mycelium-neo4j", "cypher-shell",
         "-u", "neo4j", "-p", NEO4J_PASS, "--format", "plain", cypher],
        capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return "ERROR: %s" % r.stderr.strip()[:400]
    return r.stdout.strip() or "(empty result)"


def run_cypher(cypher):
    try:
        return _http_cypher(cypher)
    except Exception as e:
        return _docker_cypher(cypher)


def main():
    question = " ".join(sys.argv[1:]).strip() or input("Question: ")

    SCHEMA_PROMPT = """You write Cypher queries for a Neo4j graph with these node types:
- Organization: name, entity_type (earner/mission/client), status
- Project: name, status (active/hibernated)
- SubAgent: name, role, status (active/stopped/fatal/starting), model
- Server: name, health
- Service: name, health, status, last_checked_at
- Agent: name, model, status, project
- Repository: name, url
- Knowledge: file_type, scope, label, agent
- CypherAtom: semantic, label
- FleetState: total_projects, active_agents, fatal_agents, errors_5min, updated_at
- SystemHealth: load_1min, load_5min, load_15min, cpu_pct, mem_used_gb
- SessionTrace: agent, user, text_preview, created_at
- FleetEvent: type, description, created_at
- ActionProposal: type, description, status, confidence
- Invariant: label, health, severity, category, check_cypher
- TestCase: label, last_result, assertion_cypher
- Being, Concept, Purpose, SovereigntyRule, Protocol, ScaleMarker, Persona: label, project

Edges: (:Project)-[:BELONGS_TO]->(:Organization), (:Project)-[:HAS_AGENT]->(:SubAgent),
(:SubAgent {node_id:'subagent-delta-hub'})-[:OVERSEES]->(:Project),
(:Server)-[:HAS_SERVICE]->(:Service), (:Agent)-[:RUNS_ON]->(:Server),
(:TestCase)-[:VALIDATES]->(:Invariant)

Write a READ-ONLY Cypher query (MATCH/RETURN only, no CREATE/MERGE/SET/DELETE)
for this question. Return ONLY the Cypher, no explanation, no markdown fences."""

    try:
        cypher = llm("Question: %s\n\n%s" % (question, SCHEMA_PROMPT))
    except Exception as e:
        print("ERROR generating Cypher: %s" % e)
        sys.exit(1)

    cypher = extract_cypher(cypher)
    if not cypher:
        print("ERROR: no Cypher generated")
        sys.exit(1)
    if not is_read_only(cypher):
        print("ERROR: refused to run a non-read-only query:\n%s" % cypher)
        sys.exit(1)

    print("CYPHER:\n%s\n" % cypher)
    result = run_cypher(cypher)
    print("RESULT:\n%s\n" % result)

    n_rows = max(len(result.splitlines()) - 1, 0) if not result.startswith("(empty") and not result.startswith("ERROR") else 0
    try:
        answer = llm(
            "The graph query returned %d data row(s):\n%s\n\n"
            "Answer the original question '%s' in 2-3 natural sentences. "
            "Base every count on the data below exactly - never invent numbers. "
            "If the data is empty, say so plainly." % (n_rows, result, question),
            "You summarize graph query results in natural language. "
            "You are precise with counts and never fabricate data.")
        print("ANSWER: %s" % answer)
    except Exception as e:
        print("ANSWER: (summary failed: %s)" % e)


if __name__ == "__main__":
    main()
