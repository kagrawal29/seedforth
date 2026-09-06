#!/usr/bin/env bash
# Test suite for mycelium inject subcommand
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test utilities
assert() {
  TESTS_RUN=$((TESTS_RUN + 1))
  local condition="$1"
  local message="$2"

  if eval "$condition"; then
    echo -e "${GREEN}✓${NC} $message"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}✗${NC} $message"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

assert_file_exists() {
  TESTS_RUN=$((TESTS_RUN + 1))
  local file="$1"

  if [ -f "$file" ]; then
    echo -e "${GREEN}✓${NC} File exists: $file"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}✗${NC} File missing: $file"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

assert_file_not_exists() {
  TESTS_RUN=$((TESTS_RUN + 1))
  local file="$1"

  if [ ! -f "$file" ]; then
    echo -e "${GREEN}✓${NC} File correctly absent: $file"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}✗${NC} File should NOT exist: $file"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

assert_dir_exists() {
  TESTS_RUN=$((TESTS_RUN + 1))
  local dir="$1"

  if [ -d "$dir" ]; then
    echo -e "${GREEN}✓${NC} Directory exists: $dir"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}✗${NC} Directory missing: $dir"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

assert_string_in_file() {
  TESTS_RUN=$((TESTS_RUN + 1))
  local string="$1"
  local file="$2"

  if grep -q "$string" "$file" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Found '$string' in $file"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}✗${NC} Missing '$string' in $file"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

assert_string_not_in_file() {
  TESTS_RUN=$((TESTS_RUN + 1))
  local string="$1"
  local file="$2"

  if ! grep -q "$string" "$file" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} '$string' correctly absent from $file"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}✗${NC} '$string' should NOT be in $file"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
}

# Cleanup function
cleanup() {
  if [ -d "$TEST_PROJECT" ]; then
    rm -rf "$TEST_PROJECT"
  fi
}

# Main test suite
main() {
  echo -e "${YELLOW}Starting mycelium inject test suite${NC}"
  echo ""

  # Create temporary test project
  TEST_PROJECT=$(mktemp -d)
  trap cleanup EXIT

  echo "Test project directory: $TEST_PROJECT"
  echo ""

  # Test 1: Basic injection with --project flag
  echo -e "${YELLOW}Test 1: Basic inject with --project flag${NC}"
  echo "# Test Project" > "$TEST_PROJECT/CLAUDE.md"
  "$REPO_ROOT/mycelium" inject --project "$TEST_PROJECT" 2>&1 | grep -v "secrets.env" || true
  assert_dir_exists "$TEST_PROJECT/.claude/rules"
  assert_file_exists "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  # CRITICAL: .mcp.json must NOT be created by inject
  assert_file_not_exists "$TEST_PROJECT/.claude/.mcp.json"
  echo ""

  # Test 2: Check mycelium-capability.md content (CLI-based, not MCP)
  echo -e "${YELLOW}Test 2: mycelium-capability.md has expected CLI sections${NC}"
  assert_string_in_file "mycelium --target prod ask" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_in_file "mycelium --target prod shell" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_in_file "mycelium --target prod status" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_in_file "Forest" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_in_file "forest aliases" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_in_file "Banyan" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_in_file "via Bash" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  # Must NOT register an MCP server or describe MCP tool names
  assert_string_not_in_file "mcpServers" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_not_in_file "mycelium_ask" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  assert_string_not_in_file "mycelium_query" "$TEST_PROJECT/.claude/rules/mycelium-capability.md"
  echo ""

  # Test 3: Check CLAUDE.md was updated
  echo -e "${YELLOW}Test 3: CLAUDE.md updated with mycelium section${NC}"
  assert_string_in_file "## Mycelium" "$TEST_PROJECT/CLAUDE.md"
  assert_string_in_file "mycelium --target prod ask" "$TEST_PROJECT/CLAUDE.md"
  assert_string_in_file "via Bash" "$TEST_PROJECT/CLAUDE.md"
  # CLAUDE.md section must NOT mention MCP tools
  assert_string_not_in_file "mycelium_ask" "$TEST_PROJECT/CLAUDE.md"
  assert_string_not_in_file "MCP" "$TEST_PROJECT/CLAUDE.md"
  echo ""

  # Test 4: Idempotency - running inject again should not duplicate
  echo -e "${YELLOW}Test 4: Idempotency - second inject is safe${NC}"
  "$REPO_ROOT/mycelium" inject --project "$TEST_PROJECT" >/dev/null 2>&1 || true
  local count=$(grep -c "## Mycelium" "$TEST_PROJECT/CLAUDE.md" || true)
  assert "[ '$count' -eq 1 ]" "Mycelium section appears exactly once (count: $count)"
  # Still no .mcp.json after re-run
  assert_file_not_exists "$TEST_PROJECT/.claude/.mcp.json"
  echo ""

  # Test 5: Inject into second project (different dir)
  echo -e "${YELLOW}Test 5: Inject into second project${NC}"
  TEST_PROJECT2=$(mktemp -d)
  trap "cleanup; rm -rf $TEST_PROJECT2" EXIT

  echo "# Another Project" > "$TEST_PROJECT2/CLAUDE.md"
  "$REPO_ROOT/mycelium" inject --project "$TEST_PROJECT2" 2>&1 | grep -v "secrets.env" || true

  assert_file_exists "$TEST_PROJECT2/.claude/rules/mycelium-capability.md"
  assert_file_not_exists "$TEST_PROJECT2/.claude/.mcp.json"
  assert_string_in_file "## Mycelium" "$TEST_PROJECT2/CLAUDE.md"
  echo ""

  # Test 6: Pre-existing .mcp.json is left alone (byte-identical)
  echo -e "${YELLOW}Test 6: Pre-existing .mcp.json is NOT touched${NC}"
  TEST_PROJECT3=$(mktemp -d)
  trap "cleanup; rm -rf $TEST_PROJECT2 $TEST_PROJECT3" EXIT

  mkdir -p "$TEST_PROJECT3/.claude"
  cat > "$TEST_PROJECT3/.claude/.mcp.json" <<'EOF'
{
  "mcpServers": {
    "other": {
      "command": "python3",
      "args": ["other-server.py"]
    }
  }
}
EOF
  local before_sha=$(shasum "$TEST_PROJECT3/.claude/.mcp.json" | awk '{print $1}')

  "$REPO_ROOT/mycelium" inject --project "$TEST_PROJECT3" 2>&1 | grep -v "secrets.env" || true

  assert_file_exists "$TEST_PROJECT3/.claude/rules/mycelium-capability.md"

  local after_sha=$(shasum "$TEST_PROJECT3/.claude/.mcp.json" | awk '{print $1}')
  assert "[ '$before_sha' = '$after_sha' ]" "Pre-existing .mcp.json is byte-identical (inject did not modify it)"

  if python3 -c "import json; d=json.load(open('$TEST_PROJECT3/.claude/.mcp.json')); assert 'other' in d['mcpServers'] and 'mycelium' not in d['mcpServers']" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} .mcp.json retains 'other' server and has NO mycelium entry"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo -e "${RED}✗${NC} .mcp.json was modified (mycelium added or other removed)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  fi
  TESTS_RUN=$((TESTS_RUN + 1))
  echo ""

  # Test 7: Non-existent directory error handling
  echo -e "${YELLOW}Test 7: Error on non-existent directory${NC}"
  if "$REPO_ROOT/mycelium" inject --project /nonexistent/path >/dev/null 2>&1; then
    echo -e "${RED}✗${NC} Should have failed for non-existent directory"
    TESTS_FAILED=$((TESTS_FAILED + 1))
  else
    echo -e "${GREEN}✓${NC} Correctly rejected non-existent directory"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  fi
  TESTS_RUN=$((TESTS_RUN + 1))
  echo ""

  # Test 8: Without CLAUDE.md
  echo -e "${YELLOW}Test 8: Inject into project without CLAUDE.md${NC}"
  TEST_PROJECT4=$(mktemp -d)
  trap "cleanup; rm -rf $TEST_PROJECT2 $TEST_PROJECT3 $TEST_PROJECT4" EXIT

  "$REPO_ROOT/mycelium" inject --project "$TEST_PROJECT4" 2>&1 | grep -v "secrets.env" || true

  assert_file_exists "$TEST_PROJECT4/.claude/rules/mycelium-capability.md"
  # Still no .mcp.json
  assert_file_not_exists "$TEST_PROJECT4/.claude/.mcp.json"
  # CLAUDE.md should not be auto-created
  assert "[ ! -f '$TEST_PROJECT4/CLAUDE.md' ]" "CLAUDE.md not auto-created"
  echo ""

  # Summary
  echo -e "${YELLOW}========================================${NC}"
  echo "Test Summary:"
  echo -e "  Total: $TESTS_RUN"
  echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
  if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
  fi
  echo -e "${YELLOW}========================================${NC}"

  if [ $TESTS_FAILED -gt 0 ]; then
    exit 1
  else
    exit 0
  fi
}

main "$@"
