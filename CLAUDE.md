# Delta -- Discord Agent Platform

## What It Is

Delta is a Discord bot that gives each project its own Claude Code instance. Users talk in Discord, Delta routes messages to isolated Claude Code processes via tmux, and Claude Code responds through a file-based bridge (inbox/outbox JSON files).

A hub orchestrator handles DMs -- it knows about all projects, can route users to project channels, and can create new projects on request.

## Architecture

```
Discord message
  -> router.py (resolve channel/DM to project)
  -> project_bridge.py (write inbox JSON, nudge tmux)
  -> Claude Code reads inbox, writes outbox JSON
  -> app.py outbox watcher sends response to Discord
```

**Core modules:**
- `delta/app.py` -- Discord client, event handlers, command dispatch, outbox watchers, reporting loop
- `delta/commands.py` -- natural language command parser (new project, status, teardown, etc.)
- `delta/provisioner.py` -- creates projects: Linux user (server) or local dir (Mac), Discord channel, tmux session, Claude Code launch, CLAUDE.md from template
- `delta/registry.py` -- JSON-backed project registry (thread-safe CRUD)
- `delta/router.py` -- resolves Discord channels/DMs to projects
- `delta/project_bridge.py` -- per-project inbox/outbox/logs bridge, tmux nudging, outbox polling
- `delta/lifecycle.py` -- tmux session + Claude Code process management (start/stop/health)
- `delta/isolation.py` -- Linux user creation/deletion for server-mode sandboxing
- `delta/connections.py` -- Composio SDK wrapper for per-user OAuth connections
- `delta/resource_manager.py` -- hibernation and resource management

**Templates:**
- `project-template/CLAUDE.md` -- injected into each project, defines agent personality and protocol
- `project-template/HUB_CLAUDE.md` -- hub agent personality and protocol
- `project-template/CHARACTER.md` -- agent character traits
- `project-template/hooks/` -- progress hooks for streaming

## Config

- `delta.env` -- DISCORD_TOKEN, ADMIN_DISCORD_ID, LOCAL_MODE, LOCAL_PROJECTS_DIR, RUBE_BEARER_TOKEN
- `delta-registry.json` -- persisted project registry (runtime, gitignored)
- `delta-last-fired.json` -- schedule fire timestamps (runtime, gitignored)
- LOCAL_MODE=true runs on Mac (no Linux users, local dirs)
- LOCAL_MODE=false (default) runs on server with Linux user isolation

## Running

```bash
# Local development
LOCAL_MODE=true python3 -m delta.app

# Server (via systemd)
systemctl start delta
```

## Testing

```bash
python3 -m pytest tests/ -x -q
```

218 tests covering registry, lifecycle, connections, isolation, project bridge, router, commands, scheduling, teardown, restore, and last-fired persistence.

## Server Deployment

- **Server:** 143.110.226.214 (SSH config alias: `delta-server`)
- **Path:** `/opt/delta`
- **Service:** `systemctl restart delta`
- **Deploy:** `cd /opt/delta && git pull && systemctl restart delta`

## Hub Orchestrator

All DMs to Delta route to a hub Claude Code instance (`__hub__`). The hub knows about all projects via a registry snapshot.

- Hub dir (server): `/opt/delta/hub`
- Hub dir (local): `{LOCAL_PROJECTS_DIR}/delta-hub`
- Hub is NOT in the registry. It lives only in the bridges dict.
- `_hub_snapshot_loop()` (every 60s) checks health and restarts if dead.

## Admin

- ADMIN_DISCORD_ID=838843068857319445 (Kshitiz)
- Service account: charlietheagent606@gmail.com (Rube/Composio connections)
- RUBE_BEARER_TOKEN in delta.env (no exp claim, long-lived)

## Git Workflow

- Branch for non-trivial work. `main` for stable changes.
- Commit at natural checkpoints. Push often.
- No emojis in code or commits.

## User Preferences

- No emojis unless asked
- No acknowledgment messages -- only substantive responses
- Concise communication
- No em dashes, no banned AI words (delve, craft, unlock, leverage), no semicolons, no rhetorical questions, active voice, short sentences
