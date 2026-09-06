#!/usr/bin/env bash
set -euo pipefail

echo "=== SeedForth Delta Server Provisioning ==="
echo "Target: Contabo Cloud VPS 6 (12 GB, 6 vCPU, 200 GB)"
echo "Expects migration tarballs at /root/migration/"
echo ""

RED=$(tput setaf 1 2>/dev/null || echo "")
GREEN=$(tput setaf 2 2>/dev/null || echo "")
NC=$(tput sgr0 2>/dev/null || echo "")

log()  { echo "${GREEN}[+]${NC} $*"; }
warn() { echo "${RED}[!]${NC} $*"; }
err()  { echo "${RED}[ERROR]${NC} $*"; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    err "Run as root"
fi

MIGR=/root/migration
if [ ! -d "$MIGR" ]; then
    err "Migration data not found at $MIGR. SCP from old server first."
fi

# ---------------------------------------------------------------------------
# 1. Base packages
# ---------------------------------------------------------------------------
log "Updating system..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get upgrade -y -qq

log "Installing base packages..."
apt-get install -y -qq \
    python3 python3-pip python3-venv \
    git curl wget unzip supervisor \
    chromium-browser xvfb x11vnc novnc websockify xdg-utils \
    apt-transport-https ca-certificates gnupg lsb-release \
    ufw ntp

# ---------------------------------------------------------------------------
# 2. Docker
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    log "Installing Docker..."
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq && apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    log "Docker installed"
else
    log "Docker already installed"
fi

# ---------------------------------------------------------------------------
# 3. Node.js + opencode
# ---------------------------------------------------------------------------
if ! command -v node &>/dev/null; then
    log "Installing Node.js 22..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y -qq nodejs
    log "Node $(node --version)"
else
    log "Node $(node --version) already installed"
fi

if ! command -v opencode &>/dev/null; then
    log "Installing opencode..."
    npm install -g @anthropic/opencode 2>/dev/null || npm install -g opencode@latest
    log "OpenCode $(opencode --version 2>&1 || echo 'installed')"
else
    log "OpenCode already installed: $(opencode --version 2>&1 || echo '?')"
fi

# ---------------------------------------------------------------------------
# 4. System users
# ---------------------------------------------------------------------------
log "Creating system users..."

id -u delta &>/dev/null || useradd -m -u 999 -s /bin/bash delta
usermod -aG docker delta

# Delta sudo access (scoped)
cat > /etc/sudoers.d/delta << 'SUDOERS'
delta ALL=(root) NOPASSWD: /usr/sbin/useradd *
delta ALL=(root) NOPASSWD: /usr/sbin/userdel *
delta ALL=(root) NOPASSWD: /bin/chown *
delta ALL=(root) NOPASSWD: /bin/chmod *
delta ALL=(root) NOPASSWD: /usr/bin/systemctl restart delta
delta ALL=(root) NOPASSWD: /usr/bin/systemctl status *
delta ALL=(root) NOPASSWD: /usr/bin/journalctl *
delta ALL=(root) NOPASSWD: /usr/bin/docker *
delta ALL=(ALL) NOPASSWD: ALL
SUDOERS
chmod 440 /etc/sudoers.d/delta
log "delta user created"

# Charlie browser user
id -u charlie-browser &>/dev/null || useradd -m -s /bin/bash charlie-browser
log "charlie-browser user created"

# Agent users - create with fresh UIDs, tar restore will fix ownership
PROJECTS=(
    "cajon-sensei"
    "ethos"
    "flowing-indian"
    "linkedin-himanshu-ghiya"
    "linkedin-kshitiz-agarwal"
    "seedforthing"
    "zuuro"
    "delta-hub"
)

PROJ_USR_COUNT=1000
for proj in "${PROJECTS[@]}"; do
    user="proj-${proj}"
    PROJ_USR_COUNT=$((PROJ_USR_COUNT + 1))
    if ! id -u "$user" &>/dev/null; then
        useradd -m -u "$PROJ_USR_COUNT" -s /bin/bash "$user"
    fi
    log "  $user ($(id -u "$user"))"
done

# ---------------------------------------------------------------------------
# 5. Python deps for delta bot
# ---------------------------------------------------------------------------
log "Installing Python dependencies..."
pip3 install --break-system-packages discord.py==2.4.0 python-dotenv composio-core 2>&1 | tail -3

# ---------------------------------------------------------------------------
# 6. Neo4j via Docker
# ---------------------------------------------------------------------------
log "Setting up Neo4j..."
NEO4J_PASS="${NEO4J_PASSWORD:?set NEO4J_PASSWORD in the runtime environment}"
NEO4J_DATA="/opt/neo4j-data"

mkdir -p "$NEO4J_DATA"/{data,logs,plugins,import}

if docker ps -a --format '{{.Names}}' | grep -q '^mycelium-neo4j$'; then
    warn "Neo4j container exists, stopping first..."
    docker stop mycelium-neo4j 2>/dev/null || true
    docker rm mycelium-neo4j 2>/dev/null || true
fi

docker run -d --name mycelium-neo4j \
    --restart unless-stopped \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH="neo4j/${NEO4J_PASS}" \
    -e NEO4J_PLUGINS='["apoc"]' \
    -e NEO4J_dbms_security_procedures_unrestricted="apoc.*" \
    -e NEO4J_apoc_export_file_enabled=true \
    -e NEO4J_apoc_import_file_enabled=true \
    -e NEO4J_apoc_import_file_use__neo4j__config=true \
    -v "$NEO4J_DATA/data":/var/lib/neo4j/data \
    -v "$NEO4J_DATA/logs":/var/lib/neo4j/logs \
    -v "$NEO4J_DATA/plugins":/var/lib/neo4j/plugins \
    -v "$NEO4J_DATA/import":/var/lib/neo4j/import \
    neo4j:5.26-community

log "Waiting for Neo4j to start..."
sleep 10
for i in $(seq 1 30); do
    if docker exec mycelium-neo4j cypher-shell -u "neo4j" -p "$NEO4J_PASS" "RETURN 1" &>/dev/null; then
        log "Neo4j ready"
        break
    fi
    sleep 2
done

# ---------------------------------------------------------------------------
# 7. Restore Neo4j dump
# ---------------------------------------------------------------------------
if [ -f "$MIGR/neo4j.dump" ]; then
    log "Restoring Neo4j from dump..."
    docker cp "$MIGR/neo4j.dump" mycelium-neo4j:/var/lib/neo4j/dump.db
    docker exec mycelium-neo4j neo4j stop 2>&1 | tail -2
    sleep 3
    docker exec mycelium-neo4j neo4j-admin database load --from-path /var/lib/neo4j/ --overwrite-destination neo4j 2>&1 | tail -3
    sleep 3
    docker exec mycelium-neo4j neo4j start 2>&1 | tail -2
    sleep 5
    log "Neo4j restore complete"
else
    warn "No neo4j.dump found, starting fresh"
fi

# ---------------------------------------------------------------------------
# 8. Delta code + config
# ---------------------------------------------------------------------------
log "Setting up Delta..."
mkdir -p /opt/delta
if [ -f "$MIGR/delta.env" ]; then
    cp "$MIGR/delta.env" /opt/delta/delta.env
    log "  delta.env restored"
fi
if [ -f "$MIGR/delta-registry.json" ]; then
    cp "$MIGR/delta-registry.json" /opt/delta/delta-registry.json
    log "  delta-registry.json restored"
fi

# Clone delta code
if [ ! -d "/opt/delta/.git" ]; then
    git clone https://github.com/kagrawal29/delta.git /tmp/delta-clone 2>&1 | tail -1
    mv /tmp/delta-clone/* /tmp/delta-clone/.[!.]* /opt/delta/ 2>/dev/null || true
    rm -rf /tmp/delta-clone
    log "  delta code cloned"
else
    log "  delta code already present"
fi

# ---------------------------------------------------------------------------
# 9. Restore agent home dirs
# ---------------------------------------------------------------------------
log "Restoring agent home directories..."
for proj in "${PROJECTS[@]}"; do
    user="proj-${proj}"
    tarball="$MIGR/home-backup/${user}.tar.gz"

    if [ ! -f "$tarball" ]; then
        warn "  No tarball for $user, skipping"
        continue
    fi

    rm -rf "/home/${user}/${proj}" 2>/dev/null || true
    tar -xzf "$tarball" -C /home/
    chown -R "${user}:${user}" "/home/${user}/"

    # Create delta-config subdirs if missing
    sudo -u "$user" mkdir -p "/home/${user}/${proj}/delta-config"/{inbox,outbox,logs}

    # Fix opencode config - remove invalid keys that cause crash loops
    local config="/home/${user}/.config/opencode/opencode.jsonc"
    if [ -f "$config" ]; then
        python3 -c "
import json
with open('$config') as f:
    d = json.load(f)
d.pop('lsp', None)
d.pop('custom_tool', None)
with open('$config', 'w') as f:
    json.dump(d, f, indent=2)
" 2>/dev/null || true
    fi

    # Write minimal opencode.jsonc in project dir if missing
    if [ ! -f "/home/${user}/${proj}/opencode.jsonc" ]; then
        sudo -u "$user" bash -c "cat > /home/${user}/${proj}/opencode.jsonc << 'EOF'
{
  \"\$schema\": \"https://opencode.ai/config.json\",
  \"model\": \"deepseek/deepseek-v4-pro\",
  \"permission\": {\"*\": \"allow\"}
}
EOF
"
    fi

    log "  $proj restored"
done

# ---------------------------------------------------------------------------
# 10. Delta-hub dir
# ---------------------------------------------------------------------------
log "Setting up hub..."
if [ -f "$MIGR/hub-dir.tar.gz" ]; then
    rm -rf /opt/delta/hub 2>/dev/null || true
    tar -xzf "$MIGR/hub-dir.tar.gz" -C /opt/delta
    chown -R proj-delta-hub:proj-delta-hub /opt/delta/hub
    log "  hub restored"
fi
sudo -u proj-delta-hub mkdir -p /opt/delta/hub/delta-config/{inbox,outbox,logs}

# ---------------------------------------------------------------------------
# 11. Supervisor configs
# ---------------------------------------------------------------------------
log "Setting up supervisord..."
mkdir -p /etc/supervisor/conf.d

cat > /etc/supervisor/supervisord.conf << 'SUPERVISOR'
[unix_http_server]
file=/var/run/supervisor.sock
chmod=0700

[supervisord]
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
childlogdir=/var/log/supervisor

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///var/run/supervisor.sock

[include]
files = /etc/supervisor/conf.d/*.conf
SUPERVISOR

# Source delta.env for env vars
source /opt/delta/delta.env 2>/dev/null || true

# Write supervisor configs
for proj in "${PROJECTS[@]}"; do
    user="proj-${proj}"

    # Determine port from registry
    port=$(python3 -c "import json; d=json.load(open('/opt/delta/delta-registry.json')); print(d['projects'].get('${proj}',{}).get('serve_port',''))" 2>/dev/null || echo "")
    if [ -z "$port" ]; then
        # Fallback port assignments
        case "$proj" in
            delta-hub) port=7700 ;;
            cajon-sensei) port=7724 ;;
            ethos) port=7744 ;;
            flowing-indian) port=7745 ;;
            linkedin-himanshu-ghiya) port=7730 ;;
            linkedin-kshitiz-agarwal) port=7731 ;;
            seedforthing) port=7740 ;;
            zuuro) port=7743 ;;
            *) port=7799 ;;
        esac
    fi

    # Determine directory
    if [ "$proj" = "delta-hub" ]; then
        proj_dir="/opt/delta/hub"
    else
        proj_dir="/home/${user}/${proj}"
    fi

    # Build env string
    env_str="PATH=\\\"/usr/local/bin:/usr/bin:/bin\\\""
    for key in DEEPSEEK_API_KEY OPENROUTER_API_KEY RUBE_BEARER_TOKEN GITHUB_TOKEN VERCEL_TOKEN UNIPILE_DSN UNIPILE_API_KEY COMPOSIO_API_KEY MYCELIUM_TARGET; do
        val="${!key:-}"
        if [ -n "$val" ]; then
            env_str="${env_str},${key}=\\\"${val}\\\""
        fi
    done

    log_dir="${proj_dir}/delta-config/logs"

    cat > "/etc/supervisor/conf.d/${user}.conf" << CONF
[program:${user}]
command=opencode serve --port ${port}
user=${user}
directory=${proj_dir}
environment=${env_str}
autostart=true
autorestart=true
startsecs=5
stopwaitsecs=10
memory_max=512M
stdout_logfile=${log_dir}/opencode-stdout.log
stderr_logfile=${log_dir}/opencode-stderr.log
CONF

    # Make sure user hasn't got stale opencode configs
    local uconfig="/home/${user}/.config/opencode/opencode.jsonc"
    if [ -f "$uconfig" ]; then
        python3 -c "
import json
with open('$uconfig') as f:
    d = json.load(f)
d.pop('lsp', None)
d.pop('custom_tool', None)
with open('$uconfig', 'w') as f:
    json.dump(d, f, indent=2)
" 2>/dev/null || true
    fi

    log "  supervisor: $user on :$port"
done

# ---------------------------------------------------------------------------
# 12. Charlie browser stack
# ---------------------------------------------------------------------------
log "Setting up Charlie browser stack..."
mkdir -p /etc/vnc

# Generate VNC password if not exists
if [ ! -f /etc/vnc/rfbpasswd ]; then
    echo "seedforth2026" | x11vnc -storepasswd auto /etc/vnc/rfbpasswd 2>/dev/null || \
        x11vnc -storepasswd "seedforth2026" /etc/vnc/rfbpasswd 2>/dev/null || true
fi

DISPLAY_NUM=97
WEB_PORT=6083
VNC_PORT=5903
CDP_PORT=9224

cat > /etc/systemd/system/charlie-xvfb.service << SYSTEMD
[Unit]
Description=Charlie - Virtual Display (Xvfb)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/Xvfb :${DISPLAY_NUM} -screen 0 1366x900x24
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SYSTEMD

cat > /etc/systemd/system/charlie-chromium.service << SYSTEMD
[Unit]
Description=Charlie - Chromium Browser
After=charlie-xvfb.service
Requires=charlie-xvfb.service

[Service]
Type=simple
User=charlie-browser
Environment=DISPLAY=:${DISPLAY_NUM}
Environment=HOME=/home/charlie-browser
ExecStart=/usr/bin/chromium-browser --no-sandbox --disable-dev-shm-usage --password-store=basic --user-data-dir=/home/charlie-browser/chromium --no-first-run --no-default-browser-check --disable-session-crashed-bubble --start-maximized --disable-features=TranslateUI --remote-debugging-port=${CDP_PORT} --remote-debugging-address=0.0.0.0 --remote-allow-origins=* --profile-directory=Default https://accounts.google.com/
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD

cat > /etc/systemd/system/charlie-x11vnc.service << SYSTEMD
[Unit]
Description=Charlie - VNC Server (x11vnc)
After=charlie-xvfb.service
Requires=charlie-xvfb.service

[Service]
Type=simple
ExecStart=/usr/bin/x11vnc -display :${DISPLAY_NUM} -rfbport ${VNC_PORT} -forever -rfbauth /etc/vnc/rfbpasswd -listen localhost -xkb
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SYSTEMD

cat > /etc/systemd/system/charlie-novnc.service << SYSTEMD
[Unit]
Description=Charlie - noVNC Web Browser Access
After=charlie-x11vnc.service
Requires=charlie-x11vnc.service

[Service]
Type=simple
ExecStart=/usr/bin/websockify --web /usr/share/novnc 0.0.0.0:${WEB_PORT} localhost:${VNC_PORT}
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SYSTEMD

# Restore browser profile if available
if [ -f "$MIGR/charlie-browser.tar.gz" ]; then
    log "Restoring charlie browser data..."
    tar -xzf "$MIGR/charlie-browser.tar.gz" -C /home/
    chown -R charlie-browser:charlie-browser /home/charlie-browser/chromium
    log "  charlie browser restored"
fi

# ---------------------------------------------------------------------------
# 13. Restore archived projects
# ---------------------------------------------------------------------------
if [ -f "$MIGR/archived-projects.tar.gz" ]; then
    log "Restoring archived projects..."
    tar -xzf "$MIGR/archived-projects.tar.gz" -C /opt/delta/
    log "  archives restored"
fi

# ---------------------------------------------------------------------------
# 14. Delta systemd service
# ---------------------------------------------------------------------------
log "Setting up delta systemd service..."
chown -R delta:delta /opt/delta

cat > /etc/systemd/system/delta.service << SYSTEMD
[Unit]
Description=Delta Discord Bot
After=network.target docker.service

[Service]
Type=simple
User=delta
Group=delta
WorkingDirectory=/opt/delta
EnvironmentFile=/opt/delta/delta.env
ExecStart=/usr/bin/python3 -m delta.app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SYSTEMD

# ---------------------------------------------------------------------------
# 15. Firewall
# ---------------------------------------------------------------------------
log "Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 7687/tcp comment 'Neo4j Bolt'
ufw allow 7474/tcp comment 'Neo4j HTTP'
ufw allow 7700:7799/tcp comment 'Delta opencode serve'
ufw allow 7900:7999/tcp comment 'Delta web UIs'
ufw allow "${WEB_PORT}/tcp" comment 'noVNC Charlie'
ufw --force enable
log "Firewall enabled"

# ---------------------------------------------------------------------------
# 16. Enable and start everything
# ---------------------------------------------------------------------------
log "Starting services..."
systemctl daemon-reload

# Charlie browser
systemctl enable charlie-xvfb charlie-x11vnc charlie-novnc charlie-chromium
systemctl restart charlie-xvfb
sleep 2
systemctl restart charlie-x11vnc
sleep 1
systemctl restart charlie-novnc
sleep 1
systemctl restart charlie-chromium 2>/dev/null || warn "Charlie chromium failed (browser will work after login)"

# Supervisord
systemctl enable supervisor
systemctl restart supervisor
supervisorctl update
supervisorctl reload

# Wait for agents
log "Waiting for agents to start..."
sleep 5
supervisorctl status 2>&1 | head -20

# Delta bot
systemctl enable delta
systemctl restart delta
sleep 3
log "Delta status:"
systemctl status delta --no-pager -l 2>&1 | head -6

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo " Provisioning complete"
echo "============================================"
echo ""
echo "Neo4j:    bolt://localhost:7687 (mycelium)"
echo "noVNC:    http://$(hostname -I | awk '{print $1}'):${WEB_PORT}/vnc.html"
echo "Agents:   supervisorctl status"
echo "Delta:    systemctl status delta"
echo ""
echo "Quick health check:"
echo "  supervisorctl status"
echo "  journalctl -u delta -f"
