#!/usr/bin/env python3
"""Remove duplicate Run 5 sections, keeping only the last occurrence."""
import pathlib

files = [
    "/workspace/maverick-meta/signals/langsmith/2026-04-10-auto.md",
    "/workspace/maverick-meta/signals/github/2026-04-10-auto.md",
    "/workspace/maverick-meta/signals/artifacts/2026-04-10-auto.md",
    "/workspace/maverick-meta/signals/delivery/2026-04-10.md",
]

for filepath in files:
    p = pathlib.Path(filepath)
    text = p.read_text()

    # Split on the run 5 divider
    marker = "\n\n---\n## Run 5\n\n"
    parts = text.split(marker)

    if len(parts) <= 2:
        print(f"{p.name}: OK (no duplicates)")
        continue

    # Keep everything before first Run5 + last Run5 section
    base = parts[0]
    last_run5 = parts[-1]
    new_text = base + marker + last_run5

    p.write_text(new_text)
    print(f"{p.name}: Fixed ({len(parts)-1} Run5 sections -> 1)")
