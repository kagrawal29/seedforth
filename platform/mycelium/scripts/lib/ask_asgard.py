"""
Ask Asgard — natural language interface to the knowledge graph.

Agents speak to the graph in plain English. No Cypher. No file reads.
The graph answers with relevant nodes, edges, and community context.

This is the coupling mechanism. Agents ask, the graph answers.
Directives tell agents WHEN to ask. This module handles HOW.

Usage:
    from scripts.lib.ask_asgard import ask

    # Agent asks a question
    answer = ask("what decisions affect the API layer?")
    answer = ask("is there demand for notification system knowledge?")
    answer = ask("what connects Trigger.dev to the memory layer?")
    answer = ask("who is working near fund-level configuration?")

Returns a text block the agent can reason about. ~200-500 tokens.
If FalkorDB is down, returns empty string (non-fatal).
"""

import os
import re
from typing import Optional

try:
    from scripts.lib.graph_observer import log_graph_interaction as _log
except ImportError:
    try:
        from graph_observer import log_graph_interaction as _log  # type: ignore
    except ImportError:
        def _log(*args, **kwargs):  # type: ignore
            pass

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"


def _get_graph():
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        return db.select_graph(GRAPH_NAME)
    except Exception:
        return None


def _escape(s):
    if s is None:
        return ""
    return str(s).replace("'", "\\'").replace("\\", "\\\\")


def _extract_keywords(question: str) -> list[str]:
    """Extract meaningful keywords from a natural language question."""
    stop_words = {
        "what", "which", "who", "how", "does", "is", "are", "the", "a", "an",
        "in", "on", "at", "to", "for", "of", "with", "and", "or", "not",
        "this", "that", "there", "about", "from", "any", "has", "have",
        "been", "being", "was", "were", "will", "would", "should", "could",
        "do", "did", "can", "may", "might", "shall", "need", "work",
        "working", "connect", "related", "affect", "between",
    }
    words = re.findall(r'[a-zA-Z][\w-]+', question.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]


def ask(question: str, max_results: int = 10) -> str:
    """
    Ask Asgard a question in natural language.
    Returns a text block with relevant graph context.

    The search strategy:
    1. Extract keywords from the question
    2. Find nodes whose labels match any keyword (fuzzy)
    3. For each matched node, get its immediate neighborhood
    4. Include community context
    5. Include demand signals if relevant
    6. Format as readable text

    This is NOT vector search. It's keyword + graph traversal.
    Fast, deterministic, no LLM cost. Good enough for directive-driven
    on-demand queries where the agent already knows roughly what it's asking.
    """
    graph = _get_graph()
    if not graph:
        return ""

    # FAST PATH: check NLQuery router first — stored patterns → stored Cypher
    # No LLM, no keyword heuristics, just pattern matching against known questions
    try:
        q_lower = question.lower()
        nl_result = graph.query(
            "MATCH (q:NLQuery) "
            "WITH q, [p IN split(q.patterns, ',') WHERE toLower($q) CONTAINS toLower(p)] AS matches "
            "WHERE size(matches) > 0 "
            "RETURN q.node_id, q.cypher, q.answer_template, size(matches) AS score "
            "ORDER BY score DESC LIMIT 1",
            params={"q": q_lower}
        )
        if not nl_result.result_set:
            # FalkorDB may not support params — fallback to inline
            conditions = []
            for kw in _extract_keywords(question):
                conditions.append(f"q.patterns CONTAINS '{_escape(kw)}'")
            if conditions:
                nl_result = graph.query(
                    f"MATCH (q:NLQuery) WHERE {' OR '.join(conditions)} "
                    f"RETURN q.node_id, q.cypher, q.answer_template LIMIT 1"
                )
        if nl_result.result_set and nl_result.result_set[0][1]:
            matched_cypher = nl_result.result_set[0][1]
            template = nl_result.result_set[0][2] or ""
            try:
                cypher_result = graph.query(matched_cypher)
                lines = [f"## Asgard answers: {question}\n"]
                if template:
                    lines.append(f"*{template}*\n")
                for row in (cypher_result.result_set or [])[:10]:
                    lines.append("- " + " | ".join(str(v) for v in row))
                result_text = "\n".join(lines)
                _log("ask_asgard", "ask_nlq", question, num_results=len(cypher_result.result_set or []), response_bytes=len(result_text.encode()))
                return result_text
            except Exception:
                pass  # Fall through to keyword search
    except Exception:
        pass  # Fall through to keyword search

    keywords = _extract_keywords(question)
    if not keywords:
        return ""

    lines = [f"## Asgard answers: {question}\n"]

    # Build a WHERE clause that matches any keyword in node labels
    conditions = " OR ".join(
        f"toLower(n.label) CONTAINS '{_escape(kw)}'" for kw in keywords
    )

    # Find matching nodes
    try:
        result = graph.query(
            f"MATCH (n) WHERE {conditions} "
            f"RETURN n.label, n.node_id, n.community, n.category, n.confidence, labels(n) "
            f"LIMIT {max_results}"
        )
        matched_nodes = result.result_set or []
    except Exception:
        matched_nodes = []

    if not matched_nodes:
        lines.append("No matching nodes found in the graph.\n")
        result_text = "\n".join(lines)
        _log("ask_asgard", "ask", question, num_results=0, response_bytes=len(result_text.encode()))
        return result_text

    # Report matched nodes
    lines.append(f"Found {len(matched_nodes)} relevant nodes:\n")
    node_ids = []
    for row in matched_nodes:
        label, node_id, community, category, confidence, node_labels = row
        node_ids.append(node_id)
        meta = []
        if category:
            meta.append(f"cat: {category}")
        if confidence:
            meta.append(f"conf: {confidence}")
        if community is not None:
            meta.append(f"community: {community}")
        meta_str = f" ({', '.join(meta)})" if meta else ""
        node_type = node_labels[0] if node_labels else "unknown"
        lines.append(f"- **{label}**{meta_str} [{node_type}]")

    # Get neighborhood for top 3 matched nodes
    lines.append(f"\n### Connections\n")
    for node_id in node_ids[:3]:
        try:
            result = graph.query(
                f"MATCH (n {{node_id: '{_escape(node_id)}'}})-[r]-(m) "
                f"RETURN n.label, type(r), m.label, m.community "
                f"LIMIT 8"
            )
            if result.result_set:
                for row in result.result_set:
                    lines.append(f"- {row[0]} --{row[1]}--> {row[2]} (community {row[3]})")
        except Exception:
            pass

    # Check demand signals
    demand_matches = []
    for kw in keywords:
        try:
            result = graph.query(
                f"MATCH (d:Demand) WHERE toLower(d.label) CONTAINS '{_escape(kw)}' "
                f"RETURN d.label LIMIT 3"
            )
            for row in (result.result_set or []):
                if row[0] not in demand_matches:
                    demand_matches.append(row[0])
        except Exception:
            pass

    if demand_matches:
        lines.append(f"\n### Active demand (team is asking about this)")
        for d in demand_matches:
            lines.append(f"- {d}")

    # Cross-person demand
    try:
        result = graph.query(
            "MATCH (a:Demand)-[:CROSS_PERSON_DEMAND]-(b:Demand) "
            "RETURN a.label, b.label LIMIT 3"
        )
        if result.result_set:
            lines.append(f"\n### Cross-person connections")
            for row in result.result_set:
                lines.append(f"- {row[0]} <-> {row[1]}")
    except Exception:
        pass

    result_text = "\n".join(lines)
    _log("ask_asgard", "ask", question, num_results=len(node_ids), response_bytes=len(result_text.encode()))
    return result_text


def ask_neighborhood(node_id: str, hops: int = 2) -> str:
    """Get the neighborhood of a specific node."""
    graph = _get_graph()
    if not graph:
        return ""

    lines = [f"## Neighborhood of {node_id} ({hops} hops)\n"]

    try:
        # Get the node itself
        result = graph.query(
            f"MATCH (n {{node_id: '{_escape(node_id)}'}}) "
            f"RETURN n.label, n.community, n.category, n.confidence"
        )
        if result.result_set:
            row = result.result_set[0]
            lines.append(f"**{row[0]}** (community {row[1]}, {row[2]}, {row[3]})\n")

        # Get connections
        result = graph.query(
            f"MATCH (n {{node_id: '{_escape(node_id)}'}})-[r]-(m) "
            f"RETURN type(r), m.label, m.node_id, m.community "
            f"ORDER BY m.community LIMIT 15"
        )
        if result.result_set:
            lines.append("Connections:")
            for row in result.result_set:
                lines.append(f"  --{row[0]}--> {row[1]} (community {row[3]})")

    except Exception as e:
        lines.append(f"Error: {e}")

    result_text = "\n".join(lines)
    num_results = len(result_text.splitlines()) - 1  # rough proxy
    _log("ask_asgard", "ask_neighborhood", node_id, num_results=num_results, response_bytes=len(result_text.encode()))
    return result_text


def ask_demand(topic: Optional[str] = None) -> str:
    """Check what the team is demanding."""
    graph = _get_graph()
    if not graph:
        return ""

    lines = ["## Team demand signals\n"]

    if topic:
        kw = _escape(topic.lower())
        result = graph.query(
            f"MATCH (d:Demand) WHERE toLower(d.label) CONTAINS '{kw}' "
            f"RETURN d.label"
        )
    else:
        result = graph.query("MATCH (d:Demand) RETURN d.label")

    if result.result_set:
        for row in result.result_set:
            lines.append(f"- {row[0]}")
    else:
        lines.append("No demand signals" + (f" matching '{topic}'" if topic else "") + ".")

    # Cross-person
    result = graph.query(
        "MATCH (a:Demand)-[:CROSS_PERSON_DEMAND]-(b:Demand) "
        "RETURN a.label, b.label LIMIT 5"
    )
    if result.result_set:
        lines.append("\nCross-person demand:")
        for row in result.result_set:
            lines.append(f"  {row[0]} <-> {row[1]}")

    result_text = "\n".join(lines)
    num_results = max(0, len(result_text.splitlines()) - 1)
    _log("ask_asgard", "ask_demand", topic or "(all)", num_results=num_results, response_bytes=len(result_text.encode()))
    return result_text


def ask_community(community_id: int) -> str:
    """Get all nodes in a community."""
    graph = _get_graph()
    if not graph:
        return ""

    lines = [f"## Community {community_id}\n"]

    result = graph.query(
        f"MATCH (n) WHERE n.community = {community_id} "
        f"RETURN n.label, n.node_id, labels(n) ORDER BY n.label"
    )
    num_results = 0
    if result.result_set:
        num_results = len(result.result_set)
        lines.append(f"{num_results} nodes:\n")
        for row in result.result_set:
            node_type = row[2][0] if row[2] else "unknown"
            lines.append(f"- {row[0]} [{node_type}]")

    result_text = "\n".join(lines)
    _log("ask_asgard", "ask_community", str(community_id), num_results=num_results, response_bytes=len(result_text.encode()))
    return result_text


def ask_bridges(community_id: int) -> str:
    """Find cross-community connections from a specific community."""
    graph = _get_graph()
    if not graph:
        return ""

    lines = [f"## Bridges from Community {community_id}\n"]

    # Outbound bridges
    try:
        result = graph.query(
            f"MATCH (a)-[r]->(b) "
            f"WHERE a.community = {community_id} AND b.community <> {community_id} "
            f"RETURN a.label, type(r), b.label, b.community "
            f"ORDER BY b.community LIMIT 20"
        )
        outbound = result.result_set or []
    except Exception:
        outbound = []

    # Inbound bridges
    try:
        result = graph.query(
            f"MATCH (a)-[r]->(b) "
            f"WHERE b.community = {community_id} AND a.community <> {community_id} "
            f"RETURN a.label, a.community, type(r), b.label "
            f"ORDER BY a.community LIMIT 20"
        )
        inbound = result.result_set or []
    except Exception:
        inbound = []

    if outbound:
        lines.append(f"### Outbound ({len(outbound)} edges)")
        for row in outbound:
            lines.append(f"- {row[0]} --{row[1]}--> {row[2]} (community {row[3]})")
        lines.append("")

    if inbound:
        lines.append(f"### Inbound ({len(inbound)} edges)")
        for row in inbound:
            lines.append(f"- {row[0]} (community {row[1]}) --{row[2]}--> {row[3]}")
        lines.append("")

    if not outbound and not inbound:
        lines.append("No cross-community bridges found.")

    # Target communities summary
    if outbound:
        targets = {}
        for row in outbound:
            c = row[3]
            targets[c] = targets.get(c, 0) + 1
        lines.append("### Bridge targets")
        for c, count in sorted(targets.items(), key=lambda x: -x[1]):
            lines.append(f"- Community {c}: {count} edges")

    num_results = len(outbound) + len(inbound)
    result_text = "\n".join(lines)
    _log("ask_asgard", "ask_bridges", str(community_id), num_results=num_results, response_bytes=len(result_text.encode()))
    return result_text
