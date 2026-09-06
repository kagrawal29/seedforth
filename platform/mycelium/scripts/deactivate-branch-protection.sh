#!/bin/bash
# deactivate-branch-protection.sh
# Removes GitHub branch protection from main and dev branches
# Usage: bash scripts/deactivate-branch-protection.sh

set -euo pipefail

REPO_OWNER="kagrawal29"
REPO_NAME="mycelium"
DEV_BRANCH="dev"
MAIN_BRANCH="main"

echo "Removing branch protection from $REPO_OWNER/$REPO_NAME..."
echo ""

read -p "Are you sure you want to remove branch protection? (yes/no) " -r
echo
if [[ ! $REPLY =~ ^yes$ ]]; then
  echo "Cancelled."
  exit 0
fi

echo "[1/2] Removing protection from $MAIN_BRANCH..."
gh api -X DELETE "repos/$REPO_OWNER/$REPO_NAME/branches/$MAIN_BRANCH/protection"
echo "  ✓ $MAIN_BRANCH protection removed"
echo ""

echo "[2/2] Removing protection from $DEV_BRANCH..."
gh api -X DELETE "repos/$REPO_OWNER/$REPO_NAME/branches/$DEV_BRANCH/protection"
echo "  ✓ $DEV_BRANCH protection removed"
echo ""

echo "=========================================="
echo "✓ Branch protection DISABLED"
echo "=========================================="
echo ""
echo "To re-enable, run: bash scripts/activate-branch-protection.sh"
echo ""
