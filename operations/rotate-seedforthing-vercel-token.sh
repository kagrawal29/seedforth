#!/usr/bin/env bash
set -euo pipefail

# Install a replacement Vercel access token without exposing it in shell
# arguments, logs, command history, or process listings. Run on delta2 as root
# (or as the owner of the target file).
#
# Usage:
#   printf '%s\n' "$REPLACEMENT" | sudo ./operations/rotate-seedforthing-vercel-token.sh --stdin
#
# The script deliberately does not revoke the old token. Revoke it from the
# Vercel account after the replacement has been installed and deployment has
# been smoke-tested.

TARGET="/home/proj-seedforthing/seedforthing/delta-config/.vercel-token-charlietheagent"
# A project-scoped token cannot call the user endpoint. Validate against the
# exact project it is intended to deploy.
API="https://api.vercel.com/v9/projects/prj_ubMP9vcriuaqrrU4HK6FFO62dD1q?teamId=team_uyYPbgdCvgMaUAtmitpuunDs"

if [[ "${1:-}" != "--stdin" ]]; then
  echo "usage: $0 --stdin" >&2
  exit 64
fi

if [[ ! -f "$TARGET" ]]; then
  echo "target token file does not exist: $TARGET" >&2
  exit 1
fi

if [[ "$(stat -c '%a' "$TARGET")" != "600" ]]; then
  echo "refusing to rotate: target mode is not 600" >&2
  exit 1
fi

target_dir="$(dirname "$TARGET")"
tmp="$(mktemp "$target_dir/.vercel-token.XXXXXX")"
cleanup() { rm -f -- "$tmp"; }
trap cleanup EXIT
chmod 600 "$tmp"

# Read exactly one line from stdin. The token is never echoed or displayed.
IFS= read -r replacement || true
if [[ -z "${replacement:-}" || "$replacement" == *$'\n'* || "$replacement" == *$'\r'* ]]; then
  echo "refusing to rotate: stdin did not contain one non-empty token line" >&2
  exit 64
fi
if IFS= read -r extra && [[ -n "$extra" ]]; then
  echo "refusing to rotate: stdin contained more than one token line" >&2
  exit 64
fi
printf '%s\n' "$replacement" > "$tmp"

status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  --header "Authorization: Bearer $replacement" "$API")"
if [[ "$status" != "200" ]]; then
  echo "refusing to rotate: replacement token validation returned HTTP $status" >&2
  exit 1
fi

chown --reference="$TARGET" "$tmp"
mv -- "$tmp" "$TARGET"
chmod 600 "$TARGET"

post_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  --header "Authorization: Bearer $(<"$TARGET")" "$API")"
if [[ "$post_status" != "200" ]]; then
  echo "rotation write completed but post-write validation returned HTTP $post_status" >&2
  exit 1
fi

echo "replacement Vercel token installed and validated; old token remains active"
