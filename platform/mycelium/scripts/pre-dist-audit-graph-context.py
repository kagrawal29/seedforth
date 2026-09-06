#!/usr/bin/env python3
"""
Pre-Distribution Audit Graph Context -- generates a detailed graph health
summary for the pre-distribution audit agent.

More detailed than the Heimdall context. Highlights:
  - Contradictions that could reach users
  - Dangerous pruning candidates
  - Coverage gaps where demand exists but knowledge doesn't
  - Structural fragility in high-demand areas

Reads:
  - knowledge/meta/graph-health-report.md
  - knowledge/meta/dream-proposals.md (if available)

Output: knowledge/meta/pre-dist-graph-context.md

Does NOT modify the pre-dist audit agent. Generates a context file
that can be included in the agent's prompt.

Usage: python3 scripts/pre-dist-audit-graph-context.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
META_DIR = REPO_ROOT / "knowledge" / "meta"


def load_file(name):
    """Load a file from META_DIR, return None if missing."""
    path = META_DIR / name
    if not path.exists():
        return None
    with open(path) as f:
        return f.read()


def extract_section(report, section_name):
    """Extract content between ## section_name and the next ## heading."""
    pattern = rf"## {re.escape(section_name)}\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, report, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_table_rows(section_text):
    """Extract data rows from a markdown table (skip header and separator)."""
    lines = section_text.strip().split("\n")
    rows = []
    for line in lines:
        if line.startswith("| ") and not line.startswith("|---"):
            cells = [c.strip() for c in line.split("|")[1:-1]]
            rows.append(cells)
    # Skip the header row (first row)
    return rows[1:] if len(rows) > 1 else []


def generate_context(report, dream_text):
    """Build detailed graph context for pre-dist audit."""
    lines = []
    lines.append("## Graph Health Context (for pre-distribution audit)")
    lines.append("")

    if not report:
        lines.append("No graph health report available. Run graph-health-check.py first.")
        lines.append("")
        lines.append("Without this data, the audit cannot verify:")
        lines.append("- Whether distributed entries contradict existing knowledge")
        lines.append("- Whether coverage gaps are being addressed")
        lines.append("- Whether pruning candidates are being sent to users")
        return "\n".join(lines)

    # Summary
    summary_section = extract_section(report, "Summary")
    if summary_section:
        lines.append("### Overall State")
        for line in summary_section.split("\n"):
            if line.strip().startswith("- "):
                lines.append(line.strip())
        lines.append("")

    # Contradictions -- critical for pre-dist
    contradictions_section = extract_section(report, "Contradictions")
    contradiction_rows = extract_table_rows(contradictions_section)
    if contradiction_rows:
        lines.append("### CONTRADICTIONS (block distribution if unresolved)")
        lines.append("")
        high_severity = [r for r in contradiction_rows if len(r) >= 4 and r[3].strip() == "HIGH"]
        medium_severity = [r for r in contradiction_rows if len(r) >= 4 and r[3].strip() == "MEDIUM"]

        if high_severity:
            lines.append(f"HIGH severity ({len(high_severity)}):")
            for r in high_severity:
                lines.append(f"  - {r[0]} vs {r[1]}: {r[2]}")
        if medium_severity:
            lines.append(f"MEDIUM severity ({len(medium_severity)}):")
            for r in medium_severity:
                lines.append(f"  - {r[0]} vs {r[1]}: {r[2]}")

        lines.append("")
        lines.append("ACTION: Do NOT distribute entries involved in HIGH contradictions "
                     "until resolved. MEDIUM contradictions need review.")
        lines.append("")
    else:
        lines.append("### Contradictions: None detected")
        lines.append("")

    # Pruning candidates -- don't distribute things about to be pruned
    pruning_section = extract_section(report, "Pruning Candidates")
    pruning_rows = extract_table_rows(pruning_section)
    if pruning_rows:
        lines.append("### PRUNING CANDIDATES (do not distribute)")
        lines.append("")
        for r in pruning_rows:
            if len(r) >= 4:
                lines.append(f"  - {r[0]}: {r[1]} (confidence: {r[2]}, rec: {r[3]})")
        lines.append("")
        lines.append("ACTION: Skip these entries in distribution. They are candidates for removal.")
        lines.append("")

    # Coverage gaps -- prioritize filling these
    coverage_section = extract_section(report, "Coverage Gaps")
    coverage_rows = extract_table_rows(coverage_section)
    if coverage_rows:
        lines.append("### COVERAGE GAPS (high-priority for new entries)")
        lines.append("")
        for r in coverage_rows[:5]:  # Top 5 gaps
            if len(r) >= 6:
                lines.append(f"  - {r[0]} (person: {r[1]}, freq: {r[2]}) -- {r[4]}")
        if len(coverage_rows) > 5:
            lines.append(f"  ... and {len(coverage_rows) - 5} more gaps")
        lines.append("")
        lines.append("ACTION: New entries that fill these gaps should get priority in distribution.")
        lines.append("")

    # Staleness -- urgent stale entries with demand
    staleness_section = extract_section(report, "Staleness")
    staleness_rows = extract_table_rows(staleness_section)
    urgent_stale = [r for r in staleness_rows if len(r) >= 5 and "URGENT" in r[4]]
    if urgent_stale:
        lines.append("### URGENT STALE (have demand but outdated)")
        lines.append("")
        for r in urgent_stale:
            lines.append(f"  - {r[0]}: {r[1]} days old, demand: {r[2]}")
        lines.append("")
        lines.append("ACTION: These entries may have outdated information being served to users. "
                     "Flag for immediate refresh.")
        lines.append("")

    # Graph structural risks
    if dream_text:
        lines.append("### Structural Risks")
        lines.append("")

        bridge_match = re.search(r"(\d+)\s*(?:critical\s*)?fragile\s*bridge", dream_text, re.IGNORECASE)
        orphan_match = re.search(r"(\d+)\s*orphan", dream_text, re.IGNORECASE)
        hub_matches = re.findall(r'"([^"]+)"\s*routes?\s*(\d+)%', dream_text)

        if bridge_match:
            lines.append(f"- {bridge_match.group(1)} fragile bridges -- "
                         "single points of failure in the knowledge graph")
        if orphan_match:
            lines.append(f"- {orphan_match.group(1)} orphan nodes -- "
                         "isolated knowledge not connected to the main graph")
        for name, pct in hub_matches:
            if int(pct) > 25:
                lines.append(f'- Hub dependency: "{name}" carries {pct}% of traffic -- '
                             "single point of failure risk")

        lines.append("")
        lines.append("ACTION: New entries that bridge orphans or create alternative paths "
                     "around fragile bridges should be prioritized.")
        lines.append("")

    # Effectiveness issues
    effectiveness_section = extract_section(report, "Effectiveness")
    effectiveness_rows = extract_table_rows(effectiveness_section)
    ignored = [r for r in effectiveness_rows if len(r) >= 6 and r[5].strip() == "IGNORED"]
    if ignored:
        lines.append("### IGNORED ENTRIES (surfaced but never cited)")
        lines.append("")
        for r in ignored[:5]:
            lines.append(f"  - {r[0]}: surfaced {r[1]}x, cited {r[2]}x")
        lines.append("")
        lines.append("ACTION: Consider deprioritizing these in distribution or rewriting for relevance.")
        lines.append("")

    # Urgent items from report
    urgent_section = extract_section(report, "Urgent Items")
    if urgent_section and "No urgent items" not in urgent_section:
        lines.append("### Urgent Items")
        lines.append("")
        for line in urgent_section.split("\n"):
            if line.strip() and line.strip()[0].isdigit():
                lines.append(line.strip())
        lines.append("")

    return "\n".join(lines)


def main():
    print("[pre-dist-audit-graph-context] Generating context for pre-distribution audit...")

    report = load_file("graph-health-report.md")
    dream_text = load_file("dream-proposals.md")

    if not report and not dream_text:
        print("  No health report or dream proposals found.")
        print("  Run graph-health-check.py first, then re-run this script.")
        return 1

    context = generate_context(report, dream_text)

    META_DIR.mkdir(parents=True, exist_ok=True)
    output_path = META_DIR / "pre-dist-graph-context.md"
    with open(output_path, "w") as f:
        f.write(context)

    print(f"  Written to: {output_path}")
    print(f"  Size: {len(context)} chars (~{len(context)//4} tokens)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
