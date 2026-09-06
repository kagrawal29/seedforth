#!/usr/bin/env bash

# Maverick CLI Uninstaller
# Removes the maverick binary, PATH entries, and related files
# Usage: bash uninstall.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

error() {
    echo -e "${RED}Error: $*${NC}" >&2
    exit 1
}

success() {
    echo -e "${GREEN}$*${NC}"
}

warn() {
    echo -e "${YELLOW}$*${NC}"
}

info() {
    echo "$*"
}

# Remove CLAUDE.md directives marked by installer
uninstall_claude_md_directives() {
  local claude_md="${HOME}/.claude/CLAUDE.md"

  if [ ! -f "$claude_md" ]; then
    info "No $claude_md found, skipping"
    return 0
  fi

  # Remove the marked block if present
  if grep -q "<!-- MAVERICK_BLOCK_START -->" "$claude_md"; then
    # Use sed to remove lines between (and including) the markers
    if [[ "$OSTYPE" == "darwin"* ]]; then
      # macOS sed requires -i''
      sed -i '' '/<!-- MAVERICK_BLOCK_START -->/,/<!-- MAVERICK_BLOCK_END -->/d' "$claude_md"
    else
      # Linux sed
      sed -i '/<!-- MAVERICK_BLOCK_START -->/,/<!-- MAVERICK_BLOCK_END -->/d' "$claude_md"
    fi
    info "Removed CLAUDE.md directives block"
  fi
}

# Remove Claude Code permissions allowlist entries managed by maverick/mycelium installer
uninstall_permissions_allowlist() {
    # Check if jq is available
    if ! command -v jq >/dev/null 2>&1; then
        info "jq not found; skipping Claude Code permissions cleanup"
        return 0
    fi

    local settings_file="${HOME}/.claude/settings.json"

    # If settings.json doesn't exist, nothing to do
    if [[ ! -f "$settings_file" ]]; then
        info "Claude Code settings not found; skipping permissions cleanup"
        return 0
    fi

    # Define the patterns to remove (must match install script exactly)
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

    # Build JSON array of patterns
    local patterns_json
    patterns_json=$(printf '%s\n' "${patterns[@]}" | jq -Rs 'split("\n") | map(select(length > 0))')

    # Use jq to remove only the patterns we added
    jq --argjson removepatterns "$patterns_json" \
        '.permissions.allow |= (. as $existing | $existing | map(select(. as $p | $removepatterns | index($p) == null))) |
         if (.permissions.allow | length) == 0 then
            del(.permissions._maverickManagedSince)
         else
            .
         end' \
        "$settings_file" > "${settings_file}.tmp" 2>/dev/null || {
            warn "Failed to update permissions with jq" >&2
            return 1
        }

    mv "${settings_file}.tmp" "$settings_file"
    info "Removed maverick/mycelium permissions from Claude Code settings"
}

# Uninstall the maverick Claude Code skill
uninstall_maverick_skill() {
    local skill_dir="${HOME}/.claude/skills/maverick"
    if [[ -d "$skill_dir" ]]; then
        rm -rf "$skill_dir"
        info "Removed maverick skill from $skill_dir"
    fi
}

# Main uninstall flow
main() {
    info "Maverick CLI Uninstaller"
    info ""

    # Remove skill
    uninstall_maverick_skill

    # Remove CLAUDE.md directives
    uninstall_claude_md_directives

    # Remove Claude Code permissions
    uninstall_permissions_allowlist

    # Remove system-wide symlink
    local system_bin="${MYCELIUM_SYSTEM_BIN:-/usr/local/bin/mycelium}"
    if [[ -L "$system_bin" || -f "$system_bin" ]]; then
        if [[ -w "$(dirname "$system_bin")" ]]; then
            rm -f "$system_bin"
            info "Removed system symlink: $system_bin"
        elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
            sudo rm -f "$system_bin"
            info "Removed system symlink: $system_bin (via sudo)"
        else
            warn "Cannot remove $system_bin (no write permission)"
            warn "Run this to remove it manually:"
            warn "  sudo rm -f $system_bin"
        fi
    fi

    # Remove installation directory
    local install_dir="${HOME}/.mycelium"
    if [[ -d "$install_dir" ]]; then
        rm -rf "$install_dir"
        info "Removed installation directory: $install_dir"
    fi

    # Remove PATH entries from shell rc files
    local rc_files=("${HOME}/.bashrc" "${HOME}/.bash_profile" "${HOME}/.zshrc")
    for rc_file in "${rc_files[@]}"; do
        if [[ -f "$rc_file" ]]; then
            # Remove mycelium PATH lines and marker comment
            if grep -q "# mycelium CLI\|${install_dir}" "$rc_file" 2>/dev/null; then
                # Use a temporary file for safe in-place editing
                local tmpfile
                tmpfile=$(mktemp)
                grep -v "# mycelium CLI\|export PATH.*${install_dir}" "$rc_file" > "$tmpfile" 2>/dev/null || true
                mv "$tmpfile" "$rc_file"
                info "Removed maverick PATH entries from $rc_file"
            fi
        fi
    done

    echo ""
    success "Maverick uninstalled successfully!"
    echo "Your shell rc files were cleaned; you may need to restart your shell."
    echo ""
}

main "$@"
