#!/usr/bin/env python3
"""
Context generation orchestrator.

Runs context-gen.py, validates output files exist, prints summary.
"""

import asyncio
import subprocess
import sys
import yaml
from pathlib import Path


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    return yaml.safe_load(config_path.read_text())


def main():
    root = Path(__file__).parent.parent
    context_dir = root / "distribution" / "person-context"
    config = load_config()

    # Ensure output directory exists
    context_dir.mkdir(parents=True, exist_ok=True)

    # Run the context generation agent
    print("=== Running context generation agent ===")
    result = subprocess.run(
        [sys.executable, str(root / "agents" / "context-gen.py")],
        cwd=str(root),
        env={**dict(__import__("os").environ), "PYTHONPATH": str(root)},
    )

    if result.returncode != 0:
        print(f"context-gen.py exited with code {result.returncode}")
        sys.exit(1)

    # Validate output
    print("\n=== Validating context files ===")
    team_names = [m["name"] for m in config["team"]]
    generated = []
    skipped = []

    for name in team_names:
        context_file = context_dir / f"{name}.md"
        if context_file.exists():
            size = context_file.stat().st_size
            # Rough token estimate: ~4 chars per token
            est_tokens = size // 4
            status = "OK" if est_tokens <= 600 else f"WARN: ~{est_tokens} tokens (target: ~500)"
            print(f"  {name}.md -- {size} bytes, ~{est_tokens} tokens -- {status}")
            generated.append(name)
        else:
            print(f"  {name}.md -- not generated (no demand data or skipped)")
            skipped.append(name)

    print(f"\n=== Summary ===")
    print(f"  Generated: {len(generated)} ({', '.join(generated)})")
    if skipped:
        print(f"  Skipped:   {len(skipped)} ({', '.join(skipped)})")
    print(f"  Output:    {context_dir}/")


if __name__ == "__main__":
    main()
