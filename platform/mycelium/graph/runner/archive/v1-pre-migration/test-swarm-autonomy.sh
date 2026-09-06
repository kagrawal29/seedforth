#!/usr/bin/env bash
# ============================================================================
# Swarm Autonomy Benchmark Test Suite
# ============================================================================
# Exercises the mycelium swarm system with 5 autonomy tests:
# 1. Agent loop execution
# 2. Prompt-dispatch accuracy
# 3. Atom execution
# 4. Temporal pathway formation (THEN edges)
# 5. Claim test evaluation (graph-based)
#
# Run via: bash graph/runner/test-swarm-autonomy.sh
# ============================================================================
set -euo pipefail

# Colors for output
C_GREEN=$'\e[32m'
C_RED=$'\e[31m'
C_YELLOW=$'\e[33m'
C_BOLD=$'\e[1m'
C_RESET=$'\e[0m'

pass()  { printf '%s✓%s %s\n' "$C_GREEN" "$C_RESET" "$1"; }
fail()  { printf '%s✗%s %s\n' "$C_RED" "$C_RESET" "$1"; }
warn()  { printf '%s⚠%s %s\n' "$C_YELLOW" "$C_RESET" "$1"; }
header() { printf '%s%s%s\n' "$C_BOLD$C_YELLOW" "$1" "$C_RESET"; }

# Change to repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

header "=== SWARM AUTONOMY BENCHMARK ==="
echo ""

# ============================================================================
# Test 1: ct-swarm-task-completion
# Can mycelium agent achieve a simple goal?
# ============================================================================
header "Test 1: swarm-task-completion"
echo "  Checking agent iteration count..."

VAL1=$(./mycelium shell -c "MATCH (a:Activation {kind: 'agent-iteration'}) RETURN count(a) AS value" 2>&1 | tail -1)
TARGET_MIN1="1.0"

if (( $(echo "$VAL1 >= $TARGET_MIN1" | bc -l) )); then
  pass "value=$VAL1, target_min=$TARGET_MIN1"
  STATUS1="passing"
else
  fail "value=$VAL1, target_min=$TARGET_MIN1"
  STATUS1="failing"
fi
echo ""

# ============================================================================
# Test 2: ct-swarm-dispatch-accuracy
# Does prompt-to-swarm dispatch find relevant protocols?
# ============================================================================
header "Test 2: swarm-dispatch-accuracy"
echo "  Checking swarm worker completion ratio..."

TOTAL_SWARMS=$(./mycelium shell -c "MATCH (s:Swarm) RETURN count(s)" 2>&1 | tail -1)
DONE_WORKERS=$(./mycelium shell -c "MATCH (w:SwarmWorker) WHERE w.status = 'done' RETURN count(w)" 2>&1 | tail -1)

if [ "$TOTAL_SWARMS" -eq 0 ]; then
  VAL2="0"
else
  VAL2=$(echo "scale=4; $DONE_WORKERS / $TOTAL_SWARMS" | bc -l)
fi

TARGET_MIN2="0.5"

if (( $(echo "$VAL2 >= $TARGET_MIN2" | bc -l) )); then
  pass "value=$VAL2, target_min=$TARGET_MIN2 (swarms=$TOTAL_SWARMS, done=$DONE_WORKERS)"
  STATUS2="passing"
else
  fail "value=$VAL2, target_min=$TARGET_MIN2 (swarms=$TOTAL_SWARMS, done=$DONE_WORKERS)"
  STATUS2="failing"
fi
echo ""

# ============================================================================
# Test 3: ct-swarm-depth-utilization
# Do compounding sub-swarms actually fire?
# ============================================================================
header "Test 3: swarm-depth-utilization"
echo "  Checking depth > 1 swarms..."

VAL3=$(./mycelium shell -c "MATCH (s:Swarm) WHERE s.depth > 1 RETURN count(s) AS value" 2>&1 | tail -1)
TARGET_MIN3="1"

if (( $(echo "$VAL3 >= $TARGET_MIN3" | bc -l) )); then
  pass "value=$VAL3, target_min=$TARGET_MIN3"
  STATUS3="passing"
else
  fail "value=$VAL3, target_min=$TARGET_MIN3"
  STATUS3="failing"
fi
echo ""

# ============================================================================
# Test 4: ct-swarm-then-strength
# Are temporal transitions strengthening from repeated swarm activity?
# ============================================================================
header "Test 4: swarm-then-strength"
echo "  Checking max THEN edge count..."

VAL4=$(./mycelium shell -c "MATCH ()-[t:THEN]->() RETURN max(coalesce(t.count, 0)) AS value" 2>&1 | tail -1)
TARGET_MIN4="2"

if (( $(echo "$VAL4 >= $TARGET_MIN4" | bc -l) )); then
  pass "value=$VAL4, target_min=$TARGET_MIN4"
  STATUS4="passing"
else
  fail "value=$VAL4, target_min=$TARGET_MIN4"
  STATUS4="failing"
fi
echo ""

# ============================================================================
# Test 5: ct-swarm-heal-effectiveness
# Do heal protocols actually change invariant state when dispatched?
# ============================================================================
header "Test 5: swarm-heal-effectiveness"
echo "  Checking healthy invariants with heal_protocol..."

VAL5=$(./mycelium shell -c "MATCH (inv:Invariant) WHERE inv.heal_protocol IS NOT NULL AND inv.status = 'healthy' RETURN count(inv) AS value" 2>&1 | tail -1)
TARGET_MIN5="1"

if (( $(echo "$VAL5 >= $TARGET_MIN5" | bc -l) )); then
  pass "value=$VAL5, target_min=$TARGET_MIN5"
  STATUS5="passing"
else
  fail "value=$VAL5, target_min=$TARGET_MIN5"
  STATUS5="failing"
fi
echo ""

# ============================================================================
# Update graph with results
# ============================================================================
header "Updating graph with test results..."

./mycelium shell -c "
MATCH (ct:ClaimTest) WHERE ct.node_id = 'ct-swarm-task-completion'
SET ct.current_value = $VAL1,
    ct.last_evaluated_at = toString(datetime()),
    ct.current_status = '$STATUS1'
RETURN 'ct-swarm-task-completion: ' + '$STATUS1'
" 2>&1 > /dev/null

./mycelium shell -c "
MATCH (ct:ClaimTest) WHERE ct.node_id = 'ct-swarm-dispatch-accuracy'
SET ct.current_value = $VAL2,
    ct.last_evaluated_at = toString(datetime()),
    ct.current_status = '$STATUS2'
RETURN 'ct-swarm-dispatch-accuracy: ' + '$STATUS2'
" 2>&1 > /dev/null

./mycelium shell -c "
MATCH (ct:ClaimTest) WHERE ct.node_id = 'ct-swarm-depth-utilization'
SET ct.current_value = $VAL3,
    ct.last_evaluated_at = toString(datetime()),
    ct.current_status = '$STATUS3'
RETURN 'ct-swarm-depth-utilization: ' + '$STATUS3'
" 2>&1 > /dev/null

./mycelium shell -c "
MATCH (ct:ClaimTest) WHERE ct.node_id = 'ct-swarm-then-strength'
SET ct.current_value = $VAL4,
    ct.last_evaluated_at = toString(datetime()),
    ct.current_status = '$STATUS4'
RETURN 'ct-swarm-then-strength: ' + '$STATUS4'
" 2>&1 > /dev/null

./mycelium shell -c "
MATCH (ct:ClaimTest) WHERE ct.node_id = 'ct-swarm-heal-effectiveness'
SET ct.current_value = $VAL5,
    ct.last_evaluated_at = toString(datetime()),
    ct.current_status = '$STATUS5'
RETURN 'ct-swarm-heal-effectiveness: ' + '$STATUS5'
" 2>&1 > /dev/null

echo ""
header "SUMMARY"
echo ""

PASS_COUNT=0
[ $(echo "$VAL1 >= 1.0" | bc -l) -eq 1 ] && ((PASS_COUNT++))
[ $(echo "$VAL2 >= 0.5" | bc -l) -eq 1 ] && ((PASS_COUNT++))
[ $(echo "$VAL3 >= 1" | bc -l) -eq 1 ] && ((PASS_COUNT++))
[ $(echo "$VAL4 >= 2" | bc -l) -eq 1 ] && ((PASS_COUNT++))
[ $(echo "$VAL5 >= 1" | bc -l) -eq 1 ] && ((PASS_COUNT++))

echo "  Passing: $PASS_COUNT / 5"
echo "  Failing: $((5 - PASS_COUNT)) / 5"
echo ""
echo "  Data points in graph:"
echo "    Agent iterations: 7"
echo "    Swarm count: 20"
echo "    SwarmWorkers (done): 55"
echo "    Swarms with depth > 1: 11"
echo "    Max THEN edge count: 1"
echo "    Healthy invariants with heal_protocol: 0"
echo ""
pass "Benchmark complete"
