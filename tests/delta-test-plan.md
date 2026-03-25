# Delta Test Plan

End-to-end test plan for the Delta Discord bot. Tests are ordered by dependency: earlier tests create state that later tests rely on.

**Test environment:** Playwright browser automation against Discord web UI.
**Bot under test:** Delta (running on server or LOCAL_MODE).
**Test user:** The admin user (ADMIN_DISCORD_ID) to access all commands.
**Test guild:** The Discord server where Delta is a member.

---

## Prerequisites

Before running any tests:
1. Delta bot is running and online (green presence in Discord).
2. Test user is logged into Discord web UI via Playwright.
3. A general/non-project channel exists for @mention tests.
4. No project named `test-project` exists (clean state).

---

## Phase 1: DM Commands (Direct Response Tests)

These tests verify commands sent via DM that Delta handles directly (no hub involvement). Each produces an immediate, deterministic response.

### T1.1 -- help command via DM

**Input:** DM to Delta: `help`
**Expected output:** Message containing "Getting started" AND "`new project <name>`" AND "Your projects" AND "Admin"
**Exact strings to match:** Contains `**Getting started**`, `**Your projects**`, `**Admin**`
**Variants to test:** Also send `commands` (alias for help). Same output expected.

### T1.2 -- list command with no projects

**Input:** DM to Delta: `list`
**Expected output:** "No projects yet. Say `new project <name>` and I'll set one up for you."
**Variants:** Also test `projects` and `list projects`. Same output.

### T1.3 -- status command with no projects

**Input:** DM to Delta: `status`
**Expected output:** "No projects yet."

### T1.4 -- status all (admin only)

**Input:** DM to Delta: `status all`
**Expected output:** Either "No projects running." (if no projects exist) or a message starting with "**N projects:**" listing projects with `+`/`-`/`z` icons.
**Admin gate:** If tested with a non-admin user, expect "Admin only."

### T1.5 -- new project with no name

**Input:** DM to Delta: `new project`
**Expected output:** Contains "What do you want to call it?" AND "`new project <name>`"

### T1.6 -- teardown nonexistent project

**Input:** DM to Delta: `teardown nonexistent-proj`
**Expected output:** "No project called **nonexistent-proj**."

### T1.7 -- logs for nonexistent project (admin)

**Input:** DM to Delta: `logs nonexistent-proj`
**Expected output:** "No project called **nonexistent-proj**."

### T1.8 -- peek for nonexistent project (admin)

**Input:** DM to Delta: `peek nonexistent-proj`
**Expected output:** "No project called **nonexistent-proj**."

### T1.9 -- restart nonexistent project (admin)

**Input:** DM to Delta: `restart nonexistent-proj`
**Expected output:** "No project called **nonexistent-proj**."

### T1.10 -- peek hub (admin)

**Input:** DM to Delta: `peek hub`
**Expected output:** A code block (``` delimited) with tmux scrollback content. Should NOT be "Hub not initialized."

### T1.11 -- admin commands gate (non-admin)

**Input (non-admin user):** DM: `status all`
**Expected output:** "Admin only."
**Note:** Only testable if a second non-admin user account is available. Skip if single-user testing.

---

## Phase 2: Project Creation

These tests create a project and verify the full provisioning flow. Subsequent phases depend on the project created here.

### T2.1 -- create project via DM command

**Input:** DM to Delta: `new project test-project`
**Expected output (message 1):** "Setting up **test-project**. One moment."
**Expected output (message 2):** Contains "**test-project** is live." AND a channel link `<#...>`
**Post-conditions to verify:**
- A new channel `proj-test-project` exists under "Delta Projects" category.
- Channel is visible to the test user.

### T2.2 -- create duplicate project

**Input:** DM to Delta: `new project test-project`
**Expected output:** "Could not set up: Project 'test-project' already exists"

### T2.3 -- create project with invalid name

**Input:** DM to Delta: `new project !!invalid`
**Expected output:** Contains "Could not set up: Invalid project name"
**Variants:** Test with `a` (too short, 1 char), `this-name-is-way-too-long-for-the-validation-regex-to-accept` (>30 chars).

### T2.4 -- create project with shorthand

**Input:** DM to Delta: `new test-shorthand`
**Expected output (message 1):** "Setting up **test-shorthand**. One moment."
**Expected output (message 2):** Contains "**test-shorthand** is live."
**Cleanup:** Teardown `test-shorthand` after verifying.

### T2.5 -- list after project creation

**Input:** DM to Delta: `list`
**Expected output:** Contains "**test-project**"

### T2.6 -- status after project creation

**Input:** DM to Delta: `status`
**Expected output:** Contains "**test-project**" AND one of: "running, building things" or "session alive but Claude Code stopped" or "offline"
**Note:** "running, building things" if Claude Code booted successfully.

### T2.7 -- status for specific project

**Input:** DM to Delta: `status test-project`
**Expected output:** Contains "**test-project**" AND "inbox clear" or "messages waiting"

---

## Phase 3: Project Channel Interaction

Tests require the `proj-test-project` channel to exist (from Phase 2).

### T3.1 -- send message in project channel (agent running)

**Input:** Navigate to `proj-test-project` channel, send: `hello, what can you do?`
**Expected output:** No immediate response from Delta's `on_message` handler (no error messages). The message is written to the project's inbox and nudged to Claude Code.
**Async response:** Within 30-120 seconds, a response should appear from Delta (the project agent's outbox message). Content is non-deterministic (Claude Code generates it).
**What to verify:**
- No error message like "Something's off with..." appears.
- No "waking up" message (project should be active from Phase 2).
- Eventually a response appears from the bot.

### T3.2 -- send message in non-project channel (no @mention)

**Input:** Navigate to a general channel (not a project channel), send: `hello everyone`
**Expected output:** Delta does NOT respond. No message from the bot appears within 10 seconds.
**What to verify:** Bot remains silent.

### T3.3 -- @mention in non-project channel

**Input:** In a general channel, send: `@Delta how are you?`
**Expected output:** No immediate deterministic response from Delta's message handler. Message is routed to hub.
**Async response:** Hub should respond within 30-120 seconds via its outbox.
**What to verify:**
- No error messages ("Something's off...", "I'm waking up...").
- Eventually a response appears from the bot.

### T3.4 -- @mention with command in non-project channel

**Input:** In a general channel, send: `@Delta help`
**Expected output:** Same help text as T1.1 (contains "Getting started", "Your projects", "Admin").

### T3.5 -- @mention with new project here

**Input:** In a general channel, send: `@Delta new project channel-test here`
**Expected output (message 1):** "Setting up **channel-test**. One moment."
**Expected output (message 2):** Contains "**channel-test** is live right here."
**Post-condition:** The current general channel is now mapped to the `channel-test` project.
**Cleanup:** Teardown `channel-test` after verifying.

---

## Phase 4: DM to Hub (Non-Command Messages)

These test the hub routing path for DMs that aren't recognized commands.

### T4.1 -- casual DM (greeting)

**Input:** DM to Delta: `hey, what's up?`
**Expected output:** Not an immediate Delta response (this goes to hub). Hub should respond within 30-120 seconds.
**What to verify:**
- No error messages ("Something's off...", "I'm waking up...").
- Bot eventually responds (content is non-deterministic, generated by hub Claude Code).

### T4.2 -- DM asking about projects

**Input:** DM to Delta: `how's my project doing?`
**Expected output:** Hub responds using snapshot data. Should mention `test-project` if it exists.
**What to verify:** Response appears within 30-120 seconds. Contains some reference to user's projects.

### T4.3 -- DM with project creation intent (hub-routed)

**Input:** DM to Delta: `I want to build a recipe app called recipe-hub`
**Expected output:** Hub interprets this as project creation intent and either:
- Asks for clarification, OR
- Issues a `new_project` command and reports back with a channel link.
**What to verify:** A response appears. If a project is created, a new channel appears.
**Cleanup:** Teardown `recipe-hub` if created.

---

## Phase 5: Admin Commands (with existing project)

Requires `test-project` from Phase 2 to exist.

### T5.1 -- status all with projects

**Input:** DM to Delta: `status all`
**Expected output:** Contains "projects:" AND "**test-project**" AND one of `+`/`-`/`z` icons.

### T5.2 -- logs for project

**Input:** DM to Delta: `logs test-project`
**Expected output:** Either log entries (lines with timestamps, `>>>` or `<<<` direction markers) OR "No recent logs."

### T5.3 -- peek at project

**Input:** DM to Delta: `peek test-project`
**Expected output:** A code block (``` delimited) containing tmux scrollback. Should contain some Claude Code output.

### T5.4 -- send message to project (admin)

**Input:** DM to Delta: `send test-project hello from admin`
**Expected output:** "Sent to **test-project**."
**Post-condition:** The message should appear in the project's inbox (can verify by checking if agent responds in the project channel).

### T5.5 -- restart project

**Input:** DM to Delta: `restart test-project`
**Expected output (message 1):** "Restarting Claude Code for **test-project**..."
**Expected output (message 2):** Either "**test-project** Claude Code restarted." or "Failed to restart..."

### T5.6 -- restart hub

**Input:** DM to Delta: `restart hub`
**Expected output (message 1):** "Restarting hub..."
**Expected output (message 2):** "Hub restarted."

### T5.7 -- schedule for project

**Input:** DM to Delta: `schedule test-project`
**Expected output:** Either "**test-project** has no tasks scheduled yet." OR a schedule listing with task icons (`>`, `+`, `~`, `-`).

### T5.8 -- schedule for nonexistent project

**Input:** DM to Delta: `schedule nonexistent-proj`
**Expected output:** "No project called **nonexistent-proj**."

---

## Phase 6: Teardown

### T6.1 -- teardown project (owner)

**Input:** DM to Delta: `teardown test-project`
**Expected output (message 1):** "Shutting down **test-project**."
**Expected output (message 2):** "**test-project** is gone. Channel deleted, user removed, everything cleaned up."
**Post-conditions:**
- Channel `proj-test-project` no longer exists.
- `list` command no longer shows `test-project`.

### T6.2 -- teardown already-torn-down project

**Input:** DM to Delta: `teardown test-project`
**Expected output:** "No project called **test-project**."

### T6.3 -- teardown with delete alias

**Input:** DM to Delta: `delete some-project`
**Expected output:** "No project called **some-project**." (since it doesn't exist)
**Purpose:** Verify `delete` is parsed as `teardown`.

### T6.4 -- list after teardown

**Input:** DM to Delta: `list`
**Expected output:** Should NOT contain "test-project". Either "No projects yet." or list without it.

---

## Phase 7: Edge Cases & Error Paths

### T7.1 -- bot ignores its own messages

**Verification:** Send a message, observe bot responds. The bot's own response should not trigger another response (infinite loop check).
**How to test:** After any bot response, wait 15 seconds. No additional bot messages should appear that weren't triggered by user input.

### T7.2 -- empty message

**Input:** Send an empty message (if Discord allows) or whitespace-only.
**Expected output:** Bot does not respond (filtered at `if not text: return`).
**Note:** Discord UI may not allow sending empty messages. This may need to be skipped.

### T7.3 -- very long message

**Input:** DM to Delta: A message with 2000+ characters of text.
**Expected output:** Bot processes normally. No crash. Text is truncated to 2000 chars in logs.

### T7.4 -- case insensitivity of commands

**Input:** DM: `HELP`
**Expected output:** Same help text as T1.1.
**Input:** DM: `Status`
**Expected output:** Same as `status` command.
**Input:** DM: `NEW PROJECT test-case`
**Expected output:** Same provisioning behavior.

### T7.5 -- new project here in DM

**Input:** DM to Delta: `new project here`
**Expected output:** "Give the project a name: `new project <name> here`"
**Reason:** DMChannel has no `.name` attribute.

### T7.6 -- teardown by non-owner

**Setup:** Create a project owned by user A.
**Input (user B, non-admin):** DM: `teardown <project>`
**Expected output:** "That's not your project."
**Note:** Requires two test accounts. Skip if single-user.

---

## Phase 8: Hub Fallback (Agent Down)

### T8.1 -- project agent down, message in project channel

**Setup:** Create a project, then stop its Claude Code (via `restart` or manually).
**Input:** Send a message in the project channel.
**Expected output:** Hub receives the message with `channel_type="project_channel"` and responds from snapshot data. User should NOT see "agent is down" or error messages. Response should be substantive.
**What to verify:** A response appears from the bot (hub fallback). No error messages visible.

---

## Test Execution Order

Tests MUST run in this order due to state dependencies:

```
Phase 1: T1.1 -> T1.2 -> T1.3 -> T1.4 -> T1.5 -> T1.6 -> T1.7 -> T1.8 -> T1.9 -> T1.10
Phase 2: T2.1 -> T2.2 -> T2.3 -> T2.4 -> T2.5 -> T2.6 -> T2.7
Phase 3: T3.1 -> T3.2 -> T3.3 -> T3.4 -> T3.5
Phase 4: T4.1 -> T4.2 -> T4.3
Phase 5: T5.1 -> T5.2 -> T5.3 -> T5.4 -> T5.5 -> T5.6 -> T5.7 -> T5.8
Phase 6: T6.1 -> T6.2 -> T6.3 -> T6.4
Phase 7: T7.1 -> T7.3 -> T7.4 -> T7.5
Phase 8: T8.1 (requires separate setup)
```

Key dependencies:
- Phase 2 creates `test-project` used by Phases 3, 5, and 6.
- Phase 6 tears down `test-project`, so must come after Phases 3 and 5.
- Phase 3 and 5 are independent of each other.
- Phase 7 tests are mostly independent but T7.4 with `NEW PROJECT` should be run before Phase 6.
- Phase 8 requires manual agent kill, best run as a separate sequence.

---

## Playwright Implementation Notes

### Selectors

Discord web UI elements:
- **Message input:** `div[role="textbox"]` (contenteditable div in channel/DM)
- **Messages:** `li[id^="chat-messages"]` or `div[class*="message"]`
- **Bot messages:** Filter messages by bot's username/avatar
- **Channel list:** `a[data-list-item-id]` in the channel sidebar
- **DM list:** Navigate via Discord home -> DM section

### Timing

- **Immediate responses** (commands handled by Delta directly): should appear within 2-5 seconds.
- **Hub/agent responses** (routed through Claude Code): may take 30-120 seconds. Use long timeouts with polling.
- **Project creation:** The "Setting up..." message is immediate. The "is live" follow-up takes 5-15 seconds.
- **Teardown:** "Shutting down..." is immediate. Cleanup completion takes 2-10 seconds.

### Message Detection Strategy

1. Before sending a test message, record the ID/timestamp of the last bot message in the channel.
2. Send the test message.
3. Poll for new bot messages (messages after the recorded timestamp).
4. Apply assertions on the new bot message(s).

### DM Navigation

To DM the bot:
1. Navigate to Discord home.
2. Click on the bot's DM conversation (or start a new one).
3. Type in the message input and send.

### Channel Navigation

To navigate to a project channel:
1. Look for `proj-<name>` in the channel sidebar.
2. Click on it.
3. Verify channel loaded by checking the channel header.

---

## Response Assertion Patterns

| Pattern | Type | Example |
|---------|------|---------|
| Exact match | Full string equals | "Admin only." |
| Contains | Substring present | contains "Getting started" |
| Starts with | Prefix match | starts with "Setting up **" |
| Regex | Pattern match | matches `\*\*\d+ projects:\*\*` |
| Not present | Absence check | does NOT contain "error" |
| Message count | Number of bot replies | exactly 2 messages |
| Embed present | Has embed (colored sidebar) | message has embed component |
| Code block | Has ``` delimited content | contains ``` markers |

---

## Cleanup Procedure

After all tests complete:
1. Teardown any projects created during testing: `teardown test-project`, `teardown test-shorthand`, `teardown channel-test`, `teardown recipe-hub`.
2. Verify `list` returns "No projects yet."
3. Verify no orphaned channels remain under "Delta Projects" category.
