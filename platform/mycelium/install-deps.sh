#!/usr/bin/env bash
# ============================================================================
# Mycelium — OS-level dependency installer
# ============================================================================
# NOTE: This script is still actively used. See docs/contributor-setup.md
# for the current contributor onboarding path. This file is kept for
# historical reference and is invoked during the setup process.
# ============================================================================
# Installs Neo4j 2026.03.1 + APOC, Qdrant, and Ollama (nomic-embed-text)
# on a teammate's local machine. Run this before `./mycelium bootstrap`.
#
# Usage:
#   ./install-deps.sh                    # uses default password: localtest12
#   ./install-deps.sh --password mypass  # set Neo4j initial password
#
# Supports: macOS (Homebrew), Ubuntu/Debian (apt)
# ============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NEO4J_VERSION="2026.03.1"
# APOC version must match Neo4j minor (2026.03.x)
APOC_VERSION="2026.3.1"
APOC_JAR="apoc-${APOC_VERSION}-core.jar"
APOC_URL="https://github.com/neo4j/apoc/releases/download/${APOC_VERSION}/${APOC_JAR}"
QDRANT_COLLECTION="mycelium-embeddings"
QDRANT_PORT=6333
OLLAMA_MODEL="nomic-embed-text"
NEO4J_USER="neo4j"
NEO4J_PASS="localtest12"  # default; override with --password

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
PREFIX="[install-deps]"
log()  { printf '%s %s\n'         "$PREFIX" "$*"; }
ok()   { printf '\e[32m%s OK\e[0m %s\n'   "$PREFIX" "$*"; }
warn() { printf '\e[33m%s WARN\e[0m %s\n' "$PREFIX" "$*"; }
err()  { printf '\e[31m%s ERROR\e[0m %s\n' "$PREFIX" "$*" >&2; exit 1; }
pass() { printf '\e[32m  [PASS]\e[0m %s\n' "$*"; }
fail() { printf '\e[31m  [FAIL]\e[0m %s\n' "$*"; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --password)
      NEO4J_PASS="${2:?--password requires a value}"
      shift 2
      ;;
    *)
      err "unknown argument: $1"
      ;;
  esac
done

if [[ "$NEO4J_PASS" == "localtest12" ]]; then
  warn "using default Neo4j password 'localtest12' -- pass --password <pw> to override"
fi

# ---------------------------------------------------------------------------
# OS detection -- fail fast on unsupported platforms
# ---------------------------------------------------------------------------
OS=""
DISTRO=""

UNAME_S="$(uname -s)"
case "$UNAME_S" in
  Darwin)
    OS="mac"
    ;;
  Linux)
    OS="linux"
    # Detect specific Linux distribution
    if [ -f /etc/os-release ]; then
      DISTRO=$(grep '^ID=' /etc/os-release | cut -d= -f2 | tr -d '"' | cut -d' ' -f1)
    elif [ -f /etc/debian_version ]; then
      DISTRO="debian"
    else
      DISTRO="unknown"
    fi
    ;;
  *)
    err "Unsupported OS: $UNAME_S

install-deps.sh supports:
  - macOS 10.15+ (with Homebrew)
  - Ubuntu/Debian (20.04+)
  - Fedora/RHEL (NOT YET TESTED)

For other OSes, see: docs/os-support.md

Manual installation (any OS):
  1. Install Neo4j 2026.03.1 from https://neo4j.com/download/
  2. Download APOC 2026.3.1: https://github.com/neo4j/apoc/releases
  3. Install Qdrant: https://qdrant.tech/documentation/install/
  4. Install Ollama: https://ollama.com/
  5. See docs/os-support.md for detailed instructions
  6. Then run: ./mycelium bootstrap

If you've got it working on another OS, please file an issue at:
  https://github.com/Qubit-Capital/maverick/issues"
fi
log "detected OS: $OS${DISTRO:+ ($DISTRO)}"

# ---------------------------------------------------------------------------
# Homebrew auto-install on macOS (if missing)
# ---------------------------------------------------------------------------
if [[ "$OS" == "mac" ]]; then
  if ! command -v brew >/dev/null 2>&1; then
    log "Homebrew not found on macOS"
    log "Homebrew is required to install dependencies."
    log ""
    read -p "Auto-install Homebrew? (y/n) [y]: " -r
    RESPONSE="${REPLY:-y}"

    if [[ "$RESPONSE" =~ ^[Yy]$ ]]; then
      log "Installing Homebrew..."
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
        err "Homebrew installation failed"
        hint "Install manually from https://brew.sh and re-run install-deps.sh"
        exit 1
      }
      ok "Homebrew installed"
    else
      err "Homebrew is required on macOS"
      hint "Install from: https://brew.sh"
      hint "Then re-run: bash install-deps.sh"
      exit 1
    fi
  fi
fi

# ---------------------------------------------------------------------------
# Helper: check if a brew formula is installed
# ---------------------------------------------------------------------------
brew_installed() { brew list --formula 2>/dev/null | grep -qx "$1"; }

# ---------------------------------------------------------------------------
# 1. Neo4j
# ---------------------------------------------------------------------------
log "checking Neo4j..."

if [[ "$OS" == "mac" ]]; then
  if brew_installed neo4j; then
    # Verify it is the expected minor version; warn but don't fail if different
    installed_ver="$(brew list --versions neo4j | awk '{print $2}' | head -1)"
    if [[ "$installed_ver" != "$NEO4J_VERSION" ]]; then
      warn "Neo4j $installed_ver is installed; expected $NEO4J_VERSION -- mismatch may cause APOC incompatibility"
    else
      ok "Neo4j $NEO4J_VERSION already installed"
    fi
  else
    log "installing Neo4j via brew..."
    # brew formula name is 'neo4j'; version pinning requires tap; install latest and warn
    brew install neo4j
    ok "Neo4j installed"
  fi

  # Locate Neo4j home (brew cellar path varies by version)
  NEO4J_HOME="$(brew --prefix neo4j)/libexec"

else
  # Linux: use the official Neo4j apt repository
  if command -v neo4j >/dev/null 2>&1; then
    ok "Neo4j already installed"
  else
    log "adding Neo4j apt repository..."
    # Official Neo4j apt repo, pinned to 2026 series
    curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key \
      | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
    echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 2026" \
      | sudo tee /etc/apt/sources.list.d/neo4j.list >/dev/null
    sudo apt-get update -qq
    log "installing Neo4j ${NEO4J_VERSION}..."
    sudo apt-get install -y "neo4j=${NEO4J_VERSION}"
    ok "Neo4j ${NEO4J_VERSION} installed"
  fi

  NEO4J_HOME="/var/lib/neo4j"
fi

# ---------------------------------------------------------------------------
# 2. Neo4j config tweaks (heap, pagecache, tx log retention)
# ---------------------------------------------------------------------------
log "applying Neo4j config tweaks..."

if [[ "$OS" == "mac" ]]; then
  NEO4J_CONF="$(brew --prefix neo4j)/libexec/conf/neo4j.conf"
else
  NEO4J_CONF="/etc/neo4j/neo4j.conf"
fi

# Idempotent sed: only append the setting if it doesn't already exist at the
# expected value; removes old value first then appends the canonical one.
set_neo4j_conf() {
  local key="$1" val="$2"
  if grep -q "^${key}=${val}$" "$NEO4J_CONF" 2>/dev/null; then
    return 0  # already set to the right value, skip
  fi
  # Remove any existing (commented or uncommented) line for this key
  sudo sed -i.bak "/^#*${key}=/d" "$NEO4J_CONF"
  echo "${key}=${val}" | sudo tee -a "$NEO4J_CONF" >/dev/null
  log "  set ${key}=${val}"
}

# 1G heap keeps Neo4j stable on laptop RAM; 512m pagecache is conservative but safe
set_neo4j_conf "server.memory.heap.initial_size"       "1g"
set_neo4j_conf "server.memory.heap.max_size"           "1g"
set_neo4j_conf "server.memory.pagecache.size"          "512m"
# Retain only 1 tx log file; prevents disk bloat on local dev machines
set_neo4j_conf "db.tx_log.rotation.retention_policy"  "1 files"

ok "Neo4j config tuned"

# ---------------------------------------------------------------------------
# 3. APOC plugin
# ---------------------------------------------------------------------------
log "checking APOC plugin..."

if [[ "$OS" == "mac" ]]; then
  # brew installs APOC into the labs/ directory inside the cellar
  LABS_DIR="$(brew --prefix neo4j)/libexec/labs"
  PLUGINS_DIR="$(brew --prefix neo4j)/libexec/plugins"
  mkdir -p "$PLUGINS_DIR"

  # Symlink the APOC jar from labs/ into plugins/ so Neo4j picks it up
  # labs/ may contain apoc-*.jar with varying patch versions; match by prefix
  APOC_IN_LABS="$(ls "${LABS_DIR}"/apoc-*-core.jar 2>/dev/null | head -1 || true)"
  if [[ -n "$APOC_IN_LABS" ]]; then
    TARGET="${PLUGINS_DIR}/$(basename "$APOC_IN_LABS")"
    if [[ -L "$TARGET" ]] || [[ -f "$TARGET" ]]; then
      ok "APOC already linked in plugins/"
    else
      ln -sf "$APOC_IN_LABS" "$TARGET"
      ok "APOC symlinked: $TARGET"
    fi
  else
    warn "APOC jar not found in $LABS_DIR -- Neo4j brew formula may not bundle it; download manually from $APOC_URL"
  fi

else
  # Linux: download the matching APOC jar from GitHub releases
  PLUGINS_DIR="/var/lib/neo4j/plugins"
  sudo mkdir -p "$PLUGINS_DIR"
  TARGET="${PLUGINS_DIR}/${APOC_JAR}"

  if [[ -f "$TARGET" ]]; then
    ok "APOC already present at $TARGET"
  else
    log "downloading APOC ${APOC_VERSION}..."
    sudo curl -fsSL "$APOC_URL" -o "$TARGET"
    sudo chown neo4j:neo4j "$TARGET"
    ok "APOC downloaded to $TARGET"
  fi
fi

# Allow APOC unrestricted procedures; needed for apoc.periodic.repeat (heartbeat)
set_neo4j_conf "dbms.security.procedures.unrestricted" "apoc.*"
set_neo4j_conf "dbms.security.procedures.allowlist"    "apoc.*"

# ---------------------------------------------------------------------------
# 4. Set Neo4j initial password
# ---------------------------------------------------------------------------
log "setting Neo4j password..."
# neo4j-admin dbms set-initial-password is idempotent if not yet changed
if [[ "$OS" == "mac" ]]; then
  "$(brew --prefix neo4j)/libexec/bin/neo4j-admin" dbms set-initial-password "$NEO4J_PASS" 2>/dev/null || true
else
  sudo neo4j-admin dbms set-initial-password "$NEO4J_PASS" 2>/dev/null || true
fi
ok "Neo4j password set"

# ---------------------------------------------------------------------------
# 5. Start Neo4j
# ---------------------------------------------------------------------------
log "starting Neo4j..."
if [[ "$OS" == "mac" ]]; then
  # brew services start is idempotent; already running is not an error
  brew services start neo4j 2>/dev/null || true
else
  sudo systemctl enable neo4j
  sudo systemctl start neo4j
fi

# Give Neo4j a moment to bind its bolt port before we verify later
sleep 5
ok "Neo4j service started"

# ---------------------------------------------------------------------------
# 6. Qdrant
# ---------------------------------------------------------------------------
log "checking Qdrant..."

if [[ "$OS" == "mac" ]]; then
  if brew_installed qdrant; then
    ok "Qdrant already installed"
  else
    log "installing Qdrant via brew..."
    brew install qdrant
    ok "Qdrant installed"
  fi

  # Start Qdrant via brew services; idempotent if already running
  brew services start qdrant 2>/dev/null || true
  log "Qdrant service started (brew services)"
  log "NOTE: to start manually without brew services: qdrant &"

else
  # Linux: download the static binary from GitHub releases
  QDRANT_BIN="/usr/local/bin/qdrant"
  if [[ -x "$QDRANT_BIN" ]]; then
    ok "Qdrant binary already at $QDRANT_BIN"
  else
    log "detecting architecture for Qdrant binary..."
    ARCH="$(uname -m)"
    case "$ARCH" in
      x86_64)  QDRANT_ARCH="x86_64-unknown-linux-musl" ;;
      aarch64) QDRANT_ARCH="aarch64-unknown-linux-musl" ;;
      *)        err "unsupported architecture for Qdrant static binary: $ARCH" ;;
    esac

    # Fetch the latest Qdrant release tag then download the matching binary
    QDRANT_TAG="$(curl -fsSL https://api.github.com/repos/qdrant/qdrant/releases/latest \
      | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")"
    QDRANT_URL="https://github.com/qdrant/qdrant/releases/download/${QDRANT_TAG}/qdrant-${QDRANT_ARCH}.tar.gz"
    log "downloading Qdrant ${QDRANT_TAG} for ${QDRANT_ARCH}..."
    TMP_DIR="$(mktemp -d)"
    curl -fsSL "$QDRANT_URL" | tar -xz -C "$TMP_DIR"
    sudo mv "${TMP_DIR}/qdrant" "$QDRANT_BIN"
    sudo chmod +x "$QDRANT_BIN"
    rm -rf "$TMP_DIR"
    ok "Qdrant binary installed at $QDRANT_BIN"
  fi

  # Create a minimal systemd unit so Qdrant auto-starts on reboot
  QDRANT_SERVICE="/etc/systemd/system/qdrant.service"
  QDRANT_DATA="/var/lib/qdrant"
  if [[ ! -f "$QDRANT_SERVICE" ]]; then
    log "creating Qdrant systemd unit..."
    sudo mkdir -p "$QDRANT_DATA"
    sudo tee "$QDRANT_SERVICE" >/dev/null <<UNIT
[Unit]
Description=Qdrant vector database
After=network.target

[Service]
ExecStart=/usr/local/bin/qdrant
WorkingDirectory=${QDRANT_DATA}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
    sudo systemctl daemon-reload
    sudo systemctl enable qdrant
    ok "Qdrant systemd unit created"
  fi

  sudo systemctl start qdrant
  ok "Qdrant service started"
fi

# Allow Qdrant to open its HTTP port before hitting it
sleep 3

# ---------------------------------------------------------------------------
# 7. Create Qdrant collection mycelium-embeddings (idempotent)
# ---------------------------------------------------------------------------
log "checking Qdrant collection '${QDRANT_COLLECTION}'..."

# First check if the collection already exists; skip creation if so
COLLECTION_STATUS="$(curl -s -o /dev/null -w '%{http_code}' \
  "http://localhost:${QDRANT_PORT}/collections/${QDRANT_COLLECTION}")"

if [[ "$COLLECTION_STATUS" == "200" ]]; then
  ok "collection '${QDRANT_COLLECTION}' already exists"
else
  log "creating collection '${QDRANT_COLLECTION}' (768 dims, cosine)..."
  # 768 dims matches nomic-embed-text; cosine matches INFERRED_SIMILAR edge semantics
  curl -fsSL -X PUT "http://localhost:${QDRANT_PORT}/collections/${QDRANT_COLLECTION}" \
    -H "Content-Type: application/json" \
    -d '{"vectors": {"size": 768, "distance": "Cosine"}}' >/dev/null
  ok "collection '${QDRANT_COLLECTION}' created"
fi

# ---------------------------------------------------------------------------
# 8. Ollama + nomic-embed-text
# ---------------------------------------------------------------------------
log "checking Ollama..."

if command -v ollama >/dev/null 2>&1; then
  ok "Ollama is installed"
  log "pulling ${OLLAMA_MODEL} (768d embedding model)..."
  # pull is idempotent; already-present models are a no-op
  ollama pull "$OLLAMA_MODEL"
  ok "${OLLAMA_MODEL} ready"
else
  warn "Ollama is NOT installed."
  warn "Mycelium requires Ollama for local embeddings (zero-LLM-cost swarm)."
  warn "Install it manually (large download, user consent required):"
  if [[ "$OS" == "mac" ]]; then
    warn "  brew install ollama   OR   https://ollama.com/download"
  else
    warn "  curl -fsSL https://ollama.com/install.sh | sh"
  fi
  warn "Then: ollama pull ${OLLAMA_MODEL}"
fi

# ---------------------------------------------------------------------------
# 9. Verification summary
# ---------------------------------------------------------------------------
echo ""
log "--- VERIFICATION ---"
PASS_COUNT=0
FAIL_COUNT=0

# Neo4j bolt
if cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASS" "RETURN 1" >/dev/null 2>&1; then
  pass "Neo4j bolt reachable (neo4j:${NEO4J_PASS})"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  fail "Neo4j bolt NOT reachable -- check: brew services info neo4j (mac) or journalctl -u neo4j (linux)"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# APOC presence
APOC_CHECK="$(cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASS" \
  "RETURN apoc.version() AS v" 2>/dev/null | tail -1 | tr -d '"' || true)"
if [[ -n "$APOC_CHECK" ]] && [[ "$APOC_CHECK" != "v" ]]; then
  pass "APOC loaded (version: ${APOC_CHECK})"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  fail "APOC NOT loaded -- check plugins/ dir and neo4j.conf allowlist"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Qdrant HTTP
if curl -fs "http://localhost:${QDRANT_PORT}/collections" >/dev/null 2>&1; then
  pass "Qdrant HTTP reachable at :${QDRANT_PORT}"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  fail "Qdrant HTTP NOT reachable -- check: brew services info qdrant (mac) or systemctl status qdrant (linux)"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Qdrant collection
if curl -fs "http://localhost:${QDRANT_PORT}/collections/${QDRANT_COLLECTION}" >/dev/null 2>&1; then
  pass "Qdrant collection '${QDRANT_COLLECTION}' exists"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  fail "Qdrant collection '${QDRANT_COLLECTION}' missing"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

# Ollama
if command -v ollama >/dev/null 2>&1; then
  pass "Ollama installed"
  PASS_COUNT=$((PASS_COUNT + 1))
else
  fail "Ollama not installed (embedding swarm will not work)"
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo ""
if [[ $FAIL_COUNT -eq 0 ]]; then
  printf '\e[32m%s ALL %d CHECKS PASSED\e[0m\n' "$PREFIX" "$PASS_COUNT"
  echo ""
  log "Ready. Run:  ./mycelium bootstrap  then  ./mycelium start"
else
  printf '\e[31m%s %d/%d CHECKS FAILED\e[0m -- resolve failures above before running bootstrap\n' \
    "$PREFIX" "$FAIL_COUNT" "$((PASS_COUNT + FAIL_COUNT))"
  exit 1
fi
