"""
Shared Graphiti client for FalkorDB-backed knowledge graph operations.

All graph operations go through this module. Reads connection settings from config.yaml.

Usage:
    from scripts.lib.graph_client import get_graphiti, sync_entry_to_graph, close_graphiti

    graphiti = await get_graphiti()
    await sync_entry_to_graph(graphiti, Path("knowledge/patterns/some-entry.md"))
    await close_graphiti(graphiti)
"""

from __future__ import annotations

import os
import re
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphiti_core import Graphiti

from scripts.lib.config import load_config


def _import_graphiti():
    """Lazy import of graphiti_core to avoid import errors when not installed."""
    from graphiti_core import Graphiti
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    from graphiti_core.nodes import EpisodeType
    return Graphiti, FalkorDriver, EpisodeType


def _get_graph_config():
    """Return the graph section from config.yaml."""
    config = load_config()
    graph = config.get("graph")
    if not graph:
        raise ValueError("Missing 'graph' section in config.yaml")
    return graph


def _parse_falkordb_url(url: str) -> dict:
    """Parse a redis:// or bolt:// URL into host, port components."""
    stripped = re.sub(r"^(redis|bolt)://", "", url)
    parts = stripped.split(":")
    host = parts[0] if parts[0] else "localhost"
    port = int(parts[1]) if len(parts) > 1 else 6379
    return {"host": host, "port": port}


async def get_graphiti(database: str = "maverick-meta") -> Graphiti:
    """
    Create and return a Graphiti instance connected to FalkorDB.

    Reads falkordb_url from config.yaml graph section.
    Requires OPENAI_API_KEY env var for LLM-powered entity extraction.
    """
    Graphiti, FalkorDriver, _ = _import_graphiti()

    if not os.environ.get("OPENAI_API_KEY"):
        raise EnvironmentError(
            "OPENAI_API_KEY must be set. Graphiti uses OpenAI for entity extraction."
        )

    graph_config = _get_graph_config()
    url = graph_config.get("falkordb_url", "redis://localhost:6380")
    conn = _parse_falkordb_url(url)

    driver = FalkorDriver(
        host=conn["host"],
        port=conn["port"],
        database=database,
    )

    graphiti = Graphiti(graph_driver=driver)
    await graphiti.build_indices_and_constraints()
    return graphiti


def parse_knowledge_entry(entry_path: Path) -> dict:
    """
    Parse a knowledge entry markdown file.

    Returns dict with:
        frontmatter: dict of YAML frontmatter fields
        title: str from the first # heading
        what_section: str content under ## What heading
        body: str full markdown body (after frontmatter)
    """
    text = entry_path.read_text(encoding="utf-8")

    # Split frontmatter from body
    frontmatter = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()

    # Extract title from first heading
    title = ""
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    # Extract ## What section
    what_section = ""
    what_match = re.search(
        r"^##\s+What\s*\n(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL
    )
    if what_match:
        what_section = what_match.group(1).strip()

    return {
        "frontmatter": frontmatter,
        "title": title,
        "what_section": what_section,
        "body": body,
    }


def _build_episode_body(parsed: dict) -> str:
    """Build an episode body string from a parsed knowledge entry."""
    fm = parsed["frontmatter"]
    parts = []

    if parsed["title"]:
        parts.append(f"Title: {parsed['title']}")

    if fm.get("category"):
        parts.append(f"Category: {fm['category']}")

    if fm.get("type"):
        parts.append(f"Type: {fm['type']}")

    if fm.get("confidence"):
        parts.append(f"Confidence: {fm['confidence']}")

    if fm.get("tags"):
        parts.append(f"Tags: {', '.join(fm['tags'])}")

    if fm.get("relevant-when"):
        parts.append(f"Relevant when: {fm['relevant-when']}")

    if parsed["what_section"]:
        parts.append(f"\n{parsed['what_section']}")
    elif parsed["body"]:
        # Fallback: use first 1500 chars of body
        parts.append(f"\n{parsed['body'][:1500]}")

    return "\n".join(parts)


def _get_reference_time(fm: dict) -> datetime:
    """Extract reference time from frontmatter dates."""
    for field in ["last-validated", "discovered"]:
        val = fm.get(field)
        if val:
            if isinstance(val, datetime):
                if val.tzinfo is None:
                    return val.replace(tzinfo=timezone.utc)
                return val
            try:
                dt = datetime.strptime(str(val), "%Y-%m-%d")
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return datetime.now(timezone.utc)


async def sync_entry_to_graph(graphiti: Graphiti, entry_path: Path) -> dict:
    """
    Parse a knowledge entry and add it as a Graphiti episode.

    Returns dict with entry id, status, and any error.
    """
    _, _, EpisodeType = _import_graphiti()

    parsed = parse_knowledge_entry(entry_path)
    fm = parsed["frontmatter"]
    entry_id = fm.get("id", entry_path.stem)

    episode_body = _build_episode_body(parsed)
    reference_time = _get_reference_time(fm)

    try:
        result = await graphiti.add_episode(
            name=parsed["title"] or entry_id,
            episode_body=episode_body,
            source_description=f"knowledge-entry:{entry_id}",
            source=EpisodeType.text,
            reference_time=reference_time,
            group_id="maverick-meta",
        )
        return {"id": entry_id, "status": "ok", "episode_uuid": str(result.episode.uuid)}
    except Exception as e:
        return {"id": entry_id, "status": "error", "error": str(e)}


async def query_graph_stats(graphiti: Graphiti) -> dict:
    """
    Query basic graph statistics using raw Cypher via the driver.

    Returns dict with node_count and edge_count.
    """
    driver = graphiti.driver

    async def run_query(query: str):
        async with driver.transaction() as tx:
            result = await tx.run(query)
            return result

    stats = {}
    try:
        result = await run_query("MATCH (n) RETURN count(n) AS cnt")
        stats["node_count"] = result.result_set[0][0] if result.result_set else 0
    except Exception:
        stats["node_count"] = "unknown"

    try:
        result = await run_query("MATCH ()-[r]->() RETURN count(r) AS cnt")
        stats["edge_count"] = result.result_set[0][0] if result.result_set else 0
    except Exception:
        stats["edge_count"] = "unknown"

    return stats


async def get_all_entity_nodes(graphiti: Graphiti) -> list:
    """Retrieve all entity nodes from the graph via Cypher."""
    driver = graphiti.driver
    try:
        async with driver.transaction() as tx:
            result = await tx.run(
                "MATCH (n:Entity) RETURN n.uuid AS uuid, n.name AS name, "
                "n.summary AS summary, n.group_id AS group_id"
            )
            nodes = []
            if result.result_set:
                for row in result.result_set:
                    nodes.append({
                        "uuid": row[0],
                        "name": row[1],
                        "summary": row[2],
                        "group_id": row[3],
                    })
            return nodes
    except Exception:
        return []


async def get_all_entity_edges(graphiti: Graphiti) -> list:
    """Retrieve all entity edges (relationships) from the graph."""
    driver = graphiti.driver
    try:
        async with driver.transaction() as tx:
            result = await tx.run(
                "MATCH (s:Entity)-[r:RELATES_TO]->(t:Entity) "
                "RETURN s.name AS source, t.name AS target, "
                "r.fact AS fact, r.uuid AS uuid"
            )
            edges = []
            if result.result_set:
                for row in result.result_set:
                    edges.append({
                        "source": row[0],
                        "target": row[1],
                        "fact": row[2],
                        "uuid": row[3],
                    })
            return edges
    except Exception:
        return []


async def get_community_nodes(graphiti: Graphiti) -> list:
    """Retrieve all community nodes from the graph."""
    driver = graphiti.driver
    try:
        async with driver.transaction() as tx:
            result = await tx.run(
                "MATCH (c:Community) RETURN c.uuid AS uuid, c.name AS name, "
                "c.summary AS summary"
            )
            communities = []
            if result.result_set:
                for row in result.result_set:
                    communities.append({
                        "uuid": row[0],
                        "name": row[1],
                        "summary": row[2],
                    })
            return communities
    except Exception:
        return []


async def close_graphiti(graphiti: Graphiti):
    """Clean up the Graphiti client connection."""
    await graphiti.close()
