"""
Graph Context Generator — injects graph intelligence into agent prompts.

The agents don't query the graph directly. This module queries FalkorDB
and produces text blocks that get appended to agent prompts. The coupling
happens through language, not through API calls.

This is how the graph speaks to the agents.

Usage:
    from scripts.lib.graph_context import (
        synthesis_context,
        heimdall_context,
        audit_context,
    )

    # In synthesis-agent prompt:
    prompt += synthesis_context(entry_id="memory-layer-decisions")

    # In Heimdall prompt:
    prompt += heimdall_context(entry_id="new-entry-to-evaluate")

    # In pre-dist audit prompt:
    prompt += audit_context()
"""

import os
import json
from typing import Optional

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"


def _get_graph():
    """Connect to FalkorDB. Returns None if unavailable."""
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        return db.select_graph(GRAPH_NAME)
    except Exception:
        return None


def _query(graph, cypher: str) -> list:
    """Run a Cypher query, return result_set or empty list."""
    try:
        result = graph.query(cypher)
        return result.result_set or []
    except Exception:
        return []


def synthesis_context(entry_ids: Optional[list[str]] = None) -> str:
    """
    Graph context for the synthesis agent.

    Provides:
    - Community structure (what communities exist, their themes)
    - Neighborhood of entries being created/updated
    - Demand signals (what the team is asking about)
    - Cross-person demand connections
    """
    graph = _get_graph()
    if not graph:
        return "\n\n## Graph Context\nFalkorDB is not available. Proceed without graph context.\n"

    lines = ["\n\n## Graph Context (from Asgard — live FalkorDB)"]
    lines.append("Use this to find connections, avoid duplicates, and detect cross-pollination.\n")

    # Community overview
    rows = _query(graph,
        "MATCH (n:Knowledge) WHERE n.community IS NOT NULL "
        "RETURN n.community, count(n) as size, collect(n.label)[0..3] as samples "
        "ORDER BY size DESC")
    if rows:
        lines.append("### Communities")
        for row in rows:
            samples = ", ".join(str(s) for s in row[2]) if row[2] else ""
            lines.append(f"- Community {row[0]} ({row[1]} nodes): {samples}")
        lines.append("")

    # Demand signals — what the team needs
    rows = _query(graph,
        "MATCH (d:Demand) RETURN d.label, d.node_id")
    if rows:
        lines.append("### Active Demand (team needs)")
        for row in rows:
            lines.append(f"- {row[0]}")
        lines.append("")

    # Cross-person demand
    rows = _query(graph,
        "MATCH (a:Demand)-[:CROSS_PERSON_DEMAND]-(b:Demand) "
        "RETURN a.label, b.label LIMIT 5")
    if rows:
        lines.append("### Cross-Person Connections")
        for row in rows:
            lines.append(f"- {row[0]} <-> {row[1]}")
        lines.append("")

    # God nodes (most connected — don't duplicate these)
    rows = _query(graph,
        "MATCH (n:Knowledge)-[r]-() "
        "RETURN n.label, n.node_id, count(r) as degree "
        "ORDER BY degree DESC LIMIT 5")
    if rows:
        lines.append("### Most Connected Nodes (avoid duplicating)")
        for row in rows:
            lines.append(f"- {row[0]} ({row[2]} edges)")
        lines.append("")

    # If specific entries mentioned, show their neighborhood
    if entry_ids:
        for eid in entry_ids[:3]:
            rows = _query(graph,
                f"MATCH (n {{node_id: '{eid}'}})-[r]-(m) "
                f"RETURN n.label, type(r), m.label, m.community LIMIT 8")
            if rows:
                lines.append(f"### Neighborhood of '{eid}'")
                for row in rows:
                    lines.append(f"  {row[0]} --{row[1]}--> {row[2]} (community {row[3]})")
                lines.append("")

    return "\n".join(lines)


def heimdall_context(entry_id: Optional[str] = None) -> str:
    """
    Graph context for Heimdall (evaluation agent).

    Provides:
    - Graph distance to nearest similar node (uniqueness check)
    - Community the entry would join
    - Demand evidence (did anyone ask about this?)
    - Node centrality context (if updating a high-centrality node, flag risk)
    """
    graph = _get_graph()
    if not graph:
        return "\n\n## Graph Topology Context\nFalkorDB unavailable. Evaluate without graph.\n"

    lines = ["\n\n## Graph Topology Context (from Asgard)"]
    lines.append("Use this for uniqueness, demand evidence, and risk assessment.\n")

    # Demand evidence
    rows = _query(graph, "MATCH (d:Demand) RETURN d.label")
    if rows:
        lines.append("### What the team is asking about (demand nodes)")
        for row in rows:
            lines.append(f"- {row[0]}")
        lines.append("")
        lines.append("If the entry being evaluated ANSWERS one of these demands, that is strong evidence for DISTRIBUTE.")
        lines.append("")

    # Unanswered demands
    rows = _query(graph,
        "MATCH (d:Demand)-[:UNANSWERED_NEAR]->(k:Knowledge) "
        "RETURN d.label, k.label LIMIT 5")
    if rows:
        lines.append("### Unanswered demands (gaps in knowledge)")
        for row in rows:
            lines.append(f"- '{row[0]}' is near '{row[1]}' but not answered")
        lines.append("")

    # High-centrality nodes (higher risk if these change)
    rows = _query(graph,
        "MATCH (n:Knowledge)-[r]-() "
        "RETURN n.label, n.node_id, count(r) as degree "
        "ORDER BY degree DESC LIMIT 5")
    if rows:
        lines.append("### High-centrality nodes (changes here have blast radius)")
        for row in rows:
            lines.append(f"- {row[0]}: {row[2]} edges (modifying this requires strong evidence)")
        lines.append("")

    # Graph stats for context
    node_count = _query(graph, "MATCH (n:Knowledge) RETURN count(n)")
    edge_count = _query(graph, "MATCH ()-[r]->() RETURN count(r)")
    demand_count = _query(graph, "MATCH (d:Demand) RETURN count(d)")
    if node_count and edge_count:
        lines.append(f"### Graph stats: {node_count[0][0]} knowledge nodes, {edge_count[0][0]} edges, {demand_count[0][0] if demand_count else 0} demand signals")
        lines.append("")

    return "\n".join(lines)


def audit_context() -> str:
    """
    Graph context for pre-distribution audit.

    Provides:
    - Graph health metrics
    - Stale communities (zero demand)
    - Community balance
    - Whether community map matches current graph state
    """
    graph = _get_graph()
    if not graph:
        return "\n\n## Graph Health Context\nFalkorDB unavailable. Audit without graph health.\n"

    lines = ["\n\n## Graph Health Context (from Asgard)"]

    # Overall stats
    nodes = _query(graph, "MATCH (n) RETURN count(n)")[0][0]
    edges = _query(graph, "MATCH ()-[r]->() RETURN count(r)")[0][0]
    knowledge = _query(graph, "MATCH (n:Knowledge) RETURN count(n)")[0][0]
    demands = _query(graph, "MATCH (d:Demand) RETURN count(d)")[0][0]

    lines.append(f"- Total: {nodes} nodes, {edges} edges")
    lines.append(f"- Knowledge: {knowledge}, Demand: {demands}")
    lines.append(f"- Edge/node ratio: {edges/max(nodes,1):.2f} (target: 1.5-3.0)")
    lines.append(f"- Demand coverage: {demands}/{knowledge} = {demands/max(knowledge,1)*100:.0f}% of knowledge has demand signal")
    lines.append("")

    # Community sizes
    rows = _query(graph,
        "MATCH (n:Knowledge) WHERE n.community IS NOT NULL "
        "RETURN n.community, count(n) as size ORDER BY size DESC")
    if rows:
        lines.append("### Community balance")
        for row in rows:
            lines.append(f"- Community {row[0]}: {row[1]} nodes")
        lines.append("")

    # Nodes with no edges (orphans)
    orphans = _query(graph,
        "MATCH (n:Knowledge) WHERE NOT (n)-[]-() RETURN count(n)")
    if orphans and orphans[0][0] > 0:
        lines.append(f"### WARNING: {orphans[0][0]} orphan nodes (no edges)")
        lines.append("")

    # Confidence distribution
    rows = _query(graph,
        "MATCH (n:Knowledge) WHERE n.confidence IS NOT NULL "
        "RETURN n.confidence, count(n) ORDER BY count(n) DESC")
    if rows:
        lines.append("### Confidence distribution")
        for row in rows:
            lines.append(f"- {row[0]}: {row[1]} entries")
        lines.append("")

    return "\n".join(lines)


def demand_context_for_person(person_name: str) -> str:
    """
    Generate demand-aware context for a specific person.
    Used by context-gen agent.
    """
    graph = _get_graph()
    if not graph:
        return ""

    lines = [f"### Graph context for {person_name}"]

    # This person's demand signals (if any exist as nodes)
    # Currently demand nodes don't have person attribution in the graph
    # but we can infer from the demand engine output files
    rows = _query(graph, "MATCH (d:Demand) RETURN d.label, d.node_id")
    if rows:
        lines.append("Active team demand signals:")
        for row in rows:
            lines.append(f"  - {row[0]}")

    # Cross-person connections
    rows = _query(graph,
        "MATCH (a:Demand)-[:CROSS_PERSON_DEMAND]-(b:Demand) "
        "RETURN a.label, b.label LIMIT 5")
    if rows:
        lines.append("Cross-person demand connections:")
        for row in rows:
            lines.append(f"  - {row[0]} <-> {row[1]}")

    return "\n".join(lines)
