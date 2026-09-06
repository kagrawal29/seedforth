# Delta Behavior Map

Comprehensive mapping of all behavior paths in the Delta Discord bot codebase.

---

## 1. DM Flow (user DMs Delta)

### 1.1 DM with a recognized command

**Trigger:** User sends a DM that `commands.parse()` matches.
**Code path:** `on_message` -> `is_dm=True` -> `commands.parse(text)` returns a tuple -> `_handle_command()`.
**Behavior:** The command is handled directly by Delta (bypasses the hub). See Section 6 for all commands.
**User sees:** Command-specific response.
**Edge cases:**
- Bot messages are ignored (`message.author.bot` check at line 1059).
- Empty text is ignored (line 1064).

### 1.2 DM with non-command text (routed to hub)

**Trigger:** User sends a DM that `commands.parse()` returns `None` for.
**Code path:** `on_message` -> `is_dm=True` -> no command -> hub_bridge.write_inbox() with `channel_type="dm"`.
**Behavior:**
1. `hub_bridge.touch_activity()` -- updates hub's last_activity timestamp.
2. Writes inbox JSON to hub's `delta-config/inbox/` with fields: `id`, `channel` (the DM channel ID), `user` (Discord user ID string), `text`, `channel_type="dm"`, `timestamp`.
3. If hub Claude Code is active (`is_project_active()`), sends a tmux nudge to hub pane.
4. If hub Claude Code is NOT active, sends user: "I'm waking up, give me a sec. Try again in a moment."

**User sees:** Nothing immediately from Delta. Response comes later via hub's outbox -> Discord.
**Edge cases:**
- Hub bridge not initialized at all -> user sees "Something's off on my end. Try again in a moment."
- Hub alive but nudge fails -> warning logged, message sits in inbox until `watch_inbox` re-nudges.

### 1.3 Hub processes a DM

**Trigger:** Hub Claude Code reads inbox JSON with `channel_type="dm"`.
**Behavior (per HUB_CLAUDE.md):**
- Hub reads `delta-config/registry-snapshot.json` for project awareness.
- If user has projects: answers with context from snapshot (schedule, logs, commits, seed).
- If user has no projects: introduces itself, asks what they want to build.
- If user wants a new project: writes `new_project` command to outbox (see Section 4.1).
- If user wants to talk to a specific project: writes `forward` command to outbox (see Section 4.3).
- Normal responses: writes outbox JSON with `channel` = DM channel ID.

---

## 2. Guild Channel Flow

### 2.1 Message in a project channel (agent running)

**Trigger:** User sends a message in a channel that `router.resolve_channel()` maps to a project.
**Code path:** `on_message` -> `project_name = router.resolve_channel(channel_id)` -> found.
**Behavior:**
1. `_get_or_create_bridge(project_name)` -- gets or creates ProjectBridge.
2. If project is hibernated (`status == "hibernated"`):
   - User sees "waking up, one sec".
   - `restore()` is called: re-creates tmux session, starts Claude Code, marks active.
   - `_start_watchers()` restarts outbox/inbox/followup watchers.
   - Sleeps 8 seconds for Claude Code to boot.
3. `bridge.touch_activity()` -- resets idle timer.
4. `bridge.cancel_pending_followups()` -- cancels any scheduled follow-ups (user re-engaged).
5. Writes inbox JSON with `channel`, `user`, `text`.
6. If project agent is active: sends tmux nudge.
7. If project agent is DOWN: falls back to hub (see 2.3).

**User sees:** Response comes via project agent's outbox -> Discord.
**Edge cases:**
- Bridge creation fails (project not in registry) -> user sees "Something's off with **name**'s bridge. Let an admin know."
- Restore fails -> user sees "Could not restore **name**."
- Nudge fails -> warning logged, `watch_inbox` will re-nudge later.

### 2.2 Message in a non-project channel (not @mentioned)

**Trigger:** Message in a guild channel not mapped to any project, bot NOT @mentioned.
**Code path:** `on_message` -> `project_name = None` -> `mentioned = False` -> `return`.
**Behavior:** Completely ignored. Delta does nothing.

### 2.3 @mention in a non-project channel

**Trigger:** Message in a guild channel not mapped to any project, bot IS @mentioned.
**Code path:** `on_message` -> `project_name = None` -> `mentioned = True`.
**Behavior:**
1. Strip the @mention from text: `re.sub(r"<@!?\d+>\s*", "", text)`.
2. If remaining text is a recognized command: handle via `_handle_command()`.
3. Otherwise, route to hub with `channel_type="channel"` and `channel_name`.
4. Hub uses snapshot to respond substantively.

**User sees:** Response from hub via outbox -> Discord.
**Edge cases:**
- Hub not active -> "I'm waking up, give me a sec. Try again in a moment."
- Hub bridge not initialized -> "Something's off on my end. Try again in a moment."
- Empty text after stripping mention -> still routed to hub (no special handling).

### 2.4 Message in a project channel (agent DOWN, hub fallback)

**Trigger:** Message in a project channel, but `bridge.is_project_active()` returns False.
**Code path:** `on_message` -> project channel -> agent not active -> hub fallback (line 1192).
**Behavior:**
1. Writes inbox JSON to HUB's inbox with:
   - `channel_type="project_channel"`
   - `channel_name` = channel name or project name
   - `project_name` = the project name
2. Hub Claude Code gets this and answers from its snapshot data.
3. Per HUB_CLAUDE.md: "Don't tell the user the agent is down. Just answer their question naturally."

**User sees:** Response from hub (appears seamless).
**Edge cases:**
- Hub also not active -> "I'm waking up, give me a sec. Try again in a moment."
- Hub bridge not initialized -> same fallback message.

---

## 3. Project Lifecycle

### 3.1 Create project (standard -- new channel)

**Trigger:** `new_project` command (from DM/channel or hub).
**Code path (direct command):** `_handle_command("new_project", ...)` -> `provision()`.
**Code path (hub-initiated):** hub writes `{"command": "new_project"}` to outbox -> `_hub_outbox_callback` -> `_provision()`.

**Steps:**
1. Validate name: `_NAME_RE = r"^[a-zA-Z0-9][a-zA-Z0-9-]{1,29}$"` (2-30 chars, alphanumeric + hyphens).
2. Check name not already in registry.
3. LOCAL_MODE:
   - Create dir at `LOCAL_PROJECTS_DIR/<name>`.
   - Or git clone if `github_repo` provided.
   - Create `delta-config/{inbox,outbox,logs}` dirs.
   - Create `delta-config/schedule.json` with `{"tasks": []}`.
   - Init git repo.
4. Server mode:
   - Create Linux user `proj-<name>`.
   - Create project dir at `/home/proj-<name>/<name>`.
   - Same delta-config setup.
5. Create private Discord channel `proj-<name>` under "Delta Projects" category.
   - Permission overwrites: deny @everyone, allow bot + owner.
6. Write CLAUDE.md from template (with `project_name`, `project_dir`, `linux_user`, `discord_channel_id` substituted).
7. Create tmux session `proj-<name>` with window "lead".
8. Start Claude Code: `cd <dir> && claude --dangerously-skip-permissions`.
9. Register in `delta-registry.json`.
10. Start watchers (outbox, inbox re-nudge, followups).

**User sees (direct):** "Setting up **name**. One moment." then "**name** is live. <#channel_id>"
**User sees (hub-initiated):** Hub gets confirmation from delta:system, relays to user.

**Edge cases:**
- Name already exists -> ValueError: "Project 'name' already exists".
- Invalid name -> ValueError with format description.
- Git clone fails -> RuntimeError.
- Channel creation fails -> continues without Discord channel ID.
- Hub provision: on failure, error written back to hub's inbox from `delta:system`.

### 3.2 Create project (in-channel -- "here" flag)

**Trigger:** `new project <name> here` or hub command with `use_channel`.
**Code path:** `provision_in_channel()` -- same as `provision()` but skips channel creation, uses existing `channel_id`.
**Difference:** No Discord channel is created. The existing channel becomes the project channel.
**User sees:** "**name** is live right here."

### 3.3 Hibernate project

**Trigger:** Resource manager detects project is idle for 10+ minutes with no pending work.
**Code path:** `resource_manager_loop()` -> `hibernate()` in provisioner.
**Steps:**
1. `git_save()`: git add -A, commit "hibernate: <timestamp>", push (best-effort).
   - Runtime logs remain outside Git; hibernation saves source and durable
     project intent only.
2. `stop_claude_code()`: Ctrl+C, wait grace period, force-kill if needed.
3. `kill_tmux_session()`: kills the tmux session.
4. `bridge.shutdown()`: signals all watcher threads to stop, removes from bridges dict.
5. `registry.update(name, status="hibernated")`.

**User sees:** Nothing. Silent background operation.
**Edge cases:**
- Git save fails -> logged as warning, hibernation continues.
- Claude Code won't stop -> force-killed via pkill.
- Project not in registry -> returns False, logged.

### 3.4 Wake/restore project

**Trigger:** User sends a message in a hibernated project's channel, or scheduled task fires.
**Code path (channel message):** `on_message` -> `proj_info.status == "hibernated"` -> `restore()`.
**Code path (scheduled):** `_wake_and_get_bridge()` -> `restore()`.
**Steps:**
1. `create_tmux_session()` (re-creates the session).
2. `start_claude_code()` (launches Claude Code in the pane).
3. `registry.update(name, status="active", last_activity=now)`.
4. `_start_watchers()` (restarts outbox/inbox/followup watchers).
5. Sleep 8 seconds for Claude Code to boot.

**User sees:** "waking up, one sec" (from channel messages). Scheduled wakes are silent.

### 3.5 Teardown project

**Trigger:** `teardown <name>` or `delete <name>` command.
**Code path:** `_handle_command("teardown", ...)` -> `teardown()`.
**Steps:**
1. Check project exists in registry.
2. Check user is owner or admin (non-owners see "That's not your project.").
3. "Shutting down **name**."
4. `stop_claude_code()` + `kill_tmux_session()`.
5. Delete Discord channel (if exists).
6. Remove from registry.
7. Delete Linux user (server mode only, not LOCAL_MODE).

**User sees:** "Shutting down **name**." then "**name** is gone. Channel deleted, user removed, everything cleaned up."
**Edge cases:**
- Project not found -> "No project called **name**."
- Channel deletion fails -> warning logged, teardown continues.
- User deletion fails -> warning logged.
- NOTE: Project directory is NOT deleted. Only tmux/channel/registry/user are removed.

---

## 4. Hub Behavior

### 4.1 Hub command interception: new_project

**Trigger:** Hub Claude Code writes `{"command": "new_project", ...}` to outbox.
**Code path:** `_hub_outbox_callback()` -> checks `data.get("command")`.
**Fields expected:** `name`, `owner_discord_id`, `reply_channel`, `github_repo`, optionally `use_channel`.
**Behavior:**
1. If `use_channel` present: calls `provision_in_channel()`.
2. Otherwise: calls `provision()`.
3. On success: `_start_watchers(name)`, writes confirmation to hub inbox from `delta:system`.
4. On failure: writes error to hub inbox from `delta:system`.

**User sees:** Hub Claude Code receives the system message and relays confirmation/error to the user.

### 4.2 Hub command interception: forward

**Trigger:** Hub Claude Code writes `{"command": "forward", ...}` to outbox.
**Fields expected:** `target_project`, `text`, `user`, `reply_channel`.
**Behavior:**
1. Gets or creates bridge for target project.
2. Writes message to target project's inbox.
3. Touches activity on target bridge.
4. If target is active, sends tmux nudge.

**User sees:** The forwarded message appears in the target project's conversation.

### 4.3 Hub normal outbox messages

**Trigger:** Hub writes a normal JSON (no `command` field) to outbox.
**Behavior:** Same as project outbox: sends to Discord channel via `channel_id`.
**Supports:** Plain text and embeds (same format as project agents).

### 4.4 Hub snapshot loop (`_hub_snapshot_loop`)

**Trigger:** Async loop runs every 60 seconds, starts on `on_ready`.
**Behavior:**
1. For each project in registry:
   - Gets health status (running/stopped/hibernated).
   - Reads SEED.md (first 500 chars).
   - Reads schedule.json (up to 15 tasks, descriptions truncated to 100 chars).
   - Reads recent logs (last 10 entries, text truncated to 200 chars).
   - Reads recent git commits (last 5 oneline).
2. Writes `registry-snapshot.json` to hub's delta-config dir.
3. Sets file permissions to 644 (readable by hub user).
4. **Hub keepalive check:**
   - If hub Claude Code is not running: stops it (grace=3), restarts it.
   - If hub has pending inbox messages AND is at prompt: re-nudges the oldest message.

**User sees:** Nothing. Background maintenance.
**Edge cases:**
- Individual project data reads (seed, schedule, logs, commits) fail silently.
- Loop exceptions caught, warning logged, continues next iteration.

### 4.5 Hub initialization (`_init_hub`)

**Trigger:** Called once during `on_ready`.
**Behavior:**
1. Creates hub directory (LOCAL_MODE: `LOCAL_PROJECTS_DIR/delta-hub`, Server: `/opt/tetrahedron/hub`).
2. Creates `delta-config/{inbox,outbox,logs}` dirs.
3. Writes `CLAUDE.md` from `HUB_CLAUDE.md` template.
4. Server mode: creates Linux user `proj-delta-hub`, sets dir permissions to 777, creates `/root/.claude/settings.json` for skip-permissions.
5. Creates tmux session `delta-hub` with window "lead".
6. Starts Claude Code in hub pane.
7. Creates ProjectBridge for hub (stored in bridges dict as `__hub__`, NOT in registry).

### 4.6 Hub NOT in registry

The hub is special: it exists only in the `bridges` dict, never in the registry. The resource manager won't hibernate it. The snapshot loop handles its keepalive.

---

## 5. Error/Fallback Paths

### 5.1 Project agent down, hub fallback

**When:** User sends message in project channel, `bridge.is_project_active()` returns False.
**Behavior:** Message routed to hub with `channel_type="project_channel"`.
**Hub behavior:** Answers from snapshot data. Per HUB_CLAUDE.md: don't tell user the agent is down.

### 5.2 Hub not active

**When:** DM or @mention arrives but `hub_bridge.is_project_active()` is False.
**User sees:** "I'm waking up, give me a sec. Try again in a moment."
**Recovery:** Snapshot loop detects dead hub every 60s and auto-restarts.

### 5.3 Hub bridge not initialized

**When:** `bridges.get(HUB_NAME)` returns None.
**User sees:** "Something's off on my end. Try again in a moment."
**This should never happen** after `on_ready` unless `_init_hub()` failed.

### 5.4 Nudge failure

**When:** `bridge.send_to_lead()` raises an exception (tmux command failure).
**Behavior:** Warning logged. Message remains in inbox. `watch_inbox` thread re-nudges every 8 seconds when pane is at prompt.

### 5.5 Outbox processing failure

**When:** Outbox JSON is malformed or Discord send fails.
**Behavior:** Error logged. File name added to `seen` set (won't be retried). File NOT deleted if `path.unlink()` not reached (stays on disk).

### 5.6 Channel not found for outbox

**When:** `client.get_channel()` returns None AND `client.fetch_channel()` fails.
**Behavior:** Warning logged, message silently dropped.

### 5.7 Provision failure

**When:** `provision()` or `provision_in_channel()` raises ValueError or RuntimeError.
**User sees (direct):** "Could not set up: <error>."
**User sees (hub-initiated):** Hub receives system message "Could not create project name: error" and relays.

### 5.8 Invalid project name

**When:** Name doesn't match `^[a-zA-Z0-9][a-zA-Z0-9-]{1,29}$`.
**User sees:** ValueError propagated as "Could not set up: Invalid project name..."

### 5.9 Bridge idle detection

**When:** `bridge.is_idle(10)` returns True (no `touch_activity` for 10+ mins) AND `has_pending_work()` returns False.
**Behavior:** Resource manager hibernates the project.
**Pending work check:** Looks for files in `followups/` dir and schedule tasks with status `in_progress` or `recurring`.

---

## 6. Commands (all parsed by `commands.parse()`)

### 6.1 User commands (any user)

| Command | Parsed as | Handler behavior |
|---------|-----------|-----------------|
| `help` or `commands` | `("help", {})` | Sends `HELP_TEXT` |
| `list` or `list projects` or `projects` | `("list", {})` | Lists projects owned by user. "No projects yet" if none. |
| `status` | `("status", {})` | Shows status for user's projects. Single project: detailed. Multiple: all shown. None: "No projects yet." |
| `status <name>` | `("status", {"project": name})` | Shows status for specific project. |
| `new project <name>` | `("new_project", {"name": name})` | Provisions new project with new channel. |
| `new <name>` | `("new_project", {"name": name})` | Shorthand for `new project <name>`. |
| `new project <name> here` | `("new_project", {"name": name, "here": True})` | Provisions project in current channel. |
| `new project here` | `("new_project", {"here": True})` | Uses channel name as project name. Only works in guild channels. |
| `new project github.com/owner/repo` | `("new_project", {"name": "repo", "github_repo": "owner/repo"})` | Clones repo. |
| `new project github.com/owner/repo here` | Same + `"here": True` | Clones repo in current channel. |
| `teardown <name>` or `tear down <name>` or `delete <name>` | `("teardown", {"project": name})` | Tears down project (owner or admin only). |
| `schedule <name>` | `("schedule", {"project": name})` | Shows project's task schedule (owner or admin only). |

### 6.2 Admin-only commands

All check `user_id == ADMIN_DISCORD_ID`. Non-admins see "Admin only."

| Command | Parsed as | Handler behavior |
|---------|-----------|-----------------|
| `status all` | `("status_all", {})` | Shows all projects with health, RAM, pending count, owner. |
| `logs <name>` | `("logs", {"project": name})` | Shows last 30 log entries (conversation history). Truncated to 1900 chars. |
| `peek <name>` | `("peek", {"project": name})` | Captures 40 lines of tmux scrollback from Claude Code pane. |
| `peek hub` | `("peek_hub", {})` | Same but for hub pane. |
| `send <name> <message>` | `("admin_send", {"project": name, "text": msg})` | Writes message to project's inbox as `admin:<user_id>`. |
| `restart <name>` | `("restart", {"project": name})` | Stops + starts Claude Code for a project. |
| `restart hub` | `("restart_hub", {})` | Stops + starts hub Claude Code, re-inits watchers. |

### 6.3 Command parsing edge cases

- `new project` (no name, no "here") -> "What do you want to call it?"
- `new project here` in DM -> tries to use `message.channel.name` which doesn't exist on DMChannel -> "Give the project a name: `new project <name> here`"
- `status` with no projects -> "No projects yet."
- Teardown by non-owner, non-admin -> "That's not your project."
- Commands are case-insensitive (text is lowered before matching).
- `new <name>` works as shorthand but `new project` prefix takes priority.

---

## 7. Background Loops & Timers

### 7.1 Hub snapshot loop

**Interval:** 60 seconds
**What it does:** Writes enriched registry snapshot, auto-restarts dead hub, re-nudges stuck hub.
See Section 4.4.

### 7.2 Reporting loop

**Interval:** 60 seconds (checks every minute)
**What it does:** For each project, checks `schedule.json` for:
- `reporting` config: time, timezone, frequency (daily/weekly). Fires once per day (tracked by `last_fired` dict).
- `morning_trip` config: time, timezone, enabled flag. Fires once per day.

**When time matches (within 5-minute window):**
1. Wakes project if hibernated.
2. Writes a nudge message to project's inbox from `delta:reporting` or `delta:morning_trip`.
3. Nudge includes style instructions for the agent.

**Report nudge content:** "Time for your report. Style: <style>. Focus on: <what_matters>. Use a Discord embed..."
**Morning trip nudge content:** "Morning trip time. Build or prototype something real, then show it..."

**Schedule time matching:** `_is_schedule_time()` checks if current hour matches and minute is within 5 of target. For weekly: only fires on Monday.

### 7.3 Resource manager loop

**Interval:** 60 seconds
**What it does:** For each active project with a bridge:
1. Syncs `bridge.last_activity` to registry (persists across restarts).
2. If idle 10+ minutes AND no pending followups AND no in_progress/recurring schedule tasks -> hibernates.

### 7.4 Outbox watcher (per project/hub)

**Type:** Daemon thread per bridge
**Interval:** Polls every 2 seconds (configurable via `outbox_poll_interval`)
**What it does:** Scans outbox dir for JSON files, calls callback, deletes processed files.
**Dedup:** Tracks `seen` file names to avoid re-processing.

### 7.5 Inbox re-nudge watcher (per project/hub)

**Type:** Daemon thread per bridge
**Interval:** Polls every 8 seconds
**What it does:** If project is active AND inbox has pending files AND pane is at prompt -> re-nudges oldest message.
**Purpose:** Catches nudges lost because Claude Code was busy.

### 7.6 Followup watcher (per project, NOT hub)

**Type:** Daemon thread per bridge
**Interval:** Polls every 10 seconds
**What it does:** Scans `followups/` dir for JSON files with `deliver_after` timestamp. If time has passed, calls callback (sends to Discord), deletes file.
**Cancellation:** `cancel_pending_followups()` deletes all files. Called when user sends a new message to the project.

---

## 8. On-Ready Startup Sequence

**Trigger:** `on_ready` Discord event.
**Steps:**
1. Log connection info and project list.
2. For each project in registry:
   - If hibernated: skip (log it).
   - If active: `_start_watchers()` (outbox, inbox, followup threads).
3. `_init_hub()`: create hub dirs, write CLAUDE.md, start tmux + Claude Code, create bridge.
4. `_start_hub_watchers()`: start hub outbox (with command interception) and inbox watchers.
5. Start `_hub_snapshot_loop()` async task.
6. Start `_reporting_loop()` async task.
7. Start `resource_manager_loop()` async task.

---

## 9. Data Flow Diagrams

### 9.1 DM -> Hub -> Discord

```
User DM -> on_message -> hub_bridge.write_inbox() -> hub inbox JSON
                                                      |
hub Claude Code reads inbox -> processes -> writes outbox JSON
                                                      |
_hub_outbox_callback -> asyncio send -> Discord channel.send()
```

### 9.2 Project Channel -> Agent -> Discord

```
User message -> on_message -> bridge.write_inbox() -> project inbox JSON
                                                       |
                              bridge.send_to_lead() -> tmux nudge
                                                       |
Project Claude Code reads inbox -> works -> writes outbox JSON
                                                       |
_outbox_callback -> asyncio send -> Discord channel.send()
```

### 9.3 Hub new_project command flow

```
Hub outbox: {"command": "new_project", ...}
     |
_hub_outbox_callback intercepts -> provision() or provision_in_channel()
     |
On success: hub_bridge.write_inbox(reply_channel, "delta:system", confirmation)
     |
Hub Claude Code reads system message -> writes response to outbox -> Discord
```

### 9.4 Agent down fallback

```
User message in project channel -> bridge.is_project_active() == False
     |
hub_bridge.write_inbox(channel_type="project_channel", project_name=name)
     |
Hub answers from registry-snapshot.json -> writes outbox -> Discord
```

---

## 10. Key File Paths

| Component | Path (LOCAL_MODE) | Path (Server) |
|-----------|------------------|---------------|
| Registry | `./delta-registry.json` | same |
| Project dir | `LOCAL_PROJECTS_DIR/<name>` | `/home/proj-<name>/<name>` |
| Project data | `<project>/delta-config/` | same |
| Hub dir | `LOCAL_PROJECTS_DIR/delta-hub` | `/opt/tetrahedron/hub` |
| Hub data | `<hub>/delta-config/` | same |
| Project template | `project-template/CLAUDE.md` | same |
| Hub template | `project-template/HUB_CLAUDE.md` | same |
| Inbox | `<data>/inbox/*.json` | same |
| Outbox | `<data>/outbox/*.json` | same |
| Logs | `<data>/logs/YYYY-MM-DD.jsonl` | same |
| Followups | `<data>/followups/*.json` | same |
| Schedule | `<data>/schedule.json` | same |
| Snapshot | `<hub>/delta-config/registry-snapshot.json` | same |
| Settings | n/a | `/root/.claude/settings.json` |

---

## 11. Message JSON Formats

### 11.1 Inbox message

```json
{
  "id": "msg-<timestamp>-<4char>",
  "channel": "<discord_channel_id>",
  "user": "<discord_user_id>" | "admin:<id>" | "delta:system" | "delta:reporting" | "delta:morning_trip",
  "text": "message content",
  "thread_ts": null,
  "timestamp": "ISO8601",
  "channel_type": "dm" | "channel" | "project_channel",  // optional, hub only
  "channel_name": "channel-name",                          // optional, hub only
  "project_name": "project-name"                           // optional, project_channel fallback only
}
```

### 11.2 Outbox message (plain text)

```json
{
  "id": "<unique-id>",
  "channel": "<discord_channel_id>",
  "text": "message content"
}
```

### 11.3 Outbox message (embed)

```json
{
  "id": "<unique-id>",
  "channel": "<discord_channel_id>",
  "text": "optional text above embed",
  "embed": {
    "title": "...",
    "description": "...",
    "color": 3066993,
    "fields": [{"name": "...", "value": "...", "inline": false}],
    "footer": "..."
  }
}
```

### 11.4 Hub command: new_project

```json
{
  "id": "cmd-<ts>",
  "command": "new_project",
  "name": "project-name",
  "owner_discord_id": "123456789",
  "reply_channel": "<channel_id>",
  "github_repo": "",
  "use_channel": "<channel_id>"  // optional, for in-channel provisioning
}
```

### 11.5 Hub command: forward

```json
{
  "id": "fwd-<ts>",
  "command": "forward",
  "target_project": "project-name",
  "text": "message to forward",
  "user": "123456789",
  "reply_channel": "<channel_id>"
}
```

### 11.6 Followup message

```json
{
  "id": "followup-<ts>",
  "channel": "<channel_id>",
  "text": "follow-up message",
  "deliver_after": "ISO8601 timestamp"
}
```

---

## 12. Thread Safety Notes

- `Registry` uses `threading.Lock` for all read/write operations.
- `ProjectBridge._shutdown_event` is `threading.Event` for graceful watcher shutdown.
- Outbox/inbox/followup watchers run in daemon threads.
- Discord API calls from threads use `asyncio.run_coroutine_threadsafe()`.
- Bridges dict is mutated from main thread (on_message, on_ready) and resource manager.

---

## 13. Important Behavioral Details

### 13.1 Pane-at-prompt detection

`_is_pane_at_prompt()` checks last 5 lines of tmux pane for the `>` (U+276F) or `>` Unicode character. This indicates Claude Code TUI is ready for input.

### 13.2 Nudge mechanism

`_nudge()` sends keystrokes to tmux pane using `tmux send-keys -l` (literal text), followed by Enter. The text is: `"Process message from <prefix>/<msg_id>.json"`.

### 13.3 Followup cancellation

When a user sends a message to a project channel, ALL pending followups are cancelled. This is intentional: the user re-engaged, so no nudges needed.

### 13.4 Hub is never hibernated

The hub lives only in the `bridges` dict, not in the registry. The resource manager only iterates registry projects. The snapshot loop handles hub keepalive separately.

### 13.5 `new project` command: `is_dm` and `channel_id` variables

In `_handle_command("new_project", ...)`, the code references `is_dm` and `channel_id` (lines 310, 318). These are NOT parameters of `_handle_command` -- they come from the `on_message` closure context. This is a **potential bug**: `_handle_command` receives `message` but relies on `is_dm` and `channel_id` being in scope from the enclosing `on_message` function. Since `_handle_command` is only called from within `on_message`, this works but is fragile.

### 13.6 Dream space flag

`provision()` accepts `is_dream_space=True`. Hub-initiated provisions with `use_channel` set this. Stored in registry but not used anywhere else currently.

### 13.7 Schedule task format

The schedule reader (`_read_project_schedule`) handles multiple field names for task descriptions: `what`, then `name`, then `description`. This provides backward compatibility.
