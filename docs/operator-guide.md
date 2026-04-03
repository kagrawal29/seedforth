# Delta Operator Guide

Day-to-day operations for running Delta on the SeedForth Discord server.

## Server access

```bash
ssh delta-server              # 143.110.226.214, key auth
```

Delta runs as the `delta` system user. Use `sudo -u delta` for Delta operations.

## Service management

```bash
# Status
systemctl status delta

# Restart (picks up code changes)
systemctl restart delta

# Logs (live)
journalctl -u delta -f

# Recent errors
journalctl -u delta --since "10 min ago" | grep ERROR
```

## Deploy code changes

```bash
cd /opt/delta
sudo -u delta git pull
sudo systemctl restart delta
```

The bot does a full restart: reconnects to Discord, restores active projects, starts hub, resumes watchers. Takes about 5 seconds. Active Claude Code sessions in tmux survive the restart.

## Creating a project

**From Discord (normal flow):**
User says `@Delta new project my-app` or `@Delta create a project for X`. Delta handles provisioning automatically.

**From server (manual):**
```bash
# Check registry
python3 -c "import json; print(json.dumps(json.load(open('/opt/delta/delta-registry.json')), indent=2))" | less
```

## Onboarding a personal agent user

In `#seedforth-onboarding`, an admin posts:
```
@Delta onboard @username -- runs a consulting firm, 3 employees
```

Delta creates `#proj-onboarding-username`, starts the 7-module intake. When complete, the channel archives and the user DMs Delta directly.

## LinkedIn onboarding

User messages in `#linkedin-onboarding`. Delta generates a Unipile auth link. After connecting, Delta creates a LinkedIn project channel for them.

## Checking project health

```bash
# All projects and their status
ssh delta-server "python3 -c \"
import json
d = json.load(open('/opt/delta/delta-registry.json'))
for k,v in d['projects'].items():
    print(f'{k:30s} {v.get(\"status\",\"?\"):12s} type={v.get(\"project_type\",\"standard\")}')
\""

# Check if a specific agent is running
ssh delta-server "tmux list-sessions | grep proj-my-app"

# Check tmux pane (see what Claude Code is doing)
ssh delta-server "tmux capture-pane -t proj-my-app:lead -p | tail -20"

# Web terminal (browser access to agent's Claude Code)
# URL: http://143.110.226.214:{port}
# Port is in delta-registry.json under ttyd_port
```

## Common issues

### Agent not responding

1. Check if tmux session exists: `tmux list-sessions | grep proj-{name}`
2. Check if Claude Code is running: `tmux capture-pane -t proj-{name}:lead -p | tail -5`
3. Check inbox for unprocessed messages: `ls /home/proj-{name}/{name}/delta-config/inbox/`
4. Check outbox for stuck responses: `ls /home/proj-{name}/{name}/delta-config/outbox/`
5. Restart the agent: `systemctl restart delta` (restores all active projects)

### OAuth token expired

Claude Code OAuth tokens expire. When this happens, agents go silent.

Signs: agents stop responding, `check_auth_error()` returns 401, logs show "API returned 401".

Fix:
```bash
ssh delta-server
claude /login        # Re-authenticate as root (tokens shared via symlink)
systemctl restart delta
```

### Hub not working (DMs/mentions ignored)

```bash
# Check hub tmux session
tmux list-sessions | grep delta-hub

# Check hub logs
cat /opt/delta/hub/delta-config/logs/$(date +%Y-%m-%d).jsonl | tail -10

# Force restart hub (restart the whole service)
systemctl restart delta
```

### Git sync not pushing

```bash
# Check timer status
systemctl status delta-git-sync.timer

# Run manually
systemctl start delta-git-sync.service

# Check logs
journalctl -u delta-git-sync -n 20
```

### Stale project (needs cleanup)

```bash
# Hibernate (keeps data, stops processes)
# Do this from Discord: @Delta hibernate my-app

# Full teardown (deletes everything)
# Do this from Discord: @Delta teardown my-app
# Or manually:
ssh delta-server "
  tmux kill-session -t proj-my-app 2>/dev/null
  userdel -r proj-my-app 2>/dev/null
  python3 -c \"
import json
d = json.load(open('/opt/delta/delta-registry.json'))
d['projects'].pop('my-app', None)
json.dump(d, open('/opt/delta/delta-registry.json', 'w'), indent=2)
\"
  systemctl restart delta
"
```

## Monitoring

### Git sync timer
Runs every 30 minutes. Commits and pushes all uncommitted project work.
```bash
systemctl status delta-git-sync.timer
journalctl -u delta-git-sync --since today
```

### Registry snapshot
Hub's live awareness of all projects. Updated every 60 seconds by the bot.
```bash
cat /opt/delta/hub/delta-config/registry-snapshot.json | python3 -m json.tool | less
```

### Conversation logs
Per-project, per-day JSONL files:
```bash
cat /home/proj-{name}/{name}/delta-config/logs/$(date +%Y-%m-%d).jsonl
```

## Infrastructure

| Component | Location | Managed by |
|---|---|---|
| Discord bot | `/opt/delta` | systemd (`delta.service`) |
| Hub agent | `/opt/delta/hub/` | Delta bot (auto-starts) |
| Project agents | `/home/proj-{name}/{name}/` | Delta bot (auto-starts active projects) |
| Git sync | `tools/git-sync.sh` | systemd timer (`delta-git-sync.timer`) |
| GitHub | Seedforth org | `delta` user, `gh` CLI as charlietheagent606-cloud |
| Web terminals | ttyd on allocated ports | Delta bot (per-project) |

## Environment variables

All in `/opt/delta/delta.env`. See [deploy/delta.env.example](../deploy/delta.env.example) for the full list.

Critical ones:
- `DISCORD_TOKEN` -- Bot dies without this
- `CLAUDE_CODE_OAUTH_TOKEN` -- Agents die without this (shared via symlink from /root/.claude)
- `GITHUB_TOKEN` -- Needed for repo creation and push
- `RUBE_BEARER_TOKEN` -- Google services (Drive, Docs, Sheets, Gmail)

## Adding a new project template

1. Create `project-template/MY_TEMPLATE.md` with `{project_name}`, `{project_dir}`, `{discord_channel_id}`, `{linux_user}`, `{ttyd_url}` placeholders
2. Add a case in `delta/provisioner.py` `_finalize_project()` for the new project_type
3. Update `delta/commands.py` if the new type needs a command keyword
4. Document in CLAUDE.md
