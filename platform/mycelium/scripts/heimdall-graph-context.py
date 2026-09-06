#!/usr/bin/env python3
"""
Heimdall Graph Context -- generates a concise (~200 token) graph state summary
for the evaluation agent (Heimdall) to consider during quality gating.

Reads:
  - knowledge/meta/graph-health-report.md
  - knowledge/meta/dream-proposals.md (if available)

Output: knowledge/meta/heimdall-graph-context.md

This file can be added to Heimdall's prompt as additional context.
It does NOT modify the evaluation agent directly.

Usage: python3 scripts/heimdall-graph-context.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
META_DIR = REPO_ROOT / "knowledge" / "meta"


def load_health_report():
    """Load the graph health report."""
    path = META_DIR / "graph-health-report.md"
    if not path.exists():
        return None
    with open(path) as f:
        return f.read()


def load_dream_proposals():
    """Load dream proposals."""
    path = META_DIR / "dream-proposals.md"
    if not path.exists():
        return None
    with open(path) as f:
        return f.read()


def extract_summary_line(report, prefix):
    """Extract a line starting with prefix from the report."""
    for line in report.split("\n"):
        if line.strip().startswith(f"- {prefix}"):
            return line.strip()[2:]  # Remove "- " prefix
    return None


def generate_context(report, dream_text):
    """Build a concise context block for Heimdall."""
    lines = []
    lines.append("## Graph Health Context (for evaluation)")
    lines.append("")

    if report:
        # Extract key metrics from summary section
        entries_line = extract_summary_line(report, "Entries:")
        effectiveness_line = extract_summary_line(report, "Effectiveness:")
        contradictions_line = extract_summary_line(report, "Contradictions:")
        coverage_line = extract_summary_line(report, "Coverage:")
        graph_line = extract_summary_line(report, "Graph:")

        if entries_line:
            lines.append(f"- {entries_line}")
        if effectiveness_line:
            lines.append(f"- {effectiveness_line}")
        if contradictions_line:
            lines.append(f"- {contradictions_line}")
        if coverage_line:
            lines.append(f"- {coverage_line}")
        if graph_line:
            lines.append(f"- {graph_line}")

        # Count pruning candidates
        prune_count = report.count("| ") - report.count("|---|")
        prune_section = report.split("## Pruning Candidates")
        if len(prune_section) > 1:
            prune_rows = [l for l in prune_section[1].split("\n")
                          if l.startswith("| ") and not l.startswith("|---")]
            if prune_rows:
                lines.append(f"- Pruning candidates: {len(prune_rows)}")

        # Extract urgent items
        urgent_section = report.split("## Urgent Items")
        if len(urgent_section) > 1:
            urgent_lines = [l.strip() for l in urgent_section[1].split("\n")
                            if l.strip() and l.strip()[0].isdigit()]
            if urgent_lines:
                lines.append("")
                lines.append("Urgent:")
                for u in urgent_lines[:3]:  # Cap at 3 to stay concise
                    lines.append(f"  {u}")
    else:
        lines.append("No graph health report available. Run graph-health-check.py first.")

    if dream_text:
        # Extract key structural risks
        lines.append("")
        lines.append("Structural risks from dream analysis:")
        bridge_match = re.search(r"(\d+)\s*(?:critical\s*)?fragile\s*bridge", dream_text, re.IGNORECASE)
        orphan_match = re.search(r"(\d+)\s*orphan", dream_text, re.IGNORECASE)
        hub_matches = re.findall(r'"([^"]+)"\s*routes?\s*(\d+)%', dream_text)

        if bridge_match:
            lines.append(f"  - {bridge_match.group(1)} fragile bridges (zero alternative paths)")
        if orphan_match:
            lines.append(f"  - {orphan_match.group(1)} orphan nodes (degree 1)")
        for name, pct in hub_matches[:2]:
            lines.append(f'  - "{name}" routes {pct}% of shortest paths')

    lines.append("")
    lines.append("Use this context when scoring UNIQUENESS (avoid duplicating over-served areas) "
                 "and RISK (flag entries in fragile or contradicted areas).")

    return "\n".join(lines)


def main():
    print("[heimdall-graph-context] Generating context for evaluation agent...")

    report = load_health_report()
    dream_text = load_dream_proposals()

    if not report and not dream_text:
        print("  No health report or dream proposals found.")
        print("  Run graph-health-check.py first, then re-run this script.")
        return 1

    context = generate_context(report, dream_text)

    META_DIR.mkdir(parents=True, exist_ok=True)
    output_path = META_DIR / "heimdall-graph-context.md"
    with open(output_path, "w") as f:
        f.write(context)

    # Check token estimate (rough: 1 token ~ 4 chars)
    estimated_tokens = len(context) // 4
    print(f"  Written to: {output_path}")
    print(f"  Estimated tokens: ~{estimated_tokens}")

    if estimated_tokens > 300:
        print(f"  WARNING: Context exceeds 200 token target ({estimated_tokens} estimated). Consider trimming.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
