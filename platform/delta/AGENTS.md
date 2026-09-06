# Delta -- Discord Agent Platform

## What It Is

Delta is a Discord bot that gives each project its own opencode agent, with two personas per project: **Delta** (internal/Discord) and **Charlie** (client-facing/WhatsApp). Users talk in Discord, Delta routes messages to isolated opencode agents running under supervisord, and the agent responds through a file-based bridge (inbox/outbox JSON files) plus an HTTP delivery path.

A hub orchestrator handles DMs and @mentions -- it knows about all projects, can route users to project channels, and can create new projects on request.

> Runtime is **opencode** (DeepSeek + OpenRouter APIs), not Claude Code. The tmux + Claude Code architecture is legacy. See `docs/migration-to-opencode.md` for the current spec.

## Architecture

```
Discord message
  -> app.py (event handler)
  -> router.py (resolve channel/DM to project or hub)
  -> project_bridge.py (write inbox JSON, deliver over HTTP)
  -> opencode serve reads message, does work, replies over HTTP
  -> app.py sends response to Discord
```

### System Users

```
delta (system user)          -- runs Discord bot process, owns /opt/delta
  |
  +-- proj-delta-hub         -- runs opencode for hub (DMs + @mentions)
  +-- proj-{project-name}    -- runs opencode per project (isolated)
```

- `delta` user runs the Python bot process via systemd. It routes messages, manages bridges, polls outboxes. It never runs the agent directly.
- `proj-*` users are sandboxed Linux users. Each runs their own `opencode serve` under supervisord. They can only access their own home directory.
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

### Agent Lifecycle & Conversation Flow (opencode runtime)

This is the current (post-migration) flow. The tmux/Claude code path below is legacy and
no longer in use since all agents were migrated to opencode serve.

**Agents are persistent HTTP servers, not spawned per-message.**

Each agent runs as `opencode serve --port {N}` under supervisord, as its own Linux user.
The process stays alive 24/7 listening on localhost:{port}. It consumes ~270 MB at idle
(Node.js runtime + opencode framework). This RAM is NEVER released while the process runs.

#### Full message flow

```
Discord message
  -> app.py (discord.py gateway, on_message event)
  -> router.py resolve_channel(channel_id) -> project name
  -> app.py _get_or_create_bridge(name) -> ProjectBridge instance
  -> bridge.deliver_message() [app.py:3237]
     1. Writes to logs/{today}.jsonl for conversation history
     2. Spawns thread that POSTs to http://127.0.0.1:{port}/session/{sid}/message
     3. OpenCode server:
        a. Checks if session {sid} exists
        b. If expired: creates new session, loads CLAUDE.md + SEED.md + AGENTS.md (~3-5s)
        c. If active: context already loaded, instant (<1s)
     4. LLM processes, returns response in HTTP response body
     5. Bridge fires callback(channel_id, response_text)
     6. app.py sends response to Discord channel
```

#### What "waking up" means

"Waking up" is when the **LLM session context** has expired and needs to be reloaded.
The process itself is always running. There is no process-level wake/sleep cycle.

- **Session alive** (messaged recently): context cached, instant response
- **Session expired** (idle > some period): reloads CLAUDE.md + SEED.md, 3-5 seconds
- **"Typing" indicator**: Delta bot got the message, bridge delivered it, agent is processing

There is NO explicit waking up message sent. The agent silently loads context and responds.

#### Memory model

| State | RAM usage | OpenCode process | LLM session |
|---|---|---|---|
| **RUNNING idle** | ~270 MB | Alive | Expired, no context loaded |
| **RUNNING processing** | ~270-350 MB | Alive | Active, context+history loaded |
| **STOPPED** | 0 MB | Dead | None |
| **HIBERNATED (delta concept)** | ~270 MB | Alive (if autostart=true) | Expired |

The "hibernation" in delta (`resource_manager.py`) only stops the **bridge** from
polling outboxes. It does NOT stop the agent process itself unless the supervisor
config has `autostart=false` and you `supervisorctl stop` it.

To actually free RAM for an inactive project:
```
supervisorctl stop proj-{name}   # kills process, frees ~270 MB
# Then set autostart=false in /etc/supervisor/conf.d/proj-{name}.conf
# to prevent it starting on reboot
```

#### Hibernate vs stop vs delete

| Action | Process | RAM freed | Data kept | Restartable |
|---|---|---|---|---|
| Delta hibernate | Bridge only stops polling | 0 MB | All data | Auto on message |
| supvervisor stop | Kill process | ~270 MB | All data | supervisor start |
| supervisor stop + autostart=false | Kill + no auto-restart | ~270 MB | All data | Manual start |
| Archive + delete | Tar home dir, delete user | All | In /opt/delta/archived-projects/ | Restore from tar |

#### When does RAM get freed

- **Immediately** when `supervisorctl stop proj-{name}` kills the process
- **NOT on delta-level hibernate** -- "hibernate" just marks the registry and stops
  the bridge watcher. opencode serve keeps running.
- **On reboot** if `autostart=false` -- process won't start at all

#### Diagnosing stuck agents

1. Check if process is alive: `supervisorctl status proj-{name}`
2. Check for crash loops: `tail -50 {project_dir}/delta-config/logs/opencode-stderr.log`
3. Check for config errors: look for `Configuration is invalid` or `lsp.disable` in stderr
4. Stale inbox files can cause agents to process old tasks before responding: `ls {project_dir}/inbox/`
5. Permission errors: delta user needs `o+x` on `/home/proj-*/` to traverse into inbox dirs

### Legacy Message Flow (tmux + Claude Code)

This flow is deprecated and was replaced by the opencode HTTP path above.
Kept for historical reference only.

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

## Browser Automation (persistent logged-in profiles)

Delta agents can drive real, logged-in browsers on the server via CDP -- no
Claude-in-Chrome, no Playwright MCP. Each profile is a persistent Chromium kept
signed in, exposed on a local CDP port. Token-efficient: a plain CLI that returns
text, so agents spend tokens on the task, not browser plumbing.

Tool: `python3 /opt/delta/tools/browser.py` (usable by any proj-* agent user).

Profiles wired for delta agents:

| Profile | CDP port | Account | noVNC (log in / view) |
|---|---|---|---|
| `charlie` | 9224 | charlietheagent606@gmail.com | http://143.110.226.214:6083/vnc.html |
| `seedforth` | 9223 | SeedForth Google session | http://143.110.226.214:6082/vnc.html |

(`iris` on 9222 is Revti Digital's browser and is deliberately NOT exposed to delta agents.)

Commands -- two modes:
```
# CONCURRENT READ (own throwaway tab, safe for many agents at once)
browser.py profiles                          # list + reachability
browser.py get   <profile> <url> [--max N]   # navigate, print page text
browser.py shot  <profile> <url> <path.png>  # navigate, screenshot
browser.py eval  <profile> <url> "<js>"      # navigate, run JS

# INTERACTIVE FLOW (drives the ONE visible tab; do one flow at a time per profile)
browser.py open  <profile> <url>             # navigate the visible tab
browser.py see   <profile> [path.png]        # screenshot visible tab (your eyes)
browser.py read  <profile> [--max N]         # print visible tab text
browser.py click <profile> "<text|css>"      # click button/link by text (else CSS)
browser.py fill  <profile> "<css>" "<value>" # type into an input
browser.py press <profile> <Key>             # e.g. Enter, Tab
```
The profile is one shared, logged-in browser. Do NOT expect a private session
per agent -- concurrent agents share cookies/identity (charlie = charlie's
Google account), just not each other's tab.

### Self-serve service access -- you CAN and MUST

When you need access to a third-party service (Vercel, Composio, Supabase,
Railway, analytics dashboards, etc.) -- an API key, a token, a connected
account, a setting -- do NOT immediately ask the human. You have a real browser
logged in as charlie. Get it yourself:

1. `open charlie https://<service>/login` (or signup).
2. `see charlie /tmp/s.png`, look, then `click charlie "Continue with Google"`
   (or "Sign in with Google").
3. If an account chooser appears, `click charlie "charlietheagent606@gmail.com"`.
   charlie is already signed into Google, so SSO is usually 1-2 clicks, no password.
4. Land on the dashboard, navigate to the API keys / tokens section, create a key,
   and read it (`read`/`see`, or `eval` to pull an input value).
5. Store the key where the project uses it -- the project's `.env` /
   `.claude/settings.json` / delta.env -- NOT in git, NOT echoed into Discord.
   Reference it by env var afterwards.

Loop of `see` -> decide -> `click`/`fill`/`press` -> `see`. Screenshot first when
unsure what is on screen.

Only escalate to the human when genuinely blocked:
- a phone/2FA/"verify it's you" challenge (needs their device),
- the service has no Google SSO and needs a fresh password (Claude never types
  passwords -- ask the human to log in via noVNC),
- payment / paid plan required,
- an irreversible or account-security action (deleting, changing security
  settings, granting third-party OAuth to an unknown app) -- confirm first.

Use charlie's identity consistently. Do not create purchases or change account
security settings without human approval.

Each profile is a 4-service systemd stack: `<name>-xvfb` (virtual display),
`<name>-chromium` (CDP), `<name>-x11vnc`, `<name>-novnc` (web login). To add a
profile, clone the `charlie-*.service` units with a fresh display/CDP/VNC/noVNC
port set. Logins are done by a human via the noVNC URL -- the browser stays
signed in across restarts (persistent user-data-dir).

## Conventions

- No emojis unless asked
- No acknowledgment messages -- only substantive responses
- Concise communication
- No em dashes, no banned AI words (delve, craft, unlock, leverage), no semicolons, no rhetorical questions, active voice, short sentences
