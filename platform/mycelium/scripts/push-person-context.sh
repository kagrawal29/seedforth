#!/bin/bash
# Pushes per-person context files to the correct branches.
#
# Each person's context file goes ONLY to branches they work on.
# Branch matching: branches containing the person's name (case-insensitive)
# or branches listed in a person-to-branch mapping.
#
# Usage: ./scripts/push-person-context.sh [--dry-run]
set -euo pipefail

DRY_RUN="${1:-}"
CONTEXT_DIR="distribution/person-context"

# Read repos from config.yaml
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

# Read team members from config
TEAM_MEMBERS=$(python3 -c "
import yaml
config = yaml.safe_load(open('config.yaml'))
for m in config['team']:
    print(m['name'])
" 2>/dev/null)

if [ ! -d "$CONTEXT_DIR" ]; then
  echo "No person-context directory at $CONTEXT_DIR"
  exit 0
fi

# Check which context files exist
CONTEXT_FILES=$(find "$CONTEXT_DIR" -name "*.md" -type f 2>/dev/null)
if [ -z "$CONTEXT_FILES" ]; then
  echo "No context files to distribute"
  exit 0
fi

echo "=== Pushing per-person context files ==="
echo ""

for FULL_REPO in $TARGET_REPOS; do
  echo "============================================"
  echo "REPO: $FULL_REPO"
  echo "============================================"

  # Get all branches
  BRANCHES=$(gh api "/repos/$FULL_REPO/branches?per_page=100" --jq '.[].name' 2>/dev/null)

  for CONTEXT_FILE in $CONTEXT_FILES; do
    PERSON=$(basename "$CONTEXT_FILE" .md)
    PERSON_LOWER=$(echo "$PERSON" | tr '[:upper:]' '[:lower:]')

    echo ""
    echo "  Person: $PERSON"

    # Find branches this person works on
    # Match: branch contains person name (case-insensitive), or branch is main/dev
    MATCHED_BRANCHES=""
    for BRANCH in $BRANCHES; do
      BRANCH_LOWER=$(echo "$BRANCH" | tr '[:upper:]' '[:lower:]')

      # Match branches containing person's name
      if echo "$BRANCH_LOWER" | grep -q "$PERSON_LOWER"; then
        MATCHED_BRANCHES="$MATCHED_BRANCHES $BRANCH"
        continue
      fi

      # Also push to dev/ branches that contain the person's name
      if echo "$BRANCH_LOWER" | grep -q "dev/$PERSON_LOWER"; then
        MATCHED_BRANCHES="$MATCHED_BRANCHES $BRANCH"
        continue
      fi
    done

    if [ -z "$MATCHED_BRANCHES" ]; then
      echo "    No matching branches found for $PERSON"
      continue
    fi

    CONTENT=$(base64 < "$CONTEXT_FILE")
    LOCAL_CONTENT=$(cat "$CONTEXT_FILE")
    TARGET_PATH=".claude/rules/person-context.md"

    for BRANCH in $MATCHED_BRANCHES; do
      echo "    Branch: $BRANCH"

      # Check if file already exists
      EXISTING=$(gh api "/repos/$FULL_REPO/contents/$TARGET_PATH?ref=$BRANCH" 2>/dev/null || echo "")
      EXISTING_SHA=$(echo "$EXISTING" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
      EXISTING_CONTENT=$(echo "$EXISTING" | python3 -c "
import json,sys,base64
data = json.load(sys.stdin)
c = data.get('content','')
print(base64.b64decode(c).decode('utf-8','ignore'))
" 2>/dev/null || echo "")

      if [ "$EXISTING_CONTENT" = "$LOCAL_CONTENT" ]; then
        echo "      person-context.md -- up to date"
        continue
      fi

      if [ "$DRY_RUN" = "--dry-run" ]; then
        if [ -n "$EXISTING_SHA" ]; then
          echo "      person-context.md -- [dry-run] would UPDATE"
        else
          echo "      person-context.md -- [dry-run] would CREATE"
        fi
        continue
      fi

      if [ -n "$EXISTING_SHA" ]; then
        gh api --method PUT "/repos/$FULL_REPO/contents/$TARGET_PATH" \
          -f message="meta: update person context for $PERSON" \
          -f content="$CONTENT" \
          -f sha="$EXISTING_SHA" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "      person-context.md -- updated" || echo "      person-context.md -- FAILED"
      else
        gh api --method PUT "/repos/$FULL_REPO/contents/$TARGET_PATH" \
          -f message="meta: add person context for $PERSON" \
          -f content="$CONTENT" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "      person-context.md -- created" || echo "      person-context.md -- FAILED"
      fi
    done
  done
done

echo ""
echo "=== Done. Person context pushed to matching branches. ==="
