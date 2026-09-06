#!/usr/bin/env bash
# register-webhooks.sh — registers GitHub webhooks on the 5 target repos.
#
# SAFETY:
#   - This script ONLY calls POST /repos/<org>/<repo>/hooks (webhook registration).
#   - It does NOT push commits, modify branches, delete files, or add labels/comments.
#   - Webhook registration is non-destructive: it adds a listener, nothing else.
#
# Prerequisites:
#   - gh CLI authenticated as an org admin of Qubit-Capital
#   - WEBHOOK_URL set to the public HTTPS ingress (Cloudflare Tunnel URL)
#   - WEBHOOK_SECRET_FILE set to /etc/mycelium-ingest/webhook.secret (or pass via env)
#
# DEFERRED: do NOT run this until Cloudflare Tunnel is live and WEBHOOK_URL is stable.
# See docs/ingress-setup.md for tunnel setup steps.

set -euo pipefail

WEBHOOK_URL="${WEBHOOK_URL:-}"
SECRET_FILE="${WEBHOOK_SECRET_FILE:-/etc/mycelium-ingest/webhook.secret}"

if [ -z "${WEBHOOK_URL}" ]; then
    echo "ERROR: WEBHOOK_URL is not set."
    echo "Set it to the public HTTPS URL of the Cloudflare Tunnel, e.g.:"
    echo "  export WEBHOOK_URL=https://mycelium-ingest.yourdomain.workers.dev/github/webhook"
    exit 1
fi

if [ ! -f "${SECRET_FILE}" ]; then
    echo "ERROR: Webhook secret not found at ${SECRET_FILE}"
    echo "Run install-ingest.sh first to generate the secret."
    exit 1
fi

WEBHOOK_SECRET=$(cat "${SECRET_FILE}")

REPOS=(
    "Qubit-Capital/VC-AI-Assoicate"
    "Qubit-Capital/maverick-market-research"
    "Qubit-Capital/maverick-marketing"
    "Qubit-Capital/Maverick-Dev"
    "Qubit-Capital/maverick"
)

EVENTS='["push","pull_request","issues","issue_comment","pull_request_review_comment","release"]'

# --------------------------------------------------
# Test against maverick-marketing first (smallest)
# --------------------------------------------------
TEST_REPO="${1:-}"
if [ -n "${TEST_REPO}" ] && [ "${TEST_REPO}" = "--test" ]; then
    echo "==> Registering test webhook on maverick-marketing only"
    gh api -X POST "/repos/Qubit-Capital/maverick-marketing/hooks" \
        -f "name=web" \
        -F "active=true" \
        -f "config[url]=${WEBHOOK_URL}" \
        -f "config[content_type]=json" \
        -f "config[secret]=${WEBHOOK_SECRET}" \
        -f "config[insecure_ssl]=0" \
        -f "events[]=${EVENTS}" \
        --jq '.id'
    echo "==> Done. Verify delivery in GitHub → Settings → Webhooks → Recent Deliveries."
    echo "    Then run without --test to register all repos."
    exit 0
fi

echo "==> Registering webhooks on ${#REPOS[@]} repos"
for REPO in "${REPOS[@]}"; do
    echo -n "  ${REPO} ... "
    HOOK_ID=$(gh api -X POST "/repos/${REPO}/hooks" \
        -f "name=web" \
        -F "active=true" \
        -f "config[url]=${WEBHOOK_URL}" \
        -f "config[content_type]=json" \
        -f "config[secret]=${WEBHOOK_SECRET}" \
        -f "config[insecure_ssl]=0" \
        -f "events[]=${EVENTS}" \
        --jq '.id' 2>&1)
    echo "hook_id=${HOOK_ID}"
done

echo ""
echo "==> All webhooks registered."
echo "    Verify in GitHub → <org>/<repo> → Settings → Webhooks"
echo "    Check Recent Deliveries to confirm payloads are reaching the service."
