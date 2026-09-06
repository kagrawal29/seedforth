#!/usr/bin/env bash
# Idempotent installer for mycelium-embed.service on pulse-server.
# Provisions a read-only HTTP proxy around local Ollama so the mycelium CLI
# (and CI) can request embeddings without installing Ollama locally.
set -euo pipefail

EMBED_USER="mycelium-embed"
EMBED_HOME="/opt/mycelium-embed"
LOG_DIR="/var/log/mycelium-embed"
BIN_DIR="$EMBED_HOME/bin"
SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/embed-proxy.py"
UNIT_SRC="$(cd "$(dirname "$0")" && pwd)/mycelium-embed.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "must be run as root" >&2
  exit 1
fi

if ! id -u "$EMBED_USER" >/dev/null 2>&1; then
  useradd --system --home "$EMBED_HOME" --shell /usr/sbin/nologin "$EMBED_USER"
fi

install -d -o "$EMBED_USER" -g "$EMBED_USER" -m 0755 "$BIN_DIR"
install -d -o "$EMBED_USER" -g "$EMBED_USER" -m 0755 "$LOG_DIR"

install -o root -g root -m 0755 "$SCRIPT_SRC" "$BIN_DIR/embed-proxy"
install -o root -g root -m 0644 "$UNIT_SRC" /etc/systemd/system/mycelium-embed.service

systemctl daemon-reload
systemctl enable --now mycelium-embed.service

# firewall: expose :7701 for CI + teammates
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  ufw allow 7701/tcp comment "mycelium embed proxy" || true
fi

echo "mycelium-embed installed."
sleep 1
systemctl --no-pager status mycelium-embed.service | head -10
curl -fsS -o /dev/null -w "health: %{http_code}\n" http://127.0.0.1:7701/health || true
