#!/bin/bash
# Git sync -- commit and push all active Delta project work.
# Run periodically via systemd timer or cron.
# Safe to run frequently: no-ops if nothing changed.

REGISTRY="/opt/delta/delta-registry.json"
GITHUB_TOKEN="${GITHUB_TOKEN:-$(sudo -u delta gh auth token 2>/dev/null)}"

if [ -z "$GITHUB_TOKEN" ]; then
    echo "No GITHUB_TOKEN available"
    exit 1
fi

# Get all project dirs from registry
projects=$(python3 -c "
import json
d = json.load(open('$REGISTRY'))
for k,v in d['projects'].items():
    print(v.get('project_dir',''))
" 2>/dev/null)

synced=0
failed=0

for dir in $projects; do
    [ -d "$dir/.git" ] || continue

    name=$(basename "$dir")
    user="proj-$name"

    # Check for changes
    changes=$(sudo -u "$user" git -C "$dir" status --porcelain 2>/dev/null | wc -l)
    [ "$changes" -eq 0 ] && continue

    echo "[$name] $changes uncommitted changes"

    # Commit
    sudo -u "$user" git -C "$dir" add -A 2>/dev/null
    sudo -u "$user" git -C "$dir" commit -m "auto: sync project work" 2>/dev/null

    # Push (set remote if missing)
    has_remote=$(sudo -u "$user" git -C "$dir" remote get-url origin 2>/dev/null)
    if [ -z "$has_remote" ]; then
        url="https://x-access-token:${GITHUB_TOKEN}@github.com/Seedforth/${name}.git"
        sudo -u "$user" git -C "$dir" remote add origin "$url"
    fi

    branch=$(cd "$dir" && sudo -u "$user" git rev-parse --abbrev-ref HEAD 2>/dev/null)
    if sudo -u "$user" git -C "$dir" push -u origin "$branch" 2>/dev/null; then
        echo "[$name] pushed"
        synced=$((synced + 1))
    else
        echo "[$name] push failed"
        failed=$((failed + 1))
    fi
done

echo "Git sync complete: $synced pushed, $failed failed"
