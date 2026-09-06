#!/usr/bin/env python3
"""
Builds an inverted search index from knowledge entries.

Reads all markdown files in knowledge/ (excluding meta/), extracts tags and
relevant-when from frontmatter, and generates:
  1. knowledge/search-index.md — inverted keyword → entries map
  2. knowledge/index.md — situation-routed human-readable catalog

Usage: python3 scripts/build-search-index.py
"""

import os
import re
import yaml
from collections import defaultdict
from pathlib import Path

KNOWLEDGE_DIR = Path("knowledge")
EXCLUDE_DIRS = {"meta"}
INDEX_PATH = KNOWLEDGE_DIR / "index.md"
SEARCH_INDEX_PATH = KNOWLEDGE_DIR / "search-index.md"


def parse_frontmatter(filepath):
    """Extract YAML frontmatter from a markdown file."""
    with open(filepath, "r") as f:
        content = f.read()

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None, content

    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, content

    body = content[match.end():].strip()
    # Extract title from first heading
    title_match = re.match(r"#\s+(.+)", body)
    if title_match:
        meta["title"] = title_match.group(1).strip()

    return meta, body


def extract_first_sentence(body):
    """Get the What section's first sentence for the one-liner."""
    what_match = re.search(r"## What\n+(.+?)(?:\n\n|\n##)", body, re.DOTALL)
    if what_match:
        text = what_match.group(1).strip()
        # First sentence
        sent = re.split(r"[.!?]\s", text)
        return sent[0].rstrip(".") if sent else text[:120]
    return ""


def collect_entries():
    """Walk knowledge/ and parse all entries."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(KNOWLEDGE_DIR):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if not fname.endswith(".md") or fname in ("index.md", "search-index.md"):
                continue
            filepath = Path(dirpath) / fname
            meta, body = parse_frontmatter(filepath)
            if meta and meta.get("id"):
                meta["_path"] = str(filepath)
                meta["_relpath"] = str(filepath.relative_to(KNOWLEDGE_DIR))
                meta["_oneliner"] = extract_first_sentence(body)
                entries.append(meta)
    return entries


def build_inverted_index(entries):
    """Build keyword → [entry paths] mapping."""
    index = defaultdict(set)

    for entry in entries:
        path = entry["_relpath"]
        # Index tags
        for tag in entry.get("tags", []):
            index[tag.lower()].add(path)
            # Also index without hyphens (e.g., "trigger-dev" → "triggerdev")
            if "-" in tag:
                index[tag.replace("-", "").lower()].add(path)
                # And each word separately
                for word in tag.split("-"):
                    if len(word) > 2:
                        index[word.lower()].add(path)

        # Index words from relevant-when
        for phrase in entry.get("relevant-when", "").split(","):
            phrase = phrase.strip().lower()
            if phrase:
                index[phrase].add(path)
                for word in phrase.split():
                    if len(word) > 3:  # skip short words
                        index[word.lower()].add(path)

        # Index category
        cat = entry.get("category", "")
        if cat:
            index[cat.lower()].add(path)

        # Index title words
        for word in entry.get("title", "").split():
            word = re.sub(r"[^a-z0-9]", "", word.lower())
            if len(word) > 3:
                index[word.lower()].add(path)

    return index


def build_situation_index(entries):
    """Group entries by situation/context for the human-readable index."""
    situations = {
        "Making architecture or stack decisions?": [
            "architecture", "database", "graphiti", "falkordb", "neo4j",
            "pgvector", "queue", "trigger-dev", "embedding", "rls",
        ],
        "Building or modifying frontend?": [
            "frontend", "fixtures", "design-system", "eslint", "tailwind",
            "next-js", "react", "storybook", "copilotkit",
        ],
        "Doing data collection or research?": [
            "research", "data-collection", "api", "scraping", "xpoz",
            "twitter", "reddit", "youtube", "competitor", "market-research",
        ],
        "Setting up tools or dev environment?": [
            "hooks", "langsmith", "tracing", "git", "auto-sync",
            "plugin", "settings", "mcp",
        ],
        "Planning work or organizing tasks?": [
            "tracking", "phases", "workstream", "parallel", "issues",
            "methodology", "deliverables",
        ],
    }

    result = {}
    for situation, keywords in situations.items():
        matched = set()
        for entry in entries:
            entry_tags = set(t.lower() for t in entry.get("tags", []))
            if entry_tags & set(keywords):
                matched.add(entry["_relpath"])
        if matched:
            result[situation] = [
                e for e in entries if e["_relpath"] in matched
            ]

    # Catch-all for unmatched
    all_matched = set()
    for v in result.values():
        for e in v:
            all_matched.add(e["_relpath"])
    unmatched = [e for e in entries if e["_relpath"] not in all_matched]
    if unmatched:
        result["Other knowledge"] = unmatched

    return result


def write_search_index(inverted, entries):
    """Write the machine-readable inverted index."""
    lines = [
        "# Search Index",
        "",
        "Auto-generated by `scripts/build-search-index.py`. Do not edit manually.",
        f"Entries indexed: {len(entries)}",
        "",
        "## Keyword → Entries",
        "",
    ]

    # Sort by keyword, group by first letter
    sorted_keywords = sorted(inverted.keys())
    current_letter = ""
    for kw in sorted_keywords:
        letter = kw[0].upper() if kw[0].isalpha() else "#"
        if letter != current_letter:
            current_letter = letter
            lines.append(f"### {letter}")
        paths = sorted(inverted[kw])
        lines.append(f"- **{kw}** → {', '.join(paths)}")

    lines.append("")

    with open(SEARCH_INDEX_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"  Search index: {SEARCH_INDEX_PATH} ({len(sorted_keywords)} keywords)")


def write_situation_index(situations, entries):
    """Write the human-readable situation-routed index."""
    lines = [
        "# Team Knowledge Base",
        "",
        f"**{len(entries)} entries** across {len(set(e.get('category','') for e in entries))} categories.",
        "When you encounter these situations, search for relevant knowledge below.",
        "",
    ]

    for situation, sit_entries in situations.items():
        lines.append(f"## {situation}")
        lines.append("")
        for e in sorted(sit_entries, key=lambda x: x.get("confidence", "") == "high", reverse=True):
            confidence = e.get("confidence", "?")
            badge = {"high": "[H]", "medium": "[M]", "low": "[L]"}.get(confidence, "[?]")
            title = e.get("title", e["id"])
            oneliner = e.get("_oneliner", "")
            path = e["_relpath"]
            lines.append(f"- {badge} [{title}]({path}) — {oneliner}")
        lines.append("")

    lines.append("---")
    lines.append("*Search with `/team-knowledge <query>` for keyword search across all entries.*")
    lines.append("")

    with open(INDEX_PATH, "w") as f:
        f.write("\n".join(lines))
    print(f"  Situation index: {INDEX_PATH} ({sum(len(v) for v in situations.values())} entries in {len(situations)} situations)")


def main():
    print("Building knowledge search index...")
    entries = collect_entries()
    print(f"  Found {len(entries)} entries")

    if not entries:
        print("  No entries found. Skipping.")
        return

    inverted = build_inverted_index(entries)
    situations = build_situation_index(entries)

    write_search_index(inverted, entries)
    write_situation_index(situations, entries)

    print("Done.")


if __name__ == "__main__":
    main()
