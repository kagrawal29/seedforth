#!/usr/bin/env bash
# install-ingest.sh — install + start the mycelium-ingest service on pulse-server
# Run as root. Idempotent.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/kagrawal29/mycelium.git}"
INSTALL_DIR="/opt/mycelium-ingest"
SERVICE_USER="mycelium-ingest"
SECRET_DIR="/etc/mycelium-ingest"
SECRET_FILE="${SECRET_DIR}/webhook.secret"
SERVICE_FILE="/etc/systemd/system/mycelium-ingest.service"
LOG_DIR="/var/log/mycelium-ingest"

echo "==> Creating system user: ${SERVICE_USER}"
id "${SERVICE_USER}" &>/dev/null || useradd --system --shell /usr/sbin/nologin "${SERVICE_USER}"

echo "==> Cloning / updating repo"
if [ -d "${INSTALL_DIR}/.git" ]; then
    git -C "${INSTALL_DIR}" pull --ff-only
else
    git clone --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
fi

echo "==> Installing Python dependencies into venv"
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --quiet --upgrade pip
"${INSTALL_DIR}/venv/bin/pip" install --quiet \
    fastapi uvicorn[standard] neo4j

echo "==> Ensuring secret directory"
mkdir -p "${SECRET_DIR}"
chmod 700 "${SECRET_DIR}"

if [ ! -f "${SECRET_FILE}" ]; then
    echo "==> Generating webhook secret"
    python3 -c "import secrets; print(secrets.token_hex(32))" > "${SECRET_FILE}"
    chmod 600 "${SECRET_FILE}"
    chown root:root "${SECRET_FILE}"
    echo "    Secret written to ${SECRET_FILE}"
    echo "    *** Copy this value when registering webhooks on GitHub ***"
    echo "    Secret: $(cat ${SECRET_FILE})"
else
    echo "==> Webhook secret already exists at ${SECRET_FILE}"
fi

# Allow the service user to read the secret
chown root:"${SERVICE_USER}" "${SECRET_FILE}"
chmod 640 "${SECRET_FILE}"

echo "==> Creating log directory"
mkdir -p "${LOG_DIR}"
chown "${SERVICE_USER}:${SERVICE_USER}" "${LOG_DIR}"

echo "==> Installing systemd unit"
cp "${INSTALL_DIR}/services/mycelium-ingest/systemd/mycelium-ingest.service" "${SERVICE_FILE}"

# Patch the ExecStart path to point at the venv python and the correct server.py
sed -i "s|ExecStart=.*|ExecStart=${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/services/mycelium-ingest/server.py|" "${SERVICE_FILE}"
sed -i "s|WorkingDirectory=.*|WorkingDirectory=${INSTALL_DIR}/services/mycelium-ingest|" "${SERVICE_FILE}"

echo "==> Enabling + starting service"
systemctl daemon-reload
systemctl enable mycelium-ingest
systemctl restart mycelium-ingest
systemctl status mycelium-ingest --no-pager

echo "==> Done. Service listening on port 9090 (loopback only)."
echo "    Public ingress (Cloudflare Tunnel) is a DEFERRED step — see docs/ingress-setup.md"
