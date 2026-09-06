#!/usr/bin/env bash
# bulk-ingest-qubit-repos.sh — Ingest all 4 Qubit-Capital repos into mycelium dev Neo4j.
#
# Idempotent: re-running re-MERGEs without creating duplicates.
# Target: bolt://5.78.206.137:7698 (dev Neo4j on pulse-server).
# Creds: loaded from /root/.mycelium-secrets (NEO4J_DEV_BOLT / NEO4J_DEV_PASS).
#
# Usage:
#   bash scripts/bulk-ingest-qubit-repos.sh
#   bash scripts/bulk-ingest-qubit-repos.sh --dry-run   (print plan, don't ingest)
#
# After a successful run, verify with:
#   mycelium --target dev shell "MATCH (c:Commit) RETURN c.project, count(*) ORDER BY count(*) DESC"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INGEST_PY="$SCRIPT_DIR/ingest_repo.py"

DRY_RUN="${1:-}"

# ── Repo manifest ──────────────────────────────────────────────────────────────
# Format: "https_url|project_node_id|max_commits"
REPOS=(
  "https://github.com/Qubit-Capital/VC-AI-Assoicate|vc-ai-associate|500"
  "https://github.com/Qubit-Capital/maverick-market-research|maverick-market-research|5000"
  "https://github.com/Qubit-Capital/maverick-marketing|maverick-marketing|500"
  "https://github.com/Qubit-Capital/Maverick-Dev|maverick-dev|500"
)

# ── Helpers ────────────────────────────────────────────────────────────────────
header() { printf '\n\e[1;36m══ %s\e[0m\n' "$*"; }
ok()     { printf '\e[32m✓\e[0m %s\n' "$*"; }
bad()    { printf '\e[31m✗\e[0m %s\n' "$*"; }
info()   { printf '  %s\n' "$*"; }

# ── Preflight ─────────────────────────────────────────────────────────────────
header "Preflight checks"

# Python available
if ! python3 --version >/dev/null 2>&1; then
  bad "python3 not found"; exit 1
fi

# neo4j driver installed
if ! python3 -c "import neo4j" 2>/dev/null; then
  bad "neo4j Python driver not installed. Run: pip install neo4j"
  exit 1
fi

# ingest_repo.py exists
if [ ! -f "$INGEST_PY" ]; then
  bad "ingest_repo.py not found at $INGEST_PY"; exit 1
fi

ok "preflight passed"

# ── Dry-run mode ──────────────────────────────────────────────────────────────
if [ "$DRY_RUN" = "--dry-run" ]; then
  header "Dry-run plan (not ingesting)"
  for entry in "${REPOS[@]}"; do
    IFS="|" read -r url project max_commits <<< "$entry"
    info "repo    : $url"
    info "project : $project"
    info "max-commits: $max_commits"
    echo ""
  done
  info "Run without --dry-run to ingest."
  exit 0
fi

# ── Ingest loop ───────────────────────────────────────────────────────────────
TOTAL=${#REPOS[@]}
PASSED=0
FAILED=0
FAILED_REPOS=()

for i in "${!REPOS[@]}"; do
  entry="${REPOS[$i]}"
  IFS="|" read -r url project max_commits <<< "$entry"
  N=$((i + 1))

  header "[$N/$TOTAL] $url"
  info "project    : $project"
  info "max-commits: $max_commits"
  echo ""

  if python3 "$INGEST_PY" "$url" \
      --project "$project" \
      --max-commits "$max_commits"; then
    ok "[$N/$TOTAL] $project done"
    PASSED=$((PASSED + 1))
  else
    bad "[$N/$TOTAL] $project FAILED"
    FAILED=$((FAILED + 1))
    FAILED_REPOS+=("$url")
  fi

  echo ""
done

# ── Summary ───────────────────────────────────────────────────────────────────
header "Bulk ingest complete"
info "passed : $PASSED / $TOTAL"
info "failed : $FAILED / $TOTAL"

if [ ${#FAILED_REPOS[@]} -gt 0 ]; then
  bad "Failed repos:"
  for r in "${FAILED_REPOS[@]}"; do
    bad "  $r"
  done
  exit 1
fi

echo ""
ok "All repos ingested. Verify with:"
echo '  mycelium --target dev shell "MATCH (c:Commit) RETURN c.project, count(*) ORDER BY count(*) DESC"'
echo '  mycelium --target dev ask "what is maverick-market-research about"'
