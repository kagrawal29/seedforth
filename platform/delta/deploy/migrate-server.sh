#!/bin/bash
# Phase 3+4+5: Server migration script
# Run on delta-server (143.110.226.214) as root
set -euo pipefail

echo "=== Phase 3: Clone delta repo and migrate state ==="

# Clone the new delta repo
if [ -d /opt/delta ]; then
    echo "/opt/delta already exists, pulling latest..."
    cd /opt/delta && git pull
else
    echo "Cloning kagrawal29/delta to /opt/delta..."
    git clone https://github.com/kagrawal29/delta.git /opt/delta
fi

# Copy runtime state from old location
echo "Copying runtime state..."
cp /opt/tetrahedron/delta.env /opt/delta/ 2>/dev/null || echo "  delta.env not found, skipping"
cp /opt/tetrahedron/delta-registry.json /opt/delta/ 2>/dev/null || echo "  registry not found, skipping"
cp /opt/tetrahedron/delta-last-fired.json /opt/delta/ 2>/dev/null || echo "  last-fired not found, skipping"
if [ -d /opt/tetrahedron/hub ]; then
    cp -r /opt/tetrahedron/hub /opt/delta/hub
    echo "  Copied hub directory"
else
    echo "  hub directory not found, skipping"
fi

# Install deps
echo "Installing Python dependencies..."
cd /opt/delta
pip3 install -r requirements.txt

# Install and restart systemd service
echo "Installing systemd service..."
cp deploy/delta.service /etc/systemd/system/delta.service
systemctl daemon-reload
systemctl restart delta

echo ""
echo "=== Phase 3 complete. Checking status... ==="
systemctl status delta --no-pager || true

echo ""
echo "=== Phase 4: ttyd server prep ==="

# Install ttyd
apt install -y ttyd 2>/dev/null || echo "ttyd not in apt, may need manual install"

# Create project-attach helper
cat > /usr/local/bin/project-attach << 'SCRIPT'
#!/bin/bash
SESSION="$1"
[ -z "$SESSION" ] && echo "Usage: project-attach <session>" && exit 1
tmux has-session -t "$SESSION" 2>/dev/null && exec tmux attach -t "$SESSION"
echo "Session '$SESSION' not found. Waiting..."
sleep 5
SCRIPT
chmod +x /usr/local/bin/project-attach

# Open firewall for ttyd ports
ufw allow 7700:7799/tcp
echo "Firewall opened for ports 7700-7799"

echo ""
echo "=== Phase 5: Cleanup ==="

# Pull updated tetrahedron (with delta files removed)
cd /opt/tetrahedron && git pull
echo "Updated /opt/tetrahedron"

# Remove old delta files from tetrahedron (they were git-tracked, git pull handles it)
echo "Old delta files removed by git pull"

echo ""
echo "=== Migration complete ==="
echo "Verify:"
echo "  systemctl status delta"
echo "  # Test Discord bot responds"
echo "  # Check observatory reads from /opt/delta paths"
