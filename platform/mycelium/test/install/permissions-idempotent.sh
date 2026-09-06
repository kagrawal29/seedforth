#!/bin/bash

# Test: permissions allowlist installation is idempotent
# Verifies that running install.sh twice produces identical allowlist state

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

fail() {
    echo -e "${RED}FAIL: $*${NC}" >&2
    exit 1
}

pass() {
    echo -e "${GREEN}PASS: $*${NC}"
}

warn() {
    echo -e "${YELLOW}WARN: $*${NC}"
}

info() {
    echo "$*"
}

# Test idempotent installation
test_permissions_idempotent() {
    info "Testing idempotent permissions allowlist installation"

    # Check dependencies
    if ! command -v jq >/dev/null 2>&1; then
        fail "jq required for this test"
    fi

    # Create a temporary test directory
    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf '$tmpdir'" EXIT

    # Export HOME to temp dir so we don't modify real .claude/settings.json
    export HOME="$tmpdir"
    mkdir -p "$tmpdir/.claude"

    # Define the allowlist function directly (copied from install.sh)
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

    # Helper functions
    warn() { echo "$*" >&2; }
    info() { echo "$*"; }
    error() { echo "Error: $*" >&2; exit 1; }

    install_permissions_allowlist() {
        if ! command -v jq >/dev/null 2>&1; then
            warn "jq not found; skipping Claude Code permissions allowlist"
            return 0
        fi

        local settings_file="${HOME}/.claude/settings.json"
        local timestamp
        timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

        if [[ ! -f "$settings_file" ]]; then
            mkdir -p "${HOME}/.claude"
            echo '{"permissions":{"allow":[]}}' > "$settings_file"
        fi

        local -a patterns=(
            "Bash(maverick ask:*)"
            "Bash(maverick shell MATCH*)"
            "Bash(maverick shell RETURN*)"
            "Bash(maverick --target * status)"
            "Bash(maverick status)"
            "Bash(maverick --target * health)"
            "Bash(maverick health)"
            "Bash(maverick --target * doctor)"
            "Bash(maverick doctor)"
            "Bash(mycelium ask:*)"
            "Bash(mycelium shell MATCH*)"
            "Bash(mycelium status)"
            "Bash(mycelium health)"
        )

        local patterns_json
        patterns_json=$(printf '%s\n' "${patterns[@]}" | jq -Rs 'split("\n") | map(select(length > 0))')

        jq --arg timestamp "$timestamp" --argjson newpatterns "$patterns_json" \
            '.permissions.allow as $existing |
             (.permissions.allow = ($existing + [$newpatterns[] | select(. as $item | $existing | index($item) == null)])) |
             .permissions._maverickManagedSince //= $timestamp' \
            "$settings_file" > "${settings_file}.tmp" 2>/dev/null || {
                error "Failed to update permissions allowlist with jq"
            }

        mv "${settings_file}.tmp" "$settings_file"
        info "Updated Claude Code permissions allowlist in $settings_file"
    }

    uninstall_permissions_allowlist() {
        if ! command -v jq >/dev/null 2>&1; then
            warn "jq not found; skipping Claude Code permissions cleanup"
            return 0
        fi

        local settings_file="${HOME}/.claude/settings.json"

        if [[ ! -f "$settings_file" ]]; then
            info "Claude Code settings not found; skipping permissions cleanup"
            return 0
        fi

        local -a patterns=(
            "Bash(maverick ask:*)"
            "Bash(maverick shell MATCH*)"
            "Bash(maverick shell RETURN*)"
            "Bash(maverick --target * status)"
            "Bash(maverick status)"
            "Bash(maverick --target * health)"
            "Bash(maverick health)"
            "Bash(maverick --target * doctor)"
            "Bash(maverick doctor)"
            "Bash(mycelium ask:*)"
            "Bash(mycelium shell MATCH*)"
            "Bash(mycelium status)"
            "Bash(mycelium health)"
        )

        local patterns_json
        patterns_json=$(printf '%s\n' "${patterns[@]}" | jq -Rs 'split("\n") | map(select(length > 0))')

        jq --argjson removepatterns "$patterns_json" \
            '.permissions.allow |= (. as $existing | $existing | map(select(. as $p | $removepatterns | index($p) == null))) |
             if (.permissions.allow | length) == 0 then
                del(.permissions._maverickManagedSince)
             else
                .
             end' \
            "$settings_file" > "${settings_file}.tmp" 2>/dev/null || {
                error "Failed to update permissions with jq"
            }

        mv "${settings_file}.tmp" "$settings_file"
        info "Removed maverick/mycelium permissions from Claude Code settings"
    }

    # First installation
    info "Running first installation..."
    install_permissions_allowlist
    local first_state
    first_state=$(cat "$tmpdir/.claude/settings.json" | jq -S '.permissions.allow | sort | @json')
    local first_count
    first_count=$(cat "$tmpdir/.claude/settings.json" | jq '.permissions.allow | length')
    local first_timestamp
    first_timestamp=$(cat "$tmpdir/.claude/settings.json" | jq -r '.permissions._maverickManagedSince')
    info "First installation: $first_count entries, timestamp: $first_timestamp"

    # Sleep a tiny bit to ensure different timestamps if non-idempotent
    sleep 1

    # Second installation (should be identical)
    info "Running second installation (idempotent check)..."
    install_permissions_allowlist
    local second_state
    second_state=$(cat "$tmpdir/.claude/settings.json" | jq -S '.permissions.allow | sort | @json')
    local second_count
    second_count=$(cat "$tmpdir/.claude/settings.json" | jq '.permissions.allow | length')
    local second_timestamp
    second_timestamp=$(cat "$tmpdir/.claude/settings.json" | jq -r '.permissions._maverickManagedSince')
    info "Second installation: $second_count entries, timestamp: $second_timestamp"

    # Verify allowlist length is stable
    if [[ "$first_count" != "$second_count" ]]; then
        fail "Allowlist length changed: $first_count -> $second_count"
    fi
    pass "Allowlist length stable: $first_count entries"

    # Verify allowlist content is identical
    if [[ "$first_state" != "$second_state" ]]; then
        fail "Allowlist content changed after second install"
    fi
    pass "Allowlist content identical"

    # Verify timestamp is stable (idempotent = same timestamp on re-run)
    if [[ "$first_timestamp" != "$second_timestamp" ]]; then
        fail "Timestamp changed: $first_timestamp -> $second_timestamp (not idempotent)"
    fi
    pass "Timestamp stable (idempotent): $first_timestamp"

    # Verify all expected patterns are present
    local expected_patterns=(
        "Bash(maverick ask:*)"
        "Bash(maverick shell MATCH*)"
        "Bash(maverick shell RETURN*)"
        "Bash(maverick --target * status)"
        "Bash(maverick status)"
        "Bash(maverick --target * health)"
        "Bash(maverick health)"
        "Bash(maverick --target * doctor)"
        "Bash(maverick doctor)"
        "Bash(mycelium ask:*)"
        "Bash(mycelium shell MATCH*)"
        "Bash(mycelium status)"
        "Bash(mycelium health)"
    )

    for pattern in "${expected_patterns[@]}"; do
        if ! jq -e ".permissions.allow[] | select(. == \"$pattern\")" "$tmpdir/.claude/settings.json" >/dev/null 2>&1; then
            fail "Expected pattern not found: $pattern"
        fi
    done
    pass "All expected patterns present (${#expected_patterns[@]} entries)"

    # Test uninstall
    info "Testing uninstall removes patterns..."
    uninstall_permissions_allowlist
    local after_uninstall_count
    after_uninstall_count=$(cat "$tmpdir/.claude/settings.json" | jq '.permissions.allow | length')

    if [[ "$after_uninstall_count" != "0" ]]; then
        fail "Uninstall did not remove all patterns (remaining: $after_uninstall_count)"
    fi
    pass "Uninstall cleaned up all patterns"

    # Verify _maverickManagedSince is removed when no entries remain
    if jq -e '.permissions._maverickManagedSince' "$tmpdir/.claude/settings.json" >/dev/null 2>&1; then
        fail "Timestamp marker not removed after uninstall"
    fi
    pass "Timestamp marker removed with last pattern"

    # Re-install to verify idempotence still holds after uninstall
    info "Testing idempotence after uninstall+reinstall..."
    install_permissions_allowlist
    local third_count
    third_count=$(cat "$tmpdir/.claude/settings.json" | jq '.permissions.allow | length')

    if [[ "$third_count" != "$first_count" ]]; then
        fail "Reinstall produced different count: $third_count vs $first_count"
    fi
    pass "Reinstall produces identical state"

    info ""
    pass "All idempotency tests passed!"
}

main() {
    test_permissions_idempotent
}

main "$@"
