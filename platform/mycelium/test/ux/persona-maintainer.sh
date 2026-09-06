#!/bin/bash
# persona-maintainer.sh — TDD red test for Maintainer persona
#
# Persona: Kshitiz + future ops teammates. Keep the shared graph healthy, ship releases.
# Requirements: SSH access to pulse-server + all of Reader/Contributor capabilities.
#
# This is a RED test — the commands and flags tested here do not exist yet.
# When the impl lands, this test will turn green.
#
# UX path (from plan Track F):
# 1. All of Persona 1 (Reader) + 2 (Contributor)
# 2. Direct SSH access to pulse-server
# 3. maverick-dev ops <subcommand> — rotation, smoke-test results, trace analytics
# 4. Release cuts via git tag v1.X.Y && git push --tags → goreleaser → published
# 5. Monitor maverick-smoke.service timer, maverick-trace.service health
#
# Time budgets (wi-ux-02): Maintainer end-to-end <10 min (600s)
#
# Success: ops tasks are one command each; dashboards live in graph, within time budget

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

# Start time tracking: Maintainer persona, 600s total budget (10 min)
budget_start "Maintainer" 600

echo "=== Maintainer Persona Test (RED) ==="
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

# Step 1: Reader persona passed (maverick binary)
run_step 1 "Reader persona completed (maverick on PATH)" \
    "command -v maverick >/dev/null 2>&1" || true

# Step 2: Contributor persona passed (maverick-dev and local commands)
run_step 2 "Contributor persona completed (maverick-dev script exists)" \
    "command -v maverick-dev >/dev/null 2>&1" || true

# Step 3: SSH to pulse-server works (or simulate with local docker if testing locally)
run_step 3 "Can reach pulse-server via SSH" \
    "ssh -o ConnectTimeout=5 pulse-server 'echo ok' 2>/dev/null | grep -q ok" || true

# Step 4: maverick-dev ops command exists
run_step 4 "maverick-dev ops subcommand exists" \
    "maverick-dev ops --help 2>/dev/null | grep -i 'ops'" || true

# Step 5: maverick-dev ops rotation command works
run_step 5 "maverick-dev ops rotation command exists" \
    "maverick-dev ops rotation --help 2>/dev/null" || true

# Step 6: maverick-dev ops rotation shows status
run_step 6 "maverick-dev ops rotation prints current rotation status" \
    "maverick-dev ops rotation 2>/dev/null | wc -l | grep -v '^0$'" || true

# Step 7: maverick-dev ops smoke-tests command works
run_step 7 "maverick-dev ops smoke-tests command exists" \
    "maverick-dev ops smoke-tests --help 2>/dev/null" || true

# Step 8: Can view smoke test results
run_step 8 "maverick-dev ops smoke-tests shows latest results" \
    "maverick-dev ops smoke-tests 2>/dev/null | wc -l | grep -v '^0$'" || true

# Step 9: maverick-dev ops trace-analytics command works
run_step 9 "maverick-dev ops trace-analytics command exists" \
    "maverick-dev ops trace-analytics --help 2>/dev/null" || true

# Step 10: Can view trace analytics
run_step 10 "maverick-dev ops trace-analytics shows query stats" \
    "maverick-dev ops trace-analytics 2>/dev/null | wc -l | grep -v '^0$'" || true

# Step 11: maverick-dev ops guide-export-drift command works
run_step 11 "maverick-dev ops guide-export-drift checks drift" \
    "maverick-dev ops guide-export-drift --help 2>/dev/null" || true

# Step 12: Can detect guide export drift
run_step 12 "maverick-dev ops guide-export-drift reports status" \
    "maverick-dev ops guide-export-drift 2>/dev/null" || true

# Step 13: git tag for release works
run_step 13 "Can create a release tag (git tag)" \
    "git tag v1.1.0-test-persona 2>/dev/null" || true

# Step 14: Can list tags
run_step 14 "git tag shows created tag" \
    "git tag -l | grep 'v1.1.0-test-persona'" || true

# Step 15: goreleaser binary exists (or can be called)
run_step 15 "goreleaser is available" \
    "command -v goreleaser >/dev/null 2>&1" || true

# Step 16: Can build a snapshot release
run_step 16 "goreleaser build --snapshot succeeds" \
    "timeout 300 goreleaser build --snapshot 2>/dev/null | grep -i 'artifact\\|success'" || true

# Step 17: maverick-smoke.service exists on pulse
run_step 17 "maverick-smoke.service monitoring available" \
    "ssh -o ConnectTimeout=5 pulse-server 'systemctl is-active maverick-smoke.service' 2>/dev/null | grep -E '(active|inactive)'" || true

# Step 18: maverick-smoke.timer exists on pulse
run_step 18 "maverick-smoke.timer scheduling available" \
    "ssh -o ConnectTimeout=5 pulse-server 'systemctl is-active maverick-smoke.timer' 2>/dev/null | grep -E '(active|inactive)'" || true

# Step 19: maverick-trace.service exists on pulse
run_step 19 "maverick-trace.service running on pulse" \
    "ssh -o ConnectTimeout=5 pulse-server 'systemctl is-active maverick-trace.service' 2>/dev/null | grep -E '(active|inactive)'" || true

# Step 20: Can query `:QueryTrace` from graph (ops dashboards)
run_step 20 "Graph analytics: can query top users via QueryTrace" \
    "maverick --target maverick-dev shell 'MATCH (t:QueryTrace) RETURN count(t) as traces' 2>/dev/null | grep -E '(traces|count)'" || true

# Step 21: Can query drift events
run_step 21 "Graph analytics: can query drift events" \
    "maverick --target maverick-dev shell 'MATCH (d:DriftEvent) RETURN count(d) as drifts' 2>/dev/null | grep -E '(drifts|count)'" || true

# Step 22: Can query smoke test results from graph
run_step 22 "Graph analytics: can query smoke test results" \
    "maverick --target maverick-dev shell 'MATCH (s:SmokeTestResult) RETURN count(s) as tests' 2>/dev/null | grep -E '(tests|count)'" || true

# Step 23: Health check command works
run_step 23 "maverick health shows system status" \
    "maverick health 2>/dev/null | grep -E '(healthy|status|health)'" || true

# Step 24: Doctor command works
run_step 24 "maverick doctor diagnoses issues" \
    "maverick doctor 2>/dev/null | grep -E '(diagnosis|issue|check)'" || true

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
        echo "This is a RED test. These failures are expected — the maintainer commands haven't been implemented yet."
    fi
    if [ $BUDGET_RESULT -ne 0 ]; then
        echo "Time budget exceeded. See [BUDGET] lines above."
    fi
    exit 1
else
    echo ""
    echo -e "${GREEN}All steps passed! Maintainer persona is ready.${NC}"
    exit 0
fi
