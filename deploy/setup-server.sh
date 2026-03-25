#!/bin/bash
# Delta server setup script
# Run as root on a fresh Ubuntu 24.04 droplet
set -euo pipefail

echo "=== Delta Server Setup ==="

# 1. System packages
echo "[1/6] Installing system packages..."
apt update && apt install -y python3-pip python3-venv tmux git curl ufw nodejs npm

# 2. Claude Code CLI
echo "[2/6] Installing Claude Code CLI..."
npm install -g @anthropic-ai/claude-code

# 3. Firewall -- SSH only
echo "[3/6] Configuring firewall..."
ufw allow OpenSSH
ufw --force enable

# 4. Clone repo
echo "[4/6] Cloning delta..."
if [ -d /opt/delta ]; then
    echo "  /opt/delta exists, pulling latest..."
    cd /opt/delta && git pull
else
    git clone https://github.com/kagrawal29/delta.git /opt/delta
fi

# 5. Python deps
echo "[5/6] Installing Python dependencies..."
cd /opt/delta
pip3 install -r requirements.txt

# 6. Systemd service
echo "[6/6] Installing systemd service..."
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
