#!/usr/bin/env python3
"""
Knowledge base linter — maintains wiki health.

Checks for:
  1. Staleness — entries not validated recently
  2. Orphans — entries not referenced in any index or related field
  3. Missing cross-refs — entries that share tags but aren't linked
  4. Broken related links — related entries that don't exist
  5. Schema compliance — missing required frontmatter fields
  6. Confidence decay — entries older than N days without revalidation

Also rebuilds the search index (calls build-search-index.py).

Usage: python3 scripts/lint-knowledge.py [--fix]
"""

import os
import re
import sys
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

KNOWLEDGE_DIR = Path("knowledge")
EXCLUDE_DIRS = {"meta"}
TODAY = datetime.now().strftime("%Y-%m-%d")

REQUIRED_FIELDS = ["id", "category", "discovered", "confidence", "source", "tags", "relevant-when", "related"]
VALID_CATEGORIES = {"patterns", "anti-patterns", "architecture", "workflows", "tool-configs"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_TYPES = {"knowledge", "procedure", "exploration"}
PROCEDURE_MAX_CHARS = 3575
PROCEDURE_REQUIRED_SECTIONS = ["## Procedure", "## Pitfalls", "## Verification"]

# Staleness thresholds (days since last-validated)
STALENESS_WARN = 7   # warn after 7 days
STALENESS_DECAY = 14 # drop confidence after 14 days


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
    return meta, content


def collect_entries():
    """Walk knowledge/ and parse all entries."""
    entries = {}
    for dirpath, dirnames, filenames in os.walk(KNOWLEDGE_DIR):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            if not fname.endswith(".md") or fname in ("index.md", "search-index.md"):
                continue
            filepath = Path(dirpath) / fname
            meta, content = parse_frontmatter(filepath)
            if meta:
                entry_id = meta.get("id", fname)
                meta["_path"] = str(filepath)
                meta["_content"] = content
                entries[entry_id] = meta
    return entries


def check_schema(entries):
    """Check all entries have required frontmatter fields."""
    issues = []
    for eid, meta in entries.items():
        for field in REQUIRED_FIELDS:
            if field not in meta or meta[field] is None:
                issues.append(("schema", meta["_path"], f"Missing field: {field}"))
        if meta.get("category") and meta["category"] not in VALID_CATEGORIES:
            issues.append(("schema", meta["_path"], f"Invalid category: {meta['category']}"))
        if meta.get("confidence") and meta["confidence"] not in VALID_CONFIDENCE:
            issues.append(("schema", meta["_path"], f"Invalid confidence: {meta['confidence']}"))
        entry_type = meta.get("type", "knowledge")
        if entry_type not in VALID_TYPES:
            issues.append(("schema", meta["_path"], f"Invalid type: {entry_type}"))
        if entry_type == "procedure":
            # Check char count
            content = meta.get("_content", "")
            body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
            if len(body) > PROCEDURE_MAX_CHARS:
                issues.append(("size", meta["_path"],
                    f"Procedure exceeds {PROCEDURE_MAX_CHARS} chars ({len(body)}) — curate or split"))
            # Check required sections
            for section in PROCEDURE_REQUIRED_SECTIONS:
                if section not in content:
                    issues.append(("schema", meta["_path"], f"Procedure missing section: {section}"))
            # Check version field
            if "version" not in meta:
                issues.append(("schema", meta["_path"], "Procedure missing version field"))
        # Check metrics block
        metrics = meta.get("metrics")
        if metrics is None:
            issues.append(("schema", meta["_path"], "Missing metrics block"))
        elif isinstance(metrics, dict):
            expected_metrics = {"surfaced_count", "cited_count", "correction_after", "effectiveness_score"}
            missing = expected_metrics - set(metrics.keys())
            if missing:
                issues.append(("schema", meta["_path"], f"Missing metrics fields: {', '.join(sorted(missing))}"))
            # Check for stale hook-based fields that should have been migrated
            stale_fields = {"injection_count", "used_count", "ignored_count"} & set(metrics.keys())
            if stale_fields:
                issues.append(("schema", meta["_path"], f"Stale metrics fields (should be trace-based): {', '.join(sorted(stale_fields))}"))
    return issues


def check_staleness(entries):
    """Find entries that haven't been validated recently."""
    issues = []
    for eid, meta in entries.items():
        last_val = meta.get("last-validated", meta.get("discovered"))
        if not last_val:
            issues.append(("stale", meta["_path"], "No last-validated or discovered date"))
            continue
        last_val_str = str(last_val)
        try:
            last_date = datetime.strptime(last_val_str, "%Y-%m-%d")
        except ValueError:
            issues.append(("stale", meta["_path"], f"Unparseable date: {last_val_str}"))
            continue

        age = (datetime.now() - last_date).days
        if age >= STALENESS_DECAY:
            issues.append(("decay", meta["_path"],
                f"Not validated in {age} days — confidence should decay "
                f"(current: {meta.get('confidence', '?')})"))
        elif age >= STALENESS_WARN:
            issues.append(("stale", meta["_path"],
                f"Not validated in {age} days — consider revalidating"))
    return issues


def check_orphans(entries):
    """Find entries that no other entry references."""
    all_ids = set(entries.keys())
    referenced = set()
    for eid, meta in entries.items():
        for ref in meta.get("related", []) or []:
            referenced.add(ref)
    orphans = all_ids - referenced
    return [("orphan", entries[oid]["_path"], "Not referenced by any other entry's `related` field")
            for oid in orphans if oid in entries]


def check_broken_refs(entries):
    """Find related references that point to non-existent entries."""
    issues = []
    all_ids = set(entries.keys())
    for eid, meta in entries.items():
        for ref in meta.get("related", []) or []:
            if ref not in all_ids:
                issues.append(("broken-ref", meta["_path"], f"Related entry not found: {ref}"))
    return issues


def check_missing_crossrefs(entries):
    """Find entries that share 3+ tags but aren't linked."""
    issues = []
    entry_list = list(entries.items())
    for i, (eid1, meta1) in enumerate(entry_list):
        tags1 = set(t.lower() for t in meta1.get("tags", []) or [])
        related1 = set(meta1.get("related", []) or [])
        for j, (eid2, meta2) in enumerate(entry_list):
            if j <= i:
                continue
            tags2 = set(t.lower() for t in meta2.get("tags", []) or [])
            shared = tags1 & tags2
            if len(shared) >= 3 and eid2 not in related1:
                related2 = set(meta2.get("related", []) or [])
                if eid1 not in related2:
                    issues.append(("missing-xref", meta1["_path"],
                        f"Shares {len(shared)} tags with {eid2} ({', '.join(list(shared)[:5])}) but no cross-reference"))
    return issues


def check_contradictions(entries):
    """Flag entries in the same category with overlapping tags — potential contradictions."""
    issues = []
    by_category = defaultdict(list)
    for eid, meta in entries.items():
        cat = meta.get("category", "")
        by_category[cat].append((eid, meta))

    for cat, cat_entries in by_category.items():
        for i, (eid1, meta1) in enumerate(cat_entries):
            tags1 = set(t.lower() for t in meta1.get("tags", []) or [])
            for j, (eid2, meta2) in enumerate(cat_entries):
                if j <= i:
                    continue
                tags2 = set(t.lower() for t in meta2.get("tags", []) or [])
                shared = tags1 & tags2
                if len(shared) >= 4:
                    issues.append(("potential-contradiction", meta1["_path"],
                        f"High tag overlap with {eid2} in same category ({cat}) — "
                        f"review for contradiction or merge opportunity"))
    return issues


def main():
    fix_mode = "--fix" in sys.argv

    print(f"Linting knowledge base... ({TODAY})")
    entries = collect_entries()
    print(f"  Entries: {len(entries)}")

    all_issues = []
    all_issues.extend(check_schema(entries))
    all_issues.extend(check_staleness(entries))
    all_issues.extend(check_orphans(entries))
    all_issues.extend(check_broken_refs(entries))
    all_issues.extend(check_missing_crossrefs(entries))
    all_issues.extend(check_contradictions(entries))

    if not all_issues:
        print("  No issues found.")
    else:
        # Group by type
        by_type = defaultdict(list)
        for issue_type, path, msg in all_issues:
            by_type[issue_type].append((path, msg))

        print(f"\n  Found {len(all_issues)} issues:\n")
        for issue_type, issues in sorted(by_type.items()):
            icon = {
                "schema": "SCHEMA",
                "stale": "STALE",
                "decay": "DECAY",
                "orphan": "ORPHAN",
                "broken-ref": "BROKEN",
                "missing-xref": "XREF",
                "potential-contradiction": "CONFLICT",
            }.get(issue_type, issue_type.upper())
            print(f"  [{icon}] ({len(issues)} issues)")
            for path, msg in issues:
                print(f"    - {path}: {msg}")
            print()

    # Write lint report
    report_path = KNOWLEDGE_DIR / "meta" / "lint-report.md"
    with open(report_path, "w") as f:
        f.write(f"# Knowledge Base Lint Report\n\n")
        f.write(f"Run: {TODAY}\n")
        f.write(f"Entries: {len(entries)}\n")
        f.write(f"Issues: {len(all_issues)}\n\n")
        if all_issues:
            by_type = defaultdict(list)
            for issue_type, path, msg in all_issues:
                by_type[issue_type].append((path, msg))
            for issue_type, issues in sorted(by_type.items()):
                f.write(f"## {issue_type.upper()} ({len(issues)})\n\n")
                for path, msg in issues:
                    f.write(f"- `{path}`: {msg}\n")
                f.write("\n")
        else:
            f.write("No issues found.\n")

    print(f"  Report: {report_path}")

    # Rebuild search index
    print("\n  Rebuilding search index...")
    os.system("python3 scripts/build-search-index.py")

    return len(all_issues)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(1 if exit_code > 0 else 0)
