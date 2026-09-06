#!/usr/bin/env bash
# Health check for the maverick-meta intelligence system container.
# Usage:
#   ./healthcheck.sh          Full status report
#   ./healthcheck.sh --quiet  Exit code only (for Docker HEALTHCHECK)

set -euo pipefail

STATUS_DIR="/workspace/status"
QUIET="${1:-}"

# --- Helper: time since file was modified ---
age_seconds() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "-1"
        return
    fi
    local now
    now=$(date +%s)
    local modified
    modified=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null)
    echo $(( now - modified ))
}

format_age() {
    local secs="$1"
    if [ "$secs" -lt 0 ]; then
        echo "never"
        return
    fi
    if [ "$secs" -lt 60 ]; then
        echo "${secs}s ago"
    elif [ "$secs" -lt 3600 ]; then
        echo "$(( secs / 60 ))m ago"
    elif [ "$secs" -lt 86400 ]; then
        echo "$(( secs / 3600 ))h ago"
    else
        echo "$(( secs / 86400 ))d ago"
    fi
}

# --- Check cron is running ---
CRON_OK=true
if ! pgrep -x cron > /dev/null 2>&1; then
    CRON_OK=false
fi

# --- Check last run times ---
JOBS=("synthesis" "entry-feedback" "skill-feedback")
ANY_FAILURE=false
HEALTHY=true

if [ "$QUIET" = "--quiet" ]; then
    # Docker healthcheck mode: just check cron is running and no recent failures
    if [ "$CRON_OK" = false ]; then
        exit 1
    fi
    for job in "${JOBS[@]}"; do
        fail_age=$(age_seconds "$STATUS_DIR/${job}.last-failure")
        success_age=$(age_seconds "$STATUS_DIR/${job}.last-success")
        # Unhealthy if failure is more recent than success
        if [ "$fail_age" -ge 0 ] && { [ "$success_age" -lt 0 ] || [ "$fail_age" -lt "$success_age" ]; }; then
            exit 1
        fi
    done
    exit 0
fi

# --- Full report ---
echo "=============================="
echo "  Maverick Meta — System Status"
echo "=============================="
echo ""

# Cron
if [ "$CRON_OK" = true ]; then
    echo "Cron daemon:  RUNNING"
else
    echo "Cron daemon:  NOT RUNNING"
    HEALTHY=false
fi

echo ""
echo "Job Status:"
echo "-------------------------------------------"
printf "%-20s %-18s %-18s\n" "Job" "Last Success" "Last Failure"
echo "-------------------------------------------"

for job in "${JOBS[@]}"; do
    success_age=$(age_seconds "$STATUS_DIR/${job}.last-success")
    failure_age=$(age_seconds "$STATUS_DIR/${job}.last-failure")

    success_str=$(format_age "$success_age")
    failure_str=$(format_age "$failure_age")

    # Mark if failure is more recent than success
    marker=""
    if [ "$failure_age" -ge 0 ] && { [ "$success_age" -lt 0 ] || [ "$failure_age" -lt "$success_age" ]; }; then
        marker=" <-- FAILING"
        ANY_FAILURE=true
    fi

    printf "%-20s %-18s %-18s%s\n" "$job" "$success_str" "$failure_str" "$marker"
done

echo ""

# Next scheduled runs
echo "Cron Schedule (UTC):"
echo "-------------------------------------------"
crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$' | while read -r line; do
    schedule=$(echo "$line" | awk '{print $1, $2, $3, $4, $5}')
    job=$(echo "$line" | sed -n 's/.*run-job[^ ]* \([^ ]*\).*/\1/p' 2>/dev/null)
    [ -z "$job" ] && job="?"
    printf "  %-15s  %s\n" "$job" "$schedule"
done

echo ""

# Repo state
REPO_DIR="/workspace/maverick-meta"
if [ -d "$REPO_DIR/.git" ]; then
    cd "$REPO_DIR"
    BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    COMMIT=$(git log -1 --format='%h %s' 2>/dev/null || echo "unknown")
    echo "Repo branch:  $BRANCH"
    echo "Last commit:  $COMMIT"
else
    echo "Repo:         NOT CLONED"
    HEALTHY=false
fi

echo ""

# Log tail
if [ -f /var/log/cron.log ]; then
    echo "Recent log (last 10 lines):"
    echo "-------------------------------------------"
    tail -10 /var/log/cron.log
else
    echo "No log file yet."
fi

echo ""
if [ "$HEALTHY" = true ] && [ "$ANY_FAILURE" = false ]; then
    echo "Overall: HEALTHY"
else
    echo "Overall: UNHEALTHY"
fi
