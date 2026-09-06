#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Qubit-Capital/maverick-meta.git"
REPO_DIR="/workspace/maverick-meta"
BIN_DIR="/workspace/bin"
LOG="/var/log/cron.log"
MODE="${MODE:-production}"  # "production" or "test"
BRANCH="${BRANCH:-main}"    # which branch to run — "main" for production, branch name for testing

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] Starting maverick-meta intelligence system (mode: $MODE)"

# --- Validate required env vars ---
missing=()
for var in CLAUDE_CODE_OAUTH_TOKEN CC_LANGSMITH_API_KEY GH_TOKEN; do
    if [ -z "${!var:-}" ]; then
        missing+=("$var")
    fi
done
if [ ${#missing[@]} -gt 0 ]; then
    echo "ERROR: Missing required environment variables: ${missing[*]}"
    exit 1
fi

# --- Create runtime dirs ---
mkdir -p "$BIN_DIR" /workspace/status

# --- Configure git for maverick user ---
su - maverick -c "git config --global user.name 'maverick-meta-bot'"
su - maverick -c "git config --global user.email 'meta-bot@qubit.capital'"
su - maverick -c "git config --global credential.helper store"

# Store GH_TOKEN for git push and gh CLI (as maverick user)
echo "https://x-access-token:${GH_TOKEN}@github.com" > /home/maverick/.git-credentials
chown maverick:maverick /home/maverick/.git-credentials
echo "${GH_TOKEN}" | su - maverick -c "gh auth login --with-token 2>/dev/null || true"

# --- Ensure maverick owns workspace ---
chown -R maverick:maverick /workspace

# --- Fix git safe.directory for cross-user access ---
git config --global --add safe.directory "$REPO_DIR"
su - maverick -c "git config --global --add safe.directory $REPO_DIR"

# --- Clone or pull the repo (as maverick user) ---
if [ -d "$REPO_DIR/.git" ]; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] Repo exists, pulling latest ($BRANCH)"
    if su - maverick -c "cd $REPO_DIR && git remote | grep -q origin"; then
        su - maverick -c "cd $REPO_DIR && git fetch origin && git checkout $BRANCH && git pull --rebase || git pull --no-rebase"
    else
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] No remote 'origin' — skipping pull (test mode restart)"
    fi
else
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] Cloning repo (branch: $BRANCH)"
    su - maverick -c "git clone -b $BRANCH $REPO_URL $REPO_DIR"
fi

# --- Apply mode-specific safety ---
if [ "$MODE" = "test" ]; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] TEST MODE: sandboxing — no remote, no hooks, no distribution"
    su - maverick -c "cd $REPO_DIR && git remote remove origin 2>/dev/null || true"
    rm -f "$REPO_DIR/.claude/hooks/auto-sync.sh" 2>/dev/null
    # Disable distribute in test mode by creating a no-op wrapper
    cat > "$REPO_DIR/agents/distribute.py" << 'NOOP'
#!/usr/bin/env python3
"""distribute.py — DISABLED in test mode. No changes pushed."""
print("[distribute] TEST MODE — skipped. No changes pushed to repos.")
NOOP
    chown maverick:maverick "$REPO_DIR/agents/distribute.py"
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] Sandbox active: remote removed, hooks disabled, distribute is no-op"
else
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] PRODUCTION MODE: full pipeline with distribution enabled"
fi

# --- Write the job runner script ---
cat > "$BIN_DIR/run-job.sh" << 'JOBSCRIPT'
#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/workspace/maverick-meta"
JOB="$1"
TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
STATUS_DIR="/workspace/status"

echo ""
echo "============================================================"
echo "  [$TIMESTAMP] Starting job: $JOB"
echo "============================================================"

# Pull latest before each run
cd "$REPO_DIR"
git pull --rebase 2>/dev/null || git pull --no-rebase 2>/dev/null || true

EXIT_CODE=0
case "$JOB" in
    synthesis)
        python3 agents/run-graph-pipeline.py || EXIT_CODE=$?
        ;;
    entry-feedback)
        python3 agents/run-feedback.py || EXIT_CODE=$?
        ;;
    skill-feedback)
        python3 agents/run-skill-feedback.py || EXIT_CODE=$?
        ;;
    full-cycle)
        python3 agents/run-cycle.py || EXIT_CODE=$?
        ;;
    *)
        echo "ERROR: Unknown job '$JOB'"
        exit 1
        ;;
esac
END_TIMESTAMP=$(date -u '+%Y-%m-%d %H:%M:%S UTC')

if [ $EXIT_CODE -eq 0 ]; then
    echo "$END_TIMESTAMP" > "$STATUS_DIR/${JOB}.last-success"
    echo "[$END_TIMESTAMP] Job $JOB completed successfully"
else
    echo "$END_TIMESTAMP exit=$EXIT_CODE" > "$STATUS_DIR/${JOB}.last-failure"
    echo "[$END_TIMESTAMP] Job $JOB FAILED (exit code $EXIT_CODE)"
fi
JOBSCRIPT
chmod +x "$BIN_DIR/run-job.sh"

# --- Export env vars for cron ---
# Cron runs in a clean environment — write env vars to a file that the wrapper sources
printenv | grep -E '^(CLAUDE_CODE_OAUTH_TOKEN|ANTHROPIC_API_KEY|CC_LANGSMITH_API_KEY|GH_TOKEN|FALKORDB_HOST|FALKORDB_PORT|PULSE_HOST|PULSE_PORT|PATH|LANG)=' \
    > "$BIN_DIR/env.sh"
echo "export HOME=/home/maverick" >> "$BIN_DIR/env.sh"
sed -i 's/^/export /' "$BIN_DIR/env.sh"
chown -R maverick:maverick "$BIN_DIR" /workspace/status

# Wrapper that sources env before running the job
cat > "$BIN_DIR/run-job-wrapper.sh" << 'WRAPPER'
#!/usr/bin/env bash
source /workspace/bin/env.sh
exec /workspace/bin/run-job.sh "$@"
WRAPPER
chmod +x "$BIN_DIR/run-job-wrapper.sh"

# --- Reload crontab (paths already correct in the file) ---
crontab /etc/cron.d/maverick-cron

# --- Seed graph if FalkorDB is available ---
if [ -n "${FALKORDB_HOST:-}" ]; then
    echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] FalkorDB configured at $FALKORDB_HOST:${FALKORDB_PORT:-6379}"
    # Wait for FalkorDB to be ready (up to 10s)
    for i in $(seq 1 10); do
        if su - maverick -c "source $BIN_DIR/env.sh && python3 -c \"import redis; redis.Redis(host='${FALKORDB_HOST}', port=${FALKORDB_PORT:-6379}).ping()\"" 2>/dev/null; then
            echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] FalkorDB is reachable"
            # Seed graph if not already seeded
            su - maverick -c "source $BIN_DIR/env.sh && cd $REPO_DIR && python3 scripts/graph-sync.py" 2>/dev/null || true
            break
        fi
        sleep 1
    done
fi

echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] Setup complete. Starting cron daemon."
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] Cron schedule:"
crontab -l | grep -v '^#' | grep -v '^$'

# Start cron daemon, tail the log to keep container alive
service cron start
echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC') [entrypoint] Cron daemon started. Tailing log."
exec tail -f "$LOG"
