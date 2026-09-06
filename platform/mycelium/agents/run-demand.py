#!/usr/bin/env python3
"""
Run Demand — orchestrator for the demand engine pipeline.

No LLM. Runs the demand-engine agent, validates output, prints summary.

Usage:
    python3 agents/run-demand.py
    python3 agents/run-demand.py --dry-run   # validate existing output only
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime


ROOT = Path(__file__).parent.parent
DEMAND_DIR = ROOT / "signals" / "demand"
CONFIG_PATH = ROOT / "config.yaml"


def load_team_names() -> list[str]:
    """Load team member names from config.yaml."""
    import yaml
    config = yaml.safe_load(CONFIG_PATH.read_text())
    return [m["name"] for m in config["team"]]


def run_demand_engine() -> bool:
    """Run the demand-engine agent. Returns True on success."""
    engine_path = ROOT / "agents" / "demand-engine.py"
    print(f"[run-demand] Running demand engine...")
    print(f"  Script: {engine_path}")
    print(f"  Time: {datetime.now().isoformat()}")
    print()

    result = subprocess.run(
        [sys.executable, str(engine_path)],
        cwd=str(ROOT),
        capture_output=False,  # stream output live
    )
    return result.returncode == 0


def validate_output(team_names: list[str]) -> dict:
    """Validate demand output files exist and are valid JSON."""
    results = {
        "valid": True,
        "persons": {},
        "cross_person": False,
        "errors": [],
    }

    for name in team_names:
        path = DEMAND_DIR / f"{name}-demand.json"
        if not path.exists():
            results["valid"] = False
            results["errors"].append(f"Missing: {path.name}")
            results["persons"][name] = None
            continue

        try:
            data = json.loads(path.read_text())
            results["persons"][name] = data
        except json.JSONDecodeError as e:
            results["valid"] = False
            results["errors"].append(f"Invalid JSON in {path.name}: {e}")
            results["persons"][name] = None

    cross_path = DEMAND_DIR / "cross-person-demands.json"
    if cross_path.exists():
        try:
            json.loads(cross_path.read_text())
            results["cross_person"] = True
        except json.JSONDecodeError as e:
            results["valid"] = False
            results["errors"].append(f"Invalid JSON in cross-person-demands.json: {e}")
    else:
        results["valid"] = False
        results["errors"].append("Missing: cross-person-demands.json")

    return results


def print_summary(validation: dict):
    """Print a human-readable summary of the demand map."""
    print()
    print("=" * 60)
    print("  DEMAND MAP SUMMARY")
    print("=" * 60)
    print()

    total_questions = 0
    total_gaps = 0
    total_clusters = 0

    for name, data in validation["persons"].items():
        if data is None:
            print(f"  {name}: [ERROR - no valid output]")
            continue

        clusters = data.get("question_clusters", [])
        summary = data.get("summary", {})
        q_count = summary.get("total_questions", 0)
        gap_count = summary.get("gaps", 0)
        frustration = summary.get("highest_frustration_domain")

        total_questions += q_count
        total_gaps += gap_count
        total_clusters += len(clusters)

        status = f"{q_count} questions, {len(clusters)} clusters, {gap_count} gaps"
        if frustration:
            status += f", frustration: {frustration}"
        print(f"  {name}: {status}")

        # Show top clusters
        for c in sorted(clusters, key=lambda x: x.get("frequency", 0), reverse=True)[:3]:
            freq = c.get("frequency", 0)
            frust = c.get("frustration", "?")
            gap = " [GAP]" if c.get("gap_signal") else ""
            print(f"    - {c.get('representative_question', '?')} (x{freq}, {frust}){gap}")

    print()
    print(f"  Total: {total_questions} questions, {total_clusters} clusters, {total_gaps} gaps")

    if validation["cross_person"]:
        cross_path = DEMAND_DIR / "cross-person-demands.json"
        cross_data = json.loads(cross_path.read_text())
        cross_demands = cross_data.get("cross_demands", [])
        if cross_demands:
            print()
            print("  Cross-person connections:")
            for cd in cross_demands:
                persons = " + ".join(cd.get("persons", []))
                concept = cd.get("shared_concept", "?")
                print(f"    - {persons}: {concept}")

    print()
    if validation["errors"]:
        print("  Errors:")
        for e in validation["errors"]:
            print(f"    - {e}")
        print()

    if validation["valid"]:
        print("  Status: ALL OUTPUT VALID")
    else:
        print("  Status: VALIDATION FAILED")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run the demand engine pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Validate existing output only, don't run the engine")
    args = parser.parse_args()

    team_names = load_team_names()
    print(f"[run-demand] Team: {', '.join(team_names)}")

    if not args.dry_run:
        success = run_demand_engine()
        if not success:
            print("[run-demand] Demand engine failed.")
            sys.exit(1)

    validation = validate_output(team_names)
    print_summary(validation)

    if not validation["valid"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
