#!/usr/bin/env bash
# staging-setup.sh — idempotent staging Neo4j + bolt-proxy provisioning for pulse-server
# Run as root on pulse-server.
# Usage: bash staging-setup.sh
#
# What it sets up:
#   - /etc/neo4j-staging      — Neo4j conf (bolt 127.0.0.1:7689, HTTP disabled)
#   - /var/lib/neo4j-staging  — data, run dirs (owned neo4j:neo4j)
#   - /var/log/neo4j-staging  — log dir
#   - /opt/neo4j-staging.password — generated 20-char password (mode 0600, root only)
#   - neo4j-staging.service   — systemd unit (copy from deploy/)
#   - bolt-proxy-staging.service — systemd unit (listen :7700, upstream :7689, RO)
#   - UFW rule: allow 7700/tcp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- 1. Preflight -----------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
  echo "ERROR: must run as root" >&2; exit 1
fi

# Check bolt-proxy binary exists
if [[ ! -x /usr/local/bin/bolt-proxy ]]; then
  echo "ERROR: /usr/local/bin/bolt-proxy not found. Build it first (see deploy/bolt-proxy/)." >&2
  exit 1
fi

# Check neo4j installed
if [[ ! -f /usr/share/neo4j/bin/neo4j ]]; then
  echo "ERROR: Neo4j not installed at /usr/share/neo4j" >&2; exit 1
fi

# --- 2. Conf dir ------------------------------------------------------------
if [[ ! -d /etc/neo4j-staging ]]; then
  echo "Creating /etc/neo4j-staging from /etc/neo4j-dev..."
  cp -r /etc/neo4j-dev /etc/neo4j-staging
else
  echo "/etc/neo4j-staging already exists, skipping copy"
fi

# Ensure bolt binds to staging port
sed -i 's|^server\.bolt\.listen_address=.*|server.bolt.listen_address=127.0.0.1:7689|' \
  /etc/neo4j-staging/neo4j.conf
grep -q '^server\.bolt\.listen_address' /etc/neo4j-staging/neo4j.conf || \
  echo "server.bolt.listen_address=127.0.0.1:7689" >> /etc/neo4j-staging/neo4j.conf

# Data / log / run dirs
sed -i 's|^server\.directories\.data=.*|server.directories.data=/var/lib/neo4j-staging/data|' \
  /etc/neo4j-staging/neo4j.conf
grep -q '^server\.directories\.data' /etc/neo4j-staging/neo4j.conf || \
  echo "server.directories.data=/var/lib/neo4j-staging/data" >> /etc/neo4j-staging/neo4j.conf

sed -i 's|^server\.directories\.logs=.*|server.directories.logs=/var/log/neo4j-staging|' \
  /etc/neo4j-staging/neo4j.conf
grep -q '^server\.directories\.logs' /etc/neo4j-staging/neo4j.conf || \
  echo "server.directories.logs=/var/log/neo4j-staging" >> /etc/neo4j-staging/neo4j.conf

sed -i 's|^server\.directories\.run=.*|server.directories.run=/var/lib/neo4j-staging/run|' \
  /etc/neo4j-staging/neo4j.conf
grep -q '^server\.directories\.run' /etc/neo4j-staging/neo4j.conf || \
  echo "server.directories.run=/var/lib/neo4j-staging/run" >> /etc/neo4j-staging/neo4j.conf

# Disable HTTP (no browser needed for staging)
sed -i 's|^server\.http\.enabled=.*|server.http.enabled=false|' /etc/neo4j-staging/neo4j.conf
grep -q '^server\.http\.enabled' /etc/neo4j-staging/neo4j.conf || \
  echo "server.http.enabled=false" >> /etc/neo4j-staging/neo4j.conf

# --- 3. Data directories ---------------------------------------------------
mkdir -p /var/lib/neo4j-staging/data /var/lib/neo4j-staging/run /var/log/neo4j-staging
chown -R neo4j:neo4j /var/lib/neo4j-staging /var/log/neo4j-staging
echo "Data dirs ready"

# --- 4. Password -----------------------------------------------------------
if [[ ! -f /opt/neo4j-staging.password ]]; then
  STAGING_PASS=$(openssl rand -base64 20 | tr -dc 'a-zA-Z0-9' | head -c 20)
  echo "$STAGING_PASS" > /opt/neo4j-staging.password
  chmod 0600 /opt/neo4j-staging.password
  chown root:root /opt/neo4j-staging.password
  echo "Generated new staging password"

  # Set before first start
  NEO4J_CONF=/etc/neo4j-staging /usr/share/neo4j/bin/neo4j-admin dbms set-initial-password \
    "$STAGING_PASS" --require-password-change=false
  echo "Initial password set"
else
  echo "Password file already exists at /opt/neo4j-staging.password"
fi

# --- 5. neo4j-staging.service ----------------------------------------------
cp "$SCRIPT_DIR/neo4j-staging.service" /etc/systemd/system/neo4j-staging.service
systemctl daemon-reload
systemctl enable neo4j-staging

if ! systemctl is-active --quiet neo4j-staging; then
  systemctl start neo4j-staging
  echo "neo4j-staging started, waiting 30s..."
  sleep 30
fi
systemctl status neo4j-staging --no-pager | head -8

# --- 6. bolt-proxy-staging env + service -----------------------------------
if [[ ! -f /etc/bolt-proxy-staging.env ]]; then
  PROXY_TOKEN=$(openssl rand -base64 20 | tr -dc 'a-zA-Z0-9' | head -c 24)
  echo "PROXY_ADMIN_TOKENS=$PROXY_TOKEN" > /etc/bolt-proxy-staging.env
  chmod 0600 /etc/bolt-proxy-staging.env
  echo "bolt-proxy-staging env created"
else
  echo "/etc/bolt-proxy-staging.env already exists"
fi

cp "$SCRIPT_DIR/bolt-proxy-staging.service" /etc/systemd/system/bolt-proxy-staging.service
systemctl daemon-reload
systemctl enable bolt-proxy-staging

if ! systemctl is-active --quiet bolt-proxy-staging; then
  systemctl start bolt-proxy-staging
  sleep 3
fi
systemctl status bolt-proxy-staging --no-pager | head -8

# --- 7. UFW ----------------------------------------------------------------
if ufw status | grep -q "Status: active"; then
  if ! ufw status | grep -q "7700"; then
    ufw allow 7700/tcp comment "mycelium staging bolt"
    echo "UFW 7700/tcp opened"
  else
    echo "UFW 7700/tcp already open"
  fi
else
  echo "UFW not active, skipping"
fi

# --- 8. Smoke test ---------------------------------------------------------
STAGING_PASS=$(cat /opt/neo4j-staging.password)
echo "--- Smoke test (read) ---"
echo "MATCH (n) RETURN count(n) AS total;" | \
  cypher-shell -a bolt://127.0.0.1:7700 -u neo4j -p "$STAGING_PASS"

echo "--- Smoke test (write, should fail) ---"
echo "CREATE (:ShouldFail {x:1});" | \
  cypher-shell -a bolt://127.0.0.1:7700 -u neo4j -p "$STAGING_PASS" 2>&1 | head -3 || true

echo ""
echo "Staging provisioning complete."
echo "  Bolt (internal): bolt://127.0.0.1:7689"
echo "  Bolt (public RO): bolt://5.78.206.137:7700"
echo "  Password: /opt/neo4j-staging.password (root-read-only)"
