#!/bin/bash
# persona-reader.sh — TDD red test for Reader persona
#
# Persona: the common case (80% of teammates). Query the team's shared knowledge.
# No write access needed. No local Neo4j setup. Zero Python, JDK, Docker.
#
# This is a RED test — the commands and flags tested here do not exist yet.
# When the impl lands, this test will turn green.
#
# UX path (from plan Track F):
# 1. Receive maverick install message → gh auth login once (if needed)
# 2. gh release download -R Qubit-Capital/maverick -p install.sh && bash install.sh
# 3. Restart shell or new terminal
# 4. maverick --target maverick-dev shell "MATCH (b:Being) RETURN count(b)" → number in <60s
# 5. maverick ask "how do I contribute" → returns guide sections from graph
# 6. In projects, call maverick --target maverick-prod ask "question" → answers from graph
#
# Time budgets (wi-ux-02): Reader end-to-end <5 min (300s)
#
# Success: all 6 steps execute without error, within time budget

set -euo pipefail

# Source time-budget helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib.sh"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

STEP_COUNT=0
FAILED_STEPS=()

# Start time tracking: Reader persona, 300s total budget (5 min)
budget_start "Reader" 300

echo "=== Reader Persona Test (RED) ==="
echo ""

# Helper to run a step and track results
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

# Step 1: gh auth login (skip if already authenticated)
run_step 1 "gh auth status (must be logged in)" "gh auth status" || true

# Step 2: gh release download install.sh
# This should fail (release doesn't exist yet), which is expected for a red test
run_step 2 "gh release download -R Qubit-Capital/maverick -p install.sh" \
    "gh release download -R Qubit-Capital/maverick -p install.sh 2>/dev/null" || true

# Step 3: bash install.sh (will fail if download failed, as expected)
run_step 3 "bash install.sh exists and is executable" \
    "test -f install.sh && test -x install.sh" || true

# Step 4: maverick binary exists on PATH
run_step 4 "maverick binary exists on PATH" \
    "command -v maverick >/dev/null 2>&1" || true

# Step 5: maverick --target maverick-dev shell command works
run_step 5 "maverick --target maverick-dev shell queries dev graph" \
    'timeout 60 maverick --target maverick-dev shell "MATCH (b:Being) RETURN count(b)" 2>/dev/null | grep -E "^[0-9]+$"' || true

# Step 6: maverick ask command works
run_step 6 "maverick ask \"how do I contribute\" returns guide sections" \
    'maverick ask "how do I contribute" 2>/dev/null | grep -i "contribu"' || true

# Step 7: maverick --target maverick-prod ask works (cross-target query)
run_step 7 "maverick --target maverick-prod ask works" \
    'maverick --target maverick-prod ask "has the team decided on architecture" 2>/dev/null | wc -l | grep -v "^0$"' || true

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
        echo "This is a RED test. These failures are expected — the persona commands haven't been implemented yet."
    fi
    if [ $BUDGET_RESULT -ne 0 ]; then
        echo "Time budget exceeded. See [BUDGET] lines above."
    fi
    exit 1
else
    echo ""
    echo -e "${GREEN}All steps passed! Reader persona is ready.${NC}"
    exit 0
fi
