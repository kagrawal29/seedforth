#!/bin/bash
# Fetches GitHub activity across Qubit-Capital org for maverick repos
# Usage: ./scripts/ingest-github.sh [--quick|--full]
# --quick: last 2 hours (for SessionStart hook)
# --full: last 24 hours (for /ingest skill)

set -euo pipefail

MODE="${1:---quick}"
# Read repos from config.yaml + always include maverick-meta
REPOS=$(python3 -c "
import yaml
config = yaml.safe_load(open('config.yaml'))
repos = [f\"{r['org']}/{r['name']}\" for r in config['repos']]
repos.append('Qubit-Capital/maverick-meta')
for r in repos:
    print(r)
" 2>/dev/null)

if [ -z "$REPOS" ]; then
  REPOS="Qubit-Capital/VC-AI-Assoicate
Qubit-Capital/maverick-market-research
Qubit-Capital/maverick-meta"
fi
OUTPUT_DIR="signals/github"
DATE=$(date +%Y-%m-%d)

if [ "$MODE" = "--quick" ]; then
  if [[ "$OSTYPE" == "darwin"* ]]; then
    SINCE=$(date -u -v-2H +%Y-%m-%dT%H:%M:%SZ)
  else
    SINCE=$(date -u -d '2 hours ago' +%Y-%m-%dT%H:%M:%SZ)
  fi
  echo "=== Quick GitHub Poll (last 2h, since $SINCE) ==="
else
  if [[ "$OSTYPE" == "darwin"* ]]; then
    SINCE=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)
  else
    SINCE=$(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)
  fi
  echo "=== Full GitHub Ingest (last 24h, since $SINCE) ==="
fi

OUTPUT=""

for FULL_REPO in $REPOS; do
  OUTPUT+="
## $FULL_REPO
"

  # Recent commits
  COMMITS=$(gh api "/repos/$FULL_REPO/commits?since=$SINCE&per_page=30" \
    --jq '.[] | "- [`\(.sha[0:7])`] \(.commit.message | split("\n")[0]) — \(.commit.author.name) (\(.commit.author.date[0:10]))"' 2>/dev/null || echo "  (no commits or access denied)")

  if [ -n "$COMMITS" ]; then
    OUTPUT+="
### Commits
$COMMITS
"
  fi

  # Recent PRs
  PRS=$(gh api "/repos/$FULL_REPO/pulls?state=all&sort=updated&direction=desc&per_page=10" \
    --jq '.[] | select(.updated_at > "'"$SINCE"'") | "- [#\(.number)] \(.title) [\(.state)] by \(.user.login)"' 2>/dev/null || echo "  (no PRs or access denied)")

  if [ -n "$PRS" ]; then
    OUTPUT+="
### Pull Requests
$PRS
"
  fi

  # Recent issues
  ISSUES=$(gh api "/repos/$FULL_REPO/issues?state=all&sort=updated&direction=desc&per_page=10" \
    --jq '.[] | select(.pull_request == null) | select(.updated_at > "'"$SINCE"'") | "- [#\(.number)] \(.title) [\(.state)] by \(.user.login)"' 2>/dev/null || echo "  (no issues or access denied)")

  if [ -n "$ISSUES" ]; then
    OUTPUT+="
### Issues
$ISSUES
"
  fi
done

if [ "$MODE" = "--full" ]; then
  mkdir -p "$OUTPUT_DIR"
  OUTFILE="$OUTPUT_DIR/$DATE.md"

  # Append if file exists (multiple ingests per day)
  {
    echo "# GitHub Activity Digest — $DATE"
    echo "Ingested at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "Since: $SINCE"
    echo "$OUTPUT"
  } >> "$OUTFILE"

  echo "Written to $OUTFILE"
else
  echo "$OUTPUT"
fi
