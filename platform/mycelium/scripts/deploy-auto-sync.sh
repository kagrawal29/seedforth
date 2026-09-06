#!/bin/bash
# Deploys auto-sync hook to all branches across target repos
# Pushes: 1) updated git-workflow.md  2) hooks/auto-sync.sh  3) merged settings.json
# Usage: ./scripts/deploy-auto-sync.sh [--dry-run]
set -euo pipefail

DRY_RUN="${1:-}"
ORG="Qubit-Capital"
TARGET_REPOS="VC-AI-Assoicate maverick-market-research"
HOOK_FILE="distribution/hooks/auto-sync.sh"
RULE_FILE="distribution/shared-rules/git-workflow.md"
MERGE_SCRIPT="scripts/merge-settings-hook.py"

for REPO in $TARGET_REPOS; do
  echo "============================================"
  echo "REPO: $ORG/$REPO"
  echo "============================================"

  BRANCHES=$(gh api "/repos/$ORG/$REPO/branches?per_page=100" --jq '.[].name' 2>/dev/null)

  while IFS= read -r BRANCH; do
    echo ""
    echo "  Branch: $BRANCH"

    # --- 1. Push updated git-workflow.md ---
    RULE_CONTENT=$(base64 < "$RULE_FILE")
    EXISTING_RULE_SHA=$(gh api "/repos/$ORG/$REPO/contents/.claude/rules/git-workflow.md?ref=$BRANCH" --jq '.sha' 2>/dev/null || echo "")

    if [ "$DRY_RUN" = "--dry-run" ]; then
      echo "    git-workflow.md — [dry-run]"
    elif [ -n "$EXISTING_RULE_SHA" ]; then
      gh api --method PUT "/repos/$ORG/$REPO/contents/.claude/rules/git-workflow.md" \
        -f message="meta: update git-workflow (hook handles push now)" \
        -f content="$RULE_CONTENT" \
        -f sha="$EXISTING_RULE_SHA" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "    git-workflow.md — updated" || echo "    git-workflow.md — FAILED"
    else
      gh api --method PUT "/repos/$ORG/$REPO/contents/.claude/rules/git-workflow.md" \
        -f message="meta: add git-workflow rule" \
        -f content="$RULE_CONTENT" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "    git-workflow.md — created" || echo "    git-workflow.md — FAILED"
    fi

    # --- 2. Push auto-sync.sh hook script ---
    HOOK_CONTENT=$(base64 < "$HOOK_FILE")
    EXISTING_HOOK_SHA=$(gh api "/repos/$ORG/$REPO/contents/.claude/hooks/auto-sync.sh?ref=$BRANCH" --jq '.sha' 2>/dev/null || echo "")

    if [ "$DRY_RUN" = "--dry-run" ]; then
      echo "    hooks/auto-sync.sh — [dry-run]"
    elif [ -n "$EXISTING_HOOK_SHA" ]; then
      gh api --method PUT "/repos/$ORG/$REPO/contents/.claude/hooks/auto-sync.sh" \
        -f message="meta: update auto-sync hook" \
        -f content="$HOOK_CONTENT" \
        -f sha="$EXISTING_HOOK_SHA" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "    hooks/auto-sync.sh — updated" || echo "    hooks/auto-sync.sh — FAILED"
    else
      gh api --method PUT "/repos/$ORG/$REPO/contents/.claude/hooks/auto-sync.sh" \
        -f message="meta: add auto-sync hook (commit triggers pull+push)" \
        -f content="$HOOK_CONTENT" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "    hooks/auto-sync.sh — created" || echo "    hooks/auto-sync.sh — FAILED"
    fi

    # --- 3. Merge settings.json ---
    EXISTING_SETTINGS_RAW=$(gh api "/repos/$ORG/$REPO/contents/.claude/settings.json?ref=$BRANCH" 2>/dev/null || echo "")
    EXISTING_SETTINGS_SHA=$(echo "$EXISTING_SETTINGS_RAW" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
    EXISTING_SETTINGS_CONTENT=$(echo "$EXISTING_SETTINGS_RAW" | python3 -c "
import json,sys,base64
data = json.load(sys.stdin)
c = data.get('content','')
print(base64.b64decode(c).decode('utf-8','ignore'))
" 2>/dev/null || echo "{}")

    MERGED=$(echo "$EXISTING_SETTINGS_CONTENT" | python3 "$MERGE_SCRIPT")

    if [ "$DRY_RUN" = "--dry-run" ]; then
      HOOKS_LIST=$(echo "$MERGED" | python3 -c "import json,sys; print(list(json.load(sys.stdin).get('hooks',{}).keys()))" 2>/dev/null)
      echo "    settings.json — [dry-run] hooks: $HOOKS_LIST"
    else
      MERGED_B64=$(echo "$MERGED" | base64)
      if [ -n "$EXISTING_SETTINGS_SHA" ]; then
        gh api --method PUT "/repos/$ORG/$REPO/contents/.claude/settings.json" \
          -f message="meta: add auto-sync PostToolUse hook" \
          -f content="$MERGED_B64" \
          -f sha="$EXISTING_SETTINGS_SHA" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "    settings.json — merged & updated" || echo "    settings.json — FAILED"
      else
        gh api --method PUT "/repos/$ORG/$REPO/contents/.claude/settings.json" \
          -f message="meta: add settings.json with auto-sync hook" \
          -f content="$MERGED_B64" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "    settings.json — created" || echo "    settings.json — FAILED"
      fi
    fi

  done <<< "$BRANCHES"
done

echo ""
echo "=== Deployment complete ==="
