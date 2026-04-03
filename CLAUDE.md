# Delta -- Discord Agent Platform

## What It Is

Delta is a Discord bot that gives each project its own Claude Code instance. Users talk in Discord, Delta routes messages to isolated Claude Code processes via tmux, and Claude Code responds through a file-based bridge (inbox/outbox JSON files).

A hub orchestrator handles DMs and @mentions -- it knows about all projects, can route users to project channels, and can create new projects on request.

## Architecture

```
Discord message
  -> app.py (event handler)
  -> router.py (resolve channel/DM to project or hub)
  -> project_bridge.py (write inbox JSON, nudge tmux pane)
  -> Claude Code reads inbox, does work, writes outbox JSON
  -> app.py outbox watcher sends response to Discord
```

### System Users

```
delta (system user)          -- runs Discord bot process, owns /opt/delta
  |
  +-- proj-delta-hub         -- runs Claude Code for hub (DMs + @mentions)
  +-- proj-{project-name}    -- runs Claude Code per project (isolated)
```

- `delta` user runs the Python bot process via systemd. It routes messages, manages bridges, polls outboxes. It never runs Claude Code directly.
- `proj-*` users are sandboxed Linux users. Each runs their own Claude Code in a tmux session. They can only access their own home directory.
- `delta` has scoped sudo: can create/delete project users, run commands as proj-* users, manage services.

### Directory Layout (Server)

```
/opt/delta/                     -- Delta codebase (Seedforth/delta repo)
  delta/                        -- Python source (app.py, provisioner.py, etc.)
  project-template/             -- Templates (source of truth)
    CLAUDE.md                   -- Standard project agent personality
    HUB_CLAUDE.md               -- Hub agent personality
    LINKEDIN.md                 -- LinkedIn project agent personality
    hooks/                      -- Progress hooks
  tools/                        -- CLI tools
    unipile.py                  -- LinkedIn API client
    github-issue.py             -- GitHub issue CRUD
  hub/                          -- Hub runtime dir (NOT in git, regenerated)
    CLAUDE.md                   -- Generated from HUB_CLAUDE.md on provision
    delta-config/               -- inbox/outbox/logs for hub
    registry-snapshot.json      -- Live project status (updated every 60s)
  delta.env                     -- Environment config (gitignored)
  delta-registry.json           -- Project registry (gitignored, runtime)

/home/proj-{name}/{name}/      -- Per-project directory
  CLAUDE.md                     -- Generated from template on provision
  SEED.md                       -- Project memory (created by agent)
  delta-config/
    inbox/                      -- Messages from Discord (transient)
    outbox/                     -- Responses to Discord (transient)
    logs/                       -- Conversation history (persisted)
    schedule.json               -- Recurring tasks
  data/                         -- Project data (LinkedIn projects)
  hooks/                        -- PostToolUse progress hook
  .claude/settings.json         -- Claude Code hooks config
```

### Discord Server Structure

Delta operates on the SeedForth Discord server with these channel types:

**Special channels (env-configured):**
- `#seedforth-onboarding` (ONBOARDING_CHANNEL_ID) -- Admin triggers personal agent onboarding here. Delta extracts the target user, creates a private project channel, and starts the onboarding flow.
- `#linkedin-onboarding` (LINKEDIN_ONBOARDING_CHANNEL_ID) -- Users connect their LinkedIn accounts here. Delta generates a Unipile auth link automatically.
- `#general` and other channels -- Delta responds to @mentions. Hub gets the message with last 10 channel messages as context.

**Project channels (dynamic):**
- Created under "Delta Projects" category as `#proj-{name}`
- Private: @everyone denied, bot + owner + optional target user allowed
- Each maps to a registered project in delta-registry.json
- Created/destroyed by provisioner during project lifecycle

**DMs:**
- All DMs route to the hub agent
- If user has a persistent personal agent, hub routes to that agent

### Project Types

| Type | Template | Use case |
|---|---|---|
| `standard` | CLAUDE.md | Builder projects (websites, apps, dashboards) |
| `personal` | PERSONAL_ONBOARDING.md | Personal agent onboarding (7-module intake) |
| `persistent` | PERSONAL_AGENT.md | Post-onboarding personal agent (auto-transitioned) |
| `linkedin` | LINKEDIN.md | LinkedIn management (Unipile integration) |

**Personal agent flow:** Admin triggers in #seedforth-onboarding -> Delta creates `onboarding-{name}` project with PERSONAL_ONBOARDING.md -> Agent runs 7-module intake (identity, goals, time, work, rules, constraints, review) -> Agent sends `onboarding_complete` command -> Delta swaps CLAUDE.md to PERSONAL_AGENT.md, restarts agent, archives channel -> User DMs Delta directly from then on.

### Hub vs Project Agents

**Hub** (`proj-delta-hub`, runs in `/opt/delta/hub/`):
- Receives all DMs and @mentions in non-project channels
- Has live awareness of all projects via `registry-snapshot.json` (updated every 60s by app.py)
- Routes users to correct project channels
- Answers status questions from snapshot without bothering project agents
- Can create new projects via outbox commands
- Never builds code. Dispatches, directs, answers.

**Project agents** (`proj-{name}`, runs in `/home/proj-{name}/{name}/`):
- Receive messages only from their own Discord channel
- Build, deploy, create. They do the actual work.
- Have access to: Vercel (deploy), Rube MCP (Google services), GitHub (push/issues), Unipile (LinkedIn)
- Maintain their own SEED.md, schedule, and conversation logs

### Message Flow Detail

1. User sends Discord message
2. `app.py` receives via discord.py gateway
3. Router checks: project channel? DM? @mention?
   - Project channel -> write to that project's inbox
   - DM or @mention -> fetch last 10 channel messages as context, write to hub inbox
4. Bridge nudges the tmux pane (sends keystroke to wake Claude Code)
5. Claude Code reads inbox JSON, processes it
6. Claude Code writes response to outbox as JSON (plain text, embed, or file)
7. Bridge outbox watcher (polling every 1s) picks up the file
8. Bot posts the response to Discord
9. Outbox file deleted after posting

### Provisioning Flow

When a new project is created:
1. Create Linux user `proj-{name}` with home dir
2. Clone GitHub repo (if provided) using GITHUB_TOKEN
3. Create delta-config subdirs (inbox, outbox, logs, etc.)
4. Render CLAUDE.md from template with project-specific variables
5. Write .claude/settings.json with progress hooks
6. Create Discord channel with permissions
7. Create tmux session and start Claude Code as the project user
8. Start ttyd web terminal
9. Register in delta-registry.json

## Infrastructure

### Server
- **Host:** 143.110.226.214 (DigitalOcean, alias: delta-server)
- **Service user:** `delta` (not root)
- **Service:** `systemctl restart delta`
- **Deploy:** `cd /opt/delta && sudo -u delta git pull && sudo systemctl restart delta`

### GitHub
- **Org:** Seedforth (github.com/Seedforth)
- **Account:** charlietheagent606-cloud (Delta's own GitHub)
- **Auth:** `gh` CLI logged in as charlietheagent606-cloud for the delta user
- **All project repos** live under `Seedforth/`

### External Services
- **Rube MCP:** Google Drive, Docs, Sheets, Gmail, Calendar (registered per project via `claude mcp add-json`)
- **Unipile:** LinkedIn API (tools/unipile.py, env vars UNIPILE_DSN + UNIPILE_API_KEY)
- **Vercel:** Web deployment (VERCEL_TOKEN in env, passed to all project agents)
- **Email:** charlietheagent606@gmail.com (via Rube MCP Gmail)

### Environment Variables (delta.env)
```
DISCORD_TOKEN          -- Discord bot token
ADMIN_DISCORD_ID       -- Kshitiz (838843068857319445)
GITHUB_TOKEN           -- charlietheagent606-cloud gh token
CLAUDE_CODE_OAUTH_TOKEN -- Claude Max subscription auth
RUBE_BEARER_TOKEN      -- Rube MCP auth (Google services)
VERCEL_TOKEN           -- Vercel deployment
COMPOSIO_API_KEY       -- Composio SDK (account connections)
UNIPILE_DSN            -- Unipile API base URL
UNIPILE_API_KEY        -- Unipile API key
```

All tokens are passed to project agents via `/tmp/.claude-token-proj-{name}` files (sourced on Claude Code startup).

## Core Modules

- `delta/app.py` -- Discord client, event handlers, command dispatch, outbox watchers, hub snapshot loop, channel history fetch
- `delta/commands.py` -- Natural language command parser (new project, status, teardown, etc.)
- `delta/provisioner.py` -- Project creation: Linux user, git clone, Discord channel, tmux, Claude Code launch, template rendering
- `delta/registry.py` -- JSON-backed project registry (thread-safe CRUD)
- `delta/router.py` -- Resolves Discord channels/DMs to projects
- `delta/project_bridge.py` -- Per-project inbox/outbox/logs bridge, tmux nudging, outbox polling
- `delta/lifecycle.py` -- tmux session + Claude Code process management, token file writing, ttyd
- `delta/isolation.py` -- Linux user creation/deletion for sandboxing
- `delta/connections.py` -- Composio SDK wrapper for per-user OAuth connections
- `delta/resource_manager.py` -- Hibernation and resource management

## Templates

Source of truth for agent personalities. Located in `project-template/`.

- `CLAUDE.md` -- Standard project agent. Builder personality, voice rules, delivery protocol, scheduling, cloud tools (Vercel, Rube, GitHub), learning system, git rhythm. Includes SEED.md memory system, 70% autonomy rule, anti-bot enforcement.
- `HUB_CLAUDE.md` -- Hub orchestrator. Chief-of-staff posture, routing logic, snapshot awareness, project creation commands. Never builds, only dispatches.
- `LINKEDIN.md` -- LinkedIn agent. Extends standard with Unipile CLI commands, autonomy tiers (auto/notify/approval/blocked), content pipeline, warmth scoring, safety rules.
- `hooks/progress_hook.py` -- PostToolUse hook that signals work progress to Discord

Templates use `{variable}` placeholders filled by provisioner: `{project_name}`, `{discord_channel_id}`, `{project_dir}`, `{linux_user}`, `{ttyd_url}`, `{unipile_tool_path}`.

## Running

```bash
# Local development (Mac, no Linux users)
LOCAL_MODE=true python3 -m delta.app

# Server (via systemd as delta user)
systemctl start delta
```

## Testing

```bash
python3 -m pytest tests/ -x -q
```

## Git Workflow

- All repos under `Seedforth/` org
- Delta pushes as charlietheagent606-cloud
- Branch for non-trivial work. `main` for stable changes.
- Commit at natural checkpoints. Push often.
- No emojis in code or commits.

## Admin

- ADMIN_DISCORD_ID=838843068857319445 (Kshitiz, kshitiz29)
- Service email: charlietheagent606@gmail.com
- GitHub: charlietheagent606-cloud (Seedforth org owner)

## Conventions

- No emojis unless asked
- No acknowledgment messages -- only substantive responses
- Concise communication
- No em dashes, no banned AI words (delve, craft, unlock, leverage), no semicolons, no rhetorical questions, active voice, short sentences
