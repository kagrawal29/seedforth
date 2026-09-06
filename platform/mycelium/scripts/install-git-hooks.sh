#!/usr/bin/env bash
# install-git-hooks.sh
# Installs pre-push hook to prevent direct pushes to main without PR
# Usage: bash scripts/install-git-hooks.sh

set -e

HOOK="$(git rev-parse --git-dir)/hooks/pre-push"

cat > "$HOOK" <<'HOOK_EOF'
#!/usr/bin/env bash
protected="main"
while read local_ref local_sha remote_ref remote_sha; do
  if [[ "$remote_ref" == "refs/heads/$protected" ]]; then
    # Allow only if last commit is a merge commit from GitHub UI (2+ parents, "Merge #" message)
    parents=$(git rev-list --parents -n 1 "$local_sha" | awk '{print NF-1}')
    msg=$(git log -1 --pretty=%s "$local_sha")
    if [[ "$parents" -ge 2 ]] && echo "$msg" | grep -qE '^Merge (pull request|#)'; then
      exit 0
    fi
    echo "✗ Direct push to main blocked by pre-push hook."
    echo "  Rule: dev/<user>/<desc> → PR → dev → PR → main"
    echo "  Override (emergencies only): git push --no-verify"
    exit 1
  fi
done
exit 0
HOOK_EOF

chmod +x "$HOOK"
echo "✓ pre-push hook installed at $HOOK"
