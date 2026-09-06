#!/usr/bin/env bash
# Hourly smoke test: mycelium binary can reach dev + prod graphs.
# Exits non-zero on any failure so the systemd timer surfaces red in `systemctl list-timers`.
set -euo pipefail

MYCELIUM_BIN="${MYCELIUM_BIN:-/usr/local/bin/mycelium}"
LOG_TAG="mycelium-smoke"
FAIL=0

check() {
  local target="$1"
  local out
  if ! out=$("$MYCELIUM_BIN" --target "$target" --timeout 10s shell "RETURN 1 AS one" 2>&1); then
    logger -t "$LOG_TAG" "FAIL target=$target output=${out:0:200}"
    FAIL=1
    return
  fi
  if ! grep -qE '(^|[^0-9])1([^0-9]|$)' <<<"$out"; then
    logger -t "$LOG_TAG" "FAIL target=$target unexpected_output=${out:0:200}"
    FAIL=1
    return
  fi
  logger -t "$LOG_TAG" "OK target=$target"
}

check dev
check prod

if [ "$FAIL" -ne 0 ]; then
  echo "smoke test failed" >&2
  exit 1
fi
echo "smoke ok: dev + prod returned 1"
