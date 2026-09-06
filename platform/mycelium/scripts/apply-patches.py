#!/usr/bin/env python3
"""
Apply pending patches to procedural knowledge entries.

Reads YAML patch files from knowledge/meta/pending-patches/,
applies operations to target entries, increments version,
and archives applied patches.

Usage: python3 scripts/apply-patches.py [--dry-run]
"""

import os
import re
import sys
import yaml
import shutil
from datetime import datetime
from pathlib import Path

PENDING_DIR = Path("knowledge/meta/pending-patches")
APPLIED_DIR = Path("knowledge/meta/applied-patches")
TODAY = datetime.now().strftime("%Y-%m-%d")


def parse_patch(filepath):
    """Read a YAML patch file."""
    with open(filepath, "r") as f:
        content = f.read()
    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        return None, None
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, None
    body = match.group(2).strip()
    return meta, body


def parse_entry(filepath):
    """Read a knowledge entry, return frontmatter dict and full content."""
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


def apply_insert_after_step(content, step_num, insert_text):
    """Insert text after a numbered step in ## Procedure."""
    # Find the step line
    pattern = rf"(^{step_num}\.\s+.*(?:\n(?!\d+\.).*)*)"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return None, f"Step {step_num} not found"
    end = match.end()
    new_content = content[:end] + "\n" + insert_text + content[end:]
    return new_content, None


def apply_add_pitfall(content, pitfall_text):
    """Add a pitfall to ## Pitfalls section."""
    if "## Pitfalls" not in content:
        return None, "No ## Pitfalls section found"
    # Insert before ## Verification
    if "## Verification" in content:
        content = content.replace("## Verification", pitfall_text + "\n\n## Verification")
    else:
        content += "\n" + pitfall_text
    return content, None


def apply_add_verification(content, check_text):
    """Add a verification check to ## Verification section."""
    if "## Verification" not in content:
        return None, "No ## Verification section found"
    # Find the last checkbox in Verification and add after it
    lines = content.split("\n")
    last_check_idx = -1
    in_verification = False
    for i, line in enumerate(lines):
        if line.strip().startswith("## Verification"):
            in_verification = True
        elif in_verification and line.strip().startswith("- ["):
            last_check_idx = i
        elif in_verification and line.strip().startswith("##"):
            break
    if last_check_idx == -1:
        return None, "No checkboxes found in Verification"
    lines.insert(last_check_idx + 1, check_text)
    return "\n".join(lines), None


def apply_replace_step(content, step_num, new_text):
    """Replace a numbered step in ## Procedure."""
    pattern = rf"^{step_num}\.\s+.*(?:\n(?!\d+\.).*)*"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return None, f"Step {step_num} not found"
    new_content = content[:match.start()] + new_text + content[match.end():]
    return new_content, None


def increment_version(content):
    """Increment the version field in frontmatter."""
    match = re.search(r"version:\s*(\d+)", content)
    if match:
        old_ver = int(match.group(1))
        content = content.replace(f"version: {old_ver}", f"version: {old_ver + 1}")
    return content


def main():
    dry_run = "--dry-run" in sys.argv

    if not PENDING_DIR.exists():
        print("No pending patches directory.")
        return 0

    patches = sorted(PENDING_DIR.glob("*.yaml")) + sorted(PENDING_DIR.glob("*.yml"))
    if not patches:
        print("No pending patches.")
        return 0

    print(f"Found {len(patches)} pending patches.")
    applied = 0
    failed = 0

    for patch_file in patches:
        meta, body = parse_patch(patch_file)
        if not meta:
            print(f"  SKIP {patch_file.name}: invalid YAML")
            failed += 1
            continue

        target = meta.get("target", "")
        operation = meta.get("operation", "")
        step = meta.get("step")

        if not os.path.exists(target):
            print(f"  SKIP {patch_file.name}: target not found: {target}")
            failed += 1
            continue

        entry_meta, content = parse_entry(target)
        if not entry_meta:
            print(f"  SKIP {patch_file.name}: cannot parse target entry")
            failed += 1
            continue

        # Apply the operation
        new_content = None
        error = None

        if operation == "insert-after-step" and step:
            new_content, error = apply_insert_after_step(content, step, body)
        elif operation == "add-pitfall":
            new_content, error = apply_add_pitfall(content, body)
        elif operation == "add-verification":
            new_content, error = apply_add_verification(content, body)
        elif operation == "replace-step" and step:
            new_content, error = apply_replace_step(content, step, body)
        else:
            error = f"Unknown operation: {operation}"

        if error:
            print(f"  FAIL {patch_file.name}: {error}")
            failed += 1
            continue

        # Increment version
        new_content = increment_version(new_content)

        # Check char limit for procedures
        if entry_meta.get("type") == "procedure":
            body_content = re.sub(r"^---\n.*?\n---\n?", "", new_content, flags=re.DOTALL)
            if len(body_content) > 3575:
                print(f"  WARN {patch_file.name}: patch would exceed 3575 chars ({len(body_content)}). Needs manual curation.")
                failed += 1
                continue

        if dry_run:
            print(f"  [dry-run] Would apply {patch_file.name} to {target} ({operation})")
        else:
            with open(target, "w") as f:
                f.write(new_content)

            # Archive the patch
            APPLIED_DIR.mkdir(parents=True, exist_ok=True)
            archive_name = f"{TODAY}-{patch_file.stem}.yaml"
            shutil.move(str(patch_file), str(APPLIED_DIR / archive_name))
            print(f"  APPLIED {patch_file.name} → {target} ({operation})")

        applied += 1

    print(f"\nDone: {applied} applied, {failed} failed.")
    return failed


if __name__ == "__main__":
    sys.exit(main())
