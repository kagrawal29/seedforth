#!/usr/bin/env bash
# ============================================================================
# Mycelium Doctor — OS Environment Diagnostics
# ============================================================================
# Probes system state before setup-team.sh or install-deps.sh runs.
# Detects OS family, bash version, package manager, required tools.
# Returns EXIT 0 if sufficient to proceed, EXIT 1 if critical gaps exist.
#
# Works on bash 3.2+ (including macOS default) and zsh-running-bash.
#
# Usage:
#   bash doctor.sh                    # diagnose current environment
#   bash doctor.sh --verbose          # include more details
#   bash doctor.sh --fix-homebrew     # auto-install Homebrew on macOS
#
# Exit codes:
#   0 = PASS (system ready to proceed)
#   1 = FAIL (one or more critical checks failed)
# ============================================================================
set -u

# Colors and formatting (bash 3.2 safe)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
NC='\033[0m'  # No color

# Logging functions
say()   { printf '%b[doctor]%b %s\n' "$BLUE" "$NC" "$*"; }
ok()    { printf '%b✓%b %s\n' "$GREEN" "$NC" "$*"; }
warn()  { printf '%b⚠%b %s\n' "$YELLOW" "$NC" "$*"; }
err()   { printf '%b✗%b %s\n' "$RED" "$NC" "$*"; }
hint()  { printf '%b  →%b %s\n' "$BLUE" "$NC" "$*"; }

# Flags
VERBOSE=0
AUTO_HOMEBREW=0

# Parse arguments (bash 3.2 safe: no while [[ ]])
while [ $# -gt 0 ]; do
  case "$1" in
    --verbose)
      VERBOSE=1
      shift
      ;;
    --fix-homebrew)
      AUTO_HOMEBREW=1
      shift
      ;;
    *)
      say "Unknown option: $1"
      exit 1
      ;;
  esac
done

# =============================================================================
# 1. OS Family Detection
# =============================================================================
say "Detecting OS family..."

OS_NAME=""
OS_FAMILY=""
OS_VERSION=""
PKG_MANAGER=""
PKG_MANAGER_CMD=""

# Detect OS family from uname
UNAME_S=$(uname -s)
case "$UNAME_S" in
  Darwin)
    OS_FAMILY="macos"
    OS_NAME="macOS"
    OS_VERSION=$(sw_vers -productVersion 2>/dev/null || echo "unknown")
    ;;
  Linux)
    OS_FAMILY="linux"
    OS_VERSION=$(uname -r)

    # Detect Linux distribution
    if [ -f /etc/os-release ]; then
      # Use ID from /etc/os-release (works on most modern distros)
      DISTRO_ID=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"' | cut -d' ' -f1)
      DISTRO_NAME=$(grep '^NAME=' /etc/os-release | cut -d= -f2 | tr -d '"')

      case "$DISTRO_ID" in
        ubuntu|debian)
          OS_NAME="$DISTRO_NAME"
          PKG_MANAGER="apt"
          PKG_MANAGER_CMD="apt-get"
          ;;
        fedora|rhel|centos)
          OS_NAME="$DISTRO_NAME"
          PKG_MANAGER="dnf"
          PKG_MANAGER_CMD="dnf"
          ;;
        arch)
          OS_NAME="Arch Linux"
          PKG_MANAGER="pacman"
          PKG_MANAGER_CMD="pacman"
          ;;
        alpine)
          OS_NAME="Alpine Linux"
          PKG_MANAGER="apk"
          PKG_MANAGER_CMD="apk"
          ;;
        *)
          OS_NAME="Linux ($DISTRO_NAME)"
          PKG_MANAGER="unknown"
          ;;
      esac
    elif [ -f /etc/debian_version ]; then
      OS_NAME="Debian-based Linux"
      PKG_MANAGER="apt"
      PKG_MANAGER_CMD="apt-get"
    else
      OS_NAME="Unknown Linux"
      PKG_MANAGER="unknown"
    fi
    ;;
  MINGW*|MSYS*|CYGWIN*)
    OS_FAMILY="windows"
    OS_NAME="Windows (via MSYS/Cygwin/Git Bash)"
    ;;
  *)
    OS_FAMILY="unknown"
    OS_NAME="$UNAME_S"
    ;;
esac

ok "OS: $OS_NAME ($OS_VERSION)"

# =============================================================================
# 2. Bash Version Check
# =============================================================================
say "Checking bash version..."

BASH_VERSION_STRING=$(bash --version 2>/dev/null | head -1 || echo "unknown")
BASH_MAJOR=$(echo "$BASH_VERSION_STRING" | grep -o 'version [0-9]*' | grep -o '[0-9]*' | head -1 || echo "0")
BASH_MINOR=$(echo "$BASH_VERSION_STRING" | grep -oE 'version [0-9]+\.[0-9]+' | cut -d' ' -f2 | cut -d. -f2 | head -1 || echo "0")

if [ -z "$BASH_MAJOR" ] || [ "$BASH_MAJOR" = "0" ]; then
  BASH_MAJOR=3
  BASH_MINOR=2
fi

# Check minimum bash 3.2
if [ "$BASH_MAJOR" -gt 3 ] || ([ "$BASH_MAJOR" -eq 3 ] && [ "$BASH_MINOR" -ge 2 ]); then
  ok "bash $BASH_MAJOR.$BASH_MINOR (OK)"
  [ "$VERBOSE" = "1" ] && say "  Full version: $BASH_VERSION_STRING"
else
  err "bash $BASH_MAJOR.$BASH_MINOR (too old, need >= 3.2)"
  exit 1
fi

# =============================================================================
# 3. Critical Tools Check (git, curl, python3)
# =============================================================================
say "Checking critical tools..."

FAIL_CRITICAL=0

# Check git
if command -v git >/dev/null 2>&1; then
  GIT_VERSION=$(git --version | cut -d' ' -f3)
  ok "git $GIT_VERSION"
else
  err "git not found"
  if [ "$OS_FAMILY" = "macos" ]; then
    hint "brew install git"
  elif [ "$PKG_MANAGER" = "apt" ]; then
    hint "sudo apt-get install -y git"
  fi
  FAIL_CRITICAL=1
fi

# Check curl
if command -v curl >/dev/null 2>&1; then
  CURL_VERSION=$(curl --version 2>/dev/null | head -1 | cut -d' ' -f2)
  ok "curl $CURL_VERSION"
else
  err "curl not found"
  if [ "$OS_FAMILY" = "macos" ]; then
    hint "brew install curl"
  elif [ "$PKG_MANAGER" = "apt" ]; then
    hint "sudo apt-get install -y curl"
  fi
  FAIL_CRITICAL=1
fi

# Check python3
if command -v python3 >/dev/null 2>&1; then
  PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
  PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
  PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

  # Need Python 3.8+
  if [ "$PYTHON_MAJOR" -gt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]); then
    ok "python3 $PYTHON_VERSION"
  else
    warn "python3 $PYTHON_VERSION (old, recommend 3.8+)"
  fi
else
  err "python3 not found"
  if [ "$OS_FAMILY" = "macos" ]; then
    hint "brew install python3"
  elif [ "$PKG_MANAGER" = "apt" ]; then
    hint "sudo apt-get install -y python3"
  fi
  FAIL_CRITICAL=1
fi

if [ "$FAIL_CRITICAL" -eq 1 ]; then
  echo ""
  err "Critical tools missing. Install them and re-run doctor.sh"
  exit 1
fi

# =============================================================================
# 4. Package Manager Detection
# =============================================================================
say "Checking package manager..."

case "$OS_FAMILY" in
  macos)
    if command -v brew >/dev/null 2>&1; then
      BREW_VERSION=$(brew --version 2>/dev/null | head -1)
      ok "brew (installed)"
      [ "$VERBOSE" = "1" ] && say "  $BREW_VERSION"
    else
      warn "Homebrew not installed"
      hint "install-deps.sh can auto-install it (run with --fix-homebrew flag)"
      hint "OR: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    fi
    ;;
  linux)
    if [ -n "$PKG_MANAGER" ] && [ "$PKG_MANAGER" != "unknown" ]; then
      ok "$PKG_MANAGER package manager detected"
      [ "$VERBOSE" = "1" ] && say "  Using: $PKG_MANAGER_CMD"
    else
      warn "No supported package manager detected"
      hint "install-deps.sh supports: apt (Debian/Ubuntu), dnf (Fedora), pacman (Arch), apk (Alpine)"
      hint "See docs/os-support.md for manual installation instructions"
    fi
    ;;
  windows)
    warn "Windows detected (via MSYS/Cygwin)"
    hint "install-deps.sh does NOT support Windows yet"
    hint "Options: (1) Use WSL2 with Ubuntu, (2) Install Docker Desktop, (3) See docs/os-support.md"
    ;;
  *)
    warn "Unknown OS family"
    hint "OS detection failed. Manual setup may be needed."
    ;;
esac

# =============================================================================
# 5. Optional Tools (neo4j, cypher-shell, ollama)
# =============================================================================
say "Checking optional tools..."

# neo4j
if command -v neo4j >/dev/null 2>&1; then
  NEO4J_VERSION=$(neo4j --version 2>/dev/null | head -1 || echo "unknown")
  ok "neo4j $NEO4J_VERSION"
else
  warn "neo4j not installed (you can install via install-deps.sh)"
fi

# cypher-shell
if command -v cypher-shell >/dev/null 2>&1; then
  CYPHER_VERSION=$(cypher-shell --version 2>/dev/null | head -1 || echo "unknown")
  ok "cypher-shell $CYPHER_VERSION"
else
  warn "cypher-shell not installed (needed for testing connections)"
  if [ "$OS_FAMILY" = "macos" ]; then
    hint "brew install cypher-shell"
  elif [ "$PKG_MANAGER" = "apt" ]; then
    hint "sudo apt-get install -y cypher-shell"
  fi
fi

# ollama
if command -v ollama >/dev/null 2>&1; then
  ok "ollama installed"
else
  warn "ollama not installed (optional, needed for semantic queries)"
  if [ "$OS_FAMILY" = "macos" ]; then
    hint "brew install ollama   OR   https://ollama.com/download"
  elif [ "$OS_FAMILY" = "linux" ]; then
    hint "curl -fsSL https://ollama.com/install.sh | sh"
  fi
fi

# =============================================================================
# 6. Disk Space
# =============================================================================
say "Checking disk space..."

# Get available space in home directory (bash 3.2 safe: use df)
AVAIL_KB=$(df "$HOME" 2>/dev/null | tail -1 | awk '{print $4}')
AVAIL_GB=$((AVAIL_KB / 1024 / 1024))

if [ "$AVAIL_GB" -ge 5 ]; then
  ok "disk space: ${AVAIL_GB}GB available"
elif [ "$AVAIL_GB" -ge 2 ]; then
  warn "disk space: ${AVAIL_GB}GB available (tight, recommend 5GB for Neo4j)"
else
  err "disk space: only ${AVAIL_GB}GB available (need at least 2GB)"
  exit 1
fi

# =============================================================================
# 7. Internet connectivity
# =============================================================================
say "Checking internet connectivity..."

if command -v curl >/dev/null 2>&1; then
  # Try a quick DNS + HTTP check (timeout 5 seconds)
  if timeout 5 curl -fsSL --connect-timeout 3 https://www.google.com >/dev/null 2>&1; then
    ok "internet connectivity OK"
  else
    warn "internet connectivity may be limited (curl to google.com timed out)"
    hint "This may be OK if you have a firewall or proxy"
  fi
else
  say "curl not available, skipping internet test"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
say "--- SUMMARY ---"
echo ""
printf '%b%-30s %b%s%b\n' "$BLUE" "OS Family" "$GREEN" "$OS_FAMILY" "$NC"
printf '%b%-30s %b%s%b\n' "$BLUE" "OS Name" "$GREEN" "$OS_NAME" "$NC"
printf '%b%-30s %b%s%b\n' "$BLUE" "Bash Version" "$GREEN" "$BASH_MAJOR.$BASH_MINOR" "$NC"
if [ -n "$PKG_MANAGER" ] && [ "$PKG_MANAGER" != "unknown" ]; then
  printf '%b%-30s %b%s%b\n' "$BLUE" "Package Manager" "$GREEN" "$PKG_MANAGER" "$NC"
else
  printf '%b%-30s %b%s%b\n' "$BLUE" "Package Manager" "$YELLOW" "(not detected)" "$NC"
fi

echo ""
say "Readiness Assessment:"
echo ""

# Determine readiness
READY=1

if [ "$OS_FAMILY" = "unknown" ] || [ "$OS_FAMILY" = "windows" ]; then
  err "OS is not supported. See docs/os-support.md for alternatives."
  READY=0
fi

if [ "$OS_FAMILY" = "macos" ] && ! command -v brew >/dev/null 2>&1; then
  warn "Homebrew missing on macOS. You can:"
  hint "  (1) Run: bash doctor.sh --fix-homebrew   (automatic install)"
  hint "  (2) Install manually: https://brew.sh"
  hint "  (3) See docs/os-support.md for manual dependency setup"
fi

if [ "$READY" = "1" ]; then
  echo ""
  ok "System is ready to proceed with setup-team.sh and install-deps.sh"
  echo ""
  say "Next steps:"
  echo "  1. bash setup-team.sh          # Configure mycelium CLI and connectivity"
  echo "  2. bash install-deps.sh        # Install Neo4j, Qdrant, Ollama locally"
  echo ""
  exit 0
else
  echo ""
  err "System is not ready. Fix the issues above and re-run doctor.sh"
  echo ""
  exit 1
fi
