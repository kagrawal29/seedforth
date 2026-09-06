# Delta

Delta turns a Discord server into an AI agency. Each project gets its own autonomous Claude Code agent -- not a thin wrapper, a full instance with filesystem access, bash, tools, and skills. Users talk in Discord. Agents build, deploy, and ship.

## How it works

```
Discord message
  -> Python bot (routes message to the right agent)
  -> JSON file dropped in agent's inbox/
  -> Claude Code reads it, does the work
  -> Claude Code writes response to outbox/
  -> Bot picks up the file, posts to Discord
```

**The bot is dumb. The agents are smart.** The bot doesn't understand messages. It delivers them. Claude Code does all the thinking -- writing code, deploying apps, creating documents, managing LinkedIn accounts, sending emails. The bot is just the mail carrier.

**File-based IPC** is the decoupling layer. No WebSocket, no SDK integration. JSON files in a directory. This makes agents completely independent of the bot framework. You could swap Discord for Slack and the agents wouldn't know.

**Each agent is sandboxed** in its own Linux user with its own home directory, tmux session, and Claude Code process. Agents can't see each other's work. The hub agent knows about all projects via a registry snapshot updated every 60 seconds.

## What agents can do

Every agent has the full power of Claude Code:

- **Build and deploy** web apps, dashboards, landing pages (Vercel)
- **Create and share** Google Docs, Sheets, Slides (Rube MCP)
- **Send emails** from charlietheagent606@gmail.com (Rube MCP + Gmail)
- **Manage LinkedIn** accounts -- search, connect, message, post (Unipile)
- **Push code** to GitHub under the Seedforth org
- **Create GitHub issues**, manage repos
- **Install MCP servers** and acquire skills on the fly
- **Run scheduled tasks** -- daily reports, weekly reviews, monitoring
- **Remember context** across restarts via SEED.md and git history

## Project types

| Type | What it does |
|---|---|
| **Standard** | Builder projects -- websites, apps, dashboards, automations |
| **Personal** | Personal agent -- onboards through 7-module intake, becomes a persistent life/work assistant |
| **LinkedIn** | LinkedIn intelligence -- manages an account's outreach, content, and relationships |

## Architecture

```
/opt/delta/                         Delta codebase
  delta/                            Python source (bot, router, provisioner)
  project-template/                 Agent personality templates
  tools/                            CLI tools (LinkedIn, GitHub, git sync)
  hub/                              Hub agent runtime (not in git)

/home/proj-{name}/{name}/          Per-project agent directory
  CLAUDE.md                         Agent's personality and instructions
  SEED.md                           Project memory (persists across restarts)
  delta-config/
    inbox/                          Messages from Discord
    outbox/                         Responses to Discord
    logs/                           Conversation history
    schedule.json                   Recurring tasks
```

**System users:**
- `delta` -- runs the Discord bot process (message routing, process management)
- `proj-{name}` -- one per project, runs Claude Code in isolation

**Discord channels:**
- `#seedforth-onboarding` -- Admin triggers personal agent onboarding
- `#linkedin-onboarding` -- Users connect LinkedIn accounts
- `#proj-{name}` -- Private project channels (auto-created)

## Running

```bash
# Server (production)
systemctl start delta

# Local development (Mac, no Linux user isolation)
LOCAL_MODE=true python3 -m delta.app
```

## Setup

See [deploy/setup-server.sh](deploy/setup-server.sh) for fresh server provisioning. Requires:
- Ubuntu 24.04
- Python 3.12+
- Claude Code CLI
- Discord bot token
- GitHub account (charlietheagent606-cloud in Seedforth org)

Environment config: copy [deploy/delta.env.example](deploy/delta.env.example) to `delta.env`.

## Documentation

- [CLAUDE.md](CLAUDE.md) -- Full architecture reference (system users, directory layout, message flow, provisioning, infrastructure, modules)
- [LEGACY-BOUNDARY.md](LEGACY-BOUNDARY.md) -- Supported runtime paths and retained migration-only scripts
- [tests/delta-behavior-map.md](tests/delta-behavior-map.md) -- Behavioral specification of every code path
- [tests/delta-test-plan.md](tests/delta-test-plan.md) -- E2E test plan (60+ cases)
- [tests/delta-test-results.md](tests/delta-test-results.md) -- Test results and known issues

## GitHub

- **Org:** [Seedforth](https://github.com/Seedforth)
- **Bot account:** charlietheagent606-cloud
- **All project repos** are private under Seedforth/

## Testing

```bash
python3 -m pip install -r requirements-test.txt
python3 -m pytest tests/ -x -q   # active suite; obsolete migration tests are excluded in tests/conftest.py
```
