#!/usr/bin/env python3
"""
Convergence Loop: generate → diff → score → analyze gap → enrich → repeat.

Runs until all generated files match actual code at 100%.
Each iteration stores CodeMatchScore nodes in the graph.
Gaps become enrichment actions. The graph learns.

Usage:
    python3 scripts/convergence-loop.py create-deal /tmp/create-deal-actual
    python3 scripts/convergence-loop.py create-deal /tmp/create-deal-actual --max-iterations 5
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
REPO_ROOT = Path(__file__).resolve().parent.parent


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


def esc(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")[:500]


def esc_dq(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")[:500]


def generate(feature, output_dir):
    """Run the generator."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate-feature.py"),
         feature, "--output", str(output_dir)],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "FALKORDB_HOST": FALKORDB_HOST},
    )
    return result.returncode == 0, result.stdout


def diff_files(generated_dir, actual_dir):
    """Diff each generated file against actual. Returns list of scores."""
    scores = []
    gen_path = Path(generated_dir)
    act_path = Path(actual_dir)

    for gen_file in sorted(gen_path.rglob("*.ts")) + sorted(gen_path.rglob("*.tsx")):
        rel = str(gen_file.relative_to(gen_path))
        actual_file = act_path / rel

        if not actual_file.exists():
            scores.append({
                "file": rel,
                "match_pct": 0,
                "diff_lines": 0,
                "total_lines": len(gen_file.read_text().split("\n")),
                "status": "no_actual",
                "gaps": [],
            })
            continue

        # Run diff
        result = subprocess.run(
            ["diff", str(gen_file), str(actual_file)],
            capture_output=True, text=True,
        )

        actual_lines = len(actual_file.read_text().split("\n"))
        gen_lines = len(gen_file.read_text().split("\n"))

        if result.returncode == 0:
            scores.append({
                "file": rel,
                "match_pct": 100,
                "diff_lines": 0,
                "total_lines": actual_lines,
                "status": "match",
                "gaps": [],
            })
            continue

        # Analyze gaps
        diff_output = result.stdout
        added = [l[2:] for l in diff_output.split("\n") if l.startswith("> ")]
        removed = [l[2:] for l in diff_output.split("\n") if l.startswith("< ")]
        diff_line_count = len(added) + len(removed)

        match_pct = max(0, 100 - diff_line_count * 100 // max(actual_lines * 2, 1))

        # Categorize gaps
        gaps = []
        for line in removed:
            line = line.strip()
            if "None" in line:
                gaps.append("null_property")
            elif "className" in line:
                gaps.append("css_mismatch")
            elif line.startswith("import"):
                gaps.append("import_missing")
            elif line.startswith("interface") or line.startswith("type "):
                gaps.append("type_mismatch")
            elif "<" in line and ">" in line:
                gaps.append("jsx_structure")
            elif line.startswith("const ") or line.startswith("function "):
                gaps.append("logic_missing")

        # Deduplicate gap types
        gap_types = list(dict.fromkeys(gaps))

        scores.append({
            "file": rel,
            "match_pct": match_pct,
            "diff_lines": diff_line_count,
            "total_lines": actual_lines,
            "status": "partial",
            "gaps": gap_types[:5],
        })

    return scores


def store_scores(graph, scores, iteration, feature):
    """Store CodeMatchScore nodes in the graph."""
    ts = datetime.now(timezone.utc).isoformat()

    for score in scores:
        score_id = f"score-{feature}-{score['file'].replace('/', '-')}-iter{iteration}"
        gaps_str = ", ".join(score["gaps"][:5])

        graph.query(
            f'MERGE (cms:CodeMatchScore {{node_id: "{esc(score_id)}"}}) '
            f'SET cms.file = "{esc(score["file"])}", '
            f'cms.match_pct = {score["match_pct"]}, '
            f'cms.diff_lines = {score["diff_lines"]}, '
            f'cms.total_lines = {score["total_lines"]}, '
            f'cms.status = "{score["status"]}", '
            f'cms.gaps = "{esc(gaps_str)}", '
            f'cms.iteration = {iteration}, '
            f'cms.feature = "{feature}", '
            f'cms.timestamp = "{esc(ts)}", '
            f'cms.file_type = "code-match-score"'
        )

    # Store iteration summary
    avg_match = sum(s["match_pct"] for s in scores) / len(scores) if scores else 0
    perfect = sum(1 for s in scores if s["match_pct"] == 100)
    total = len(scores)

    graph.query(
        f'MERGE (ci:ConvergenceIteration {{node_id: "conv-{feature}-iter{iteration}"}}) '
        f'SET ci.feature = "{feature}", '
        f'ci.iteration = {iteration}, '
        f'ci.avg_match = {round(avg_match, 1)}, '
        f'ci.perfect_files = {perfect}, '
        f'ci.total_files = {total}, '
        f'ci.timestamp = "{esc(ts)}", '
        f'ci.file_type = "convergence-iteration"'
    )

    # Link to previous iteration
    if iteration > 1:
        graph.query(
            f'MATCH (curr:ConvergenceIteration {{node_id: "conv-{feature}-iter{iteration}"}}), '
            f'(prev:ConvergenceIteration {{node_id: "conv-{feature}-iter{iteration - 1}"}}) '
            f'MERGE (curr)-[:FOLLOWS]->(prev)'
        )


def analyze_and_fix(graph, scores, feature):
    """Analyze gaps and attempt automatic fixes in the graph."""
    fixes_applied = 0

    for score in scores:
        if score["match_pct"] == 100:
            continue

        comp_name = score["file"].replace("ui/", "").replace(".tsx", "")
        comp_id = f"ui-create-deal-{comp_name.lower()}"

        for gap in score["gaps"]:
            if gap == "null_property":
                # Check for None props and fix
                r = graph.query(
                    f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[r:ACCEPTS_PROP]->(p:Prop) '
                    f'WHERE p.name IS NULL OR p.type IS NULL '
                    f'RETURN p.node_id'
                )
                for row in r.result_set:
                    graph.query(
                        f'MATCH (p:Prop {{node_id: "{row[0]}"}}) DETACH DELETE p'
                    )
                    fixes_applied += 1

                # Check for None pattern properties
                r = graph.query(
                    f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[:USES_PATTERN]->(pat:UIPattern) '
                    f'WHERE pat.title_class IS NULL '
                    f'RETURN pat.node_id, pat.name'
                )
                for row in r.result_set:
                    # Set default classes from the pattern name
                    pat_name = row[1] or "default"
                    graph.query(
                        f'MATCH (pat:UIPattern {{node_id: "{row[0]}"}}) '
                        f'SET pat.title_class = "mb-1 text-sm font-semibold text-foreground", '
                        f'pat.description_class = "mb-3 text-xs leading-relaxed text-foreground-secondary"'
                    )
                    fixes_applied += 1

    return fixes_applied


def run_convergence(feature, actual_dir, max_iterations=10):
    """Run the convergence loop."""
    graph = get_graph()
    output_dir = f"/tmp/generated-{feature}"

    print(f"[convergence] Feature: {feature}")
    print(f"[convergence] Actual: {actual_dir}")
    print(f"[convergence] Max iterations: {max_iterations}")
    print()

    for iteration in range(1, max_iterations + 1):
        print(f"{'=' * 60}")
        print(f"  ITERATION {iteration}")
        print(f"{'=' * 60}")

        # Step 1: Generate
        ok, output = generate(feature, output_dir)
        if not ok:
            print(f"  [generate] FAILED")
            break

        gen_lines = output.split("\n")
        file_count = sum(1 for l in gen_lines if l.strip().startswith("ui/") or
                        l.strip().startswith("lib/") or l.strip().startswith("model/") or
                        l.strip().startswith("index"))
        print(f"  [generate] {file_count} files generated")

        # Step 2: Diff
        scores = diff_files(output_dir, actual_dir)

        # Step 3: Score
        store_scores(graph, scores, iteration, feature)

        avg_match = sum(s["match_pct"] for s in scores) / len(scores) if scores else 0
        perfect = sum(1 for s in scores if s["match_pct"] == 100)

        print(f"  [score] Average: {avg_match:.0f}%, Perfect: {perfect}/{len(scores)}")
        print()

        for s in sorted(scores, key=lambda x: x["match_pct"]):
            gaps = f" gaps: {', '.join(s['gaps'])}" if s["gaps"] else ""
            print(f"    {'OK' if s['match_pct'] == 100 else s['match_pct']:>3}%  {s['file']}{gaps}")

        # Step 4: Check convergence
        if all(s["match_pct"] == 100 for s in scores):
            print(f"\n  [CONVERGED] All files at 100% after {iteration} iterations!")
            break

        # Step 5: Analyze and auto-fix
        fixes = analyze_and_fix(graph, scores, feature)
        if fixes:
            print(f"\n  [auto-fix] {fixes} fixes applied to graph")
        else:
            print(f"\n  [auto-fix] No automatic fixes available")
            print(f"  Remaining gaps need manual enrichment or template evolution")

        print()

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"  CONVERGENCE SUMMARY")
    print(f"{'=' * 60}")

    r = graph.query(
        f'MATCH (ci:ConvergenceIteration {{feature: "{feature}"}}) '
        f'RETURN ci.iteration, ci.avg_match, ci.perfect_files, ci.total_files '
        f'ORDER BY ci.iteration'
    )
    print(f"\n  Iteration history:")
    for row in r.result_set:
        print(f"    Iter {row[0]}: {row[1]}% avg, {row[2]}/{row[3]} perfect")

    # Current gap summary
    print(f"\n  Remaining gaps:")
    r = graph.query(
        f'MATCH (cms:CodeMatchScore {{feature: "{feature}"}}) '
        f'WHERE cms.match_pct < 100 '
        f'AND cms.iteration = (MATCH (ci:ConvergenceIteration {{feature: "{feature}"}}) '
        f'RETURN max(ci.iteration))[0] '
        f'RETURN cms.file, cms.match_pct, cms.gaps'
    )
    # Simpler query
    latest_scores = [s for s in scores if s["match_pct"] < 100]
    for s in latest_scores:
        print(f"    {s['file']}: {s['match_pct']}% — {', '.join(s['gaps'])}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("feature", help="Feature name")
    parser.add_argument("actual_dir", help="Directory with actual source files")
    parser.add_argument("--max-iterations", type=int, default=5)
    args = parser.parse_args()

    run_convergence(args.feature, args.actual_dir, args.max_iterations)
