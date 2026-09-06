#!/usr/bin/env bash
# Test utilities for UX test harness (Track F)
# Provides: timing budgets, graph assertions, sync verification

set -uo pipefail

# ANSI color codes
ansi_green="\033[32m"
ansi_red="\033[31m"
ansi_yellow="\033[33m"
ansi_blue="\033[34m"
ansi_dim="\033[2m"
ansi_reset="\033[0m"

# Repository root
TEST_REPO="$(cd "$(dirname "$0")/../.." && pwd)"

# Graph CLI (will use maverick once renamed)
GRAPH_CLI="${GRAPH_CLI:-./maverick-dev}"

# Timing and results tracking
declare -a TEST_RESULTS=()
TEST_PASS_COUNT=0
TEST_FAIL_COUNT=0

# ============================================================================
# Timing utilities (Track F wi-ux-02 budget tracking)
# ============================================================================

start_timer() {
  echo "$(date +%s%N)"
}

elapsed_seconds() {
  local start_ns="$1"
  local end_ns="${2:-$(date +%s%N)}"
  local elapsed_ns=$((end_ns - start_ns))
  echo $((elapsed_ns / 1000000000))
}

assert_time_budget() {
  local label="$1"
  local elapsed="$2"
  local budget="$3"

  if [ "$elapsed" -le "$budget" ]; then
    echo -e "${ansi_green}PASS${ansi_reset} $label: ${elapsed}s (budget: ${budget}s)"
    return 0
  else
    echo -e "${ansi_red}FAIL${ansi_reset} $label: ${elapsed}s exceeds budget of ${budget}s"
    return 1
  fi
}

# ============================================================================
# Graph assertion utilities
# ============================================================================

assert_node_exists() {
  local node_id="$1"
  local label="${2:-}"

  local query="MATCH (n"
  if [ -n "$label" ]; then
    query="${query}:${label}"
  fi
  query="${query} {node_id: '$node_id'}) RETURN count(n) as cnt"

  local result=$("$GRAPH_CLI" shell "$query" 2>&1 | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' || echo "0")

  if [ "$result" -eq 1 ]; then
    echo -e "${ansi_green}PASS${ansi_reset} assert_node_exists: $node_id"
    return 0
  else
    echo -e "${ansi_red}FAIL${ansi_reset} assert_node_exists: $node_id not found (count: $result)"
    return 1
  fi
}

assert_node_count() {
  local query="$1"
  local expected="$2"
  local label="${3:-nodes}"

  local result=$("$GRAPH_CLI" shell "$query" 2>&1 | grep -oE '\| [0-9]+ \|' | tail -1 | grep -oE '[0-9]+' || echo "0")

  if [ "$result" -eq "$expected" ]; then
    echo -e "${ansi_green}PASS${ansi_reset} assert_node_count: $label count = $expected"
    return 0
  else
    echo -e "${ansi_red}FAIL${ansi_reset} assert_node_count: expected $expected $label, got $result"
    return 1
  fi
}

assert_node_property() {
  local node_id="$1"
  local property="$2"
  local expected_value="$3"

  local query="MATCH (n {node_id: '$node_id'}) RETURN n.$property as val"
  local result=$("$GRAPH_CLI" shell "$query" 2>&1 | grep -v "^\|" | grep -v "^+" | head -1 | tr -d ' \n' || echo "")

  if [ "$result" = "$expected_value" ]; then
    echo -e "${ansi_green}PASS${ansi_reset} assert_node_property: $node_id.$property = $expected_value"
    return 0
  else
    echo -e "${ansi_red}FAIL${ansi_reset} assert_node_property: $node_id.$property; expected '$expected_value', got '$result'"
    return 1
  fi
}

assert_no_sync_conflicts() {
  local query="MATCH (c:SyncConflict) RETURN count(c) as cnt"
  local result=$("$GRAPH_CLI" shell "$query" 2>&1 | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' || echo "0")

  if [ "$result" -eq 0 ]; then
    echo -e "${ansi_green}PASS${ansi_reset} assert_no_sync_conflicts: 0 conflicts"
    return 0
  else
    echo -e "${ansi_red}FAIL${ansi_reset} assert_no_sync_conflicts: $result conflicts found"
    return 1
  fi
}

# ============================================================================
# Sync and namespace utilities
# ============================================================================

seed_local_nodes() {
  local count="$1"
  local namespace="${2:-local-testuser}"
  local label="${3:-TestNode}"

  echo "Seeding $count local nodes in namespace '$namespace' with label '$label'..."

  for i in $(seq 1 "$count"); do
    local node_id="${namespace}-node-${i}"
    local cypher="MERGE (n:${label} {node_id: '$node_id', project: '${namespace}', local_only: true}) SET n.created_at = datetime(), n.test_index = $i RETURN n.node_id"
    "$GRAPH_CLI" shell "$cypher" >/dev/null 2>&1 || {
      echo -e "${ansi_red}FAIL${ansi_red} Failed to seed node $i"
      return 1
    }
  done

  echo -e "${ansi_green}PASS${ansi_reset} Seeded $count local nodes"
  return 0
}

assert_local_nodes_preserved() {
  local expected_count="$1"
  local namespace="${2:-local-testuser}"

  local query="MATCH (n {project: '${namespace}', local_only: true}) RETURN count(n) as cnt"
  local result=$("$GRAPH_CLI" shell "$query" 2>&1 | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' || echo "0")

  if [ "$result" -eq "$expected_count" ]; then
    echo -e "${ansi_green}PASS${ansi_reset} assert_local_nodes_preserved: $expected_count nodes preserved"
    return 0
  else
    echo -e "${ansi_red}FAIL${ansi_reset} assert_local_nodes_preserved: expected $expected_count, got $result"
    return 1
  fi
}

assert_manifest_applied() {
  local query="$1"
  local label="${2:-}"

  # Generic check: if query returns > 0, manifest has content
  local result=$("$GRAPH_CLI" shell "$query" 2>&1 | grep -oE '\| [0-9]+ \|' | grep -oE '[0-9]+' || echo "0")

  if [ "$result" -gt 0 ]; then
    echo -e "${ansi_green}PASS${ansi_reset} assert_manifest_applied: $label present (count: $result)"
    return 0
  else
    echo -e "${ansi_red}FAIL${ansi_reset} assert_manifest_applied: $label not found (count: $result)"
    return 1
  fi
}

# ============================================================================
# Test result tracking
# ============================================================================

record_test() {
  local name="$1"
  local passed="$2"

  if [ "$passed" -eq 1 ]; then
    TEST_PASS_COUNT=$((TEST_PASS_COUNT + 1))
    TEST_RESULTS+=("${ansi_green}PASS${ansi_reset}: $name")
  else
    TEST_FAIL_COUNT=$((TEST_FAIL_COUNT + 1))
    TEST_RESULTS+=("${ansi_red}FAIL${ansi_reset}: $name")
  fi
}

print_summary() {
  echo ""
  echo "============================================"
  echo "Test Summary"
  echo "============================================"
  echo -e "${ansi_green}PASS: $TEST_PASS_COUNT${ansi_reset}"
  echo -e "${ansi_red}FAIL: $TEST_FAIL_COUNT${ansi_reset}"

  if [ "$TEST_FAIL_COUNT" -gt 0 ]; then
    return 1
  fi
  return 0
}
