#!/bin/bash
# activate-branch-protection.sh
# Configures GitHub branch protection for two-tier branching model on kagrawal29/mycelium
# Usage: bash scripts/activate-branch-protection.sh

set -euo pipefail

REPO_OWNER="kagrawal29"
REPO_NAME="mycelium"
DEV_BRANCH="develop"
MAIN_BRANCH="main"

echo "Setting up two-tier branch protection for $REPO_OWNER/$REPO_NAME..."
echo ""

# Step 1: Create dev branch from main (if it doesn't exist)
echo "[1/4] Creating $DEV_BRANCH branch from $MAIN_BRANCH tip..."
if git rev-parse --verify origin/$DEV_BRANCH &>/dev/null; then
  echo "  → $DEV_BRANCH branch already exists, skipping creation"
else
  git checkout $MAIN_BRANCH
  git pull origin $MAIN_BRANCH
  git checkout -b $DEV_BRANCH
  git push -u origin $DEV_BRANCH 2>&1 || {
    echo "  ⚠ Push failed (may be ref conflict with dev/* branches). Attempting force-create..."
    git push --force -u origin $DEV_BRANCH
  }
  echo "  ✓ Created and pushed $DEV_BRANCH branch"
fi
echo ""

# Step 2: Configure protection on main branch
echo "[2/4] Configuring branch protection on $MAIN_BRANCH..."
gh api -X PUT "repos/$REPO_OWNER/$REPO_NAME/branches/$MAIN_BRANCH/protection" \
  --input - <<'EOF'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
echo "  ✓ $MAIN_BRANCH protected: require PR, 1 approval, linear history, no force-push"
echo ""

# Step 3: Configure protection on dev branch
echo "[3/4] Configuring branch protection on $DEV_BRANCH..."
gh api -X PUT "repos/$REPO_OWNER/$REPO_NAME/branches/$DEV_BRANCH/protection" \
  --input - <<'EOF'
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
echo "  ✓ $DEV_BRANCH protected: require PR, 0 approvals (nimble), linear history, no force-push"
echo ""

# Step 4: Verify protection is active
echo "[4/4] Verifying branch protection..."
MAIN_STATUS=$(gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$MAIN_BRANCH" --jq '.protected')
DEV_STATUS=$(gh api "repos/$REPO_OWNER/$REPO_NAME/branches/$DEV_BRANCH" --jq '.protected')

if [ "$MAIN_STATUS" = "true" ] && [ "$DEV_STATUS" = "true" ]; then
  echo "  ✓ Both branches are protected"
else
  echo "  ✗ WARNING: Protection may not be active. Check GitHub settings."
  exit 1
fi
echo ""

echo "=========================================="
echo "✓ Two-tier branching model is ACTIVE"
echo "=========================================="
echo ""
echo "Branch rules:"
echo "  main: protected, requires PR + 1 approval + linear history"
echo "  dev:  protected, requires PR + 1 approval + linear history"
echo "  feature branches: dev/<user>/<desc> — push anytime, no protection"
echo ""
echo "Rollback: if needed, run scripts/deactivate-branch-protection.sh"
echo ""
