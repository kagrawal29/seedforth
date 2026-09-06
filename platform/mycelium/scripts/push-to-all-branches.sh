#!/bin/bash
# Pushes shared rules to ALL branches across target repos via GitHub API
# Usage: ./scripts/push-to-all-branches.sh [--dry-run]
set -euo pipefail

DRY_RUN="${1:-}"
SHARED_DIR="distribution/shared-rules"

# Read repos from config.yaml (no hardcoded repo names)
TARGET_REPOS=$(python3 -c "
import yaml
config = yaml.safe_load(open('config.yaml'))
for r in config['repos']:
    print(f\"{r['org']}/{r['name']}\")
" 2>/dev/null)

if [ -z "$TARGET_REPOS" ]; then
  echo "Failed to read repos from config.yaml. Falling back to defaults."
  TARGET_REPOS="Qubit-Capital/VC-AI-Assoicate
Qubit-Capital/maverick-market-research"
fi

if [ ! -d "$SHARED_DIR" ]; then
  echo "No shared rules directory"
  exit 1
fi

RULE_FILES=$(find "$SHARED_DIR" -name "*.md" -type f)
if [ -z "$RULE_FILES" ]; then
  echo "No rule files to distribute"
  exit 0
fi

for FULL_REPO in $TARGET_REPOS; do
  echo "============================================"
  echo "REPO: $FULL_REPO"
  echo "============================================"

  # Get all branches
  BRANCHES=$(gh api "/repos/$FULL_REPO/branches?per_page=100" --jq '.[].name' 2>/dev/null)

  for BRANCH in $BRANCHES; do
    echo ""
    echo "  Branch: $BRANCH"

    for RULE_FILE in $RULE_FILES; do
      BASENAME=$(basename "$RULE_FILE")
      CONTENT=$(base64 < "$RULE_FILE")
      TARGET_PATH=".claude/rules/$BASENAME"

      # Check if file already exists on this branch
      EXISTING=$(gh api "/repos/$FULL_REPO/contents/$TARGET_PATH?ref=$BRANCH" 2>/dev/null || echo "")
      EXISTING_SHA=$(echo "$EXISTING" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
      EXISTING_CONTENT=$(echo "$EXISTING" | python3 -c "
import json,sys,base64
data = json.load(sys.stdin)
c = data.get('content','')
print(base64.b64decode(c).decode('utf-8','ignore'))
" 2>/dev/null || echo "")

      # Read local file content for comparison
      LOCAL_CONTENT=$(cat "$RULE_FILE")

      if [ "$EXISTING_CONTENT" = "$LOCAL_CONTENT" ]; then
        echo "    $BASENAME — already up to date"
        continue
      fi

      if [ "$DRY_RUN" = "--dry-run" ]; then
        if [ -n "$EXISTING_SHA" ]; then
          echo "    $BASENAME — [dry-run] would UPDATE"
        else
          echo "    $BASENAME — [dry-run] would CREATE"
        fi
        continue
      fi

      # Push the file
      if [ -n "$EXISTING_SHA" ]; then
        gh api --method PUT "/repos/$FULL_REPO/contents/$TARGET_PATH" \
          -f message="meta: update shared rule $BASENAME" \
          -f content="$CONTENT" \
          -f sha="$EXISTING_SHA" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "    $BASENAME — updated" || echo "    $BASENAME — FAILED to update"
      else
        gh api --method PUT "/repos/$FULL_REPO/contents/$TARGET_PATH" \
          -f message="meta: add shared rule $BASENAME" \
          -f content="$CONTENT" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "    $BASENAME — created" || echo "    $BASENAME — FAILED to create"
      fi
    done
  done
done

echo ""
echo "=== Done. Rules pushed to all branches. ==="
