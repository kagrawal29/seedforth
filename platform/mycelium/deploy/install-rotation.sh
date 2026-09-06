#!/usr/bin/env bash
# install-rotation.sh — one-time installer for rotate-dev-password.sh on pulse-server
#
# Places rotate-dev-password.sh into /usr/local/sbin/ with correct permissions.
# Idempotent: safe to re-run. Requires root.
#
# Usage: sudo bash deploy/install-rotation.sh

set -euo pipefail

log() { printf '[install-rotation] %s\n' "$*" >&2; }
die() { log "FATAL: $*"; exit 1; }

[[ $EUID -eq 0 ]] || die "must run as root (use: sudo bash deploy/install-rotation.sh)"

SCRIPT_SOURCE="deploy/rotate-dev-password.sh"
SCRIPT_DEST="/usr/local/sbin/rotate-dev-password"

[[ -f "$SCRIPT_SOURCE" ]] || die "source script not found: $SCRIPT_SOURCE"

log "installing $SCRIPT_SOURCE → $SCRIPT_DEST"

# Copy with mode 0700 (rwx------)
install -m 0700 "$SCRIPT_SOURCE" "$SCRIPT_DEST"

log "installed: $SCRIPT_DEST (mode 0700)"
log ""
log "Usage:"
log "  export OLD_PASSWORD='...'"
log "  export NEW_PASSWORD='...'"
log "  sudo rotate-dev-password"
log ""
