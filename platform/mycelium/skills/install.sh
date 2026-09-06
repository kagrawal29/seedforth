#!/bin/bash
# Install Claude Code skills to ~/.claude/skills/
# Idempotent: safe to run multiple times

set -e

SKILLS_DIR="$( cd "$(dirname "${BASH_SOURCE[0]}")" && pwd )"
TARGET_DIR="${HOME}/.claude/skills"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy all .md files from skills/ to ~/.claude/skills/
for skill in "$SKILLS_DIR"/*.md; do
    if [ -f "$skill" ]; then
        skill_name=$(basename "$skill")
        cp "$skill" "$TARGET_DIR/$skill_name"
        echo "Installed: $skill_name"
    fi
done

echo "Claude Code skills installed to $TARGET_DIR"
echo "Skills will activate automatically on next Claude Code session."
