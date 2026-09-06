#!/bin/bash
#
# rotate-team-creds.sh
# Rotate read-only team credentials for Neo4j instances on pulse-server.
#
# Usage:
#   bash scripts/rotate-team-creds.sh [--target {prod|dev|both}] [--dry-run] [--restart-proxy]
#
# Behavior:
#   - Connects to pulse-server via SSH
#   - Generates new 24-char alphanumeric passwords for neo4j user 'team'
#   - Updates both prod (bolt://127.0.0.1:7687) and dev (bolt://127.0.0.1:7688)
#   - Verifies new passwords work with a test connection
#   - Prints new passwords to stdout under a clear banner (once only)
#   - Includes safety checks (1-hour cooldown, SSH verification)
#
# Exit codes:
#   0: Success
#   1: SSH failure, invalid target, cooldown active, or other error
#

set -euo pipefail

# Configuration
TARGET_ENV="both"
DRY_RUN=false
RESTART_PROXY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --target requires a value (prod|dev|both)"
                exit 1
            fi
            TARGET_ENV="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --restart-proxy)
            RESTART_PROXY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: bash scripts/rotate-team-creds.sh [--target {prod|dev|both}] [--dry-run] [--restart-proxy]"
            exit 1
            ;;
    esac
done

# Validate target
case "$TARGET_ENV" in
    prod|dev|both)
        ;;
    *)
        echo "Error: --target must be one of: prod, dev, both"
        exit 1
        ;;
esac

# Helper: print banner
print_banner() {
    echo "========================================"
    echo "NEW TEAM CREDENTIALS BELOW"
    echo "========================================"
}

# Helper: generate random password (24 chars, alphanumeric only)
gen_password() {
    openssl rand -base64 24 | tr -d '/+=' | cut -c1-24
}

# Helper: check cooldown
check_cooldown() {
    local log_file="/root/.mycelium-secrets-rotation-log"

    # If log doesn't exist, no cooldown
    if ! ssh pulse-server "test -f $log_file"; then
        return 0
    fi

    # Read the last rotation timestamp
    local last_rotation
    last_rotation=$(ssh pulse-server "tail -1 $log_file" 2>/dev/null || echo "")

    if [[ -z "$last_rotation" ]]; then
        return 0
    fi

    # Parse the timestamp (format: ISO8601, e.g., 2026-04-18T14:30:45Z)
    local last_epoch
    last_epoch=$(date -d "$last_rotation" +%s 2>/dev/null || echo "0")
    local now_epoch=$(date +%s)
    local elapsed=$((now_epoch - last_epoch))
    local cooldown=3600  # 1 hour in seconds

    if [[ $elapsed -lt $cooldown ]]; then
        echo "Error: Last rotation was $((cooldown - elapsed)) seconds ago. Must wait at least 1 hour between rotations."
        return 1
    fi

    return 0
}

# Helper: rotate single environment
rotate_env() {
    local env=$1        # "prod" or "dev"
    local bolt_port=$2  # 7687 for prod, 7688 for dev
    local new_password=$3

    echo "[*] Rotating $env credentials..."

    # SSH command to run on pulse-server
    local ssh_cmd="
set -euo pipefail

# Read admin creds from /root/.mycelium-secrets
ADMIN_PASS=\$(grep '^NEO4J_ADMIN_PASS=' /root/.mycelium-secrets 2>/dev/null | cut -d= -f2-)
if [[ -z \"\$ADMIN_PASS\" ]]; then
    echo 'Error: NEO4J_ADMIN_PASS not found in /root/.mycelium-secrets'
    exit 1
fi

# Cypher command to set the new password
CYPHER=\"ALTER USER team SET PASSWORD '$new_password' CHANGE NOT REQUIRED;\"

# Run Cypher-shell with admin creds
echo \"\$CYPHER\" | cypher-shell -a bolt://127.0.0.1:$bolt_port -u neo4j -p \"\$ADMIN_PASS\" 2>&1 || {
    echo 'Error: Failed to alter password for $env'
    exit 1
}

# Verify: try a simple query with the new password
echo 'RETURN 1;' | cypher-shell -a bolt://127.0.0.1:$bolt_port -u team -p '$new_password' >/dev/null 2>&1 || {
    echo 'Error: New password verification failed for $env'
    exit 1
}

echo 'Success: $env password rotated and verified'
"

    if [[ "$DRY_RUN" == true ]]; then
        echo "[DRY RUN] Would execute: $ssh_cmd"
        echo "[DRY RUN] New password would be: $new_password"
        return 0
    fi

    # Execute SSH command
    if ! ssh pulse-server "$ssh_cmd"; then
        echo "Error: Failed to rotate $env credentials"
        return 1
    fi
}

# Helper: update team-credentials.env in the local maverick repo
update_credentials_file() {
    local creds_file="$1"
    local prod_pass="$2"
    local dev_pass="$3"

    if [[ ! -f "$creds_file" ]]; then
        echo "Warning: team-credentials.env not found at $creds_file"
        return 0
    fi

    # Use Python for safe TOML-like parsing and update
    python3 - "$creds_file" "$prod_pass" "$dev_pass" <<'PYTHON'
import sys
import re
from datetime import datetime

creds_file = sys.argv[1]
prod_pass = sys.argv[2]
dev_pass = sys.argv[3]

with open(creds_file, 'r') as f:
    content = f.read()

# Update PROD_PASS
content = re.sub(
    r'^MYCELIUM_PROD_PASS=.*$',
    f'MYCELIUM_PROD_PASS={prod_pass}',
    content,
    flags=re.MULTILINE
)

# Update DEV_PASS
content = re.sub(
    r'^MYCELIUM_DEV_PASS=.*$',
    f'MYCELIUM_DEV_PASS={dev_pass}',
    content,
    flags=re.MULTILINE
)

# Update ROTATED_AT timestamp
timestamp = datetime.utcnow().strftime('%Y-%m-%d')
content = re.sub(
    r'^ROTATED_AT=.*$',
    f'ROTATED_AT={timestamp}',
    content,
    flags=re.MULTILINE
)

with open(creds_file, 'w') as f:
    f.write(content)

print("Updated team-credentials.env")
PYTHON
}

# Main flow

echo "[*] Credential rotation for Mycelium Neo4j team access"
echo "[*] Target: $TARGET_ENV"
[[ "$DRY_RUN" == true ]] && echo "[*] DRY RUN MODE"

# Verify SSH access
if ! ssh -o ConnectTimeout=5 pulse-server "echo 'SSH OK'" >/dev/null 2>&1; then
    echo "Error: Cannot SSH to pulse-server. Verify your SSH key and network access."
    exit 1
fi

# Check cooldown
if ! check_cooldown; then
    exit 1
fi

# Generate new passwords
PROD_PASSWORD=$(gen_password)
DEV_PASSWORD=$(gen_password)

echo "[*] Generated new passwords (not displayed until final banner)"

# Rotate prod if requested
if [[ "$TARGET_ENV" == "prod" ]] || [[ "$TARGET_ENV" == "both" ]]; then
    rotate_env "prod" "7687" "$PROD_PASSWORD" || exit 1
fi

# Rotate dev if requested
if [[ "$TARGET_ENV" == "dev" ]] || [[ "$TARGET_ENV" == "both" ]]; then
    rotate_env "dev" "7688" "$DEV_PASSWORD" || exit 1
fi

# Log rotation timestamp (on pulse-server)
if [[ "$DRY_RUN" != true ]]; then
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    ssh pulse-server "echo '$timestamp' >> /root/.mycelium-secrets-rotation-log" 2>/dev/null || true
fi

# Print banner with new passwords
print_banner
if [[ "$TARGET_ENV" == "prod" ]] || [[ "$TARGET_ENV" == "both" ]]; then
    echo "prod: $PROD_PASSWORD"
fi
if [[ "$TARGET_ENV" == "dev" ]] || [[ "$TARGET_ENV" == "both" ]]; then
    echo "dev: $DEV_PASSWORD"
fi
print_banner

# Update team-credentials.env in the repo (if not a dry run)
if [[ "$DRY_RUN" != true ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    MAVERICK_ROOT="$(dirname "$SCRIPT_DIR")"
    CREDS_FILE="$MAVERICK_ROOT/team-credentials.env"

    if [[ "$TARGET_ENV" == "prod" ]] || [[ "$TARGET_ENV" == "both" ]]; then
        # For "both" or "prod", we update the file
        if [[ "$TARGET_ENV" == "both" ]]; then
            update_credentials_file "$CREDS_FILE" "$PROD_PASSWORD" "$DEV_PASSWORD"
        else
            # "prod" only: update just prod, keep dev unchanged
            python3 - "$CREDS_FILE" "$PROD_PASSWORD" <<'PYTHON'
import sys, re
creds_file = sys.argv[1]
prod_pass = sys.argv[2]

with open(creds_file, 'r') as f:
    content = f.read()

content = re.sub(
    r'^MYCELIUM_PROD_PASS=.*$',
    f'MYCELIUM_PROD_PASS={prod_pass}',
    content,
    flags=re.MULTILINE
)

from datetime import datetime
timestamp = datetime.utcnow().strftime('%Y-%m-%d')
content = re.sub(
    r'^ROTATED_AT=.*$',
    f'ROTATED_AT={timestamp}',
    content,
    flags=re.MULTILINE
)

with open(creds_file, 'w') as f:
    f.write(content)
PYTHON
        fi
    else
        # "dev" only
        python3 - "$CREDS_FILE" "$DEV_PASSWORD" <<'PYTHON'
import sys, re
creds_file = sys.argv[1]
dev_pass = sys.argv[2]

with open(creds_file, 'r') as f:
    content = f.read()

content = re.sub(
    r'^MYCELIUM_DEV_PASS=.*$',
    f'MYCELIUM_DEV_PASS={dev_pass}',
    content,
    flags=re.MULTILINE
)

from datetime import datetime
timestamp = datetime.utcnow().strftime('%Y-%m-%d')
content = re.sub(
    r'^ROTATED_AT=.*$',
    f'ROTATED_AT={timestamp}',
    content,
    flags=re.MULTILINE
)

with open(creds_file, 'w') as f:
    f.write(content)
PYTHON
    fi

    echo ""
    echo "[+] team-credentials.env updated. To commit and push:"
    echo ""
    echo "    git add team-credentials.env"
    echo "    git commit -m 'rotate: team readonly creds $(date +%Y-%m-%d)'"
    echo "    git push"
    echo ""
    echo "Teammates' next 'git pull' will pick up the new credentials."
fi

# Restart proxy if requested (usually not necessary)
if [[ "$RESTART_PROXY" == true ]] && [[ "$DRY_RUN" != true ]]; then
    echo "[*] Restarting bolt-proxy services..."
    if [[ "$TARGET_ENV" == "prod" ]] || [[ "$TARGET_ENV" == "both" ]]; then
        ssh pulse-server "sudo systemctl restart bolt-proxy-prod" 2>/dev/null || echo "Warning: Could not restart bolt-proxy-prod"
    fi
    if [[ "$TARGET_ENV" == "dev" ]] || [[ "$TARGET_ENV" == "both" ]]; then
        ssh pulse-server "sudo systemctl restart bolt-proxy-dev" 2>/dev/null || echo "Warning: Could not restart bolt-proxy-dev"
    fi
fi
