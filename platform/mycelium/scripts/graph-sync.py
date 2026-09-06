#!/usr/bin/env python3
"""
Graph Sync — syncs knowledge entries to FalkorDB after synthesis.

This is the afferent coupling that makes the graph alive.
Every time synthesis creates or updates an entry, this script
ensures FalkorDB reflects the change.

No LLM needed. Reads markdown, writes Cypher.
Detects new/changed/deleted entries via content hashing.

Usage:
    python3 scripts/graph-sync.py              # sync all changed entries
    python3 scripts/graph-sync.py --full       # force full resync
    python3 scripts/graph-sync.py --verify     # just check what's out of sync
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import yaml
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
SYNC_STATE_PATH = REPO_ROOT / ".mycelium" / "sync-state.json"
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"

# Directories and files to skip
SKIP_DIRS = {"meta"}
SKIP_FILES = {"index.md", "search-index.md", "community-map.md"}


def cypher_escape(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_frontmatter(path):
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}
    return {}


def find_knowledge_entries():
    """Walk knowledge/ and return all eligible .md files."""
    entries = []
    for md_file in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        if md_file.name in SKIP_FILES:
            continue
        rel = md_file.relative_to(KNOWLEDGE_DIR)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        entries.append(md_file)
    return entries


def load_sync_state():
    if SYNC_STATE_PATH.exists():
        return json.loads(SYNC_STATE_PATH.read_text())
    return {"entries": {}}


def save_sync_state(state):
    SYNC_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_PATH.write_text(json.dumps(state, indent=2))


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(GRAPH_NAME)


def sync_entry(graph, entry_path, frontmatter):
    """Sync a single knowledge entry to FalkorDB."""
    rel_path = str(entry_path.relative_to(REPO_ROOT))
    entry_id = frontmatter.get("id", entry_path.stem)
    category = frontmatter.get("category", "unknown")
    confidence = frontmatter.get("confidence", "low")
    entry_type = frontmatter.get("type", "knowledge")
    tags = frontmatter.get("tags", [])
    if isinstance(tags, list):
        tags_str = ", ".join(str(t) for t in tags)
    else:
        tags_str = str(tags)

    # Title from first heading
    text = entry_path.read_text(encoding="utf-8", errors="replace")
    title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    title = title_match.group(1) if title_match else entry_path.stem

    label = cypher_escape(title)
    node_id = cypher_escape(entry_id)
    source = cypher_escape(rel_path)
    cat = cypher_escape(category)
    conf = cypher_escape(confidence)
    etype = cypher_escape(entry_type)
    tags_esc = cypher_escape(tags_str)

    # Determine community from existing node (if any)
    try:
        result = graph.query(f"MATCH (n:Knowledge {{node_id: '{node_id}'}}) RETURN n.community")
        existing_community = result.result_set[0][0] if result.result_set else -1
    except Exception:
        existing_community = -1

    query = (
        f"MERGE (n:Knowledge {{node_id: '{node_id}'}}) "
        f"SET n.label = '{label}', "
        f"n.source_file = '{source}', "
        f"n.category = '{cat}', "
        f"n.confidence = '{conf}', "
        f"n.entry_type = '{etype}', "
        f"n.tags = '{tags_esc}', "
        f"n.community = {existing_community}, "
        f"n.file_type = 'knowledge'"
    )

    graph.query(query)

    # Sync `related` field as edges
    related = frontmatter.get("related", [])
    if related:
        for rel_id in related:
            rel_id_esc = cypher_escape(rel_id)
            try:
                graph.query(
                    f"MATCH (a:Knowledge {{node_id: '{node_id}'}}), "
                    f"(b:Knowledge {{node_id: '{rel_id_esc}'}}) "
                    f"MERGE (a)-[r:RELATES_TO_ENTRY]->(b) "
                    f"SET r.confidence = 'EXTRACTED', r.confidence_score = 1.0"
                )
            except Exception:
                pass  # Target node may not exist yet

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Force full resync")
    parser.add_argument("--verify", action="store_true", help="Just check, don't sync")
    args = parser.parse_args()

    entries = find_knowledge_entries()
    state = load_sync_state()
    print(f"[graph-sync] Found {len(entries)} knowledge entries")

    # Detect changes
    to_sync = []
    unchanged = 0
    for entry in entries:
        rel = str(entry.relative_to(REPO_ROOT))
        current_hash = file_hash(entry)
        prev_hash = state["entries"].get(rel, {}).get("hash")

        if args.full or current_hash != prev_hash:
            to_sync.append(entry)
        else:
            unchanged += 1

    # Detect deletions
    current_paths = {str(e.relative_to(REPO_ROOT)) for e in entries}
    deleted = [p for p in state["entries"] if p not in current_paths]

    print(f"  Changed/new: {len(to_sync)}")
    print(f"  Unchanged: {unchanged}")
    print(f"  Deleted: {len(deleted)}")

    if args.verify:
        if to_sync:
            print("\nFiles needing sync:")
            for e in to_sync:
                print(f"  {e.relative_to(REPO_ROOT)}")
        if deleted:
            print("\nDeleted files (nodes to expire):")
            for d in deleted:
                print(f"  {d}")
        return

    if not to_sync and not deleted:
        print("[graph-sync] Everything in sync. Nothing to do.")
        return

    # Connect to FalkorDB
    try:
        graph = get_graph()
    except Exception as e:
        print(f"[graph-sync] FalkorDB connection failed: {e}")
        print("[graph-sync] Pipeline continues — graph sync is non-fatal.")
        sys.exit(0)  # Exit 0 so pipeline doesn't break

    start = time.time()
    ok = 0
    errors = 0

    for entry in to_sync:
        rel = str(entry.relative_to(REPO_ROOT))
        frontmatter = parse_frontmatter(entry)
        try:
            sync_entry(graph, entry, frontmatter)
            state["entries"][rel] = {
                "hash": file_hash(entry),
                "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            ok += 1
        except Exception as e:
            print(f"  ERROR: {rel}: {e}")
            errors += 1

    # Handle deletions — mark as expired, don't delete
    for deleted_path in deleted:
        entry_id = Path(deleted_path).stem
        try:
            graph.query(
                f"MATCH (n:Knowledge {{source_file: '{cypher_escape(deleted_path)}'}}) "
                f"SET n.expired = true"
            )
            del state["entries"][deleted_path]
        except Exception:
            pass

    elapsed = time.time() - start
    save_sync_state(state)
    print(f"\n[graph-sync] Done: {ok} synced, {errors} errors, {len(deleted)} expired ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
