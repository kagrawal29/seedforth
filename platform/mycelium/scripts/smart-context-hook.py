#!/usr/bin/env python3
"""
Smart PreToolUse context injection hook.

Reads the tool input (what Claude is about to search for),
looks up relevant context from BOTH the code graph AND the
knowledge base, and returns a merged context block.

Runs in <1s. No LLM calls. Pure keyword matching + graph lookup.

Install in .claude/settings.json:
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Glob|Grep|Read",
      "hooks": [{
        "type": "command",
        "command": "python3 scripts/smart-context-hook.py"
      }]
    }]
  }
}
"""

import json
import sys
import re
import os
from pathlib import Path

# Paths (relative to project root)
GRAPH_PATH = "graphify-out/graph.json"
SEARCH_INDEX_PATH = "knowledge/search-index.md"
KNOWLEDGE_DIR = "knowledge"

# Minimum relevance threshold
MIN_GRAPH_MATCHES = 1
MIN_KB_MATCHES = 1

# Token budget for context injection
MAX_OUTPUT_CHARS = 1500


def load_graph(path):
    """Load graph.json, return nodes dict and edges list."""
    if not os.path.exists(path):
        return {}, []
    try:
        data = json.loads(Path(path).read_text())
        nodes = {n["id"]: n for n in data.get("nodes", [])}
        edges = data.get("edges", [])
        return nodes, edges
    except Exception:
        return {}, []


def load_search_index(path):
    """Load inverted search index, return keyword → entries mapping."""
    if not os.path.exists(path):
        return {}
    index = {}
    try:
        for line in Path(path).read_text().split("\n"):
            m = re.match(r"- \*\*(.+?)\*\* → (.+)", line)
            if m:
                kw = m.group(1).lower()
                entries = [e.strip() for e in m.group(2).split(",")]
                index[kw] = entries
    except Exception:
        pass
    return index


def extract_query_terms(tool_input):
    """Extract meaningful search terms from the tool input."""
    # Get the search pattern/path from tool input
    text = ""
    if isinstance(tool_input, dict):
        # Glob: pattern field, Grep: pattern field, Read: file_path field
        text = tool_input.get("pattern", "") or tool_input.get("file_path", "") or ""
    elif isinstance(tool_input, str):
        text = tool_input

    # Extract words (lowercase, 3+ chars, no common words)
    stopwords = {"the", "and", "for", "that", "this", "with", "from", "are", "was",
                 "not", "but", "have", "has", "had", "will", "would", "could", "should",
                 "src", "tsx", "jsx", "test", "spec", "index", "node_modules", "dist"}
    words = set(re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{2,}', text.lower()))
    words -= stopwords
    return words


def search_graph(nodes, edges, terms):
    """Find graph nodes matching query terms. Return top matches with context."""
    matches = []
    for nid, node in nodes.items():
        label = node.get("label", "").lower()
        source = node.get("source_file", "").lower()
        score = 0
        for term in terms:
            if term in label:
                score += 3  # label match is strongest
            elif term in source:
                score += 1  # file path match is weaker
        if score > 0:
            matches.append((score, nid, node))

    matches.sort(reverse=True)
    results = []
    for score, nid, node in matches[:5]:
        # Get neighbors
        neighbors = []
        for e in edges:
            if e.get("source") == nid:
                target_node = nodes.get(e["target"], {})
                neighbors.append(f'{e.get("relation", "→")} {target_node.get("label", e["target"])}')
            elif e.get("target") == nid:
                source_node = nodes.get(e["source"], {})
                neighbors.append(f'{source_node.get("label", e["source"])} {e.get("relation", "→")} this')

        community = node.get("community", "?")
        results.append({
            "label": node.get("label", nid),
            "file": node.get("source_file", "?"),
            "community": community,
            "neighbors": neighbors[:5],
        })
    return results


def search_knowledge(index, terms):
    """Find knowledge entries matching query terms."""
    entry_scores = {}
    for term in terms:
        # Exact match
        if term in index:
            for entry in index[term]:
                entry_scores[entry] = entry_scores.get(entry, 0) + 2
        # Partial match
        for kw, entries in index.items():
            if term in kw or kw in term:
                for entry in entries:
                    entry_scores[entry] = entry_scores.get(entry, 0) + 1

    sorted_entries = sorted(entry_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_entries[:3]


def extract_inline_content(entry_path):
    """Extract the key inline content from a knowledge entry.

    For declarative entries: the first sentence of ## What
    For procedures: the most relevant step + any pitfall one-liner
    For anti-patterns: the warning in one line

    Returns a short string (1-2 lines) that can be injected directly.
    """
    # Try both possible base paths
    for base in [KNOWLEDGE_DIR, ".claude/knowledge/entries"]:
        full_path = os.path.join(base, entry_path)
        if os.path.exists(full_path):
            break
    else:
        return None

    try:
        content = Path(full_path).read_text()
    except Exception:
        return None

    # Determine type from frontmatter
    entry_type = "knowledge"
    type_match = re.search(r"type:\s*(\w+)", content)
    if type_match:
        entry_type = type_match.group(1)

    category = ""
    cat_match = re.search(r"category:\s*([\w-]+)", content)
    if cat_match:
        category = cat_match.group(1)

    # Extract the ## What section's first sentence (key fact)
    what_match = re.search(r"## What\n+(.+?)(?:\n\n|\n##)", content, re.DOTALL)
    key_fact = ""
    if what_match:
        text = what_match.group(1).strip()
        # First sentence
        sentences = re.split(r'[.!?]\s', text)
        key_fact = sentences[0].rstrip('.') if sentences else text[:150]

    # For anti-patterns, the fact IS the warning
    if category == "anti-patterns":
        return f"⚠ {key_fact}"

    # For procedures, extract a relevant step or pitfall
    if entry_type == "procedure":
        # Get first pitfall as a one-liner warning
        pitfall_match = re.search(r"## Pitfalls\n+- What breaks: (.+?)(?:\n-|\n\n|\n##)", content, re.DOTALL)
        if pitfall_match:
            pitfall = pitfall_match.group(1).split(". Fix:")[0].strip()
            return f"{key_fact}. Warning: {pitfall}"
        return key_fact

    # For declarative, just the key fact
    return key_fact


def format_output(graph_results, kb_results, terms):
    """Format merged context for Claude.

    Design principle: RIGHT CONTEXT AT THE RIGHT MOMENT.
    - Inline actual content, not file pointers
    - One line per fact/warning, not full entries
    - Code structure + decisions + warnings merged
    """
    if not graph_results and not kb_results:
        return ""  # Nothing relevant — stay silent

    parts = []
    parts.append(f"[CONTEXT] Relevant to: {', '.join(sorted(terms)[:5])}")

    if graph_results:
        parts.append("")
        parts.append("Code:")
        for r in graph_results[:3]:
            neighbors_str = ""
            if r["neighbors"]:
                neighbors_str = " → " + ", ".join(r["neighbors"][:2])
            parts.append(f"  {r['label']} ({r['file']}){neighbors_str}")

    # Inline content from knowledge entries (not pointers)
    decisions = []
    warnings = []
    procedures = []

    for entry_path, score in kb_results:
        content = extract_inline_content(entry_path)
        if not content:
            continue

        if content.startswith("⚠"):
            warnings.append(content)
        elif "Warning:" in content:
            procedures.append(content)
        else:
            decisions.append(f"• {content}")

    if decisions:
        parts.append("")
        parts.append("Decisions:")
        parts.extend(f"  {d}" for d in decisions[:3])

    if warnings:
        parts.append("")
        for w in warnings[:2]:
            parts.append(f"  {w}")

    if procedures:
        parts.append("")
        for p in procedures[:2]:
            parts.append(f"  {p}")

    output = "\n".join(parts)
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + "\n  ..."

    return output


def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        return  # Malformed input, stay silent

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    # Only activate for file search tools
    if tool_name not in ("Glob", "Grep", "Read"):
        return

    # Extract search terms
    terms = extract_query_terms(tool_input)
    if not terms:
        return  # Nothing meaningful to search for

    # Search both systems
    nodes, edges = load_graph(GRAPH_PATH)
    graph_results = search_graph(nodes, edges, terms) if nodes else []

    index = load_search_index(SEARCH_INDEX_PATH)
    kb_results = search_knowledge(index, terms) if index else []

    # Only output if we found something relevant
    if len(graph_results) >= MIN_GRAPH_MATCHES or len(kb_results) >= MIN_KB_MATCHES:
        output = format_output(graph_results, kb_results, terms)
        if output:
            print(output)


if __name__ == "__main__":
    main()
