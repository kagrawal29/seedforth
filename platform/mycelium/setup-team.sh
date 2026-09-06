#!/usr/bin/env bash
# ============================================================================
# Team Onboarding Script for Mycelium
# ============================================================================
# Sets up a new teammate's local environment with access to prod/dev on
# pulse-server and a writable local copy of mycelium.
#
# Idempotent: safe to re-run. Detects existing config and prompts first.
# Supports both macOS and Linux.
#
# Usage:
#   bash setup-team.sh
#
# After setup:
#   mycelium --target prod ask "what is the system health status"
#   mycelium --target local status
# ============================================================================
set -euo pipefail

# Colors for output
say()   { printf '\e[1;36m[setup]\e[0m %s\n' "$*"; }
ok()    { printf '\e[32m✓\e[0m %s\n' "$*"; }
warn()  { printf '\e[33m⚠\e[0m %s\n' "$*"; }
err()   { printf '\e[31m✗\e[0m %s\n' "$*"; }

# Configuration paths
MYCELIUM_DIR="${MYCELIUM_DIR:-$HOME/.mycelium}"
CONFIG_TOML="$MYCELIUM_DIR/config.toml"
SECRETS_ENV="$MYCELIUM_DIR/secrets.env"

# Defaults
TEAM_NAME=""
PROD_PASS=""
DEV_PASS=""
SKIP_CONNECTIVITY_TEST=0

# Helper: prompt for hidden input (password)
prompt_password() {
  local prompt="$1"
  local value=""

  if [ -t 0 ]; then
    # Terminal attached: use stty to hide input
    printf '%s' "$prompt"
    stty -echo
    read -r value
    stty echo
    printf '\n'
  else
    # No terminal (CI/automation): read from env var
    printf '%s (via env var): ' "$prompt"
    read -r value
  fi

  echo "$value"
}

# Helper: prompt for visible input
prompt_input() {
  local prompt="$1"
  local default="${2:-}"
  local value=""

  if [ -n "$default" ]; then
    printf '%s [%s]: ' "$prompt" "$default"
  else
    printf '%s: ' "$prompt"
  fi
  read -r value

  if [ -z "$value" ]; then
    value="$default"
  fi
  echo "$value"
}

# Helper: check if command exists
has_command() {
  command -v "$1" >/dev/null 2>&1
}

# Helper: run command with timeout if available
maybe_timeout() {
  local secs="$1"; shift
  if has_command timeout; then
    timeout "$secs" "$@"
  elif has_command gtimeout; then
    gtimeout "$secs" "$@"
  else
    "$@"
  fi
}

# Helper: prompt yes/no with explicit default
prompt_yes_no() {
  local prompt="$1"
  local default="${2:-n}"  # default is 'n' (no) unless specified
  local response=""

  printf '%s [%s]: ' "$prompt" "$default"
  read -r response </dev/tty 2>/dev/null || read -r response

  if [ -z "$response" ]; then
    response="$default"
  fi

  case "$response" in
    [yY]|[yY][eE][sS]) return 0 ;;
    *) return 1 ;;
  esac
}

# Helper: validate and normalize forest alias
validate_forest_alias() {
  local alias="$1"
  local normalized=""

  # Normalize to lowercase first
  normalized=$(echo "$alias" | tr '[:upper:]' '[:lower:]')

  # Capitalize first letter (portable solution)
  normalized="$(echo "$normalized" | cut -c1 | tr '[:lower:]' '[:upper:]')$(echo "$normalized" | cut -c2-)"

  # Check against allowed list
  case "$normalized" in
    Banyan|Sequoia|Birch|Cedar|Oak|Mycelium)
      echo "$normalized"
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

# ============================================================================
# 0a. Platform guard — macOS / Linux / WSL only. Native Windows (PowerShell,
#     cmd.exe, Git Bash without WSL) is redirected to docs/windows-setup.md.
# ============================================================================
detect_platform() {
  case "$(uname -s 2>/dev/null)" in
    Darwin)               echo "macos" ;;
    Linux)
      if grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null; then
        echo "wsl"
      else
        echo "linux"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*) echo "windows-native" ;;
    *)                    echo "unknown" ;;
  esac
}

PLATFORM="$(detect_platform)"
case "$PLATFORM" in
  macos|linux|wsl)
    ok "Detected platform: $PLATFORM"
    ;;
  windows-native)
    err "Native Windows (Git Bash / Cygwin / MSYS) is not supported."
    err "Mycelium's toolchain (Neo4j, cypher-shell, Ollama) is Unix-native."
    say ""
    say "On Windows: install WSL2 + Ubuntu, then run this script from inside Ubuntu."
    say "Full guide: docs/windows-setup.md"
    say ""
    say "TL;DR (from PowerShell as Administrator):"
    say "    wsl --install -d Ubuntu"
    say "Then open Ubuntu, clone this repo there, and re-run bash setup-team.sh"
    exit 2
    ;;
  unknown)
    warn "Unknown platform: $(uname -s). Proceeding but some steps may fail."
    ;;
esac

# ============================================================================
# 0. Run OS Diagnostics
# ============================================================================
say "Running OS environment diagnostics..."

# Get the directory where this script is running (maverick root)
MAVERICK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCTOR_SCRIPT="$MAVERICK_DIR/doctor.sh"

if [ ! -f "$DOCTOR_SCRIPT" ]; then
  warn "doctor.sh not found at $DOCTOR_SCRIPT"
  say "Skipping OS diagnostics and continuing with basic checks..."
else
  if bash "$DOCTOR_SCRIPT"; then
    ok "OS environment ready"
  else
    err "OS environment check failed. See messages above."
    say ""
    say "For unsupported OSes, see: docs/os-support.md"
    exit 1
  fi
fi

# ============================================================================
# 1. Check Prerequisites
# ============================================================================
say "Checking prerequisites..."

if ! has_command git; then
  err "git is required"
  exit 1
fi
ok "git found"

if ! has_command python3; then
  err "python3 is required"
  exit 1
fi
ok "python3 found"

# Check Neo4j (optional but recommended locally)
if ! has_command neo4j; then
  warn "neo4j not found in PATH (install with: brew install neo4j)"
  if ! prompt_yes_no "Continue without Neo4j? (read-only access to prod/dev)"; then
    exit 1
  fi
  SKIP_CONNECTIVITY_TEST=1
else
  ok "neo4j found"
fi

# Check for APOC driver availability (can be checked after connection)
# Check for Ollama (optional but recommended)
if ! has_command ollama; then
  warn "ollama not found (optional, needed for semantic queries)"
else
  ok "ollama found"
fi

# ============================================================================
# 2. Check Existing Config
# ============================================================================
if [ -f "$CONFIG_TOML" ]; then
  warn "Existing config found at $CONFIG_TOML"
  if ! prompt_yes_no "Overwrite existing configuration?"; then
    say "Keeping existing config. Exiting."
    exit 0
  fi
fi

say "Creating $MYCELIUM_DIR..."
mkdir -p "$MYCELIUM_DIR"

# ============================================================================
# 3. Load Team Credentials from team-credentials.env
# ============================================================================
say ""
say "Loading team credentials from team-credentials.env..."

TEAM_CREDS_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/team-credentials.env"

if [ ! -f "$TEAM_CREDS_FILE" ]; then
  err "team-credentials.env not found at $TEAM_CREDS_FILE"
  err ""
  err "The credentials file should be at the repo root. If it's missing, run:"
  err "  bash scripts/rotate-team-creds.sh --target both"
  err ""
  err "Then commit and push the updated team-credentials.env:"
  err "  git add team-credentials.env"
  err "  git commit -m 'rotate: team readonly creds $(date +%Y-%m-%d)'"
  err "  git push"
  exit 1
fi

# Source the credentials file (contains MYCELIUM_PROD_USER, MYCELIUM_PROD_PASS, etc.)
# shellcheck disable=SC1090
source "$TEAM_CREDS_FILE"

PROD_PASS="${MYCELIUM_PROD_PASS:-}"
if [ -z "$PROD_PASS" ]; then
  err "MYCELIUM_PROD_PASS not found in team-credentials.env"
  exit 1
fi

DEV_PASS="${MYCELIUM_DEV_PASS:-}"
if [ -z "$DEV_PASS" ]; then
  err "MYCELIUM_DEV_PASS not found in team-credentials.env"
  exit 1
fi

ok "Team credentials loaded from repo"

# ============================================================================
# 4. Prompt for Team Name (Forest Alias) — Optional
# ============================================================================
say ""
say "Forest aliases: Banyan, Sequoia, Birch, Cedar, Oak, Mycelium"

# Check for environment variable override
TEAM_NAME="${MYCELIUM_ALIAS:-}"

if [ -z "$TEAM_NAME" ]; then
  # Interactive prompt with validation loop (optional, defaults to prompting)
  while true; do
    TEAM_NAME=$(prompt_input "Your forest alias (optional, for identity)")
    if [ -z "$TEAM_NAME" ]; then
      warn "No alias provided. You can set MYCELIUM_ALIAS env var to automate this."
      continue
    fi

    # Validate and normalize
    VALIDATED=$(validate_forest_alias "$TEAM_NAME" 2>/dev/null) && {
      TEAM_NAME="$VALIDATED"
      break
    }

    err "Invalid alias. Choose from: Banyan, Sequoia, Birch, Cedar, Oak, Mycelium"
  done
else
  # Validate environment variable value
  VALIDATED=$(validate_forest_alias "$TEAM_NAME" 2>/dev/null) || {
    err "Invalid MYCELIUM_ALIAS: $TEAM_NAME"
    exit 1
  }
  TEAM_NAME="$VALIDATED"
fi

ok "Team name: $TEAM_NAME"

# ============================================================================
# 5. Write config.toml (0600)
# ============================================================================
say "Writing $CONFIG_TOML..."
cat > "$CONFIG_TOML" <<'EOF'
# Mycelium Team Configuration
# This file defines targets (local, prod, dev) and how to reach them.
# Do NOT commit. Do NOT share passwords.

[local]
# Your local Neo4j instance (requires: neo4j install.sh + local startup)
bolt = "bolt://localhost:7687"
http = "http://localhost:7474"
user = "neo4j"
pass = "localtest12"  # default from native install
mode = "rw"
note = "Your laptop — full read/write, safe for experimentation"

[prod]
# Canonical instance on pulse-server via Bolt proxy (read-only)
# Direct: 5.78.206.137:7699 (proxy guards writes)
bolt = "bolt://5.78.206.137:7699"
http = "http://5.78.206.137:7474"
user = "team"
pass = ""  # set by setup-team.sh
mode = "ro"
note = "pulse production — canonical state, ticking, read-only"

[dev]
# Active development instance on pulse-server via Bolt proxy (read-only)
# Direct: 5.78.206.137:7698 (proxy guards writes)
bolt = "bolt://5.78.206.137:7698"
http = "http://5.78.206.137:7475"
user = "team"
pass = ""  # set by setup-team.sh
mode = "ro"
note = "pulse development — evolving, read-only"

[metadata]
# Team onboarding metadata (informational only)
team_name = ""  # set by setup-team.sh
installed_at = ""  # set by setup-team.sh
mcp_server = "Qubit-Capital/maverick"
EOF

# Update passwords and metadata in config.toml
sed -i '' "s|^\(  pass = \)\"\"  # set by setup-team.sh|pass = \"$PROD_PASS\"|" "$CONFIG_TOML" || true
sed -i '' "s|team_name = \"\"  # set by setup-team.sh|team_name = \"$TEAM_NAME\"|" "$CONFIG_TOML" || true
sed -i '' "s|installed_at = \"\"  # set by setup-team.sh|installed_at = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"|" "$CONFIG_TOML" || true

# Fix the prod/dev sections more carefully
python3 - "$CONFIG_TOML" "$PROD_PASS" "$DEV_PASS" "$TEAM_NAME" <<'PYTHON'
import sys, os
from datetime import datetime, timezone

config_file = sys.argv[1]
prod_pass = sys.argv[2]
dev_pass = sys.argv[3]
team_name = sys.argv[4]

with open(config_file, 'r') as f:
    content = f.read()

# Replace prod password
content = content.replace(
    '[prod]\n# Canonical instance on pulse-server via Bolt proxy (read-only)\n# Direct: 5.78.206.137:7699 (proxy guards writes)\nbolt = "bolt://5.78.206.137:7699"\nhttp = "http://5.78.206.137:7474"\nuser = "team"\npass = ""  # set by setup-team.sh',
    f'[prod]\n# Canonical instance on pulse-server via Bolt proxy (read-only)\n# Direct: 5.78.206.137:7699 (proxy guards writes)\nbolt = "bolt://5.78.206.137:7699"\nhttp = "http://5.78.206.137:7474"\nuser = "team"\npass = "{prod_pass}"'
)

# Replace dev password
content = content.replace(
    '[dev]\n# Active development instance on pulse-server via Bolt proxy (read-only)\n# Direct: 5.78.206.137:7698 (proxy guards writes)\nbolt = "bolt://5.78.206.137:7698"\nhttp = "http://5.78.206.137:7475"\nuser = "team"\npass = ""  # set by setup-team.sh',
    f'[dev]\n# Active development instance on pulse-server via Bolt proxy (read-only)\n# Direct: 5.78.206.137:7698 (proxy guards writes)\nbolt = "bolt://5.78.206.137:7698"\nhttp = "http://5.78.206.137:7475"\nuser = "team"\npass = "{dev_pass}"'
)

# Replace metadata
ts = datetime.now(timezone.utc).isoformat() + 'Z'
content = content.replace(
    'team_name = ""  # set by setup-team.sh',
    f'team_name = "{team_name}"'
)
content = content.replace(
    'installed_at = ""  # set by setup-team.sh',
    f'installed_at = "{ts}"'
)

with open(config_file, 'w') as f:
    f.write(content)
PYTHON

chmod 600 "$CONFIG_TOML"
ok "config.toml written (mode 600)"

# ============================================================================
# 6. Write secrets.env (0600)
# ============================================================================
say "Writing $SECRETS_ENV..."
cat > "$SECRETS_ENV" <<EOF
# Mycelium Secrets — Keep Private!
# Sourced by scripts and CLI for read access to prod/dev on pulse-server.
# Do NOT commit. Do NOT share.

# Bolt proxy credentials for prod/dev (read-only)
MYCELIUM_PROD_PASS="$PROD_PASS"
MYCELIUM_DEV_PASS="$DEV_PASS"

# Metadata
MYCELIUM_TEAM_NAME="$TEAM_NAME"
MYCELIUM_SETUP_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Optional: if you have a local ASGARD_GRAPH_TOKEN for semantic search
# ASGARD_GRAPH_TOKEN="..."
EOF

chmod 600 "$SECRETS_ENV"
ok "secrets.env written (mode 600)"

# Verify file permissions are correct (cross-platform check)
verify_permissions() {
  local file="$1"
  local expected="${2:-600}"

  # Get perms in a cross-platform way
  local perms=$(stat -f '%A' "$file" 2>/dev/null || stat -c '%a' "$file" 2>/dev/null || echo "644")

  # Normalize to remove leading zeros
  perms="${perms#0}"
  expected="${expected#0}"

  if [ "$perms" != "$expected" ]; then
    warn "$file has unexpected permissions: $perms (expected $expected)"
    return 1
  fi
  return 0
}

verify_permissions "$CONFIG_TOML" "600" || true
verify_permissions "$SECRETS_ENV" "600" || true

# ============================================================================
# 7. Global CLI Installation
# ============================================================================
say ""
say "Installing mycelium CLI globally..."

# MAVERICK_DIR already set in section 0
MYCELIUM_CLI="$MAVERICK_DIR/mycelium"

if [ ! -f "$MYCELIUM_CLI" ]; then
  err "mycelium CLI not found at $MYCELIUM_CLI"
  warn "Skipping global install. You can run: ./mycelium from the maverick directory"
else
  # Detect writable PATH destination in order of preference
  PATH_DEST=""

  # Try /usr/local/bin first (macOS default, often writable)
  if [ -d "/usr/local/bin" ]; then
    if [ -w "/usr/local/bin" ]; then
      PATH_DEST="/usr/local/bin"
    elif has_command sudo && sudo -n true 2>/dev/null; then
      # User has passwordless sudo
      PATH_DEST="/usr/local/bin"
    fi
  fi

  # Fallback to $HOME/.local/bin if /usr/local/bin is not writable
  if [ -z "$PATH_DEST" ]; then
    PATH_DEST="$HOME/.local/bin"
    # Create directory if it doesn't exist
    if [ ! -d "$PATH_DEST" ]; then
      mkdir -p "$PATH_DEST"
      ok "Created $PATH_DEST"
    fi

    # Check if $HOME/.local/bin is on PATH
    if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
      warn "$PATH_DEST is not on your PATH. Adding to shell config..."

      # Detect shell and add to appropriate rc file
      SHELL_RC=""
      if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
      elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
      fi

      if [ -n "$SHELL_RC" ]; then
        # Only add if not already present
        if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$SHELL_RC"; then
          echo "" >> "$SHELL_RC"
          echo "# Added by mycelium setup ($(date +%Y-%m-%d))" >> "$SHELL_RC"
          echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$SHELL_RC"
          ok "Added PATH export to $SHELL_RC"
        fi
      fi
    fi
  fi

  # Prompt user for global install
  say ""
  SYMLINK_PATH="$PATH_DEST/mycelium"
  SHOULD_INSTALL_GLOBAL="yes"

  # Check for environment variable override (for non-interactive runs)
  if [ "${MYCELIUM_GLOBAL_INSTALL:-}" = "yes" ]; then
    # Non-interactive: environment var says yes, proceed
    SHOULD_INSTALL_GLOBAL="yes"
  elif [ "${MYCELIUM_GLOBAL_INSTALL:-}" = "no" ]; then
    # Non-interactive: environment var says no, skip install
    warn "Skipping global install (MYCELIUM_GLOBAL_INSTALL=no)"
    warn "You can run mycelium as: $MAVERICK_DIR/mycelium"
    SHOULD_INSTALL_GLOBAL="no"
  else
    # Interactive: prompt with default yes
    if ! prompt_yes_no "Install mycelium globally at $PATH_DEST?" "y"; then
      warn "Skipping global install. You can run mycelium as: $MAVERICK_DIR/mycelium"
      SHOULD_INSTALL_GLOBAL="no"
    fi
  fi

  if [ "$SHOULD_INSTALL_GLOBAL" = "yes" ]; then
    # Check if destination already exists
    if [ -e "$SYMLINK_PATH" ]; then
      if [ -L "$SYMLINK_PATH" ]; then
        # It's a symlink
        EXISTING_TARGET=$(readlink "$SYMLINK_PATH")
        if [ "$EXISTING_TARGET" = "$MYCELIUM_CLI" ]; then
          ok "mycelium already installed at $SYMLINK_PATH"
        else
          warn "Existing symlink at $SYMLINK_PATH points to $EXISTING_TARGET"
          if prompt_yes_no "Overwrite with new symlink to $MYCELIUM_CLI?" "n"; then
            rm "$SYMLINK_PATH"
            ln -s "$MYCELIUM_CLI" "$SYMLINK_PATH"
            ok "mycelium installed at $SYMLINK_PATH"
          else
            warn "Keeping existing symlink"
          fi
        fi
      else
        # It's a regular file, not a symlink
        err "File exists at $SYMLINK_PATH but is not a symlink"
        err "Please remove or move it manually: rm $SYMLINK_PATH"
        warn "Skipping global install"
      fi
    else
      # Create the symlink
      if [ -w "/usr/local/bin" ] || [ "$PATH_DEST" = "$HOME/.local/bin" ]; then
        ln -s "$MYCELIUM_CLI" "$SYMLINK_PATH"
        ok "mycelium installed at $SYMLINK_PATH"
      else
        # Need sudo for /usr/local/bin
        say "Sudo is required to install to /usr/local/bin. Enter your password:"
        sudo ln -s "$MYCELIUM_CLI" "$SYMLINK_PATH"
        ok "mycelium installed at $SYMLINK_PATH (via sudo)"
      fi
    fi

    # Verify the install works
    say "Verifying global installation..."
    if command -v mycelium >/dev/null 2>&1; then
      ok "mycelium is now globally available"
    else
      warn "mycelium not found in PATH yet"
      if [ "$PATH_DEST" = "$HOME/.local/bin" ]; then
        say "Open a new terminal and try again, or run: export PATH=\"\$HOME/.local/bin:\$PATH\""
      fi
    fi
  fi
fi

# ============================================================================
# 8. Install Claude Code Skill
# ============================================================================
say ""
say "Installing Claude Code Skill for team-wide mycelium access..."

SKILLS_SCRIPT="$MAVERICK_DIR/skills/install.sh"

if [ ! -f "$SKILLS_SCRIPT" ]; then
  warn "skills/install.sh not found — skipping skill installation"
else
  # The skill installer is idempotent: safe to run even if ~/.claude/skills/mycelium.md exists
  if bash "$SKILLS_SCRIPT"; then
    ok "Claude Skill installed to ~/.claude/skills/mycelium.md — Claude Code sessions anywhere on this laptop will now discover mycelium automatically."
  else
    # Soft warning: skill install failed (likely because ~/.claude/ doesn't exist, which is fine if teammate doesn't use Claude Code)
    warn "Claude Skill installation encountered an issue."
    warn "This is only a problem if you plan to use Claude Code. Otherwise, it can be safely ignored."
    warn "To install manually later: bash $SKILLS_SCRIPT"
  fi
fi

# ============================================================================
# 9. Connectivity Smoke Tests
# ============================================================================
if [ "$SKIP_CONNECTIVITY_TEST" -eq 1 ]; then
  warn "Skipping connectivity tests (no local neo4j)"
  say ""
  say "Manual connectivity check:"
  say "  cypher-shell -a bolt://5.78.206.137:7699 -u team -p '***' 'RETURN 1'"
else
  say ""
  say "Running connectivity smoke tests..."

  # Source secrets for use in tests
  # shellcheck disable=SC1090
  source "$SECRETS_ENV"

  # Test prod
  say "Testing prod (bolt://5.78.206.137:7699)..."
  if maybe_timeout 20 cypher-shell -a "bolt://5.78.206.137:7699" -u team -p "$MYCELIUM_PROD_PASS" "RETURN 1" >/tmp/smoke-prod.out 2>&1; then
    ok "prod connectivity OK"
  else
    err_msg=$(head -1 /tmp/smoke-prod.out 2>/dev/null || echo "Connection failed")
    warn "prod connectivity failed: $err_msg"
  fi

  # Test dev
  say "Testing dev (bolt://5.78.206.137:7698)..."
  if maybe_timeout 20 cypher-shell -a "bolt://5.78.206.137:7698" -u team -p "$MYCELIUM_DEV_PASS" "RETURN 1" >/tmp/smoke-dev.out 2>&1; then
    ok "dev connectivity OK"
  else
    err_msg=$(head -1 /tmp/smoke-dev.out 2>/dev/null || echo "Connection failed")
    warn "dev connectivity failed: $err_msg"
  fi

  # Test local (if neo4j is running)
  say "Testing local (bolt://localhost:7687)..."
  if maybe_timeout 20 cypher-shell -a "bolt://localhost:7687" -u neo4j -p "localtest12" "RETURN 1" >/tmp/smoke-local.out 2>&1; then
    ok "local connectivity OK"
  else
    err_msg=$(head -1 /tmp/smoke-local.out 2>/dev/null || echo "Connection failed")
    warn "local connectivity not available: $err_msg"
  fi
fi

# ============================================================================
# 10. Auto-Sync Local Graph from Dev (if local Neo4j is running)
# ============================================================================
say ""
say "Attempting to seed local graph from dev..."

LOCAL_NEO4J_READY=0
if command -v cypher-shell >/dev/null 2>&1; then
  # Check if local Neo4j is reachable
  if maybe_timeout 20 cypher-shell -a "bolt://localhost:7687" -u neo4j -p "localtest12" "RETURN 1" >/dev/null 2>&1; then
    LOCAL_NEO4J_READY=1
    ok "Local Neo4j is running and reachable"

    # Source the CLI and run sync from dev
    if command -v mycelium >/dev/null 2>&1 || [ -f "$MAVERICK_DIR/mycelium" ]; then
      say "Syncing local graph from dev..."

      # Use the mycelium CLI if available globally, or fall back to the repo copy
      MYCELIUM_CMD="mycelium"
      if ! command -v mycelium >/dev/null 2>&1; then
        MYCELIUM_CMD="$MAVERICK_DIR/mycelium"
      fi

      # Run sync and capture output
      sync_output=$($MYCELIUM_CMD sync --from dev 2>&1)
      sync_exit=$?

      if [ $sync_exit -eq 0 ]; then
        # Extract sync summary from output
        new_nodes=$(echo "$sync_output" | grep -oP '(?<=new: )\d+' | head -1 || echo "0")
        updated_nodes=$(echo "$sync_output" | grep -oP '(?<=updated: )\d+' | head -1 || echo "0")
        unchanged_nodes=$(echo "$sync_output" | grep -oP '(?<=unchanged: )\d+' | head -1 || echo "0")
        total=$((new_nodes + updated_nodes + unchanged_nodes))

        ok "Local graph synced from dev ($total nodes merged)"
      else
        warn "Local graph sync from dev encountered an issue (you can run manually: mycelium sync --from dev)"
      fi
    else
      warn "mycelium CLI not found; skipping local sync (you can run manually: mycelium sync --from dev)"
    fi
  else
    warn "Local Neo4j is not running or not reachable (bolt://localhost:7687)"
    say "To set up local Neo4j and auto-seed, run: bash install-deps.sh"
    warn "Skipping local graph sync; you can run manually later: mycelium sync --from dev"
  fi
else
  warn "cypher-shell not found; cannot check local Neo4j"
  say "To set up local Neo4j, run: bash install-deps.sh"
fi

# ============================================================================
# 11. Install Git Hooks
# ============================================================================
say ""
say "Installing git pre-push hook..."

HOOKS_SCRIPT="$MAVERICK_DIR/scripts/install-git-hooks.sh"
if [ -f "$HOOKS_SCRIPT" ]; then
  if bash "$HOOKS_SCRIPT" >/dev/null 2>&1; then
    ok "Pre-push hook installed (prevents accidental direct pushes to main)"
  else
    warn "Pre-push hook installation failed. You can install manually: bash scripts/install-git-hooks.sh"
  fi
else
  warn "Hook script not found. You can install manually: bash scripts/install-git-hooks.sh"
fi

# ============================================================================
# 12. Global CLI Verification
# ============================================================================
say ""
say "Verifying global CLI installation..."

# Try to run mycelium from root directory
if command -v mycelium >/dev/null 2>&1; then
  say "Testing from root directory..."
  if (cd / && maybe_timeout 10 mycelium --target prod help >/dev/null 2>&1); then
    ok "Global mycelium CLI is fully functional"
  else
    warn "Global mycelium is available but may not be fully operational yet"
    say "Try opening a new terminal to refresh your PATH"
  fi
else
  warn "Global mycelium not in PATH (will work after opening a new terminal)"
fi

# ============================================================================
# 13. Installation Complete
# ============================================================================
say ""
ok "Setup complete!"
say ""
say "Configuration written to:"
say "  $CONFIG_TOML (0600)"
say "  $SECRETS_ENV (0600)"
say ""
say "Next steps:"
say "  1. Open a new terminal to refresh your PATH (if using ~/.local/bin)"
say "  2. Source secrets: source $SECRETS_ENV"
say "  3. Verify global CLI: mycelium --target prod help"
say "  4. Verify local Neo4j (if using):"
say "     bash install-deps.sh"
say "  5. Read the docs: see docs/onboarding.md"
say "  6. Try a query:"
say "     mycelium --target prod ask 'what is the system health status'"
say ""
say "For help:"
say "  - Reach Kshitiz on Slack/Signal"
say "  - Read OPERATING-SYSTEM.md for autonomy overview"
say "  - Query the graph: mycelium ask 'how does X work'"
say ""
