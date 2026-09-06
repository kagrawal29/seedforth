#!/usr/bin/env bash
# rotate-dev-password.sh — idempotent Neo4j dev password rotation on pulse-server
#
# Rotates the neo4j-dev password (port 7688) and updates bolt-proxy-dev accordingly.
# Intended for incident response or scheduled quarterly rotation.
#
# Idempotent: safe to re-run with same OLD/NEW passwords (will be idempotent against
# the current state). Each run logs to /var/log/mycelium-rotations.log (SHA256 only).
#
# Required environment variables (NEVER pass as command-line args — leaks via ps):
#   OLD_PASSWORD          Current Neo4j dev password
#   NEW_PASSWORD          New password (min 16 chars, mixed case/digits/symbols)
#
# Usage:
#   export OLD_PASSWORD='current-password-here'
#   export NEW_PASSWORD='new-password-here'
#   sudo bash deploy/rotate-dev-password.sh

set -euo pipefail

log() { printf '[rotate-dev-password] %s\n' "$*" >&2; }
die() { log "FATAL: $*"; exit 1; }

usage() {
  log ""
  log "Usage:"
  log "  export OLD_PASSWORD='...current password...'"
  log "  export NEW_PASSWORD='...new password (min 16 chars)...'"
  log "  sudo bash $(basename "$0")"
  log ""
  log "Environment Variables (required, never pass as args):"
  log "  OLD_PASSWORD    Current Neo4j dev password"
  log "  NEW_PASSWORD    New password (min 16 chars, mixed case/number/symbol)"
  log ""
  exit 2
}

# Validate inputs BEFORE requiring root — so dry-run / lint paths surface
# argument errors with the right exit code, not a "must run as root" shortcut.

# Require env vars
if [[ -z "${OLD_PASSWORD:-}" ]] || [[ -z "${NEW_PASSWORD:-}" ]]; then
  log "ERROR: OLD_PASSWORD and NEW_PASSWORD environment variables required"
  usage
fi

# Validate password strength (min 16 chars, at least 3 of 4 categories: upper, lower, digit, symbol)
validate_password() {
  local pw="$1"
  local len=${#pw}

  # Length check
  if (( len < 16 )); then
    log "ERROR: NEW_PASSWORD too short (${len} chars, need at least 16)"
    exit 3
  fi

  # Complexity check: require at least 3 categories
  local has_upper=0 has_lower=0 has_digit=0 has_symbol=0

  [[ "$pw" =~ [A-Z] ]] && has_upper=1
  [[ "$pw" =~ [a-z] ]] && has_lower=1
  [[ "$pw" =~ [0-9] ]] && has_digit=1
  [[ "$pw" =~ [^A-Za-z0-9] ]] && has_symbol=1

  local complexity=$(( has_upper + has_lower + has_digit + has_symbol ))
  if (( complexity < 3 )); then
    log "ERROR: NEW_PASSWORD too simple (has $complexity/4 categories: upper=$has_upper lower=$has_lower digit=$has_digit symbol=$has_symbol)"
    log "       Require at least 3 categories. Example: MyNewPass2026!"
    exit 3
  fi
}

validate_password "$NEW_PASSWORD"

# Only now enforce root — rotation needs write access to /var/log + systemd.
[[ $EUID -eq 0 ]] || die "must run as root (use: sudo -E bash deploy/rotate-dev-password.sh)"

# Ensure logging directory exists
mkdir -p /var/log/
touch /var/log/mycelium-rotations.log
chmod 0600 /var/log/mycelium-rotations.log

log "rotating neo4j-dev password on port 7688"

# Rotate password via cypher-shell
log "executing ALTER USER via cypher-shell"
if ! timeout 10 /usr/share/neo4j/bin/cypher-shell \
  -a "bolt://localhost:7688" \
  -u neo4j \
  -p "$OLD_PASSWORD" \
  "ALTER CURRENT USER SET PASSWORD FROM '$OLD_PASSWORD' TO '$NEW_PASSWORD'"; then
  die "cypher-shell failed — check OLD_PASSWORD is correct and Neo4j dev is running"
fi

log "password altered in Neo4j"

# Update bolt-proxy-dev override (drop-in file approach, preserve existing overrides)
log "updating bolt-proxy-dev systemd override"
PROXY_OVERRIDE_DIR="/etc/systemd/system/bolt-proxy-dev.service.d"
PROXY_OVERRIDE_FILE="${PROXY_OVERRIDE_DIR}/override.conf"

mkdir -p "$PROXY_OVERRIDE_DIR"

# Create override file with password env var
# If the file exists, we replace only the NEO4J_PASSWORD line; preserve any other settings
if [[ -f "$PROXY_OVERRIDE_FILE" ]]; then
  # Remove existing NEO4J_PASSWORD line(s), preserve the rest
  sed -i '/^Environment=NEO4J_PASSWORD=/d' "$PROXY_OVERRIDE_FILE"
fi

# Append new password (file might be empty, might have other content — both OK)
echo "Environment=NEO4J_PASSWORD=$NEW_PASSWORD" >> "$PROXY_OVERRIDE_FILE"

log "wrote override to ${PROXY_OVERRIDE_FILE}"

# Reload systemd and restart bolt-proxy-dev
log "reloading systemd daemon"
systemctl daemon-reload

log "restarting bolt-proxy-dev"
if ! systemctl restart bolt-proxy-dev; then
  die "failed to restart bolt-proxy-dev — check systemctl status bolt-proxy-dev"
fi

# Verify bolt-proxy-dev is active
sleep 1
if ! systemctl is-active --quiet bolt-proxy-dev; then
  die "bolt-proxy-dev failed after restart — check systemctl status bolt-proxy-dev"
fi

log "bolt-proxy-dev restarted and verified active"

# Write credential to secure file for CI jobs
log "writing credential to /opt/mycelium-dev/deploy/.dev-password (mode 0600)"
CRED_DIR="/opt/mycelium-dev/deploy"
[[ -d "$CRED_DIR" ]] || mkdir -p "$CRED_DIR"

echo -n "$NEW_PASSWORD" > "${CRED_DIR}/.dev-password"
chmod 0600 "${CRED_DIR}/.dev-password"
chown root:root "${CRED_DIR}/.dev-password"

log "credential written to ${CRED_DIR}/.dev-password"

# Log rotation event (SHA256 hash only, never plaintext)
PASSWORD_HASH=$(printf '%s' "$NEW_PASSWORD" | sha256sum | cut -d' ' -f1)
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
echo "${TIMESTAMP} | neo4j-dev rotated | hash=${PASSWORD_HASH}" >> /var/log/mycelium-rotations.log

log ""
log "SUCCESS: neo4j-dev password rotated"
log ""
log "NEXT STEPS:"
log "  1. Update CI secret in Qubit-Capital/maverick → Settings → Secrets → MYCELIUM_CREDS_TOML"
log "  2. Re-run release workflow to embed new password in binary"
log "  3. Verify: mycelium --target dev doctor (within 5 min, after CI redeploys)"
log ""
log "ROLLBACK (if rotation breaks):"
log "  1. Re-run this script with OLD_PASSWORD and NEW_PASSWORD swapped"
log "  2. OR manually set password back and restart bolt-proxy-dev"
log ""
