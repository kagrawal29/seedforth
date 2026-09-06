#!/usr/bin/env python3
"""
Intelligent Convergence Loop: generate → diff → LLM analyzes → enriches graph → repeat.

The LLM reads the diff between generated and actual code, understands WHY they differ,
and writes Cypher MERGE statements to fix the graph. The generator then produces
code that's closer to actual. Loop until 100%.

Usage:
    python3 scripts/convergence-intelligent.py create-deal /tmp/create-deal-actual
    python3 scripts/convergence-intelligent.py create-deal /tmp/create-deal-actual --file ui/DealCreatedSuccess.tsx
    python3 scripts/convergence-intelligent.py create-deal /tmp/create-deal-actual --max-iterations 5
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from falkordb import FalkorDB
    import anthropic
except ImportError as e:
    print(f"ERROR: pip install falkordb anthropic — {e}", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
REPO_ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-sonnet-4-20250514"


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


def esc(s):
    if s is None: return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")[:500]


def generate(feature, output_dir):
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "generate-feature.py"),
         feature, "--output", str(output_dir)],
        capture_output=True, text=True, timeout=60,
        env={**os.environ, "FALKORDB_HOST": FALKORDB_HOST},
    )
    return result.returncode == 0


def diff_file(generated_path, actual_path):
    if not Path(actual_path).exists():
        return None, 0, 0
    result = subprocess.run(
        ["diff", "-u", str(generated_path), str(actual_path)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return "", 100, 0

    actual_lines = len(Path(actual_path).read_text().split("\n"))
    diff_lines = len([l for l in result.stdout.split("\n")
                      if l.startswith("+") or l.startswith("-")])
    match_pct = max(0, 100 - diff_lines * 100 // max(actual_lines * 2, 1))
    return result.stdout, match_pct, diff_lines


def get_component_graph_context(graph, comp_id):
    """Get everything the graph knows about a component."""
    context_parts = []

    # Component node
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{comp_id}"}}) RETURN c'
    )
    if r.result_set:
        props_dict = r.result_set[0][0].properties
        context_parts.append(f"Component: {props_dict}")

    # Props
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[r:ACCEPTS_PROP]->(p:Prop) '
        f'RETURN p.name, p.type, p.required, r.prop_order ORDER BY r.prop_order'
    )
    if r.result_set:
        context_parts.append(f"Props: {r.result_set}")

    # Imports
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[:USES]->(i) '
        f'RETURN labels(i)[0], i.name, i.import_path'
    )
    if r.result_set:
        context_parts.append(f"Imports: {r.result_set}")

    # Pattern
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[:USES_PATTERN]->(pat:UIPattern) '
        f'RETURN pat'
    )
    if r.result_set:
        context_parts.append(f"Pattern: {r.result_set[0][0].properties}")

    # Copy
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[:HAS_COPY]->(cp:CopyText) '
        f'RETURN cp'
    )
    if r.result_set:
        context_parts.append(f"Copy: {r.result_set[0][0].properties}")

    # Logic
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[:HAS_LOGIC]->(l:DerivedLogic) '
        f'RETURN l.code, l.description'
    )
    if r.result_set:
        context_parts.append(f"Logic: {r.result_set}")

    # Types
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{comp_id}"}})-[:DEPENDS_ON_TYPE]->(t:TypeDef) '
        f'RETURN t.name, t.source'
    )
    if r.result_set:
        context_parts.append(f"Types: {r.result_set}")

    return "\n".join(context_parts)


def llm_analyze_and_fix(graph, file_path, generated_code, actual_code, diff_text, graph_context, comp_id):
    """Ask Claude to analyze the diff and write Cypher to fix the graph."""

    client = anthropic.Anthropic()

    prompt = f"""You are enriching a FalkorDB knowledge graph so that a code generator can produce React components that match actual production code.

COMPONENT: {file_path}
COMPONENT NODE ID: {comp_id}

CURRENT GRAPH STATE FOR THIS COMPONENT:
{graph_context}

GENERATED CODE (from graph):
```tsx
{generated_code}
```

ACTUAL CODE (production):
```tsx
{actual_code}
```

DIFF (what's different):
```
{diff_text[:3000]}
```

Your task: Write FalkorDB Cypher MERGE statements that will enrich the graph so the generator produces code matching the actual file.

Focus on:
1. Missing or wrong Props (name, type, required, order)
2. Missing imports (USES edges to SharedComponent/IconImport nodes)
3. Wrong UIPattern (container classes, icon classes, etc.)
4. Missing or wrong CopyText (title, description, buttons)
5. Missing DerivedLogic (computed values, lookups)
6. The JSX TEMPLATE — if the component has a fundamentally different layout than a warning-card, describe the structure

Rules:
- Use MERGE, never CREATE
- Component node_id is: {comp_id}
- For new Prop nodes, use node_id format: prop-{{comp_short}}-{{propname}}
- For CopyText, use node_id format: copy-{{comp_short}}
- For DerivedLogic, use node_id format: logic-{{comp_short}}-{{description}}
- For new SharedComponent/IconImport nodes, use existing node_ids if they exist (shared-import-button, icon-check-circle, etc.)
- Set prop_order on ACCEPTS_PROP edges
- If the component needs a completely different JSX template than what the generator currently supports, store the full JSX template as a property: SET c.jsx_template = "..."

Output ONLY Cypher statements. No explanation. One statement per line. Each ending with semicolon."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    cypher_text = response.content[0].text
    cost = (response.usage.input_tokens * 0.003 + response.usage.output_tokens * 0.015) / 1000

    # Extract and execute Cypher statements
    statements = []
    for line in cypher_text.split("\n"):
        line = line.strip()
        if line and (line.startswith("MERGE") or line.startswith("MATCH") or line.startswith("SET")):
            # Clean up — remove trailing semicolons for FalkorDB
            if line.endswith(";"):
                line = line[:-1]
            statements.append(line)

    # Execute multi-line statements (MATCH ... MERGE ... SET ...)
    executed = 0
    errors = 0
    current_statement = []

    for line in statements:
        current_statement.append(line)
        # Execute when we hit a complete statement (MERGE+SET or standalone MERGE)
        if line.startswith("SET") or (line.startswith("MERGE") and "SET" in line):
            full = " ".join(current_statement)
            try:
                graph.query(full)
                executed += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"      Cypher error: {str(e)[:80]}")
            current_statement = []
        elif line.startswith("MERGE") and not any(l.startswith("SET") or l.startswith("MATCH") for l in current_statement[1:]):
            # Standalone MERGE
            try:
                graph.query(line)
                executed += 1
            except Exception as e:
                errors += 1
            current_statement = []

    # Execute any remaining
    if current_statement:
        full = " ".join(current_statement)
        try:
            graph.query(full)
            executed += 1
        except Exception as e:
            errors += 1

    return executed, errors, cost


def run_intelligent_convergence(feature, actual_dir, target_file=None, max_iterations=5):
    graph = get_graph()
    output_dir = f"/tmp/generated-{feature}"
    actual_path = Path(actual_dir)
    total_cost = 0.0

    print(f"[convergence] Intelligent loop with Claude in the loop")
    print(f"[convergence] Feature: {feature}")
    print(f"[convergence] Model: {MODEL}")
    print()

    for iteration in range(1, max_iterations + 1):
        print(f"{'=' * 60}")
        print(f"  ITERATION {iteration}")
        print(f"{'=' * 60}")

        # Step 1: Generate
        generate(feature, output_dir)
        gen_path = Path(output_dir)

        # Step 2: Score all files
        files_to_fix = []
        all_scores = []

        for gen_file in sorted(list(gen_path.rglob("*.tsx")) + list(gen_path.rglob("*.ts"))):
            rel = str(gen_file.relative_to(gen_path))

            if target_file and rel != target_file:
                continue

            actual_file = actual_path / rel
            diff_text, match_pct, diff_lines = diff_file(gen_file, actual_file)

            all_scores.append((rel, match_pct))

            if diff_text is None:
                continue

            if match_pct < 100:
                files_to_fix.append((rel, gen_file, actual_file, diff_text, match_pct))

        # Print scores
        avg = sum(s[1] for s in all_scores) / len(all_scores) if all_scores else 0
        perfect = sum(1 for s in all_scores if s[1] == 100)
        print(f"  [score] Average: {avg:.0f}%, Perfect: {perfect}/{len(all_scores)}")
        print()
        for rel, pct in sorted(all_scores, key=lambda x: x[1]):
            marker = "OK" if pct == 100 else f"{pct}%"
            print(f"    {marker:>5}  {rel}")

        # Check convergence
        if not files_to_fix:
            print(f"\n  [CONVERGED] All files at 100%!")
            break

        # Step 3: Pick worst file and fix it with LLM
        files_to_fix.sort(key=lambda x: x[4])  # worst first

        # Fix up to 3 files per iteration
        fix_count = min(3, len(files_to_fix))
        print(f"\n  [llm] Fixing {fix_count} files with Claude...")

        for i in range(fix_count):
            rel, gen_file, actual_file, diff_text, match_pct = files_to_fix[i]

            # Determine component ID
            comp_name = rel.replace("ui/", "").replace(".tsx", "").replace(".ts", "")
            comp_id = f"ui-create-deal-{comp_name.lower()}"

            # Get graph context
            graph_context = get_component_graph_context(graph, comp_id)

            generated_code = gen_file.read_text()
            actual_code = actual_file.read_text()

            print(f"\n    [{rel}] {match_pct}% → asking Claude...")

            executed, errors, cost = llm_analyze_and_fix(
                graph, rel, generated_code, actual_code, diff_text,
                graph_context, comp_id
            )
            total_cost += cost

            print(f"    [{rel}] {executed} Cypher executed, {errors} errors, ${cost:.4f}")

        # Store iteration
        ts = datetime.now(timezone.utc).isoformat()
        graph.query(
            f'MERGE (ci:ConvergenceIteration {{node_id: "conv-{feature}-smart-iter{iteration}"}}) '
            f'SET ci.feature = "{feature}", ci.iteration = {iteration}, '
            f'ci.avg_match = {round(avg, 1)}, ci.perfect_files = {perfect}, '
            f'ci.total_files = {len(all_scores)}, ci.cost = {round(total_cost, 4)}, '
            f'ci.timestamp = "{esc(ts)}", ci.method = "intelligent"'
        )

        print()

    # Final report
    print(f"\n{'=' * 60}")
    print(f"  CONVERGENCE REPORT")
    print(f"{'=' * 60}")
    print(f"  Iterations: {iteration}")
    print(f"  Total LLM cost: ${total_cost:.4f}")
    print(f"  Final average: {avg:.0f}%")
    print(f"  Perfect files: {perfect}/{len(all_scores)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("feature")
    parser.add_argument("actual_dir")
    parser.add_argument("--file", help="Target specific file")
    parser.add_argument("--max-iterations", type=int, default=5)
    args = parser.parse_args()

    run_intelligent_convergence(args.feature, args.actual_dir, args.file, args.max_iterations)
