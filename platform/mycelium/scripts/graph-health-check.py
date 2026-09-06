#!/usr/bin/env python3
"""
Graph Health Check -- comprehensive integrity report for the knowledge graph.

Checks:
  1. Staleness -- entries not validated recently, cross-referenced with demand
  2. Effectiveness -- surfaced/cited/correction metrics analysis
  3. Contradictions -- conflicting entries on the same topic
  4. Coverage -- demand vs knowledge supply gaps
  5. Graph structural health -- fragile bridges, orphans, hub dependencies

Output: knowledge/meta/graph-health-report.md

Usage: python3 scripts/graph-health-check.py
"""

import json
import os
import re
import sys
import yaml
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Resolve repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
META_DIR = KNOWLEDGE_DIR / "meta"
SIGNALS_DIR = REPO_ROOT / "signals"
GRAPHIFY_DIR = REPO_ROOT / "graphify-out"

sys.path.insert(0, str(REPO_ROOT))
from scripts.lib.config import load_config, get_settings

EXCLUDE_DIRS = {"meta"}
TODAY = datetime.now().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Shared helpers (mirrored from lint-knowledge.py)
# ---------------------------------------------------------------------------

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
                entry_id = meta.get("id", fname.replace(".md", ""))
                meta["_path"] = str(filepath.relative_to(REPO_ROOT))
                meta["_content"] = content
                meta["_filename"] = fname
                entries[entry_id] = meta
    return entries


def load_demand_data():
    """Load demand signals if they exist. Returns dict of person -> list of demand items."""
    demand_dir = SIGNALS_DIR / "demand"
    if not demand_dir.exists():
        return None

    demand = {}
    for fp in demand_dir.glob("*.yaml"):
        try:
            with open(fp) as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                person = data.get("person", fp.stem)
                demand[person] = data.get("queries", data.get("demands", []))
        except Exception:
            continue

    for fp in demand_dir.glob("*.json"):
        try:
            with open(fp) as f:
                data = json.load(f)
            if data and isinstance(data, dict):
                person = data.get("person", fp.stem)
                demand[person] = data.get("queries", data.get("demands", []))
        except Exception:
            continue

    return demand if demand else None


def load_dream_proposals():
    """Load dream analysis proposals if available."""
    path = META_DIR / "dream-proposals.md"
    if not path.exists():
        return None
    with open(path) as f:
        return f.read()


def load_graph_data():
    """Load graph-v4.json if available."""
    path = GRAPHIFY_DIR / "graph-v4.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Health checks
# ---------------------------------------------------------------------------

def check_staleness(entries, settings, demand_data):
    """Check each entry's age since last-validated. Cross-reference with demand."""
    warn_days = settings.get("staleness_warn_days", 7)
    decay_days = settings.get("staleness_decay_days", 14)

    results = []
    for eid, meta in entries.items():
        last_val = meta.get("last-validated", meta.get("discovered"))
        if not last_val:
            results.append({
                "entry": eid, "path": meta["_path"], "days": "?",
                "demand": "unknown", "status": "NO DATE", "action": "Add last-validated date"
            })
            continue

        try:
            last_date = datetime.strptime(str(last_val), "%Y-%m-%d")
        except ValueError:
            results.append({
                "entry": eid, "path": meta["_path"], "days": "?",
                "demand": "unknown", "status": "BAD DATE", "action": "Fix date format"
            })
            continue

        age = (datetime.now() - last_date).days
        has_demand = _entry_has_demand(eid, meta, demand_data)
        demand_label = "yes" if has_demand else ("no" if demand_data is not None else "unknown")

        if age >= decay_days:
            if has_demand:
                action = "URGENT: refresh (has demand but stale)"
            else:
                action = "Prune candidate (stale + no demand)"
            results.append({
                "entry": eid, "path": meta["_path"], "days": age,
                "demand": demand_label, "status": "DECAY", "action": action
            })
        elif age >= warn_days:
            action = "Revalidate soon" if has_demand else "Monitor"
            results.append({
                "entry": eid, "path": meta["_path"], "days": age,
                "demand": demand_label, "status": "WARNING", "action": action
            })

    return results


def _entry_has_demand(entry_id, meta, demand_data):
    """Check if any demand signal matches this entry's tags or title."""
    if demand_data is None:
        return False
    tags = set(t.lower() for t in meta.get("tags", []) or [])
    title = meta.get("_filename", "").replace(".md", "").replace("-", " ").lower()
    for person, queries in demand_data.items():
        for q in queries:
            q_lower = str(q).lower() if isinstance(q, str) else str(q.get("query", "")).lower()
            # Match if any tag appears in the query or title words overlap
            if any(tag in q_lower for tag in tags if len(tag) > 3):
                return True
            if any(word in q_lower for word in title.split() if len(word) > 3):
                return True
    return False


def check_effectiveness(entries):
    """Analyze metrics for effectiveness problems."""
    results = []
    for eid, meta in entries.items():
        metrics = meta.get("metrics")
        if not metrics or not isinstance(metrics, dict):
            results.append({
                "entry": eid, "path": meta["_path"],
                "surfaced": "?", "cited": "?", "corrections": "?",
                "score": "?", "status": "NO METRICS"
            })
            continue

        surfaced = metrics.get("surfaced_count", 0)
        cited = metrics.get("cited_count", 0)
        corrections = metrics.get("correction_after", 0)
        score = metrics.get("effectiveness_score", 0.0)

        if score < -0.2:
            results.append({
                "entry": eid, "path": meta["_path"],
                "surfaced": surfaced, "cited": cited, "corrections": corrections,
                "score": score, "status": "REMOVE CANDIDATE"
            })
        elif surfaced == 0:
            results.append({
                "entry": eid, "path": meta["_path"],
                "surfaced": surfaced, "cited": cited, "corrections": corrections,
                "score": score, "status": "UNREACHED"
            })
        elif surfaced > 0 and cited == 0:
            results.append({
                "entry": eid, "path": meta["_path"],
                "surfaced": surfaced, "cited": cited, "corrections": corrections,
                "score": score, "status": "IGNORED"
            })

    return results


def check_contradictions(entries):
    """Find entries that may contradict each other."""
    results = []
    by_category = defaultdict(list)
    for eid, meta in entries.items():
        cat = meta.get("category", "uncategorized")
        by_category[cat].append((eid, meta))

    # Check within same category for high tag overlap
    for cat, cat_entries in by_category.items():
        for i, (eid1, meta1) in enumerate(cat_entries):
            tags1 = set(t.lower() for t in meta1.get("tags", []) or [])
            related1 = set(meta1.get("related", []) or [])
            for j, (eid2, meta2) in enumerate(cat_entries):
                if j <= i:
                    continue
                tags2 = set(t.lower() for t in meta2.get("tags", []) or [])
                shared = tags1 & tags2

                # Direct references to each other are worth checking
                related2 = set(meta2.get("related", []) or [])
                mutually_related = eid2 in related1 and eid1 in related2

                # Mutual references alone are normal (related entries reference each other).
                # Only flag when combined with high tag overlap suggesting duplicate coverage.
                if len(shared) >= 5:
                    severity = "HIGH"
                    results.append({
                        "entry_a": eid1, "entry_b": eid2,
                        "conflict": f"{len(shared)} shared tags in {cat}",
                        "severity": severity
                    })
                elif len(shared) >= 4:
                    severity = "MEDIUM"
                    results.append({
                        "entry_a": eid1, "entry_b": eid2,
                        "conflict": f"{len(shared)} shared tags in {cat}",
                        "severity": severity
                    })

    # Check for stale explorations (type: exploration older than 14 days)
    settings = get_settings()
    decay_days = settings.get("staleness_decay_days", 14)
    for eid, meta in entries.items():
        if meta.get("type") == "exploration":
            last_val = meta.get("last-validated", meta.get("discovered"))
            if last_val:
                try:
                    age = (datetime.now() - datetime.strptime(str(last_val), "%Y-%m-%d")).days
                    if age > decay_days:
                        results.append({
                            "entry_a": eid, "entry_b": "(none)",
                            "conflict": f"Stale exploration ({age} days) -- went nowhere?",
                            "severity": "LOW"
                        })
                except ValueError:
                    pass

    return results


def check_coverage(entries, demand_data):
    """Cross-reference demand against knowledge supply."""
    if demand_data is None:
        return None

    results = []
    for person, queries in demand_data.items():
        for q in queries:
            query_text = str(q) if isinstance(q, str) else str(q.get("query", ""))
            freq = q.get("frequency", 1) if isinstance(q, dict) else 1
            q_lower = query_text.lower()

            best_match = None
            best_score = 0
            for eid, meta in entries.items():
                tags = set(t.lower() for t in meta.get("tags", []) or [])
                title = meta.get("_filename", "").replace(".md", "").replace("-", " ").lower()
                score = sum(1 for tag in tags if tag in q_lower and len(tag) > 3)
                score += sum(1 for word in title.split() if word in q_lower and len(word) > 3)
                if score > best_score:
                    best_score = score
                    best_match = eid

            coverage = "covered" if best_score >= 2 else ("partial" if best_score == 1 else "gap")
            results.append({
                "demand": query_text[:60], "person": person, "frequency": freq,
                "best_match": best_match or "(none)", "coverage": coverage,
                "gap": query_text if coverage == "gap" else ""
            })

    return results


def check_graph_structure(graph_data, dream_text):
    """Analyze graph structural health from dream proposals and graph data."""
    result = {
        "fragile_bridges": 0,
        "orphans": 0,
        "hub_dependencies": [],
        "communities": 0,
        "details": []
    }

    # Parse dream proposals if available
    if dream_text:
        # Extract counts from the dream-proposals markdown
        bridge_match = re.search(r"(\d+)\s*(?:critical\s*)?fragile\s*bridge", dream_text, re.IGNORECASE)
        if bridge_match:
            result["fragile_bridges"] = int(bridge_match.group(1))

        orphan_match = re.search(r"(\d+)\s*orphan", dream_text, re.IGNORECASE)
        if orphan_match:
            result["orphans"] = int(orphan_match.group(1))

        # Look for hub dependency info
        hub_matches = re.findall(r'"([^"]+)"\s*routes?\s*(\d+)%', dream_text)
        for name, pct in hub_matches:
            result["hub_dependencies"].append({"name": name, "percent": int(pct)})

        # Community count
        comm_match = re.search(r"(\d+)\s*communit", dream_text, re.IGNORECASE)
        if comm_match:
            result["communities"] = int(comm_match.group(1))

    # Parse graph data directly
    if graph_data:
        nodes = graph_data.get("nodes", [])
        links = graph_data.get("links", [])
        result["node_count"] = len(nodes)
        result["edge_count"] = len(links)

        # Count communities from graph data
        communities = set()
        for node in nodes:
            c = node.get("community")
            if c is not None:
                communities.add(c)
        if communities:
            result["communities"] = len(communities)

        # Compute degree per node
        degree = defaultdict(int)
        for link in links:
            degree[link.get("source", "")] += 1
            degree[link.get("target", "")] += 1

        # Orphans (degree 1)
        if not dream_text:
            result["orphans"] = sum(1 for d in degree.values() if d <= 1)

        # Hub concentration
        if degree:
            total_degree = sum(degree.values())
            for node_id, d in sorted(degree.items(), key=lambda x: -x[1])[:5]:
                pct = round(d / total_degree * 100, 1)
                node_label = node_id
                for n in nodes:
                    if n.get("id") == node_id:
                        node_label = n.get("label", node_id)
                        break
                result["details"].append(f"{node_label}: degree {d} ({pct}% of all connections)")

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_pruning_candidates(staleness_results, effectiveness_results, contradictions):
    """Combine signals to identify pruning candidates."""
    candidates = []

    # Stale + no demand
    for s in staleness_results:
        if s["status"] == "DECAY" and s["demand"] == "no":
            candidates.append({
                "entry": s["entry"], "reason": f"Stale ({s['days']}d) with no demand",
                "confidence": "high", "recommendation": "Remove or archive"
            })

    # Negative effectiveness
    for e in effectiveness_results:
        if e["status"] == "REMOVE CANDIDATE":
            candidates.append({
                "entry": e["entry"], "reason": f"Negative effectiveness ({e['score']})",
                "confidence": "high", "recommendation": "Remove"
            })

    # Ignored entries (surfaced but never cited)
    for e in effectiveness_results:
        if e["status"] == "IGNORED" and isinstance(e["surfaced"], int) and e["surfaced"] >= 3:
            candidates.append({
                "entry": e["entry"],
                "reason": f"Surfaced {e['surfaced']}x but never cited",
                "confidence": "medium", "recommendation": "Review relevance or rewrite"
            })

    return candidates


def build_urgent_items(staleness_results, contradictions, graph_health):
    """Identify items needing immediate attention."""
    urgent = []

    # Stale entries with demand
    for s in staleness_results:
        if "URGENT" in s.get("action", ""):
            urgent.append(f"STALE WITH DEMAND: {s['entry']} ({s['days']} days old)")

    # High severity contradictions
    for c in contradictions:
        if c["severity"] == "HIGH":
            urgent.append(f"CONTRADICTION: {c['entry_a']} vs {c['entry_b']} -- {c['conflict']}")

    # Hub dependencies above 30%
    for hub in graph_health.get("hub_dependencies", []):
        if hub["percent"] > 30:
            urgent.append(f"HUB RISK: '{hub['name']}' routes {hub['percent']}% of paths")

    return urgent


def generate_report(entries, staleness, effectiveness, contradictions, coverage,
                    graph_health, pruning, urgent):
    """Generate the full health report as markdown."""
    total = len(entries)
    stale_count = len(staleness)
    healthy = total - stale_count
    decay_count = sum(1 for s in staleness if s["status"] == "DECAY")
    warn_count = sum(1 for s in staleness if s["status"] == "WARNING")

    eff_positive = sum(1 for e in entries.values()
                       if isinstance(e.get("metrics", {}).get("effectiveness_score"), (int, float))
                       and e["metrics"]["effectiveness_score"] > 0)
    eff_negative = sum(1 for e in entries.values()
                       if isinstance(e.get("metrics", {}).get("effectiveness_score"), (int, float))
                       and e["metrics"]["effectiveness_score"] < 0)
    eff_neutral = total - eff_positive - eff_negative
    unreached = sum(1 for e in effectiveness if e["status"] == "UNREACHED")

    coverage_pct = "N/A"
    if coverage is not None:
        covered = sum(1 for c in coverage if c["coverage"] == "covered")
        coverage_pct = f"{covered}/{len(coverage)} ({round(covered/max(len(coverage),1)*100)}%)"

    lines = []
    lines.append(f"# Graph Health Report -- {TODAY}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Entries: {total} total, {healthy} healthy, {warn_count} warnings, {decay_count} decay candidates")
    lines.append(f"- Effectiveness: {eff_positive} positive, {eff_neutral} neutral, {eff_negative} negative, {unreached} unreached")
    lines.append(f"- Contradictions: {len(contradictions)} detected")
    lines.append(f"- Coverage: {coverage_pct}")
    lines.append(f"- Graph: {graph_health.get('fragile_bridges', '?')} fragile bridges, "
                 f"{graph_health.get('orphans', '?')} orphans, "
                 f"{len(graph_health.get('hub_dependencies', []))} hub dependencies")
    if graph_health.get("node_count"):
        lines.append(f"- Graph size: {graph_health['node_count']} nodes, {graph_health['edge_count']} edges, "
                     f"{graph_health.get('communities', '?')} communities")
    lines.append("")

    # Staleness table
    lines.append("## Staleness")
    if staleness:
        lines.append("")
        lines.append("| Entry | Days since validation | Demand | Status | Action |")
        lines.append("|---|---|---|---|---|")
        for s in sorted(staleness, key=lambda x: (0 if x["status"] == "DECAY" else 1, str(x["days"]))):
            lines.append(f"| {s['entry']} | {s['days']} | {s['demand']} | {s['status']} | {s['action']} |")
    else:
        lines.append("No staleness issues detected.")
    lines.append("")

    # Effectiveness table
    lines.append("## Effectiveness")
    if effectiveness:
        lines.append("")
        lines.append("| Entry | Surfaced | Cited | Corrections | Score | Status |")
        lines.append("|---|---|---|---|---|---|")
        for e in sorted(effectiveness, key=lambda x: str(x["score"])):
            lines.append(f"| {e['entry']} | {e['surfaced']} | {e['cited']} | "
                         f"{e['corrections']} | {e['score']} | {e['status']} |")
    else:
        lines.append("All entries have acceptable effectiveness metrics.")
    lines.append("")

    # Contradictions table
    lines.append("## Contradictions")
    if contradictions:
        lines.append("")
        lines.append("| Entry A | Entry B | Conflict | Severity |")
        lines.append("|---|---|---|---|")
        for c in sorted(contradictions, key=lambda x: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(x["severity"], 3)):
            lines.append(f"| {c['entry_a']} | {c['entry_b']} | {c['conflict']} | {c['severity']} |")
    else:
        lines.append("No contradictions detected.")
    lines.append("")

    # Coverage gaps
    lines.append("## Coverage Gaps")
    if coverage is not None:
        gaps = [c for c in coverage if c["coverage"] == "gap"]
        if gaps:
            lines.append("")
            lines.append("| Demand cluster | Person | Frequency | Best matching entry | Coverage | Gap |")
            lines.append("|---|---|---|---|---|---|")
            for g in sorted(gaps, key=lambda x: -x.get("frequency", 0)):
                lines.append(f"| {g['demand']} | {g['person']} | {g['frequency']} | "
                             f"{g['best_match']} | {g['coverage']} | {g['gap'][:40]} |")
        else:
            lines.append("All demand clusters have at least partial coverage.")
    else:
        lines.append("No demand data available. Run demand analysis (Cluster 2) to enable coverage checks.")
    lines.append("")

    # Pruning candidates
    lines.append("## Pruning Candidates")
    if pruning:
        lines.append("")
        lines.append("| Entry | Reason | Confidence | Recommendation |")
        lines.append("|---|---|---|---|")
        for p in pruning:
            lines.append(f"| {p['entry']} | {p['reason']} | {p['confidence']} | {p['recommendation']} |")
    else:
        lines.append("No pruning candidates identified.")
    lines.append("")

    # Graph structural health
    if graph_health.get("details"):
        lines.append("## Graph Structure")
        lines.append("")
        lines.append("Top nodes by degree:")
        for detail in graph_health["details"]:
            lines.append(f"- {detail}")
        lines.append("")

    # Urgent items
    lines.append("## Urgent Items")
    if urgent:
        for i, item in enumerate(urgent, 1):
            lines.append(f"{i}. {item}")
    else:
        lines.append("No urgent items.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"[graph-health-check] Running health check... ({TODAY})")

    settings = get_settings()
    entries = collect_entries()
    print(f"  Entries: {len(entries)}")

    # Load optional data sources
    demand_data = load_demand_data()
    dream_text = load_dream_proposals()
    graph_data = load_graph_data()

    print(f"  Demand data: {'available' if demand_data else 'not found'}")
    print(f"  Dream proposals: {'available' if dream_text else 'not found'}")
    print(f"  Graph data: {'available' if graph_data else 'not found'}")

    # Run checks
    staleness = check_staleness(entries, settings, demand_data)
    effectiveness = check_effectiveness(entries)
    contradictions = check_contradictions(entries)
    coverage = check_coverage(entries, demand_data)
    graph_health = check_graph_structure(graph_data, dream_text)

    # Derive composite results
    pruning = build_pruning_candidates(staleness, effectiveness, contradictions)
    urgent = build_urgent_items(staleness, contradictions, graph_health)

    # Generate report
    report = generate_report(entries, staleness, effectiveness, contradictions,
                             coverage, graph_health, pruning, urgent)

    # Write report
    META_DIR.mkdir(parents=True, exist_ok=True)
    report_path = META_DIR / "graph-health-report.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n  Report written to: {report_path}")
    print(f"  Staleness issues: {len(staleness)}")
    print(f"  Effectiveness issues: {len(effectiveness)}")
    print(f"  Contradictions: {len(contradictions)}")
    print(f"  Pruning candidates: {len(pruning)}")
    print(f"  Urgent items: {len(urgent)}")

    return len(urgent)


if __name__ == "__main__":
    sys.exit(main())
