#!/usr/bin/env bash
# pulse-setup.sh — idempotent reconstruction of pulse-server's Mycelium stack.
#
# Reproduces what's live on pulse-server (5.78.206.137) as of 2026-04-18:
#   - Neo4j 2026.03.1 prod (bolt :7687, http :7474)
#   - Neo4j 2026.03.1 dev  (bolt :7688, http :7475) sharing binary, separate data+conf
#   - APOC 2026.03.1-core plugin symlinked into plugins/
#   - Qdrant 1.11.5 binary on 127.0.0.1:6333 (localhost only)
#   - CLI wrappers /usr/local/bin/mycelium-{prod,dev}
#   - UFW rules for 7474/7475/7687/7688
#   - /opt/mycelium checked out from Qubit-Capital/maverick on main
#
# Idempotent: safe to re-run. Run as root on a fresh Ubuntu 24.04 server.
#
# Usage: sudo ./deploy/pulse-setup.sh --prod-pass <pw> --dev-pass <pw>
#
# Required flags:
#   --prod-pass <pw>    Neo4j prod admin password (required)
#   --dev-pass <pw>     Neo4j dev admin password (required)

set -euo pipefail

log() { printf '[pulse-setup] %s\n' "$*" >&2; }
die() { log "FATAL: $*"; exit 1; }

usage() {
  log "Usage: $0 --prod-pass <pw> --dev-pass <pw>"
  log "Both --prod-pass and --dev-pass are required."
  exit 1
}

[[ $EUID -eq 0 ]] || die "must run as root"
[[ -f /etc/os-release ]] && . /etc/os-release || die "no /etc/os-release"
[[ "$ID" == "ubuntu" ]] || die "requires Ubuntu (got $ID)"

PROD_PASS=""
DEV_PASS=""
NEO4J_VER="2026.03.1"
QDRANT_VER="1.11.5"
REPO_URL="https://github.com/Qubit-Capital/maverick.git"
REPO_BRANCH="dev"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod-pass) PROD_PASS="$2"; shift 2 ;;
    --dev-pass)  DEV_PASS="$2";  shift 2 ;;
    -h|--help) usage ;;
    *) die "unknown arg: $1" ;;
  esac
done

# Validate required flags
[[ -n "$PROD_PASS" ]] || die "missing required flag: --prod-pass"
[[ -n "$DEV_PASS" ]] || die "missing required flag: --dev-pass"

# --- 1. Neo4j install (apt, pinned minor) -----------------------------------
if ! command -v neo4j >/dev/null; then
  log "installing neo4j ${NEO4J_VER}"
  apt-get update -qq
  apt-get install -y -qq curl gpg ca-certificates openjdk-21-jre-headless
  curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
  echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 2026.03" \
    > /etc/apt/sources.list.d/neo4j.list
  apt-get update -qq
  apt-get install -y -qq "neo4j=1:${NEO4J_VER}"
  apt-mark hold neo4j
else
  log "neo4j already installed ($(neo4j --version 2>&1 | head -1))"
fi

# --- 2. APOC symlink ---------------------------------------------------------
APOC_JAR="/var/lib/neo4j/labs/apoc-${NEO4J_VER}-core.jar"
APOC_LINK="/var/lib/neo4j/plugins/apoc-${NEO4J_VER}-core.jar"
[[ -f "$APOC_JAR" ]] || die "APOC jar missing at $APOC_JAR (shipped in neo4j package labs/)"
if [[ ! -L "$APOC_LINK" ]]; then
  log "symlinking APOC plugin"
  ln -sf "$APOC_JAR" "$APOC_LINK"
  chown -h neo4j:neo4j "$APOC_LINK"
fi

# --- 3. Neo4j prod config tweaks (idempotent append-and-replace) ------------
set_conf() {
  # $1=file, $2=key, $3=value
  local f="$1" k="$2" v="$3"
  # strip any existing occurrence (commented or not)
  sed -i -E "/^#?\s*${k}\s*=/d" "$f"
  echo "${k}=${v}" >> "$f"
}

apply_prod_conf() {
  local f=/etc/neo4j/neo4j.conf
  log "applying prod neo4j.conf overrides"
  set_conf "$f" "server.default_listen_address" "0.0.0.0"
  set_conf "$f" "server.memory.heap.initial_size" "512m"
  set_conf "$f" "server.memory.heap.max_size" "1g"
  set_conf "$f" "server.memory.pagecache.size" "512m"
  set_conf "$f" "db.tx_log.rotation.retention_policy" "1 files"
  set_conf "$f" "db.tx_log.rotation.size" "16m"
  set_conf "$f" "db.checkpoint.interval.time" "5m"
  set_conf "$f" "db.checkpoint.interval.volume" "50m"
  set_conf "$f" "dbms.security.procedures.unrestricted" "apoc.*,gds.*"
  set_conf "$f" "dbms.security.procedures.allowlist" "apoc.*,gds.*"
}
apply_prod_conf

# --- 4. Neo4j dev instance (separate conf + data, shared binary) ------------
log "setting up neo4j-dev"
mkdir -p /etc/neo4j-dev /var/lib/neo4j-dev/{data,run} /var/log/neo4j-dev
cp -n /etc/neo4j/neo4j.conf /etc/neo4j-dev/neo4j.conf || true
cp -n /etc/neo4j/*-logs.xml /etc/neo4j-dev/ 2>/dev/null || true
apply_dev_conf() {
  local f=/etc/neo4j-dev/neo4j.conf
  # base tweaks (copied from prod) already present; apply dev-specific on top
  set_conf "$f" "server.bolt.listen_address" ":7688"
  set_conf "$f" "server.http.listen_address"  ":7475"
  set_conf "$f" "server.https.enabled" "false"
  set_conf "$f" "server.directories.data" "/var/lib/neo4j-dev/data"
  set_conf "$f" "server.directories.logs" "/var/log/neo4j-dev"
  set_conf "$f" "server.directories.run"  "/var/lib/neo4j-dev/run"
  # dev inherits plugins dir from prod so APOC symlink is shared
}
apply_dev_conf
chown -R neo4j:neo4j /var/lib/neo4j-dev /var/log/neo4j-dev /etc/neo4j-dev

# --- 5. neo4j-dev systemd unit ----------------------------------------------
cat > /etc/systemd/system/neo4j-dev.service <<'EOF'
[Unit]
Description=Neo4j Graph Database (dev instance)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=neo4j
Group=neo4j
Environment=NEO4J_CONF=/etc/neo4j-dev NEO4J_HOME=/var/lib/neo4j
ExecStart=/usr/share/neo4j/bin/neo4j console
Restart=on-failure
LimitNOFILE=60000

[Install]
WantedBy=multi-user.target
EOF

# --- 6. Qdrant binary + systemd ---------------------------------------------
if [[ ! -x /usr/local/bin/qdrant ]]; then
  log "installing qdrant ${QDRANT_VER}"
  curl -fsSL -o /tmp/qdrant.tar.gz \
    "https://github.com/qdrant/qdrant/releases/download/v${QDRANT_VER}/qdrant-x86_64-unknown-linux-musl.tar.gz"
  tar -xzf /tmp/qdrant.tar.gz -C /usr/local/bin qdrant
  chmod +x /usr/local/bin/qdrant
  rm /tmp/qdrant.tar.gz
fi

id qdrant >/dev/null 2>&1 || useradd -r -s /usr/sbin/nologin -d /var/lib/qdrant qdrant
mkdir -p /etc/qdrant /var/lib/qdrant/storage
cat > /etc/qdrant/config.yaml <<'EOF'
storage:
  storage_path: /var/lib/qdrant/storage
service:
  host: 127.0.0.1
  http_port: 6333
  grpc_port: 6334
log_level: INFO
EOF
chown -R qdrant:qdrant /var/lib/qdrant /etc/qdrant

cat > /etc/systemd/system/qdrant.service <<'EOF'
[Unit]
Description=Qdrant vector database
After=network-online.target

[Service]
Type=simple
User=qdrant
Group=qdrant
ExecStart=/usr/local/bin/qdrant --config-path /etc/qdrant/config.yaml
Restart=on-failure
LimitNOFILE=60000

[Install]
WantedBy=multi-user.target
EOF

# --- 7. Repo at /opt/mycelium -----------------------------------------------
if [[ ! -d /opt/mycelium/.git ]]; then
  log "cloning ${REPO_URL} (branch: ${REPO_BRANCH}) -> /opt/mycelium"
  git clone -b "$REPO_BRANCH" "$REPO_URL" /opt/mycelium
  git -C /opt/mycelium checkout "$REPO_BRANCH"
else
  log "/opt/mycelium exists — pulling"
  git -C /opt/mycelium checkout "$REPO_BRANCH" || log "WARN: checkout ${REPO_BRANCH} failed"
  git -C /opt/mycelium pull --ff-only origin "$REPO_BRANCH" || log "WARN: pull failed, manual intervention may be needed"
fi

# --- 8. CLI wrappers --------------------------------------------------------
# Fixes #40 + #44:
#   - exec ./mycelium-dev (the bash write-path script) NOT ./mycelium (which
#     is the dispatcher shim that forks into the global Go binary → recursion).
#   - export MYCELIUM_LOCAL_PASS alongside NEO4J_PASS so the dev script's
#     target-case block does not overwrite the admin pass with the team
#     read-only pass. (The script now respects caller NEO4J_PASS directly,
#     but mirroring keeps the wrapper compatible with older script versions.)
cat > /usr/local/bin/mycelium-prod <<EOF
#!/usr/bin/env bash
export NEO4J_BOLT=bolt://127.0.0.1:7687
export NEO4J_HTTP=http://127.0.0.1:7474
export NEO4J_USER=neo4j
export NEO4J_PASS=${PROD_PASS}
export MYCELIUM_LOCAL_PASS=${PROD_PASS}
cd /opt/mycelium && exec ./mycelium-dev "\$@"
EOF
cat > /usr/local/bin/mycelium-dev <<EOF
#!/usr/bin/env bash
export NEO4J_BOLT=bolt://127.0.0.1:7688
export NEO4J_HTTP=http://127.0.0.1:7475
export NEO4J_USER=neo4j
export NEO4J_PASS=${DEV_PASS}
export MYCELIUM_LOCAL_PASS=${DEV_PASS}
cd /opt/mycelium && exec ./mycelium-dev "\$@"
EOF
chmod +x /usr/local/bin/mycelium-{prod,dev}

# --- 9. UFW --------------------------------------------------------------
if command -v ufw >/dev/null; then
  log "applying UFW rules"
  ufw allow 7474/tcp comment 'mycelium-prod http' >/dev/null
  ufw allow 7687/tcp comment 'mycelium-prod bolt' >/dev/null
  ufw allow 7475/tcp comment 'mycelium-dev http'  >/dev/null
  ufw allow 7688/tcp comment 'mycelium-dev bolt'  >/dev/null
  # Qdrant intentionally NOT opened — localhost only
fi

# --- 10. Set initial passwords (idempotent via cypher-shell) ---------------
set_neo4j_pass() {
  local bolt="$1" pw="$2"
  # DBMS-level password change. Fails harmlessly if already set to target.
  timeout 10 /usr/share/neo4j/bin/cypher-shell -a "$bolt" -u neo4j -p "$pw" \
    'RETURN 1' >/dev/null 2>&1 && return 0
  # initial default is "neo4j" + forced change
  echo "ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO '$pw';" | \
    timeout 10 /usr/share/neo4j/bin/cypher-shell -a "$bolt" -u neo4j -p neo4j >/dev/null 2>&1 || \
    log "WARN: could not set password on $bolt (may already be set to something else)"
}

# --- 10b. Auto-deploy timer (pull + bootstrap every 5 min) ------------------
install -m 0644 /opt/mycelium/deploy/mycelium-autodeploy.service /etc/systemd/system/
install -m 0644 /opt/mycelium/deploy/mycelium-autodeploy.timer   /etc/systemd/system/

# --- 11. Enable + start everything -----------------------------------------
systemctl daemon-reload
systemctl enable --now neo4j neo4j-dev qdrant mycelium-autodeploy.timer

sleep 5  # give bolt listeners a moment
set_neo4j_pass bolt://127.0.0.1:7687 "$PROD_PASS"
set_neo4j_pass bolt://127.0.0.1:7688 "$DEV_PASS"

# --- 12. Verify --------------------------------------------------------------
log "verifying services"
systemctl is-active --quiet neo4j     && log "  neo4j (prod) OK"     || log "  neo4j (prod) FAIL"
systemctl is-active --quiet neo4j-dev && log "  neo4j-dev OK"         || log "  neo4j-dev FAIL"
systemctl is-active --quiet qdrant    && log "  qdrant OK"            || log "  qdrant FAIL"
curl -fsS http://127.0.0.1:6333/collections >/dev/null && log "  qdrant http OK" || log "  qdrant http FAIL"

log "done. Next: cd /opt/mycelium && mycelium-prod bootstrap"
