#!/usr/bin/env python3
"""
Seed the FalkorDB knowledge graph with all existing knowledge entries.

One-time script that walks knowledge/ and loads each .md entry as a Graphiti episode.
Skips index.md, search-index.md, and files under meta/.

Usage:
    python3 scripts/seed-graph.py

Requires:
    - FalkorDB running (docker compose -f docker/docker-compose.yml up -d falkordb)
    - OPENAI_API_KEY set in environment
    - pip install graphiti-core[falkordb]
"""

import asyncio
import sys
import time
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.lib.graph_client import (
    get_graphiti,
    sync_entry_to_graph,
    query_graph_stats,
    close_graphiti,
)

# Files and directories to skip
SKIP_FILES = {"index.md", "search-index.md"}
SKIP_DIRS = {"meta"}


def find_knowledge_entries() -> list[Path]:
    """Walk knowledge/ and return all eligible .md files."""
    knowledge_dir = REPO_ROOT / "knowledge"
    if not knowledge_dir.exists():
        print(f"ERROR: {knowledge_dir} does not exist")
        sys.exit(1)

    entries = []
    for md_file in sorted(knowledge_dir.rglob("*.md")):
        # Skip files by name
        if md_file.name in SKIP_FILES:
            continue
        # Skip files in meta/ subdirectory
        rel = md_file.relative_to(knowledge_dir)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        entries.append(md_file)

    return entries


async def main():
    print("=== Seeding FalkorDB Knowledge Graph ===\n")

    # Find entries
    entries = find_knowledge_entries()
    print(f"Found {len(entries)} knowledge entries to load\n")

    if not entries:
        print("No entries found. Nothing to do.")
        return

    # Connect to graph
    print("Connecting to FalkorDB via Graphiti...")
    try:
        graphiti = await get_graphiti()
    except EnvironmentError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Could not connect to FalkorDB: {e}")
        print("Make sure FalkorDB is running: docker compose -f docker/docker-compose.yml up -d falkordb")
        sys.exit(1)

    print("Connected.\n")

    # Seed entries
    ok_count = 0
    err_count = 0
    errors = []
    start = time.time()

    for i, entry_path in enumerate(entries, 1):
        rel_path = entry_path.relative_to(REPO_ROOT)
        print(f"[{i}/{len(entries)}] {rel_path} ... ", end="", flush=True)

        result = await sync_entry_to_graph(graphiti, entry_path)

        if result["status"] == "ok":
            ok_count += 1
            print(f"ok (episode: {result['episode_uuid'][:8]}...)")
        else:
            err_count += 1
            errors.append(result)
            print(f"ERROR: {result['error'][:80]}")

    elapsed = time.time() - start

    # Print summary
    print(f"\n=== Seeding Complete ===")
    print(f"Time:    {elapsed:.1f}s")
    print(f"Success: {ok_count}/{len(entries)}")
    print(f"Errors:  {err_count}/{len(entries)}")

    if errors:
        print(f"\nFailed entries:")
        for err in errors:
            print(f"  - {err['id']}: {err['error'][:100]}")

    # Verify graph stats
    print(f"\n=== Graph Statistics ===")
    stats = await query_graph_stats(graphiti)
    for key, val in stats.items():
        print(f"  {key}: {val}")

    await close_graphiti(graphiti)


if __name__ == "__main__":
    asyncio.run(main())
