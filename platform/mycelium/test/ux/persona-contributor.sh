#!/bin/bash
# persona-contributor.sh — TDD red test for Contributor persona
#
# Persona: the minority (20% of teammates). Write Cypher and land it in maverick-dev.
# Requirements: Docker Desktop + all of Reader persona.
#
# This is a RED test — the commands and flags tested here do not exist yet.
# When the impl lands, this test will turn green.
#
# UX path (from plan Track F):
# 1. Complete Reader steps 1-4
# 2. gh repo clone Qubit-Capital/maverick && cd maverick
# 3. maverick local bootstrap → Docker stack up → Neo4j + Ollama running locally <120s
# 4. maverick fork maverick-dev → snapshot of dev graph copied to local <120s
# 5. Edit a .cypher file under graph/protocols/ or graph/knowledge/
# 6. maverick-dev test --target maverick-local → merge-gate checks against local
# 7. git checkout -b dev/<name>/<desc> && git commit && git push && gh pr create
# 8. CI runs: drift check, e2e UX harness, merge-gate validators → Green
# 9. Reviewer merges → autodeploy updates maverick-dev
# 10. maverick local teardown (optional)
#
# Time budgets (wi-ux-02): Contributor end-to-end <10 min (600s), fork <2 min (120s), bootstrap <2 min (120s)
#
# Success: contributor workflow from clone to PR-ready, within time budgets

set -euo pipefail

# Source time-budget helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

STEP_COUNT=0
FAILED_STEPS=()

# Track per-step timings
BOOTSTRAP_START=""
BOOTSTRAP_END=""
FORK_START=""
FORK_END=""

# Start time tracking: Contributor persona, 600s total budget (10 min)
budget_start "Contributor" 600

echo "=== Contributor Persona Test (RED) ==="
echo ""

run_step() {
    local step_num=$1
    local description=$2
    local command=$3

    STEP_COUNT=$((STEP_COUNT + 1))
    echo -n "[Step $step_num] $description ... "

    if eval "$command" &> /dev/null; then
        echo -e "${GREEN}PASS${NC}"
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        FAILED_STEPS+=("$step_num: $description")
        return 1
    fi
}

# Step 1: Reader persona passed (maverick binary exists)
run_step 1 "Reader persona completed (maverick on PATH)" \
    "command -v maverick >/dev/null 2>&1" || true

# Step 2: gh repo clone Qubit-Capital/maverick
run_step 2 "gh repo clone Qubit-Capital/maverick" \
    "gh repo clone Qubit-Capital/maverick /tmp/test-maverick-contrib 2>/dev/null" || true

# Step 3: cd into cloned repo
run_step 3 "Repo cloned and accessible" \
    "test -d /tmp/test-maverick-contrib && test -f /tmp/test-maverick-contrib/go.mod" || true

# Step 4: Docker Desktop is running (prerequisite)
run_step 4 "Docker Desktop is running (docker info works)" \
    "docker info >/dev/null 2>&1" || true

# Step 5: maverick local bootstrap command exists
run_step 5 "maverick local bootstrap command exists" \
    "maverick local bootstrap --help >/dev/null 2>&1" || true

# Step 6: Docker compose stack comes up (with timing)
budget_check_step "bootstrap" 120
BOOTSTRAP_START=$(date +%s)
run_step 6 "Docker compose services start (Neo4j + Ollama + embed-proxy)" \
    "timeout 120 maverick local bootstrap 2>/dev/null && sleep 5 && docker ps | grep -E '(neo4j|ollama|embed)'" || true
BOOTSTRAP_END=$(date +%s)
BOOTSTRAP_ELAPSED=$((BOOTSTRAP_END - BOOTSTRAP_START))
budget_assert_step "bootstrap" 120 $BOOTSTRAP_ELAPSED || FAILED_STEPS+=("6: bootstrap exceeded 120s budget")

# Step 7: Local Neo4j is queryable
run_step 7 "Local Neo4j responds to queries" \
    "timeout 10 maverick --target maverick-local shell 'RETURN 1' 2>/dev/null | grep '1'" || true

# Step 8: maverick fork maverick-dev command exists
run_step 8 "maverick fork command exists" \
    "maverick fork --help 2>/dev/null | grep -i fork" || true

# Step 9: Fork dev graph into local (with timing)
budget_check_step "fork" 120
FORK_START=$(date +%s)
run_step 9 "maverick fork maverick-dev completes" \
    "timeout 120 maverick fork maverick-dev 2>/dev/null" || true
FORK_END=$(date +%s)
FORK_ELAPSED=$((FORK_END - FORK_START))
budget_assert_step "fork" 120 $FORK_ELAPSED || FAILED_STEPS+=("9: fork exceeded 120s budget")

# Step 10: Forked data is in local
run_step 10 "Forked graph has nodes" \
    "maverick --target maverick-local shell 'MATCH (n) RETURN count(n)' 2>/dev/null | grep -v '^0$'" || true

# Step 11: Can edit a .cypher file in graph/protocols/
run_step 11 "graph/protocols directory exists" \
    "test -d /tmp/test-maverick-contrib/graph/protocols" || true

# Step 12: Create a test Cypher file
run_step 12 "Create test Cypher file for editing" \
    "cat > /tmp/test-maverick-contrib/graph/protocols/test-persona.cypher <<'EOF'\nMERGE (p:Protocol {node_id: 'test-persona-v1'})\nSET p.name = 'Test Persona Protocol'\nSET p.created_at = datetime()\nRETURN p\nEOF" || true

# Step 13: maverick-dev test command exists
run_step 13 "maverick-dev test command exists" \
    "maverick-dev test --help 2>/dev/null | grep -i test" || true

# Step 14: maverick-dev verify against local
run_step 14 "maverick-dev verify --target maverick-local command works" \
    "cd /tmp/test-maverick-contrib && timeout 60 maverick-dev verify --target maverick-local 2>/dev/null" || true

# Step 15: maverick-dev diff shows changes
run_step 15 "maverick-dev diff --target maverick-local works" \
    "cd /tmp/test-maverick-contrib && maverick-dev diff --target maverick-local --against maverick-dev 2>/dev/null | wc -l | grep -v '^0$'" || true

# Step 16: Can create a git branch
run_step 16 "Create dev branch (git checkout -b dev/persona/test)" \
    "cd /tmp/test-maverick-contrib && git checkout -b dev/persona/test-contrib 2>/dev/null" || true

# Step 17: Can commit changes
run_step 17 "git commit with graph changes" \
    "cd /tmp/test-maverick-contrib && git add graph/protocols/test-persona.cypher && git commit -m 'test: contributor persona cypher' 2>/dev/null" || true

# Step 18: Can push branch
run_step 18 "git push -u origin dev/persona/test-contrib" \
    "cd /tmp/test-maverick-contrib && git push -u origin dev/persona/test-contrib 2>/dev/null" || true

# Step 19: gh pr create works
run_step 19 "gh pr create opens a PR" \
    "cd /tmp/test-maverick-contrib && gh pr create --title 'persona-contrib: test' --body 'TDD test' 2>/dev/null | grep -i 'pull.*request\\|https.*github'"  || true

# Step 20: maverick local teardown command exists
run_step 20 "maverick local teardown command exists" \
    "maverick local teardown --help 2>/dev/null | grep -i teardown" || true

# Step 21: Teardown succeeds
run_step 21 "maverick local teardown stops containers" \
    "timeout 30 maverick local teardown 2>/dev/null" || true

echo ""
echo "=== Test Summary ==="
echo "Total steps: $STEP_COUNT"
echo "Passed: $(($STEP_COUNT - ${#FAILED_STEPS[@]}))"
echo "Failed: ${#FAILED_STEPS[@]}"

# Check time budget
budget_check_total
BUDGET_RESULT=$?

if [ ${#FAILED_STEPS[@]} -gt 0 ] || [ $BUDGET_RESULT -ne 0 ]; then
    echo ""
    if [ ${#FAILED_STEPS[@]} -gt 0 ]; then
        echo -e "${RED}Failed steps:${NC}"
        for failed in "${FAILED_STEPS[@]}"; do
            echo "  - $failed"
        done
        echo ""
        echo "This is a RED test. These failures are expected — the contributor commands haven't been implemented yet."
    fi
    if [ $BUDGET_RESULT -ne 0 ]; then
        echo "Time budget exceeded. See [BUDGET] lines above."
    fi
    exit 1
else
    echo ""
    echo -e "${GREEN}All steps passed! Contributor persona is ready.${NC}"
    exit 0
fi
