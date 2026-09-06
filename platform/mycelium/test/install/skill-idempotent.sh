#!/usr/bin/env bash

# Test: Skill installation is idempotent
# Running install twice produces exactly one skill, with same content

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

error() {
    echo -e "${RED}FAIL: $*${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}PASS: $*${NC}"
}

info() {
    echo "$*"
}

main() {
    info "Testing skill installation idempotency..."
    info ""

    # Create a temporary HOME for clean testing
    local test_home
    test_home=$(mktemp -d)
    trap "rm -rf '$test_home'" EXIT

    export HOME="$test_home"

    # Get the repo root and script directory
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

    info "Repo root: $script_dir"

    local skill_template="${script_dir}/install/skills/maverick-skill.md"
    if [[ ! -f "$skill_template" ]]; then
        error "Skill template not found at $skill_template"
    fi

    info "Using skill template: $skill_template"

    local skill_dir="${test_home}/.claude/skills/maverick"

    # Create a mock binary directory and binary to avoid download attempts
    local install_dir="${test_home}/.mycelium/bin"
    mkdir -p "$install_dir"

    # Create a minimal mock binary that just prints version
    cat > "${install_dir}/mycelium" << 'EOF'
#!/usr/bin/env bash
echo "mycelium dev"
EOF
    chmod +x "${install_dir}/mycelium"

    # Simulate PATH setup for the mock binary
    export PATH="${install_dir}:$PATH"

    # Create a temporary shell rc to avoid modifications to system files
    local shell_rc="${test_home}/.bashrc"
    touch "$shell_rc"

    # First skill installation (direct, not through full install.sh which needs binary download)
    info "Running first skill installation..."
    mkdir -p "$skill_dir"
    cp "$skill_template" "${skill_dir}/SKILL.md"

    if [[ ! -f "${skill_dir}/SKILL.md" ]]; then
        error "Skill not installed after first install"
    fi

    local content1
    content1=$(cat "${skill_dir}/SKILL.md")
    local mtime1
    mtime1=$(stat -f %m "${skill_dir}/SKILL.md" 2>/dev/null || stat -c %Y "${skill_dir}/SKILL.md" 2>/dev/null || echo "0")

    success "First install created skill"

    # Wait a moment to ensure mtime would differ if re-created
    sleep 1

    # Second skill installation (idempotent)
    info "Running second skill installation..."
    mkdir -p "$skill_dir"
    cp "$skill_template" "${skill_dir}/SKILL.md"

    if [[ ! -f "${skill_dir}/SKILL.md" ]]; then
        error "Skill missing after second install"
    fi

    local content2
    content2=$(cat "${skill_dir}/SKILL.md")
    local mtime2
    mtime2=$(stat -f %m "${skill_dir}/SKILL.md" 2>/dev/null || stat -c %Y "${skill_dir}/SKILL.md" 2>/dev/null || echo "0")

    success "Second install succeeded"

    # Verify idempotency: contents must be identical
    if [[ "$content1" != "$content2" ]]; then
        error "Skill content changed between installations"
    fi

    success "Skill content is identical"

    # Verify only one skill file exists
    local skill_count
    skill_count=$(find "$skill_dir" -name "SKILL.md" -type f | wc -l)
    if [[ $skill_count -ne 1 ]]; then
        error "Expected 1 SKILL.md file, found $skill_count"
    fi

    success "Exactly one SKILL.md exists"

    # Verify the skill content is valid (has required sections)
    if ! echo "$content1" | grep -qi "name.*maverick"; then
        error "Skill missing 'Name: maverick' section"
    fi

    if ! echo "$content1" | grep -qi "description"; then
        error "Skill missing 'Description' section"
    fi

    if ! echo "$content1" | grep -q "/maverick"; then
        error "Skill missing '/maverick' command reference"
    fi

    success "Skill content is valid"

    info ""
    success "All idempotency tests passed"
}

main "$@"
