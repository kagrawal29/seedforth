#!/bin/bash
# install-species-hook.sh — install the post-commit hook that auto-verifies species.
# Runs on the server where the canonical git repo lives.

set -e

REPO="$(cd "$(dirname "$0")/.." && pwd)"
HOOK_PATH="$REPO/.git/hooks/post-commit"

cat > "$HOOK_PATH" << 'HOOK'
#!/bin/bash
# Auto-verify species on commit. Runs for any commit on a species/* branch.
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" == species/* ]]; then
    DNA="${BRANCH#species/}"
    REPO_ROOT=$(git rev-parse --show-toplevel)
    echo ""
    echo "┌────────────────────────────────────────────────────────┐"
    echo "│  POST-COMMIT HOOK: verifying species/$DNA"
    echo "└────────────────────────────────────────────────────────┘"
    bash "$REPO_ROOT/scripts/verify-species-local.sh" "$DNA" || {
        echo ""
        echo "✗ VERIFICATION FAILED — this species is not trustless"
        exit 1
    }
fi
HOOK
chmod +x "$HOOK_PATH"

echo "✓ post-commit hook installed at $HOOK_PATH"
echo "  → any commit on a species/* branch will auto-verify"
