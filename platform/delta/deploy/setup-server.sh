#!/bin/bash
# Delta server setup script v3
# Run as root on a fresh Ubuntu 24.04 droplet
set -euo pipefail

echo "=== Delta Server Setup v3 ==="

# 1. System packages
echo "[1/9] Installing system packages..."
apt update && apt install -y python3-pip python3-venv tmux git curl ufw supervisor

# 2. Node.js 20 from NodeSource
echo "[2/9] Installing Node.js 20 from NodeSource..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# 3. opencode CLI
echo "[3/9] Installing opencode CLI..."
npm install -g opencode-ai@1.18.4

# 4. GitHub CLI
echo "[4/9] Installing GitHub CLI..."
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt-get update && apt-get install -y gh

# 5. Mycelium CLI
echo "[5/9] Installing mycelium CLI..."
gh release download --repo kagrawal29/mycelium -p "*linux*" -O /usr/local/bin/mycelium
chmod +x /usr/local/bin/mycelium

# 6. Firewall -- SSH only
echo "[6/9] Configuring firewall..."
ufw allow OpenSSH
ufw --force enable

# 7. Clone repo
echo "[7/9] Cloning delta..."
if [ -d /opt/delta ]; then
    echo "  /opt/delta exists, pulling latest..."
    cd /opt/delta && git pull
else
    git clone https://github.com/kagrawal29/delta.git /opt/delta
fi

# 8. Python deps
echo "[8/9] Installing Python dependencies..."
cd /opt/delta
pip3 install -r requirements.txt --break-system-packages

# 9. Services, logrotate, opencode config
echo "[9/9] Installing systemd service, logrotate, opencode config..."

cp deploy/delta.service /etc/systemd/system/delta.service
systemctl daemon-reload
systemctl enable delta
systemctl enable supervisor

cat > /etc/logrotate.d/delta-agents << 'LOGROTATE'
/opt/delta/*/logs/*.log
/opt/delta/*/delta-config/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
LOGROTATE

mkdir -p /root/.config/opencode
cat > /root/.config/opencode/opencode.jsonc << 'OPENCODE'
{
    "model": "deepseek/deepseek-v4-pro",
    "env": {
        "DEEPSEEK_API_KEY": "${DEEPSEEK_API_KEY}",
        "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}"
    }
}
OPENCODE

echo ""
echo "=== Setup complete ==="
echo ""
echo "Remaining manual steps:"
echo "  1. Create /opt/delta/delta.env (see deploy/delta.env.example)"
echo "  2. Configure gh auth: gh auth login or set GITHUB_TOKEN in delta.env"
echo "  3. Run 'systemctl start delta' to launch the Discord bot"
echo "  4. Run 'systemctl start supervisor' for agent process management"
echo ""
