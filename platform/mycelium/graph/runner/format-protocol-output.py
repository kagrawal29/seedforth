#!/usr/bin/env python3
"""
Format protocol output JSON for human readability.

If results array exists with pipe-delimited strings, format them nicely.
Otherwise, print JSON.
"""
import json
import sys

try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)

if "results" not in data or not data["results"]:
    print(json.dumps(data, indent=2))
    sys.exit(0)

# Format results
for row in data["results"]:
    if not isinstance(row, list) or len(row) == 0:
        continue

    cell = row[0]
    if not isinstance(cell, str):
        continue

    if '|' not in cell:
        print(f"  {cell}")
        continue

    parts = cell.split('|', 2)
    if len(parts) < 2:
        print(f"  {cell}")
        continue

    name, status = parts[0], parts[1]
    msg = parts[2] if len(parts) > 2 else ""

    # Color code by status
    if status == "success" or status == "ok":
        color = "\033[32m"  # green
    elif status == "info":
        color = "\033[33m"  # yellow
    else:
        color = "\033[31m"  # red
    reset = "\033[0m"

    print(f"  {color}[{status}]{reset} {name}: {msg}")
