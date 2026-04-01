#!/bin/bash
# Delta server setup script
# Run as root on a fresh Ubuntu 24.04 droplet
set -euo pipefail

echo "=== Delta Server Setup ==="

# 1. System packages
echo "[1/6] Installing system packages..."
apt update && apt install -y python3-pip python3-venv tmux git curl ufw nodejs npm

# 2. Claude Code CLI
echo "[2/7] Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# 3. GitHub CLI
echo "[3/7] Installing GitHub CLI..."
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg 2>/dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null
apt-get update && apt-get install -y gh

# 4. Firewall -- SSH only
echo "[4/7] Configuring firewall..."
ufw allow OpenSSH
ufw --force enable

# 5. Clone repo
echo "[5/7] Cloning delta..."
if [ -d /opt/delta ]; then
    echo "  /opt/delta exists, pulling latest..."
    cd /opt/delta && git pull
else
    git clone https://github.com/kagrawal29/delta.git /opt/delta
fi

# 6. Python deps
echo "[6/7] Installing Python dependencies..."
cd /opt/delta
pip3 install -r requirements.txt

# 7. Systemd service
echo "[7/7] Installing systemd service..."
cp deploy/delta.service /etc/systemd/system/delta.service
systemctl daemon-reload
systemctl enable delta

echo ""
echo "=== Setup complete ==="
echo ""
echo "Remaining manual steps:"
echo "  1. Create /opt/delta/delta.env with DISCORD_TOKEN"
echo "  2. Run 'claude' once as root to authenticate with Max subscription"
echo "  3. Run 'systemctl start delta' to launch"
echo ""
