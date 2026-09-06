#!/usr/bin/env bash

# Mycelium CLI Installer
# Downloads and installs the mycelium binary for macOS, Linux, or Windows Subsystem for Linux.
# Usage: bash install.sh

set -euo pipefail

# Dependencies: bash, curl, sha256sum, tar, jq (for permissions allowlist)

# Colors for output (safe fallback if tput unavailable)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Detect OS and architecture
detect_platform() {
    local os
    local arch

    case "$(uname -s)" in
        Darwin)
            os="darwin"
            ;;
        Linux)
            os="linux"
            ;;
        *)
            error "Unsupported OS: $(uname -s). Only macOS and Linux are supported."
            ;;
    esac

    case "$(uname -m)" in
        x86_64)
            arch="amd64"
            ;;
        aarch64)
            arch="arm64"
            ;;
        arm64)
            arch="arm64"
            ;;
        *)
            error "Unsupported architecture: $(uname -m). Only amd64 and arm64 are supported."
            ;;
    esac

    echo "${os}_${arch}"
}

# Detect shell from SHELL environment variable
detect_shell() {
    local shell_path="${SHELL:-/bin/bash}"
    basename "$shell_path"
}

# Add to PATH if not already present
add_to_path() {
    local bin_dir="$1"
    local shell_rc="$2"
    local path_line="export PATH=\"$bin_dir:\$PATH\""

    # Check if already in the file
    if grep -q "$(echo "$bin_dir" | sed 's/[[\.*^$/]/\\&/g')" "$shell_rc" 2>/dev/null; then
        info "PATH entry already exists in $shell_rc"
        return 0
    fi

    # Append to shell rc file
    {
        echo ""
        echo "# mycelium CLI"
        echo "$path_line"
    } >> "$shell_rc"

    info "Added mycelium to PATH in $shell_rc"
}

# Install Claude Code permissions allowlist for read-only maverick/mycelium patterns
install_permissions_allowlist() {
    # Check if jq is available
    if ! command -v jq >/dev/null 2>&1; then
        warn "jq not found; skipping Claude Code permissions allowlist"
        return 0
    fi

    local settings_file="${HOME}/.claude/settings.json"
    local timestamp
    timestamp=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

    # If settings.json doesn't exist, create a minimal structure
    if [[ ! -f "$settings_file" ]]; then
        mkdir -p "${HOME}/.claude"
        echo '{"permissions":{"allow":[]}}' > "$settings_file"
    fi

    # Define the read-only patterns to allow (these do not prompt)
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

    # Use jq to merge patterns idempotently: keep existing, add new (no duplicates)
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

# Install the maverick Claude Code skill
install_maverick_skill() {
    local skill_dir="${HOME}/.claude/skills/maverick"
    mkdir -p "$skill_dir"

    # Get the directory where this script is located (for relative path to skill template)
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Copy the skill template
    if [[ -f "${script_dir}/skills/maverick-skill.md" ]]; then
        cp "${script_dir}/skills/maverick-skill.md" "${skill_dir}/SKILL.md"
        info "Installed maverick skill to $skill_dir/SKILL.md"
    else
        warn "Skill template not found at ${script_dir}/skills/maverick-skill.md (this is OK if installing from release)"
    fi
}

# Main installation flow
main() {
    info "Mycelium CLI Installer"
    info ""

    # Detect platform
    local platform
    platform=$(detect_platform)
    info "Detected platform: $platform"

    # Parse platform
    local os arch
    IFS='_' read -r os arch <<< "$platform"

    # Construct release URL. MYCELIUM_INSTALL_BASE_URL overrides the default
    # for local e2e testing against a snapshot build (file:// or http://localhost/...).
    local base_url="${MYCELIUM_INSTALL_BASE_URL:-https://github.com/Qubit-Capital/maverick/releases/latest/download}"
    local tar_filename="mycelium_${os}_${arch}"

    # Handle tar.gz vs zip (windows uses zip, unix uses tar.gz)
    local archive_filename
    if [[ "$os" == "windows" ]]; then
        archive_filename="${tar_filename}.zip"
    else
        archive_filename="${tar_filename}.tar.gz"
    fi

    local download_url="${base_url}/${archive_filename}"
    local checksums_url="${base_url}/checksums.txt"

    info "Downloading from: $download_url"

    # Download to temp directory
    local tmpdir
    tmpdir=$(mktemp -d)
    trap "rm -rf '$tmpdir'" EXIT

    local archive_path="${tmpdir}/${archive_filename}"
    local checksums_path="${tmpdir}/checksums.txt"

    # Fetch helper: try plain curl first (works for public repos / custom mirrors);
    # on 404, fall back to `gh release download` since Qubit-Capital/maverick is a
    # private repo and teammates authenticate via `gh auth login`.
    fetch_asset() {
        local url="$1" out="$2" name="$3"
        if curl -fsSL "$url" -o "$out" 2>/dev/null; then
            return 0
        fi
        if [[ "${MYCELIUM_INSTALL_BASE_URL:-}" != "" ]]; then
            return 1
        fi
        if ! command -v gh >/dev/null 2>&1; then
            error "Direct download failed (private repo) and \`gh\` CLI is not installed.
  Install GitHub CLI: https://cli.github.com/
  Then authenticate:   gh auth login
  Then re-run this installer."
        fi
        if ! gh auth status >/dev/null 2>&1; then
            error "Direct download failed (private repo) and \`gh\` is not authenticated.
  Run: gh auth login
  Then re-run this installer."
        fi
        info "Public download failed; using gh CLI to fetch $name from private repo..."
        local gh_args=(--repo Qubit-Capital/maverick --pattern "$name" --output "$out" --clobber)
        if [[ -n "${MYCELIUM_RELEASE_TAG:-}" ]]; then
            gh release download "$MYCELIUM_RELEASE_TAG" "${gh_args[@]}" 2>&1 \
                || error "gh release download failed for $name (tag: $MYCELIUM_RELEASE_TAG)"
        else
            gh release download "${gh_args[@]}" 2>&1 \
                || error "gh release download failed for $name"
        fi
    }

    # Download archive
    fetch_asset "$download_url" "$archive_path" "$archive_filename"
    info "Downloaded $archive_filename"

    # Download checksums
    fetch_asset "$checksums_url" "$checksums_path" "checksums.txt"

    # Verify SHA256
    info "Verifying SHA256 checksum..."
    local expected_checksum
    expected_checksum=$(grep "$archive_filename" "$checksums_path" | awk '{print $1}')

    if [[ -z "$expected_checksum" ]]; then
        error "Checksum not found in checksums.txt for $archive_filename"
    fi

    local actual_checksum
    actual_checksum=$(shasum -a 256 "$archive_path" | awk '{print $1}')

    if [[ "$expected_checksum" != "$actual_checksum" ]]; then
        error "Checksum mismatch! Expected: $expected_checksum, Got: $actual_checksum"
    fi
    info "Checksum verified"

    # Create install directory
    local install_dir="${HOME}/.mycelium/bin"
    mkdir -p "$install_dir"

    # Extract binary
    info "Extracting binary..."
    if [[ "$os" == "windows" ]]; then
        unzip -q "$archive_path" -d "$tmpdir" || error "Failed to extract $archive_filename"
    else
        tar -xzf "$archive_path" -C "$tmpdir" || error "Failed to extract $archive_filename"
    fi

    # Find the binary in extracted files (may be in a subdirectory)
    local binary_path
    binary_path=$(find "$tmpdir" -name "mycelium" -type f | head -1)

    if [[ -z "$binary_path" ]]; then
        error "Binary 'mycelium' not found in archive"
    fi

    # Copy to install directory
    cp "$binary_path" "${install_dir}/mycelium"
    chmod 0755 "${install_dir}/mycelium"
    info "Installed mycelium to $install_dir/mycelium"

    # System-wide symlink — makes mycelium available to every process on the
    # machine including Claude Code subprocesses (which don't source rc files).
    # Opt out with MYCELIUM_SYSTEM_SYMLINK=0, override target with MYCELIUM_SYSTEM_BIN.
    local system_bin="${MYCELIUM_SYSTEM_BIN:-/usr/local/bin/mycelium}"
    local system_dir
    system_dir=$(dirname "$system_bin")
    if [[ "${MYCELIUM_SYSTEM_SYMLINK:-1}" == "1" ]]; then
        if [[ -w "$system_dir" ]]; then
            ln -sf "${install_dir}/mycelium" "$system_bin"
            success "Linked $system_bin -> $install_dir/mycelium (no sudo needed)"
        elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
            sudo ln -sf "${install_dir}/mycelium" "$system_bin" \
                && success "Linked $system_bin -> $install_dir/mycelium (via passwordless sudo)"
        else
            warn "Skipping system-wide symlink: no write access to $system_dir and no passwordless sudo."
            warn "Run this once to enable agent + subprocess access:"
            warn "  sudo ln -sf ${install_dir}/mycelium $system_bin"
        fi
    fi

    # Update PATH in the user's shell rc so interactive sessions also pick it up.
    local shell_name
    shell_name=$(detect_shell)

    local shell_rc
    case "$shell_name" in
        bash)
            if [[ -f "${HOME}/.bashrc" ]]; then
                shell_rc="${HOME}/.bashrc"
            elif [[ -f "${HOME}/.bash_profile" ]]; then
                shell_rc="${HOME}/.bash_profile"
            else
                shell_rc="${HOME}/.bashrc"
                touch "$shell_rc"
            fi
            ;;
        zsh)
            shell_rc="${HOME}/.zshrc"
            if [[ ! -f "$shell_rc" ]]; then
                touch "$shell_rc"
            fi
            ;;
        *)
            warn "Unsupported shell: $shell_name. Skipping PATH update."
            warn "Manually add to your shell profile: export PATH=\"${install_dir}:\$PATH\""
            shell_rc=""
            ;;
    esac

    if [[ -n "$shell_rc" ]]; then
        add_to_path "$install_dir" "$shell_rc"
    fi

    # Install Claude Code permissions allowlist
    install_permissions_allowlist

    # Install the maverick skill for Claude Code
    install_maverick_skill

    # Success message
    echo ""
    success "mycelium installed successfully!"
    echo ""
    info "To get started:"
    info "  1. Restart your shell or run: source $shell_rc"
    info "  2. Verify installation: mycelium version"
    info ""
    info "For more information, see:"
    info "  https://github.com/Qubit-Capital/maverick/blob/main/README.md"
}

main "$@"
