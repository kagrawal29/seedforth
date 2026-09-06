#!/usr/bin/env python3
"""
Generate knowledge-graph-map.md from the live FalkorDB graph.

Replaces the static JSON-based community map generator. Queries FalkorDB via Graphiti
to get entities, edges, and communities, then produces the same markdown format used
by the distribution system.

Usage:
    python3 scripts/generate-community-map-live.py

Output:
    distribution/shared-rules/knowledge-graph-map.md

Requires:
    - FalkorDB running with a seeded graph
    - OPENAI_API_KEY set
    - pip install graphiti-core[falkordb] networkx
"""

import asyncio
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.graph_client import (
    get_graphiti,
    get_all_entity_nodes,
    get_all_entity_edges,
    get_community_nodes,
    close_graphiti,
)

OUTPUT_PATH = REPO_ROOT / "distribution" / "shared-rules" / "knowledge-graph-map.md"


def build_networkx_graph(nodes: list, edges: list):
    """Build a networkx graph from entity nodes and edges."""
    import networkx as nx

    G = nx.Graph()
    for node in nodes:
        G.add_node(node["name"], summary=node.get("summary", ""), uuid=node.get("uuid", ""))
    for edge in edges:
        if edge["source"] and edge["target"]:
            G.add_edge(edge["source"], edge["target"], fact=edge.get("fact", ""))
    return G


def detect_communities_louvain(G):
    """Detect communities using Louvain method. Returns {node_name: community_id}."""
    if len(G.nodes) == 0:
        return {}

    try:
        from networkx.algorithms.community import louvain_communities
        communities = louvain_communities(G, seed=42)
        mapping = {}
        for i, community in enumerate(communities):
            for node in community:
                mapping[node] = i
        return mapping
    except ImportError:
        # Fallback: greedy modularity
        from networkx.algorithms.community import greedy_modularity_communities
        communities = greedy_modularity_communities(G)
        mapping = {}
        for i, community in enumerate(communities):
            for node in community:
                mapping[node] = i
        return mapping


def find_god_nodes(G, top_n: int = 5) -> list:
    """Find nodes with highest degree centrality (most connections)."""
    if len(G.nodes) == 0:
        return []
    degree = dict(G.degree())
    sorted_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)
    return sorted_nodes[:top_n]


def find_bridge_nodes(G, community_map: dict) -> list:
    """Find nodes that connect different communities."""
    bridges = []
    for node in G.nodes:
        if node not in community_map:
            continue
        node_community = community_map[node]
        neighbor_communities = set()
        for neighbor in G.neighbors(node):
            if neighbor in community_map:
                neighbor_communities.add(community_map[neighbor])
        # A bridge connects 2+ communities beyond its own
        other_communities = neighbor_communities - {node_community}
        if len(other_communities) >= 2:
            bridges.append((node, len(other_communities), sorted(other_communities)))
    bridges.sort(key=lambda x: x[1], reverse=True)
    return bridges[:10]


def find_cross_cutting_patterns(edges: list, community_map: dict) -> list:
    """Find edge facts that cross community boundaries."""
    cross_edges = []
    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if src in community_map and tgt in community_map:
            if community_map[src] != community_map[tgt]:
                cross_edges.append(edge)
    return cross_edges


def generate_markdown(
    nodes: list,
    edges: list,
    communities_from_db: list,
    community_map: dict,
    god_nodes: list,
    bridge_nodes: list,
    cross_patterns: list,
    G,
) -> str:
    """Generate the knowledge-graph-map.md content."""
    import networkx as nx

    lines = []
    lines.append("# Knowledge Graph Map (Live)")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Source: FalkorDB live graph")
    lines.append(f"Entities: {len(nodes)} | Relationships: {len(edges)}")
    lines.append("")

    # Communities section
    lines.append("## Communities")
    lines.append("")

    if communities_from_db:
        # Use Graphiti's built-in communities
        for i, comm in enumerate(communities_from_db):
            name = comm.get("name", f"Community {i}")
            summary = comm.get("summary", "No summary available")
            lines.append(f"### {name}")
            lines.append(f"{summary}")
            lines.append("")
    elif community_map:
        # Use networkx-detected communities
        community_members = defaultdict(list)
        for node_name, comm_id in community_map.items():
            community_members[comm_id].append(node_name)

        for comm_id in sorted(community_members.keys()):
            members = sorted(community_members[comm_id])
            lines.append(f"### Cluster {comm_id} ({len(members)} entities)")
            lines.append(f"Members: {', '.join(members)}")
            lines.append("")
    else:
        lines.append("No communities detected.")
        lines.append("")

    # God nodes section
    lines.append("## High-Connectivity Nodes (God Nodes)")
    lines.append("")
    if god_nodes:
        for name, degree in god_nodes:
            summary = ""
            for n in nodes:
                if n["name"] == name:
                    summary = (n.get("summary") or "")[:120]
                    break
            lines.append(f"- **{name}** ({degree} connections) -- {summary}")
        lines.append("")
    else:
        lines.append("No high-connectivity nodes found.")
        lines.append("")

    # Bridge nodes section
    lines.append("## Bridge Nodes")
    lines.append("")
    if bridge_nodes:
        lines.append("Entities connecting multiple communities:")
        lines.append("")
        for name, count, comm_ids in bridge_nodes:
            lines.append(f"- **{name}** bridges {count + 1} communities")
        lines.append("")
    else:
        lines.append("No bridge nodes identified.")
        lines.append("")

    # Cross-cutting patterns
    lines.append("## Cross-Cutting Patterns")
    lines.append("")
    if cross_patterns:
        lines.append("Relationships that span community boundaries:")
        lines.append("")
        for edge in cross_patterns[:15]:
            fact = edge.get("fact", "related to")
            lines.append(f"- {edge['source']} -> {edge['target']}: {fact}")
        lines.append("")
    else:
        lines.append("No cross-cutting patterns found.")
        lines.append("")

    # Stats
    lines.append("## Graph Statistics")
    lines.append("")
    if G and len(G.nodes) > 0:
        density = nx.density(G)
        components = nx.number_connected_components(G)
        lines.append(f"- Density: {density:.4f}")
        lines.append(f"- Connected components: {components}")
        lines.append(f"- Average degree: {sum(dict(G.degree()).values()) / len(G.nodes):.1f}")
    lines.append("")

    return "\n".join(lines)


async def main():
    print("=== Generating Community Map from Live Graph ===\n")

    try:
        graphiti = await get_graphiti()
    except EnvironmentError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not connect to FalkorDB: {e}")
        sys.exit(1)

    print("Fetching entities...")
    nodes = await get_all_entity_nodes(graphiti)
    print(f"  Found {len(nodes)} entity nodes")

    print("Fetching relationships...")
    edges = await get_all_entity_edges(graphiti)
    print(f"  Found {len(edges)} entity edges")

    print("Fetching communities...")
    communities_from_db = await get_community_nodes(graphiti)
    print(f"  Found {len(communities_from_db)} community nodes")

    # Build networkx graph for analysis
    G = build_networkx_graph(nodes, edges)

    # Community detection (use DB communities if available, else networkx)
    if communities_from_db:
        print("Using Graphiti built-in communities")
        community_map = {}
    else:
        print("Running Louvain community detection via networkx...")
        community_map = detect_communities_louvain(G)

    god_nodes = find_god_nodes(G)
    bridge_nodes = find_bridge_nodes(G, community_map)
    cross_patterns = find_cross_cutting_patterns(edges, community_map)

    markdown = generate_markdown(
        nodes, edges, communities_from_db, community_map,
        god_nodes, bridge_nodes, cross_patterns, G,
    )

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")
    print(f"\nWritten to {OUTPUT_PATH}")

    print(f"\nSummary:")
    print(f"  Entities: {len(nodes)}")
    print(f"  Relationships: {len(edges)}")
    print(f"  Communities: {len(communities_from_db) or len(set(community_map.values()))}")
    print(f"  God nodes: {len(god_nodes)}")
    print(f"  Bridge nodes: {len(bridge_nodes)}")

    await close_graphiti(graphiti)


if __name__ == "__main__":
    asyncio.run(main())
