#!/bin/bash
# Pushes the knowledge wiki + search skill to all branches across target repos
# This replaces individual rule pushing with a full knowledge base distribution
#
# What gets pushed to each repo:
#   .claude/knowledge/index.md          — situation-routed catalog
#   .claude/knowledge/search-index.md   — inverted keyword index
#   .claude/knowledge/community-map.md  — graph community structure (the map Claude reads)
#   .claude/knowledge/entries/*.md      — all knowledge entries
#   .claude/skills/team-knowledge/SKILL.md — search skill
#
# Usage: ./scripts/push-knowledge.sh [--dry-run]
set -euo pipefail

DRY_RUN="${1:-}"
KNOWLEDGE_DIR="knowledge"

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

# Collect all files to push
declare -a FILES_TO_PUSH
declare -a TARGET_PATHS

# Knowledge index files
FILES_TO_PUSH+=("$KNOWLEDGE_DIR/index.md")
TARGET_PATHS+=(".claude/knowledge/index.md")

FILES_TO_PUSH+=("$KNOWLEDGE_DIR/search-index.md")
TARGET_PATHS+=(".claude/knowledge/search-index.md")

# Community map — the graph structure Claude reads before answering
if [ -f "$KNOWLEDGE_DIR/community-map.md" ]; then
  FILES_TO_PUSH+=("$KNOWLEDGE_DIR/community-map.md")
  TARGET_PATHS+=(".claude/knowledge/community-map.md")
fi

# All knowledge entries (excluding meta/)
while IFS= read -r f; do
  rel="${f#$KNOWLEDGE_DIR/}"
  FILES_TO_PUSH+=("$f")
  TARGET_PATHS+=(".claude/knowledge/entries/$rel")
done < <(find "$KNOWLEDGE_DIR" -name "*.md" -not -path "*/meta/*" -not -name "index.md" -not -name "search-index.md" -not -name "community-map.md" -type f | sort)

# Skills (real T8 workflows only)
for skill_dir in architecture-validation fix-workflow spec-to-ship; do
  if [ -f ".claude/skills/$skill_dir/SKILL.md" ]; then
    FILES_TO_PUSH+=(".claude/skills/$skill_dir/SKILL.md")
    TARGET_PATHS+=(".claude/skills/$skill_dir/SKILL.md")
  fi
done

# Hooks — NEVER auto-distributed (security invariant 2)
# Hooks execute code on every session/commit. Auto-distributing them
# means a poisoned hook propagates to the entire team. Hooks must be
# reviewed and pushed manually.
# To distribute hooks intentionally: SKIP_HOOKS=false bash scripts/push-knowledge.sh
if [ "${SKIP_HOOKS:-true}" = "false" ]; then
  echo "WARNING: Hook distribution enabled (SKIP_HOOKS=false)"
  for hook_file in .claude/hooks/*; do
    if [ -f "$hook_file" ]; then
      FILES_TO_PUSH+=("$hook_file")
      TARGET_PATHS+=("$hook_file")
    fi
  done
else
  echo "Hooks: skipped (security invariant 2 — never auto-distributed)"
fi

echo "Files to distribute: ${#FILES_TO_PUSH[@]}"
echo ""

for FULL_REPO in $TARGET_REPOS; do
  echo "============================================"
  echo "REPO: $FULL_REPO"
  echo "============================================"

  BRANCHES=$(gh api "/repos/$FULL_REPO/branches?per_page=100" --jq '.[].name' 2>/dev/null)

  for BRANCH in $BRANCHES; do
    echo ""
    echo "  Branch: $BRANCH"

    for i in "${!FILES_TO_PUSH[@]}"; do
      LOCAL_FILE="${FILES_TO_PUSH[$i]}"
      TARGET_PATH="${TARGET_PATHS[$i]}"
      BASENAME=$(basename "$LOCAL_FILE")

      if [ ! -f "$LOCAL_FILE" ]; then
        echo "    $BASENAME — MISSING locally, skipping"
        continue
      fi

      CONTENT=$(base64 < "$LOCAL_FILE")
      LOCAL_CONTENT=$(cat "$LOCAL_FILE")

      # Check if file already exists on this branch
      EXISTING=$(gh api "/repos/$FULL_REPO/contents/$TARGET_PATH?ref=$BRANCH" 2>/dev/null || echo "")
      EXISTING_SHA=$(echo "$EXISTING" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
      EXISTING_CONTENT=$(echo "$EXISTING" | python3 -c "
import json,sys,base64
data = json.load(sys.stdin)
c = data.get('content','')
print(base64.b64decode(c).decode('utf-8','ignore'))
" 2>/dev/null || echo "")

      if [ "$EXISTING_CONTENT" = "$LOCAL_CONTENT" ]; then
        echo "    $BASENAME — up to date"
        continue
      fi

      if [ "$DRY_RUN" = "--dry-run" ]; then
        if [ -n "$EXISTING_SHA" ]; then
          echo "    $TARGET_PATH — [dry-run] would UPDATE"
        else
          echo "    $TARGET_PATH — [dry-run] would CREATE"
        fi
        continue
      fi

      if [ -n "$EXISTING_SHA" ]; then
        gh api --method PUT "/repos/$FULL_REPO/contents/$TARGET_PATH" \
          -f message="meta: update knowledge $BASENAME" \
          -f content="$CONTENT" \
          -f sha="$EXISTING_SHA" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "    $TARGET_PATH — updated" || echo "    $TARGET_PATH — FAILED"
      else
        gh api --method PUT "/repos/$FULL_REPO/contents/$TARGET_PATH" \
          -f message="meta: add knowledge $BASENAME" \
          -f content="$CONTENT" \
          -f branch="$BRANCH" \
          --silent 2>/dev/null && echo "    $TARGET_PATH — created" || echo "    $TARGET_PATH — FAILED"
      fi
    done
  done
done

# --- Phase 2: Patch settings.json to wire up rules-loaded hook ---
echo ""
echo "=== Patching settings.json on all branches ==="
for FULL_REPO in $TARGET_REPOS; do
  BRANCHES=$(gh api "/repos/$FULL_REPO/branches?per_page=100" --jq '.[].name' 2>/dev/null)
  for BRANCH in $BRANCHES; do
    EXISTING=$(gh api "/repos/$FULL_REPO/contents/.claude/settings.json?ref=$BRANCH" 2>/dev/null || echo "")
    EXISTING_SHA=$(echo "$EXISTING" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
    EXISTING_CONTENT=$(echo "$EXISTING" | python3 -c "
import json,sys,base64
data = json.load(sys.stdin)
c = data.get('content','')
print(base64.b64decode(c).decode('utf-8','ignore'))
" 2>/dev/null || echo "")

    PATCHED=$(echo "$EXISTING_CONTENT" | python3 scripts/patch-settings-hooks.py)

    if [ "$EXISTING_CONTENT" = "$PATCHED" ]; then
      continue  # Already has the hook
    fi

    if [ "$DRY_RUN" = "--dry-run" ]; then
      echo "  $FULL_REPO ($BRANCH) — [dry-run] would patch settings.json"
      continue
    fi

    CONTENT_B64=$(echo "$PATCHED" | base64)
    if [ -n "$EXISTING_SHA" ]; then
      gh api --method PUT "/repos/$FULL_REPO/contents/.claude/settings.json" \
        -f message="meta: add rules-loaded SessionStart hook" \
        -f content="$CONTENT_B64" \
        -f sha="$EXISTING_SHA" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "  $FULL_REPO ($BRANCH) — settings.json patched" || echo "  $FULL_REPO ($BRANCH) — FAILED"
    else
      gh api --method PUT "/repos/$FULL_REPO/contents/.claude/settings.json" \
        -f message="meta: add rules-loaded SessionStart hook" \
        -f content="$CONTENT_B64" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "  $FULL_REPO ($BRANCH) — settings.json created" || echo "  $FULL_REPO ($BRANCH) — FAILED"
    fi
  done
done

# --- Phase 3: Patch .mcp.json to wire up Asgard Graph MCP server ---
echo ""
echo "=== Patching .mcp.json on all branches (Asgard Graph MCP) ==="
for FULL_REPO in $TARGET_REPOS; do
  BRANCHES=$(gh api "/repos/$FULL_REPO/branches?per_page=100" --jq '.[].name' 2>/dev/null)
  for BRANCH in $BRANCHES; do
    EXISTING=$(gh api "/repos/$FULL_REPO/contents/.mcp.json?ref=$BRANCH" 2>/dev/null || echo "")
    EXISTING_SHA=$(echo "$EXISTING" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")
    EXISTING_CONTENT=$(echo "$EXISTING" | python3 -c "
import json,sys,base64
data = json.load(sys.stdin)
c = data.get('content','')
print(base64.b64decode(c).decode('utf-8','ignore'))
" 2>/dev/null || echo "{}")

    PATCHED=$(echo "$EXISTING_CONTENT" | python3 scripts/patch-mcp-config.py)

    if [ "$EXISTING_CONTENT" = "$PATCHED" ]; then
      continue  # Already has asgard-graph configured
    fi

    if [ "$DRY_RUN" = "--dry-run" ]; then
      echo "  $FULL_REPO ($BRANCH) — [dry-run] would patch .mcp.json"
      continue
    fi

    CONTENT_B64=$(echo "$PATCHED" | base64)
    if [ -n "$EXISTING_SHA" ]; then
      gh api --method PUT "/repos/$FULL_REPO/contents/.mcp.json" \
        -f message="meta: add Asgard Graph MCP server" \
        -f content="$CONTENT_B64" \
        -f sha="$EXISTING_SHA" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "  $FULL_REPO ($BRANCH) — .mcp.json patched" || echo "  $FULL_REPO ($BRANCH) — FAILED"
    else
      gh api --method PUT "/repos/$FULL_REPO/contents/.mcp.json" \
        -f message="meta: add Asgard Graph MCP server" \
        -f content="$CONTENT_B64" \
        -f branch="$BRANCH" \
        --silent 2>/dev/null && echo "  $FULL_REPO ($BRANCH) — .mcp.json created" || echo "  $FULL_REPO ($BRANCH) — FAILED"
    fi
  done
done

# --- Phase 4: Clean up old asgard.md rule (replaced by asgard-graph.md) ---
echo ""
echo "=== Removing old .claude/rules/asgard.md (replaced by asgard-graph.md) ==="
for FULL_REPO in $TARGET_REPOS; do
  BRANCHES=$(gh api "/repos/$FULL_REPO/branches?per_page=100" --jq '.[].name' 2>/dev/null)
  for BRANCH in $BRANCHES; do
    OLD_FILE=$(gh api "/repos/$FULL_REPO/contents/.claude/rules/asgard.md?ref=$BRANCH" 2>/dev/null || echo "")
    OLD_SHA=$(echo "$OLD_FILE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('sha',''))" 2>/dev/null || echo "")

    if [ -z "$OLD_SHA" ]; then
      continue  # File doesn't exist on this branch
    fi

    if [ "$DRY_RUN" = "--dry-run" ]; then
      echo "  $FULL_REPO ($BRANCH) — [dry-run] would DELETE .claude/rules/asgard.md"
      continue
    fi

    gh api --method DELETE "/repos/$FULL_REPO/contents/.claude/rules/asgard.md" \
      -f message="meta: remove old asgard.md (replaced by asgard-graph.md)" \
      -f sha="$OLD_SHA" \
      -f branch="$BRANCH" \
      --silent 2>/dev/null && echo "  $FULL_REPO ($BRANCH) — asgard.md removed" || echo "  $FULL_REPO ($BRANCH) — FAILED"
  done
done

echo ""
echo "=== Done. Knowledge base + hooks + Asgard Graph MCP pushed to all branches. ==="
