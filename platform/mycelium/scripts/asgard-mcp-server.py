#!/usr/bin/env python3
"""
Asgard Graph MCP Server — the graph speaks to every Claude session.

Exposes FalkorDB as an MCP server. Team members' Claude sessions
connect directly to the live knowledge graph. No flat files. No stale caches.
Every query is a structural coupling event — demand traced back
automatically.

Tools:
  asgard_graph_ask           — natural language question → graph answer
  asgard_graph_query         — execute Cypher → raw results
  asgard_graph_demand        — what is the team asking about?
  asgard_graph_schema        — graph structure, node/edge types, example queries
  asgard_graph_trace         — record a demand signal (structural coupling write-back)
  asgard_graph_neighborhood  — explore connections from a specific node
  asgard_graph_bridges       — cross-community connections

Usage:
  python3 scripts/asgard-mcp-server.py                    # stdio transport (local)
  python3 scripts/asgard-mcp-server.py --port 6381        # HTTP/SSE transport (remote)
"""

import argparse
import asyncio
import contextvars
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# MCP SDK
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Secret redaction — strip credentials before they enter traces/graph
try:
    from scripts.lib.redact import redact as _redact_secrets
except ImportError:
    try:
        from lib.redact import redact as _redact_secrets
    except ImportError:
        def _redact_secrets(text):
            return text  # Fallback: no redaction if module not found

# Graph client
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"

# Trace files
QUERY_LOG = REPO_ROOT / "knowledge" / "meta" / "asgard-query-log.md"
TRACE_LOG = REPO_ROOT / "knowledge" / "meta" / "asgard-graph-traces.jsonl"
DEMAND_TRACE = REPO_ROOT / "knowledge" / "meta" / "mcp-demand-trace.jsonl"

# Track request timing
import time as _time

# PII → alias mapping (forest names only in traces)
_NAME_TO_ALIAS = {
    "sahiram": "Banyan", "banyan": "Banyan",
    "abhishek": "Sequoia", "sequoia": "Sequoia",
    "ankit-s": "Birch", "ankit": "Birch", "birch": "Birch",
    "sahil": "Cedar", "cedar": "Cedar",
    "pranav": "Oak", "oak": "Oak",
    "kshitiz": "Mycelium", "mycelium": "Mycelium",
}


def _to_alias(name: str) -> str:
    """Convert a person name to their forest alias. No PII in traces."""
    if not name:
        return ""
    alias = _NAME_TO_ALIAS.get(name.lower().strip())
    if alias:
        return alias
    # If already an alias or unknown, return as-is (no PII leaked)
    return name


# ─── Per-person token auth ───────────────────────────────────────────────────
# Maps token → forest alias.  Loaded from ASGARD_TOKENS_FILE (YAML) or
# ASGARD_TOKENS_JSON (env var, JSON string).  The legacy ASGARD_GRAPH_TOKEN
# is kept as an admin/fallback token (authenticates as "admin", no person).
#
# Token file format (YAML):
#   tokens:
#     Banyan:  <token>
#     Sequoia: <token>
#     ...
#
# JSON env var format:
#   {"Banyan": "<token>", "Sequoia": "<token>", ...}

_TOKEN_TO_PERSON: dict[str, str] = {}  # populated by _load_person_tokens()

# ContextVar lets us pass the authenticated person from the ASGI auth layer
# into the MCP call_tool handler without modifying the MCP SDK.
_authenticated_person: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_authenticated_person", default=""
)


def _verify_token_via_graph(token: str) -> str | None:
    """Graph-native auth: hash the token, query Person nodes for matching hash.

    Returns the person's alias if found, None otherwise.
    The token never enters the graph — only its SHA-256 hash is compared.
    """
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    try:
        graph = get_graph()
        r = graph.query(
            f"MATCH (p:Person {{token_hash: '{token_hash}'}}) RETURN p.alias"
        )
        if r.result_set and r.result_set[0][0]:
            return str(r.result_set[0][0])
    except Exception:
        pass
    return None


def _load_person_tokens() -> dict[str, str]:
    """Load per-person tokens.  Returns {token: alias} mapping.

    Sources (checked in order):
    1. Graph-native: Person nodes with token_hash (verified at auth time, not loaded)
    2. ASGARD_TOKENS_FILE env var → path to a YAML file
    3. ASGARD_TOKENS_JSON env var → inline JSON string
    4. /app/tokens.yaml (default Docker path)

    Graph-native auth doesn't need pre-loading — it verifies on each request.
    File/env sources are kept as fallback for bootstrapping new instances.
    """
    global _TOKEN_TO_PERSON
    mapping: dict[str, str] = {}

    # Check if graph has token hashes (graph-native auth available)
    try:
        graph = get_graph()
        r = graph.query(
            "MATCH (p:Person) WHERE p.token_hash IS NOT NULL RETURN count(p)"
        )
        graph_auth_count = r.result_set[0][0] if r.result_set else 0
        if graph_auth_count > 0:
            print(f"Graph-native auth available: {graph_auth_count} Person nodes with token_hash", file=sys.stderr)
    except Exception:
        pass

    # Source 1: YAML file
    tokens_file = os.environ.get("ASGARD_TOKENS_FILE", "")
    if not tokens_file and Path("/app/tokens.yaml").exists():
        tokens_file = "/app/tokens.yaml"

    if tokens_file and Path(tokens_file).exists():
        try:
            import yaml
            with open(tokens_file) as f:
                data = yaml.safe_load(f) or {}
            token_dict = data.get("tokens", data)  # support top-level or nested
            for alias, tok in token_dict.items():
                if isinstance(tok, str) and tok:
                    mapping[tok] = str(alias)
        except Exception as e:
            print(f"WARNING: Failed to load tokens from {tokens_file}: {e}", file=sys.stderr)

    # Source 2: JSON env var (overrides / supplements file)
    tokens_json = os.environ.get("ASGARD_TOKENS_JSON", "")
    if tokens_json:
        try:
            token_dict = json.loads(tokens_json)
            for alias, tok in token_dict.items():
                if isinstance(tok, str) and tok:
                    mapping[tok] = str(alias)
        except Exception as e:
            print(f"WARNING: Failed to parse ASGARD_TOKENS_JSON: {e}", file=sys.stderr)

    _TOKEN_TO_PERSON = mapping
    if mapping:
        print(f"Loaded {len(mapping)} per-person tokens: {', '.join(sorted(mapping.values()))}", file=sys.stderr)
    return mapping


def generate_tokens_for_team() -> dict[str, str]:
    """Generate a fresh token for each team member.  Returns {alias: token}.

    Reads team from config.yaml.  Tokens are URL-safe, 32-byte random strings.
    """
    config_path = REPO_ROOT / "config.yaml"
    try:
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"ERROR: Cannot read {config_path}: {e}", file=sys.stderr)
        sys.exit(1)

    tokens: dict[str, str] = {}
    for member in cfg.get("team", []):
        alias = member.get("alias", "")
        if alias:
            tokens[alias] = secrets.token_urlsafe(32)
    return tokens


def get_graph():
    from falkordb import FalkorDB
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(GRAPH_NAME)


def _esc(s):
    """Escape string for Cypher."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def structural_couple(
    tool: str,
    query: str,
    num_results: int,
    latency_ms: float,
    person: str = "",
    touched_nodes: list[str] | None = None,
):
    """Write a CouplingEvent to the graph — the interaction changes the graph's shape.

    Every tool call that touches the graph leaves a structural trace:
    1. CouplingEvent node with metadata (who, what, when, which tool)
    2. If a person is identified, COUPLED edge from person
    3. If knowledge nodes were touched, ACTIVATED edges to those nodes
    4. If the query looks like a demand, upsert/strengthen a Demand node
    """
    # Only couple meaningful human-session interactions
    # Skip: schema requests, queries without a person, raw Cypher from pipeline agents
    if not person or person.lower() in ("unknown", "mcp", ""):
        return
    if tool in ("asgard_graph_schema",):
        return

    try:
        graph = get_graph()
        alias = _to_alias(person)
        ts = datetime.now(timezone.utc).isoformat()

        # CM7: Per-person flood protection — max 10 CouplingEvents per person per hour
        one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        try:
            r = graph.query(
                f"MATCH (ce:CouplingEvent) "
                f"WHERE ce.person = '{_esc(alias)}' AND ce.timestamp > '{one_hour_ago}' "
                f"RETURN count(ce)"
            )
            recent_count = r.result_set[0][0] if r.result_set else 0
            if recent_count >= 10:
                # Log but don't couple — flood protection
                return
        except Exception:
            pass  # If check fails, allow the coupling

        event_id = f"ce-{ts[:19].replace(':', '-').replace('T', '-')}-{alias}-{tool}"

        # Create CouplingEvent node (these decay — pruned after 7 days by integrity rules)
        graph.query(
            f"CREATE (e:CouplingEvent {{"
            f"node_id: '{_esc(event_id)}', "
            f"label: '{_esc(query[:150])}', "
            f"tool: '{_esc(tool)}', "
            f"person: '{_esc(alias)}', "
            f"timestamp: '{_esc(ts)}', "
            f"num_results: {num_results}, "
            f"latency_ms: {round(latency_ms, 1)}, "
            f"file_type: 'coupling'"
            f"}})"
        )

        # Link to Knowledge nodes that were touched/returned
        if touched_nodes:
            for node_id in touched_nodes[:10]:
                try:
                    graph.query(
                        f"MATCH (e:CouplingEvent {{node_id: '{_esc(event_id)}'}}), "
                        f"(k:Knowledge {{node_id: '{_esc(node_id)}'}}) "
                        f"CREATE (e)-[:ACTIVATED]->(k)"
                    )
                except Exception:
                    pass

        # Don't create Demand nodes here — let the demand engine curate.
        # The JSONL trace (already written by log_trace) feeds the demand engine.
        # CouplingEvents are the raw signal; Demand nodes are the curated output.

    except Exception:
        pass  # Structural coupling is non-blocking — never fail the query


def log_trace(
    tool: str,
    query: str,
    response: str,
    num_results: int,
    latency_ms: float,
    person: str = "",
    error: str = "",
    touched_nodes: list[str] | None = None,
):
    """Full trace — JSONL file + structural coupling to graph.

    All person references stored as forest aliases — no PII in trace files.
    All text is redacted for secrets before writing.
    """
    alias = _to_alias(person)
    ts = datetime.now(timezone.utc).isoformat()
    # Redact secrets from query and response before any persistence
    query = _redact_secrets(query)
    response = _redact_secrets(response)
    entry = {
        "timestamp": ts,
        "tool": tool,
        "query": query,
        "response_preview": response[:500] if response else "",
        "response_bytes": len(response.encode()) if response else 0,
        "num_results": num_results,
        "latency_ms": round(latency_ms, 1),
        "person": alias,
        "error": error,
    }
    try:
        TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACE_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    # Also append to the human-readable markdown log (backwards compat)
    try:
        line = f"| {ts[:19]}Z | {person or 'mcp'} | {tool} | {query[:80]} | {num_results} | {latency_ms:.0f}ms |\n"
        with open(QUERY_LOG, "a") as f:
            f.write(line)
    except Exception:
        pass

    # Structural coupling — the graph changes shape from this interaction
    if not error:
        structural_couple(
            tool=tool, query=query, num_results=num_results,
            latency_ms=latency_ms, person=person, touched_nodes=touched_nodes,
        )

    # Real-time micro-intelligence — the graph responds to being touched
    if not error and person:
        realtime_coupling(person, query, touched_nodes)


def realtime_coupling(person: str, query: str, touched_nodes: list[str] | None = None):
    """Real-time micro-intelligence — fires on EVERY query. All Cypher. $0.

    5 coupling steps:
    1. Answer already delivered (upstream)
    2. CouplingEvent already created (structural_couple)
    3. Check routed knowledge for this person
    4. Check if query touches a proposal target
    5. Quick convergence with other recent queries

    Results are appended to the MCP demand trace for the demand engine
    to pick up, and surfaced as JSONL for context generation.
    """
    alias = _to_alias(person) if person else ""
    if not alias or alias == "unknown":
        return

    try:
        graph = get_graph()
    except Exception:
        return

    # Step 3: Check routed knowledge waiting for this person
    try:
        r = graph.query(
            f"MATCH (k:Knowledge)-[r:ROUTED_TO]->(pc:PersonContext {{person: '{_esc(alias)}'}}) "
            f"RETURN k.label, r.routed_at"
        )
        if r.result_set:
            for row in r.result_set:
                # Log that routed knowledge was available during this person's session
                ts = datetime.now(timezone.utc).isoformat()
                try:
                    DEMAND_TRACE.parent.mkdir(parents=True, exist_ok=True)
                    entry = {
                        "timestamp": ts, "person": alias, "type": "routed_knowledge_available",
                        "knowledge": row[0], "routed_at": row[1], "source": "realtime-coupling",
                    }
                    with open(DEMAND_TRACE, "a") as f:
                        f.write(json.dumps(entry) + "\n")
                except Exception:
                    pass
    except Exception:
        pass

    # Step 4: Check if query touches nodes near an unexecuted proposal
    try:
        if touched_nodes:
            for nid in touched_nodes[:3]:
                r = graph.query(
                    f"MATCH (ap:ActionProposal {{status: 'proposed'}})-[:RESOLVES_WITH]->(k:Knowledge {{node_id: '{_esc(nid)}'}}) "
                    f"RETURN ap.label, ap.person"
                )
                if r.result_set:
                    # This person's query is near a pending proposal — record proximity
                    ts = datetime.now(timezone.utc).isoformat()
                    try:
                        entry = {
                            "timestamp": ts, "person": alias, "type": "proposal_proximity",
                            "proposal": r.result_set[0][0], "touched_node": nid,
                            "source": "realtime-coupling",
                        }
                        with open(DEMAND_TRACE, "a") as f:
                            f.write(json.dumps(entry) + "\n")
                    except Exception:
                        pass
    except Exception:
        pass

    # Step 5: Quick convergence — is this person asking about the same region as others recently?
    try:
        r = graph.query(
            f"MATCH (ce:CouplingEvent) "
            f"WHERE ce.person <> '{_esc(alias)}' "
            f"AND ce.person <> 'unknown' "
            f"RETURN ce.person, ce.label, ce.tool "
            f"ORDER BY ce.timestamp DESC LIMIT 3"
        )
        # If recent coupling events from OTHER people touch similar topics, that's live convergence
        if r.result_set and query:
            query_words = set(w.lower() for w in query.split() if len(w) > 4)
            for row in r.result_set:
                other_person, other_query, other_tool = row
                if other_query:
                    other_words = set(w.lower() for w in str(other_query).split() if len(w) > 4)
                    overlap = query_words & other_words
                    if len(overlap) >= 2:
                        ts = datetime.now(timezone.utc).isoformat()
                        try:
                            entry = {
                                "timestamp": ts, "person": alias, "type": "live_convergence",
                                "other_person": other_person, "shared_words": list(overlap)[:5],
                                "source": "realtime-coupling",
                            }
                            with open(DEMAND_TRACE, "a") as f:
                                f.write(json.dumps(entry) + "\n")
                        except Exception:
                            pass
    except Exception:
        pass


def trace_demand(question: str, person: str):
    """Write demand trace — structural coupling write-back.

    Does two things:
    1. Appends to JSONL file for the demand engine to pick up
    2. Upserts a Demand node in the graph for immediate visibility

    All person references stored as forest aliases — no PII.
    """
    alias = _to_alias(person)
    ts = datetime.now(timezone.utc).isoformat()

    # 1. JSONL append
    try:
        DEMAND_TRACE.parent.mkdir(parents=True, exist_ok=True)
        entry = {"timestamp": ts, "person": alias, "question": question, "source": "mcp"}
        with open(DEMAND_TRACE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

    # 2. Upsert Demand node in graph
    try:
        graph = get_graph()
        safe_q = question.replace("'", "\\'").replace("\\", "\\\\")
        safe_a = alias.replace("'", "\\'").replace("\\", "\\\\")
        graph.query(
            f"MERGE (d:Demand {{label: '{safe_q}'}}) "
            f"SET d.last_asked = '{ts}', d.last_asked_by = '{safe_a}'"
        )
    except Exception:
        pass


def _is_read_only_cypher(query: str) -> tuple[bool, str]:
    """Validate that a Cypher query contains no write operations.

    Returns (is_safe, reason). Strips string literals before checking
    so that keywords inside quoted strings don't trigger false positives.

    Blocks: CREATE, MERGE, SET, DELETE, DETACH, REMOVE, DROP, CALL, FOREACH,
            LOAD CSV (can trigger writes via APOC), multi-statement queries.
    """
    import re

    if not query or not query.strip():
        return False, "Empty query"

    # Reject multi-statement queries (semicolons outside string literals)
    # First strip strings, then check for semicolons
    # Replace single-quoted and double-quoted string literals with placeholders
    stripped = re.sub(r"'(?:[^'\\]|\\.)*'", "'__STR__'", query)
    stripped = re.sub(r'"(?:[^"\\]|\\.)*"', '"__STR__"', stripped)

    if ";" in stripped:
        return False, "Multi-statement queries are not allowed"

    # Check for write keywords (case-insensitive, word-boundary)
    # We check against the string-stripped version so keywords inside
    # literals don't cause false positives.
    write_keywords = [
        r"\bCREATE\b",
        r"\bMERGE\b",
        r"\bSET\b",
        r"\bDELETE\b",
        r"\bDETACH\b",
        r"\bREMOVE\b",
        r"\bDROP\b",
        r"\bCALL\b",
        r"\bFOREACH\b",
        r"\bLOAD\s+CSV\b",
    ]

    upper = stripped.upper()
    for pattern in write_keywords:
        m = re.search(pattern, upper)
        if m:
            keyword = m.group(0).strip()
            return False, f"Write operation not allowed: {keyword}"

    return True, ""


def _run_realtime_heal(graph):
    """Continuous crystallization: the graph runs its own heartbeat.

    Not a Python heartbeat. Not a cron. The graph reads its own Protocol
    nodes, executes their Cypher, evaluates its own TestCases, and
    computes its own health. Pure Cypher, driven by the graph's own topology.

    The graph IS the nervous system. This function is just the hand that
    turns the crank — the intelligence lives in the stored Cypher.
    """
    # 1. Run all enabled excrete-phase protocols (the graph's own Cypher)
    try:
        protocols = graph.query("""
            MATCH (p:Protocol)
            WHERE p.enabled = true AND p.cypher IS NOT NULL AND p.cypher <> ''
            AND p.phase = 'excrete'
            RETURN p.node_id, p.cypher
            ORDER BY p.node_id
            LIMIT 15
        """)
        for row in (protocols.result_set or []):
            try:
                graph.query(row[1])
            except Exception:
                pass
    except Exception:
        pass

    # 2. Re-evaluate failing tests (the graph tests itself)
    try:
        tests = graph.query("""
            MATCH (tc:TestCase)
            WHERE tc.last_result = 'fail' AND tc.cypher IS NOT NULL
            RETURN tc.node_id, tc.cypher
            LIMIT 10
        """)
        for row in (tests.result_set or []):
            tc_id, tc_cypher = row[0], row[1]
            try:
                result = graph.query(tc_cypher)
                passed = False
                if result.result_set and len(result.result_set) > 0:
                    val = result.result_set[0][0]
                    passed = val is True or val == 'true' or val == 1
                if passed:
                    graph.query(f"""
                        MATCH (tc:TestCase {{node_id: '{tc_id}'}})
                        SET tc.last_result = 'pass'
                    """)
            except Exception:
                pass
    except Exception:
        pass

    # 3. Compute health score (the graph measures itself)
    try:
        graph.query("""
            MATCH (tc:TestCase)
            WITH count(tc) AS total,
              sum(CASE WHEN tc.last_result = 'pass' THEN 1 ELSE 0 END) AS passing
            WHERE total > 0
            MERGE (hc:HealthCheck {node_id: 'healthcheck-latest'})
            SET hc.previous_score = coalesce(hc.score, 0),
                hc.score = toInteger(toFloat(passing) / total * 100),
                hc.status = CASE
                  WHEN toFloat(passing) / total >= 0.8 THEN 'HEALTHY'
                  WHEN toFloat(passing) / total >= 0.6 THEN 'DEGRADED'
                  WHEN toFloat(passing) / total >= 0.4 THEN 'UNHEALTHY'
                  ELSE 'CRITICAL' END,
                hc.passed = passing,
                hc.total = total,
                hc.score_trend = CASE
                  WHEN toInteger(toFloat(passing) / total * 100) > coalesce(hc.score, 0) THEN 'improving'
                  WHEN toInteger(toFloat(passing) / total * 100) < coalesce(hc.score, 0) THEN 'degrading'
                  ELSE 'stable' END
        """)
    except Exception:
        pass

    # 3. Mutation gate: detect if this write degraded health
    try:
        result = graph.query("""
            MATCH (hc:HealthCheck {node_id: 'healthcheck-latest'})
            RETURN hc.score
        """)
        if result.result_set:
            current_score = result.result_set[0][0]
            # Store score trajectory for trend detection
            graph.query(f"""
                MERGE (hc:HealthCheck {{node_id: 'healthcheck-latest'}})
                SET hc.previous_score = coalesce(hc.score, {current_score}),
                    hc.score_trend = CASE
                      WHEN {current_score} > coalesce(hc.score, {current_score}) THEN 'improving'
                      WHEN {current_score} < coalesce(hc.score, {current_score}) THEN 'degrading'
                      ELSE 'stable' END
            """)
    except Exception:
        pass


def _merge_mcp_query_node(query_text: str, person: str, tool: str):
    """MERGE an MCPQuery node so the IngestionRule can process it later.

    Uses a hash of the query text as node_id for deduplication.
    Sets _digested = null so the ingestion pipeline picks it up.
    Non-blocking — failures are silently ignored.
    """
    if not query_text or query_text in ("(schema request)", "(all)"):
        return
    try:
        import hashlib
        node_id = "mcpq-" + hashlib.sha256(query_text.encode()).hexdigest()[:16]
        graph = get_graph()
        alias = _to_alias(person) if person else ""
        ts = datetime.now(timezone.utc).isoformat()
        graph.query(
            f"MERGE (q:MCPQuery {{node_id: '{_esc(node_id)}'}}) "
            f"ON CREATE SET q.query_text = '{_esc(query_text[:500])}', "
            f"q.person = '{_esc(alias)}', "
            f"q.tool = '{_esc(tool)}', "
            f"q.timestamp = '{_esc(ts)}', "
            f"q._digested = NULL"
        )
    except Exception:
        pass  # Non-blocking — never fail the query


def _extract_node_ids_from_response(text: str) -> list[str]:
    """Best-effort extraction of node_ids from a text response.

    Looks for patterns like node_id: 'xxx' or known kebab-case identifiers
    that match knowledge entry IDs.
    """
    import re
    # Match kebab-case identifiers that look like node_ids
    ids = re.findall(r'\b([a-z][a-z0-9_-]{5,}(?:-[a-z0-9]+)+)\b', text.lower())
    return list(dict.fromkeys(ids))[:10]  # Dedupe, cap at 10


def _extract_node_ids_from_cypher(rows: list) -> list[str]:
    """Extract node_id-like strings from Cypher result rows."""
    ids = []
    for row in rows:
        for cell in row:
            if isinstance(cell, str) and len(cell) > 5 and "-" in cell and " " not in cell:
                ids.append(cell)
    return list(dict.fromkeys(ids))[:10]


# Create MCP server
server = Server("asgard-graph")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="asgard_graph_ask",
            description=(
                "Ask Asgard Graph a question in natural language. "
                "Returns relevant nodes, connections, demand signals, and cross-person "
                "dependencies from the team's knowledge graph. "
                "Pass your name/alias so the graph can surface knowledge routed to you."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question about architecture, decisions, team work, or connections"
                    },
                    "person": {
                        "type": "string",
                        "description": "Your name or forest alias (e.g. Oak, Banyan). Enables personalized responses."
                    }
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="asgard_graph_demand",
            description=(
                "Check what the team is actively asking about. Returns demand signals "
                "extracted from traces — the team's real needs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Optional topic filter. Omit for all demand signals."
                    }
                }
            }
        ),
        Tool(
            name="asgard_graph_query",
            description=(
                "Execute a read-only Cypher query against the Asgard Graph (FalkorDB). "
                "For structural analysis, path finding, community inspection. "
                "Write operations (CREATE, MERGE, SET, DELETE, etc.) are blocked — "
                "use asgard_graph_admin_query for writes. "
                "Call asgard_graph_schema first to understand the graph structure."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cypher": {
                        "type": "string",
                        "description": "Cypher query to execute against FalkorDB"
                    }
                },
                "required": ["cypher"]
            }
        ),
        Tool(
            name="asgard_graph_schema",
            description=(
                "Get the Asgard Graph schema — node types, edge types, properties, "
                "community structure, and example queries. Read this first before "
                "writing Cypher or exploring the graph."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="asgard_graph_trace",
            description=(
                "Record a demand signal — structural coupling write-back. "
                "Call this to let the graph know what was asked and by whom. "
                "Every trace strengthens the demand topology and helps the system "
                "detect convergence across team members."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question or topic that was explored"
                    },
                    "person": {
                        "type": "string",
                        "description": "Who is asking (team member name or alias)"
                    }
                },
                "required": ["question", "person"]
            }
        ),
        Tool(
            name="asgard_graph_neighborhood",
            description=(
                "Explore the neighborhood of a specific node — what connects to it, "
                "which communities it bridges, what edges it has. Use node_id from "
                "schema or query results."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "The node_id to explore (e.g. 'memory_layer_decisions')"
                    },
                    "hops": {
                        "type": "integer",
                        "description": "Number of hops to traverse (default 2)",
                        "default": 2
                    }
                },
                "required": ["node_id"]
            }
        ),
        Tool(
            name="asgard_graph_bridges",
            description=(
                "Find cross-community connections from a specific community. "
                "Shows which edges bridge to other communities — reveals structural "
                "gaps and coordination opportunities between domains."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "community_id": {
                        "type": "integer",
                        "description": "Community ID to inspect (use asgard_graph_schema to see community list)"
                    }
                },
                "required": ["community_id"]
            }
        ),
        Tool(
            name="asgard_graph_admin_query",
            description=(
                "Execute a Cypher query with write access (CREATE, MERGE, SET, DELETE, etc.). "
                "Requires an admin_token matching the ASGARD_ADMIN_TOKEN environment variable. "
                "Use asgard_graph_query for read-only operations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "cypher": {
                        "type": "string",
                        "description": "Cypher query to execute (read or write)"
                    },
                    "admin_token": {
                        "type": "string",
                        "description": "Admin token (must match ASGARD_ADMIN_TOKEN env var)"
                    }
                },
                "required": ["cypher", "admin_token"]
            }
        ),
    ]


def _resolve_person(arguments: dict) -> str:
    """Determine the person for this request.

    Priority:
    1. Token-authenticated identity (set by _check_auth via contextvars)
       — cannot be spoofed by the client.
    2. Client-provided 'person' argument (honor-system fallback for
       stdio transport or admin tokens).
    """
    authed = _authenticated_person.get("")
    if authed and authed != "admin":
        # Token identifies a specific person — use it, ignore client arg
        return _to_alias(authed)
    # Admin token or stdio: fall back to client-provided person
    return _to_alias(arguments.get("person", ""))


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    t0 = _time.monotonic()
    result = ""
    num_results = 0
    query_text = ""
    person = ""
    error = ""
    touched_nodes = []  # node_ids of Knowledge nodes activated by this query

    try:
        if name == "asgard_graph_ask":
            from scripts.lib.ask_asgard import ask
            query_text = arguments.get("question", "")
            person = _resolve_person(arguments)
            result = ask(query_text)
            num_results = result.count("\n")
            touched_nodes = _extract_node_ids_from_response(result)

            # Surface routed knowledge for this person
            if person and person != "unknown":
                try:
                    graph = get_graph()
                    r = graph.query(
                        f"MATCH (k:Knowledge)-[rt:ROUTED_TO]->(pc:PersonContext {{person: '{_esc(person)}'}}) "
                        f"RETURN k.label, rt.routed_at"
                    )
                    if r.result_set:
                        result += "\n\n---\n**Routed to you by Mycelium:**\n"
                        for row in r.result_set:
                            result += f"- **{row[0]}** (routed {row[1][:10]})\n"
                        result += "\n*The system detected this knowledge is relevant to your current work.*"
                except Exception:
                    pass

        elif name == "asgard_graph_demand":
            from scripts.lib.ask_asgard import ask_demand
            query_text = arguments.get("topic") or "(all)"
            result = ask_demand(arguments.get("topic"))
            num_results = result.count("\n")

        elif name == "asgard_graph_query":
            query_text = arguments.get("cypher", "")
            is_safe, reason = _is_read_only_cypher(query_text)
            if not is_safe:
                raise ValueError(
                    f"Read-only query required. {reason}. "
                    f"Use asgard_graph_admin_query for write operations."
                )
            graph = get_graph()
            raw = graph.query(query_text)
            rows = raw.result_set or []
            result = json.dumps(rows, default=str, indent=2)
            num_results = len(rows)
            # Extract node_ids from Cypher results
            touched_nodes = _extract_node_ids_from_cypher(rows)

        elif name == "asgard_graph_schema":
            query_text = "(schema request)"
            graph = get_graph()
            nodes = graph.query(
                "MATCH (n) RETURN labels(n) as type, count(n) as c ORDER BY c DESC"
            ).result_set
            edges = graph.query(
                "MATCH ()-[r]->() RETURN type(r) as rel, count(r) as c ORDER BY c DESC"
            ).result_set
            communities = graph.query(
                "MATCH (n) WHERE n.community IS NOT NULL "
                "RETURN n.community, count(n) as size, collect(n.label)[0..3] as samples "
                "ORDER BY size DESC"
            ).result_set
            total_nodes = graph.query("MATCH (n) RETURN count(n)").result_set[0][0]
            total_edges = graph.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]

            schema = {
                "graph": "asgard",
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_types": [{"type": r[0], "count": r[1]} for r in nodes],
                "edge_types": [{"type": r[0], "count": r[1]} for r in edges],
                "communities": [
                    {"id": r[0], "size": r[1], "samples": r[2]} for r in communities
                ],
                "node_properties": {
                    "Knowledge": ["label", "node_id", "community", "category", "confidence", "source_file", "file_type"],
                    "Demand": ["label", "node_id", "person", "frequency", "frustration", "gap_signal", "coverage_score"],
                    "Intent": ["label", "node_id", "domain", "graph_region", "person", "recurrence_count"],
                    "Convergence": ["label", "node_id", "convergence_type", "strength", "person_count", "persons"],
                    "Phase": ["label", "node_id", "demand_character", "dispersion", "active", "micro_phase_count"],
                    "CouplingEvent": ["label", "node_id", "tool", "person", "timestamp", "num_results"],
                },
                "example_queries": [
                    "MATCH (n) RETURN n.label, n.community, labels(n) LIMIT 20",
                    "MATCH (d:Demand) RETURN d.label, d.last_asked_by",
                    "MATCH (n)-[r]-(m) WHERE toLower(n.label) CONTAINS 'memory' RETURN n.label, type(r), m.label LIMIT 10",
                    "MATCH (n) WHERE n.community = 0 RETURN n.label ORDER BY n.label",
                    "MATCH (a)-[r]->(b) WHERE a.community <> b.community RETURN a.label, a.community, type(r), b.label, b.community LIMIT 20",
                    "MATCH (a:Demand)-[:CROSS_PERSON_DEMAND]-(b:Demand) RETURN a.label, b.label",
                    "MATCH (n)-[r]-() RETURN n.label, n.community, count(r) as degree ORDER BY degree DESC LIMIT 10",
                ],
            }
            result = json.dumps(schema, indent=2, default=str)
            num_results = len(nodes) + len(edges)

        elif name == "asgard_graph_trace":
            query_text = arguments.get("question", "")
            person = _resolve_person(arguments) or _to_alias("unknown")
            trace_demand(query_text, person)
            result = f"Demand signal recorded: '{query_text}' by {person}"
            num_results = 1

        elif name == "asgard_graph_neighborhood":
            from scripts.lib.ask_asgard import ask_neighborhood
            query_text = arguments.get("node_id", "")
            hops = arguments.get("hops", 2)
            result = ask_neighborhood(query_text, hops)
            num_results = result.count("\n")
            touched_nodes = [query_text]  # The node being explored
            touched_nodes.extend(_extract_node_ids_from_response(result))

        elif name == "asgard_graph_bridges":
            from scripts.lib.ask_asgard import ask_bridges
            community_id = arguments.get("community_id", 0)
            query_text = f"community {community_id}"
            result = ask_bridges(community_id)
            num_results = result.count("\n")
            touched_nodes = _extract_node_ids_from_response(result)

        elif name == "asgard_graph_admin_query":
            query_text = arguments.get("cypher", "")
            provided_token = arguments.get("admin_token", "")
            expected_token = os.environ.get("ASGARD_ADMIN_TOKEN", "") or os.environ.get("ASGARD_GRAPH_TOKEN", "")
            if not expected_token:
                raise ValueError(
                    "ASGARD_ADMIN_TOKEN environment variable is not set. "
                    "Admin queries are disabled."
                )
            if not secrets.compare_digest(provided_token, expected_token):
                raise ValueError("Invalid admin_token. Write access denied.")
            graph = get_graph()
            raw = graph.query(query_text)
            rows = raw.result_set or []
            result = json.dumps(rows, default=str, indent=2)
            num_results = len(rows)
            touched_nodes = _extract_node_ids_from_cypher(rows)

        else:
            result = f"Unknown tool: {name}"
            error = "unknown_tool"

    except Exception as e:
        error = str(e)
        result = f"Error: {error}"

    # MERGE an MCPQuery node for the ingestion pipeline
    latency_ms = (_time.monotonic() - t0) * 1000
    if not error:
        _merge_mcp_query_node(query_text, person, tool=name)

    # CONTINUOUS CRYSTALLIZATION: after every write, run realtime heal chain
    if not error and name == "asgard_graph_admin_query":
        try:
            _run_realtime_heal(graph)
        except Exception:
            pass  # Healing must never block the primary operation

    # Full trace + structural coupling — every interaction changes the graph
    log_trace(
        tool=name,
        query=query_text,
        response=result,
        num_results=num_results,
        latency_ms=latency_ms,
        person=person,
        error=error,
        touched_nodes=touched_nodes,
    )

    return [TextContent(type="text", text=result)]


async def main():
    parser = argparse.ArgumentParser(description="Asgard Graph MCP Server")
    parser.add_argument("--port", type=int, help="HTTP/SSE port (omit for stdio)")
    parser.add_argument(
        "--generate-tokens", metavar="OUTPUT_FILE",
        help="Generate per-person tokens YAML file and exit. "
             "Reads team from config.yaml, writes tokens to OUTPUT_FILE."
    )
    args = parser.parse_args()

    # Token generation mode — run and exit
    if args.generate_tokens:
        import yaml
        tokens = generate_tokens_for_team()
        out = {"tokens": tokens}
        outpath = Path(args.generate_tokens)
        if outpath.exists():
            print(f"ERROR: {outpath} already exists. Remove it first or pick a different path.", file=sys.stderr)
            sys.exit(1)
        outpath.parent.mkdir(parents=True, exist_ok=True)
        with open(outpath, "w") as f:
            yaml.dump(out, f, default_flow_style=False)
        print(f"Generated tokens for {len(tokens)} team members -> {outpath}", file=sys.stderr)
        print("\nPer-person .mcp.json URLs:", file=sys.stderr)
        host = os.environ.get("ASGARD_MCP_HOST", "5.78.206.137")
        port = os.environ.get("ASGARD_MCP_PORT", "6381")
        for alias, tok in sorted(tokens.items()):
            print(f"  {alias:10s}  http://{host}:{port}/mcp?token={tok}", file=sys.stderr)
        return

    if args.port:
        # SSE + Streamable HTTP transports for remote access
        from mcp.server.sse import SseServerTransport
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
        import uvicorn

        # Auth setup — load per-person tokens + admin fallback
        admin_token = os.environ.get("ASGARD_GRAPH_TOKEN", "")
        if not admin_token:
            print("ERROR: ASGARD_GRAPH_TOKEN must be set for SSE mode", file=sys.stderr)
            sys.exit(1)

        _load_person_tokens()

        sse = SseServerTransport("/messages/")
        http_session_mgr = StreamableHTTPSessionManager(
            app=server,
            stateless=True,  # Each request is independent — no session tracking needed
        )

        def _extract_token_from_scope(scope) -> str:
            """Extract bearer token from Authorization header or ?token= query param."""
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth.startswith("Bearer "):
                return auth[7:]
            qs = scope.get("query_string", b"").decode()
            for param in qs.split("&"):
                if param.startswith("token="):
                    return param[6:]
            return ""

        def _check_auth(scope) -> str | None:
            """Authenticate a request.  Returns the person's forest alias, or None if unauthorized.

            Token resolution order:
            1. Graph-native: hash token, query Person.token_hash (no secrets in graph)
            2. Per-person token from env/file (fallback for bootstrap)
            3. Admin token (ASGARD_GRAPH_TOKEN) → returns "admin"
            4. No match → returns None (unauthorized)
            """
            tok = _extract_token_from_scope(scope)
            if not tok:
                return None
            # 1. Graph-native auth: hash and query
            person = _verify_token_via_graph(tok)
            if person:
                return person
            # 2. Check per-person tokens from env/file
            person = _TOKEN_TO_PERSON.get(tok)
            if person:
                return person
            # 3. Fallback: admin token
            if tok == admin_token:
                return "admin"
            return None

        async def _send_401(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [[b"content-type", b"text/plain"]],
            })
            await send({
                "type": "http.response.body",
                "body": b"unauthorized",
            })

        async def app(scope, receive, send):
            """Raw ASGI app — routes /sse, /messages/, and /mcp with auth."""
            if scope["type"] == "lifespan":
                # Handle lifespan events — start Streamable HTTP session manager
                while True:
                    message = await receive()
                    if message["type"] == "lifespan.startup":
                        # StreamableHTTPSessionManager needs its run() context
                        # started before it can handle requests. We enter it here
                        # and hold it open for the server's lifetime.
                        http_session_mgr._run_cm = http_session_mgr.run()
                        await http_session_mgr._run_cm.__aenter__()
                        await send({"type": "lifespan.startup.complete"})
                    elif message["type"] == "lifespan.shutdown":
                        await http_session_mgr._run_cm.__aexit__(None, None, None)
                        await send({"type": "lifespan.shutdown.complete"})
                        return
                return

            if scope["type"] != "http":
                return

            path = scope.get("path", "")

            if path == "/mcp":
                # Streamable HTTP transport — preferred by newer Claude Code clients
                authed_person = _check_auth(scope)
                if authed_person is None:
                    await _send_401(scope, receive, send)
                    return
                _authenticated_person.set(authed_person)
                await http_session_mgr.handle_request(scope, receive, send)
            elif path == "/sse":
                # Legacy SSE transport — kept for backwards compatibility
                authed_person = _check_auth(scope)
                if authed_person is None:
                    await _send_401(scope, receive, send)
                    return
                _authenticated_person.set(authed_person)
                async with sse.connect_sse(scope, receive, send) as streams:
                    await server.run(
                        streams[0], streams[1], server.create_initialization_options()
                    )
            elif path.startswith("/messages"):
                authed_person = _check_auth(scope)
                if authed_person is None:
                    await _send_401(scope, receive, send)
                    return
                _authenticated_person.set(authed_person)
                await sse.handle_post_message(scope, receive, send)
            elif path == "/webhook/github":
                # GitHub webhook → ingest commits and issues in real-time
                await _handle_github_webhook(scope, receive, send)
            else:
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [[b"content-type", b"text/plain"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"not found",
                })

        async def _handle_github_webhook(scope, receive, send):
            """Handle GitHub webhook POST — ingest commits and issues into graph."""
            import hashlib as _hashlib
            import hmac as _hmac

            # Read request body
            body = b""
            while True:
                message = await receive()
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break

            # Verify webhook secret (HMAC-SHA256)
            webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
            if webhook_secret:
                headers = dict(scope.get("headers", []))
                sig_header = headers.get(b"x-hub-signature-256", b"").decode()
                expected = "sha256=" + _hmac.new(
                    webhook_secret.encode(), body, _hashlib.sha256
                ).hexdigest()
                if not _hmac.compare_digest(sig_header, expected):
                    await send({"type": "http.response.start", "status": 403,
                                "headers": [[b"content-type", b"text/plain"]]})
                    await send({"type": "http.response.body", "body": b"invalid signature"})
                    return

            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                await send({"type": "http.response.start", "status": 400,
                            "headers": [[b"content-type", b"text/plain"]]})
                await send({"type": "http.response.body", "body": b"invalid json"})
                return

            headers = dict(scope.get("headers", []))
            event_type = headers.get(b"x-github-event", b"").decode()

            ingested = 0
            print(f"[webhook] event={event_type}, payload_keys={list(payload.keys())[:5]}", file=sys.stderr)
            try:
                graph = get_graph()
                print(f"[webhook] graph connected", file=sys.stderr)

                if event_type == "push":
                    repo = payload.get("repository", {}).get("name", "unknown")
                    for commit in payload.get("commits", []):
                        sha = commit.get("id", "")[:7]
                        msg = commit.get("message", "").split("\n")[0][:200]
                        author = commit.get("author", {}).get("name", "")
                        files = ",".join(
                            commit.get("added", []) + commit.get("modified", []) + commit.get("removed", [])
                        )[:500]
                        ts = commit.get("timestamp", "")
                        node_id = f"commit-{_esc(repo)}-{_esc(sha)}"
                        graph.query(
                            f"MERGE (c:Commit {{node_id: '{_esc(node_id)}'}}) "
                            f"SET c.label = '{_esc(msg)}', c.sha = '{_esc(sha)}', "
                            f"c.repo = '{_esc(repo)}', c.author = '{_esc(author)}', "
                            f"c.timestamp = '{_esc(ts)}', c.files_changed = '{_esc(files)}', "
                            f"c.source = 'github-webhook', c.file_type = 'commit'"
                        )
                        ingested += 1

                elif event_type == "issues":
                    action = payload.get("action", "")
                    issue = payload.get("issue", {})
                    repo = payload.get("repository", {}).get("name", "unknown")
                    number = issue.get("number", 0)
                    title = issue.get("title", "")[:200]
                    state = issue.get("state", "")
                    issue_body = issue.get("body", "")[:500] if issue.get("body") else ""
                    node_id = f"issue-{_esc(repo)}-{number}"
                    graph.query(
                        f"MERGE (i:Issue {{node_id: '{_esc(node_id)}'}}) "
                        f"SET i.label = '{_esc(title)}', i.number = {number}, "
                        f"i.repo = '{_esc(repo)}', i.state = '{_esc(state)}', "
                        f"i.body = '{_esc(issue_body)}', "
                        f"i.source = 'github-webhook', i.file_type = 'issue'"
                    )
                    ingested += 1

                elif event_type == "pull_request":
                    pr = payload.get("pull_request", {})
                    repo = payload.get("repository", {}).get("name", "unknown")
                    number = pr.get("number", 0)
                    title = pr.get("title", "")[:200]
                    state = pr.get("state", "")
                    node_id = f"issue-{_esc(repo)}-{number}"
                    graph.query(
                        f"MERGE (i:Issue {{node_id: '{_esc(node_id)}'}}) "
                        f"SET i.label = '{_esc(title)}', i.number = {number}, "
                        f"i.repo = '{_esc(repo)}', i.state = '{_esc(state)}', "
                        f"i.source = 'github-webhook', i.file_type = 'issue'"
                    )
                    ingested += 1

            except Exception as e:
                import traceback
                print(f"[webhook] Error: {str(e)[:200]}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

            response = json.dumps({"ok": True, "ingested": ingested}).encode()
            await send({"type": "http.response.start", "status": 200,
                        "headers": [[b"content-type", b"application/json"]]})
            await send({"type": "http.response.body", "body": response})

        print(f"Asgard Graph MCP server starting on port {args.port} (SSE + Streamable HTTP)", file=sys.stderr)
        config = uvicorn.Config(app, host="0.0.0.0", port=args.port, log_level="info")
        s = uvicorn.Server(config)
        await s.serve()
    else:
        # Stdio transport for local use
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
