# Delta Testing Patterns

Extracted from the Delta codebase. 262 unit tests, 60+ E2E test cases.

---

## 1. Unit Test Patterns

### 1.1 Test file structure

16 test files in `tests/`, each covering one module:

| File | Module | Test count | Pattern |
|------|--------|-----------|---------|
| test_commands.py | delta.commands | 24 | Parser combinatorics |
| test_connections.py | delta.connections | 16 | SDK wrapper mocking |
| test_dm_persistent_routing.py | delta.app (DM routing) | 32 | DM session persistence |
| test_enriched_snapshot.py | delta.app (snapshot) | 18 | Registry snapshot enrichment |
| test_forward_access_control.py | delta.app (forwarding) | 5 | Message forwarding permissions |
| test_gh_auth.py | delta.app (GitHub) | 8 | GitHub auth flow |
| test_isolation.py | delta.isolation | 9 | Subprocess mocking |
| test_last_fired.py | delta.app (last_fired) | 7 | Persistence roundtrip |
| test_lifecycle.py | delta.lifecycle | 14 | Process management mocking |
| test_onboarding_intake.py | delta.app (onboarding) | 10 | Chiron onboarding flow |
| test_project_bridge.py | delta.project_bridge | 15 | Bridge I/O, auth detection |
| test_registry.py | delta.registry | 12 | JSON persistence, CRUD |
| test_restore_on_startup.py | delta.app (restore) | 6 | Restore state machine |
| test_router.py | delta.router | 6 | Lookup resolution |
| test_schedule_delta.py | delta.app (schedule) | 76 | Schedule timing, persistence |
| test_teardown_cleanup.py | delta.provisioner | 4 | Async teardown, safety checks |

### 1.2 Fixture patterns

**conftest.py provides three shared fixtures:**

```python
@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create inbox/outbox/logs directories."""
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    logs = tmp_path / "logs"
    inbox.mkdir()
    outbox.mkdir()
    logs.mkdir()
    return tmp_path

@pytest.fixture
def charlie_env(tmp_data_dir, monkeypatch):
    """Set env vars pointing to temp dirs."""
    monkeypatch.setenv("CHARLIE_CONFIG_DIR", str(tmp_data_dir))
    monkeypatch.setenv("CHARLIE_DATA_DIR", str(tmp_data_dir))
    # ...

@pytest.fixture
def sample_schedule_yaml(tmp_path):
    """Write a YAML schedule file to tmp_path."""
    content = """..."""
    yaml_file = tmp_path / "schedule.yaml"
    yaml_file.write_text(content)
    return yaml_file
```

**Key pattern: fixtures return paths, not objects.** The test imports and reloads the module after env vars are set. This prevents stale module-level config.

**Per-test fixtures using tmp_path:**

```python
@pytest.fixture
def bridge(tmp_path):
    return ProjectBridge(
        name="test-project",
        data_dir=str(tmp_path),
        tmux_lead_pane="test:lead",
    )
```

Any module that reads from filesystem (inbox/outbox, config files, schedules) should use `tmp_path` fixtures with pre-created directory structure.

### 1.3 Mocking patterns

**Pattern A: subprocess mocking for shell commands**

Used by: test_isolation.py, test_lifecycle.py

```python
@patch("delta.isolation.subprocess.run")
def test_create_user_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stderr="")
    result = create_user("myapp")
    assert result == "proj-myapp"
    assert mock_run.call_count == 2
    useradd_call = mock_run.call_args_list[0]
    assert "useradd" in useradd_call[0][0]
```

Helper to reduce boilerplate:
```python
def _mock_run(returncode=0, stdout="", stderr=""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)
```

**Pattern B: side_effect for multi-call sequences**

Used when a function makes multiple subprocess calls in sequence:

```python
@patch("delta.lifecycle._run")
def test_is_claude_running_true(mock_run):
    mock_run.side_effect = [
        _mock_run(0),            # has-session
        _mock_run(0, "12345"),   # list-panes pane_pid
        _mock_run(0, "67890"),   # pgrep -P
        _mock_run(0, "claude"),  # ps -p <pid> -o command=
    ]
    assert is_claude_running("myproject:lead") is True
```

**Pattern C: patch.object for method replacement**

Used for internal method mocking within a class:

```python
def test_detects_401(self, bridge):
    with patch.object(bridge, "capture_tmux_scrollback",
                      return_value="Error: API returned 401"):
        result = bridge.check_auth_error()
        assert result is not None
```

**Pattern D: monkeypatch for module-level config**

Used when a module reads config at import time:

```python
def test_detect_alerts_with_keywords(charlie_env, monkeypatch):
    import charlie.config
    importlib.reload(charlie.config)
    monkeypatch.setattr(charlie.config, "ALERT_KEYWORDS", ["error", "failed"])
    import charlie.bridge
    importlib.reload(charlie.bridge)
```

**Pattern E: Composio SDK mocking (layered fixtures)**

```python
@pytest.fixture
def mock_composio():
    mock_client = MagicMock()
    with patch("delta.connections._get_client", return_value=mock_client):
        yield mock_client

@pytest.fixture
def mock_composio_none():
    with patch("delta.connections._get_client", return_value=None):
        yield
```

Then tests use the fixture name to select which mock layer:
```python
def test_returns_redirect_url(self, mock_composio):
    entity = MagicMock()
    req = MagicMock()
    req.redirectUrl = "https://composio.dev/auth/hubspot"
    # ...
```

**Pattern F: patch("delta.app.datetime") for time-dependent logic**

```python
def test_matches_exact_time(self):
    with patch("delta.app.datetime") as mock_dt:
        mock_now = datetime(2026, 3, 2, 9, 0, tzinfo=ZoneInfo("UTC"))
        mock_dt.now.return_value = mock_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        assert fn("09:00", "UTC") is True
```

The `side_effect` trick is critical: it lets `datetime(...)` constructor calls pass through to the real datetime while `.now()` is mocked.

**Pattern G: MagicMock factories for domain objects**

```python
def _make_project_info(name, status="active", tmux_session=None, ...):
    info = MagicMock()
    info.name = name
    info.status = status
    info.tmux_session = tmux_session or f"proj-{name}"
    # ...
    return info
```

### 1.4 Assertion patterns

**Direct equality:** `assert result == "proj-myapp"`

**Substring in output:** `assert "useradd" in useradd_call[0][0]`

**Not present:** `assert registry.find_by_discord_channel("UNKNOWN") is None`

**Collection membership:** `assert set(result) == {"audioworld", "projectb"}`

**File existence after operation:** `assert inbox_file.exists()` / `assert not (outbox_dir / "test-1.json").exists()`

**JSON roundtrip:** Parse file, check fields:
```python
data = json.loads(inbox_file.read_text())
assert data["channel"] == "C123"
assert data["text"] == "hello world"
```

**Call count and args:**
```python
mock_start.assert_called_once_with("/root/project-b", "project-b:lead")
mock_stop.assert_not_called()
assert mock_run.call_count == 2
```

**Exception raising:**
```python
with pytest.raises(RuntimeError, match="useradd failed"):
    create_user("myapp")
```

### 1.5 Test categories by what they test

**Pure logic tests** (no I/O, no mocks): test_commands.py, test_schedule.py. These test parse functions and time-slot math. Fastest to write and most reliable.

**Filesystem I/O tests**: test_bridge.py, test_registry.py, test_project_bridge.py. Use `tmp_path` for isolation. Test write-then-read roundtrips.

**Subprocess mock tests**: test_isolation.py, test_lifecycle.py. Mock `subprocess.run` to test command construction without running actual commands.

**State machine tests**: test_restore_on_startup.py. Mock multiple dependencies to test transition logic.

**Async tests**: test_teardown_cleanup.py. Use `@pytest.mark.asyncio` with `AsyncMock` and multiple `patch` context managers.

**Threading tests**: test_schedule_delta.py (watch_followups). Start threads, sleep, verify delivery, then shut down:
```python
t = threading.Thread(target=run_watcher, daemon=True)
t.start()
time.sleep(1.5)
bridge.shutdown()
t.join(timeout=15)
assert len(delivered) == 1
```

### 1.6 Test organization patterns

**Class-based grouping for related tests:**

```python
class TestCheckAuthError:
    def test_returns_none_when_no_error(self, bridge): ...
    def test_detects_401(self, bridge): ...
    def test_detects_oauth_token_expired(self, bridge): ...

class TestWriteInbox:
    def test_creates_inbox_file(self, bridge): ...
    def test_extra_kwargs_merged(self, bridge): ...
```

**Function-based for simpler modules:**

```python
def test_parse_help():
    assert parse("help") == ("help", {})

def test_parse_list():
    assert parse("list") == ("list", {})
```

Use classes when testing a single method across many edge cases (auth detection, schedule timing). Use functions for combinatorial testing (command parsing).

### 1.7 Robustness testing patterns

**Corrupt input handling:**
```python
def test_corrupt_file_loads_ok(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not json at all")
    r = Registry(f)
    assert r.list_projects() == []
```

**Missing file handling:**
```python
def test_returns_empty_when_no_file(self, tmp_path):
    with patch.object(app, "_LAST_FIRED_PATH", tmp_path / "missing.json"):
        assert app._load_last_fired() == {}
```

**Boundary conditions:**
```python
def test_slot_boundary_start_inclusive(self):
    slot = Slot("09:00", "13:00", ["mon"])
    dt = datetime(2026, 3, 2, 9, 0, ...)
    assert slot.contains(dt) is True

def test_slot_boundary_end_exclusive(self):
    slot = Slot("09:00", "13:00", ["mon"])
    dt = datetime(2026, 3, 2, 13, 0, ...)
    assert slot.contains(dt) is False
```

**Sandbox safety (deletion guards):**
```python
async def test_teardown_refuses_outside_sandbox(tmp_registry, tmp_path, local_projects_dir):
    outside_dir = tmp_path / "outside-project"
    outside_dir.mkdir()
    (outside_dir / "important.txt").write_text("don't delete me")
    # ... teardown ...
    assert outside_dir.exists()  # must NOT be deleted
    assert (outside_dir / "important.txt").exists()
```

### 1.8 Polling loop testing pattern

For functions that run in infinite loops (outbox watcher, followup watcher), the pattern is:

1. Replace `sleep` or `event.wait` with a counter that breaks after N iterations
2. Pre-populate the directory with test data
3. Run the loop
4. Assert on collected results

```python
def test_outbox_watcher_processes_files(charlie_env):
    # Pre-populate outbox
    (outbox_dir / "test-1.json").write_text(json.dumps(test_data))

    results = []
    call_count = 0

    def limited_sleep(secs):
        nonlocal call_count
        call_count += 1
        if call_count > 1:
            raise KeyboardInterrupt
        original_sleep(0.01)

    with patch.object(charlie.bridge.time, "sleep", limited_sleep):
        try:
            charlie.bridge.watch_outbox(fake_callback)
        except KeyboardInterrupt:
            pass

    assert len(results) == 1
```

---

## 2. E2E Test Methodology (Playwright + Discord)

### 2.1 Architecture

E2E tests use Playwright to control Chrome via CDP (Chrome DevTools Protocol). The browser is already logged into Discord as the test user. Tests connect to the existing browser session rather than launching a new one.

```
Playwright script -> CDP (port 9222) -> Chrome -> Discord web UI -> Delta bot
```

### 2.2 CDP connection pattern

Every Playwright script follows this boilerplate:

```python
CDP_PORT = 9222

def ensure_chrome_cdp():
    """Check if Chrome CDP is available, relaunch if needed."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', CDP_PORT))
    sock.close()
    if result == 0:
        return True
    # Relaunch Chrome with --remote-debugging-port=9222
    subprocess.Popen([
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        f"--remote-debugging-port={CDP_PORT}",
        "--restore-last-session",
    ], ...)

def get_discord_page(browser):
    """Find Discord tab in existing browser contexts."""
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "discord" in pg.url.lower():
                pg.bring_to_front()
                return pg
    # Fallback: open Discord
    ctx = browser.contexts[0]
    pg = ctx.new_page()
    pg.goto("https://discord.com/channels/@me")
    return pg
```

### 2.3 Discord interaction helpers

Five reusable functions across all test scripts:

```python
def send_message(page, text):
    """Send a message in the current Discord chat."""
    msg_input = page.locator('[role="textbox"]').last
    msg_input.click()
    time.sleep(0.5)
    page.keyboard.press("Meta+a")
    page.keyboard.press("Backspace")
    page.keyboard.type(text, delay=30)
    time.sleep(0.5)
    page.keyboard.press("Enter")

def scroll_to_bottom(page):
    """Scroll the message area to the bottom."""
    page.evaluate("""
        const scroller = document.querySelector('[class*="scroller"][class*="messages"]')
            || document.querySelector('[data-list-id="chat-messages"]')
            || document.querySelector('ol[class*="scrollerInner"]')?.parentElement;
        if (scroller) scroller.scrollTop = scroller.scrollHeight;
    """)

def shot(page, name):
    """Screenshot with auto-scroll to bottom."""
    scroll_to_bottom(page)
    time.sleep(1)
    page.screenshot(path=f"{SCREENSHOTS}/{name}.png")
```

### 2.4 Navigation patterns

**Go to DMs:**
```python
home_btn = page.locator('a[href="/channels/@me"]').first
home_btn.click()
```

**Find a bot's DM:**
```python
delta_dm = page.locator('a[aria-label*="Delta"]').first
delta_dm.click()
```

**Find a server in sidebar:**
```python
servers = page.locator('[data-list-item-id^="guildsnav___"]')
for i in range(servers.count()):
    label = servers.nth(i).get_attribute("aria-label") or ""
    if "seed" in label.lower():
        servers.nth(i).click()
        break
```

**@mention via autocomplete (critical -- raw text does not work):**
```python
page.keyboard.type("@Delta", delay=80)
time.sleep(2)
auto_items = page.locator('[id*="autocomplete"][role="option"]')
if auto_items.count() > 0:
    auto_items.first.click()
```

### 2.5 Test script taxonomy

Five scripts serving different purposes:

| Script | Purpose | Usage |
|--------|---------|-------|
| test-hub.py | Full multi-step test suite | `python3 test-hub.py` (runs 8 tests sequentially) |
| test-step.py | One step at a time | `python3 test-step.py send-hey` |
| test-action.py | Generic actions with args | `python3 test-action.py send "hello" 20 shot-name` |
| test-scroll.py | Scroll and screenshot | `python3 test-scroll.py up scrolled-up` |
| test-nav.py | Navigate Discord UI | `python3 test-nav.py click-s` |

**Reusable for Vinod:** The three-tier approach works well:
1. **Full suite script** for regression testing
2. **Step-based script** for interactive debugging
3. **Action-based script** for ad-hoc operations

### 2.6 Screenshot-based verification

All E2E tests use screenshots as the primary evidence mechanism. The naming convention:

```
{phase}-{step}-{description}.png
```

Examples:
- `phase1-step0-delta-dm-loaded.png`
- `sprint2-test2-18-rube-auth-fail.png`
- `t1-step4-vercel-link-delivered.png`
- `round5-delivery-visible.png`

Screenshots are saved to `/test-screenshots/` with subdirectories for sprints (`sprint3/`, `sprint3-rerun/`).

**Pattern: before/after pairs.** Every test takes a screenshot before sending a message and after receiving a response.

**Pattern: waiting checkpoints.** Long-running tests take screenshots at intervals:
```
t4-step1-waiting-30s.png
t4-step2-waiting-90s.png
t4-step3-waiting-180s-stuck.png
```

### 2.7 Timing patterns

| Response type | Expected wait | Pattern |
|--------------|---------------|---------|
| Direct command (help, status, list) | 2-5 seconds | `time.sleep(10)` |
| Hub response (DM routing) | 30-120 seconds | `time.sleep(20)` then check, retry |
| Project creation | 5-30 seconds | `time.sleep(30)` |
| Agent build response | 1-5 minutes | Multiple checkpoint screenshots |
| Teardown | 2-10 seconds | `time.sleep(10)` |

### 2.8 Limitations discovered

1. **@mention via Playwright fails with raw text.** Discord needs the autocomplete popup to convert `@Delta` to `<@BOT_ID>`. Raw typed text is literal, not a mention.

2. **Empty messages can't be sent.** Discord UI blocks it. Skip this test.

3. **Browser crashes during long waits.** Playwright MCP disconnects if the browser process dies. Round 7 was lost to this.

4. **No programmatic assertion on message content.** Screenshots are visual evidence but can't be asserted in code. The tester (human or agent) must interpret screenshots.

5. **Single-user testing only.** No way to simulate a second Discord user without a second account.

---

## 3. UX Research Methodology

### 3.1 Trust score framework

The core metric is a composite trust score (1-10) computed across weighted dimensions. The framework evolved across 4 sprints:

**Sprint 1 dimensions (4):**

| Dimension | What it measures |
|-----------|-----------------|
| Speed to Magic | Time from request to working result |
| Accompaniment | User feels accompanied during wait |
| Intelligence | Agent understands intent, adds value |
| Autonomy | Agent acts without unnecessary questions |

**Sprint 3 dimensions (6, with weights):**

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| Speed to Magic | 1x | Time from request to result |
| Accompaniment | 2x | Max gap between messages during build |
| Intelligence | 1x | Intent understanding, delivery method selection |
| Autonomy | 1x | Acts without unnecessary questions |
| Security Confidence | 1x | User feels data is safe during auth |
| Reliability | 2x | Scheduled tasks fire consistently |

**Calculation:** Weighted average of all dimension scores.

### 3.2 Scoring rubrics

**Accompaniment (by max gap between messages):**

| Gap | Score |
|-----|-------|
| < 20s | 10 |
| 20-35s | 9 |
| 35-50s | 8 |
| 50-65s | 7 |
| 65-90s | 6 |
| 90-120s | 5 |
| 120s+ | 4 |

Content quality modifier:
- 0 = generic ("still working") -- caps at 5
- 1 = activity ("building report") -- caps at 7
- 2 = specific info ("found 23 stale leads") -- no cap

Final Accompaniment = min(gap_score, content_quality_cap)

**Reliability (schedule fire accuracy):**

| Behavior | Score |
|----------|-------|
| Fires within 60s, every time | 10 |
| Fires within 2 min, every time | 9 |
| Fires within 5 min, or one late | 8 |
| Correct setup, fire unverified | 7 |
| One missed delivery | 6 |
| Wrong time (timezone bug) | 4 |
| Multiple misses | 3 |

**Real-language tests (7 dimensions):**
1. Problem understanding (binary)
2. Right tool suggestion (binary)
3. Self-initiated connection (binary)
4. Solve vs display (10/4/0)
5. Felt understood (1-10)
6. Language matching (1-10)
7. Connection invisibility (binary)

### 3.3 Trust score progression

| Sprint | Score | Key change |
|--------|-------|------------|
| Sprint 1 Round 1 | 6.0 | False auth lockouts, no status transparency |
| Sprint 1 Round 2 | 7.5 | Auth fix, multi-turn works |
| Sprint 1 Round 3 | 8.5 | Typing indicator, honest status |
| Sprint 1 Round 7 | 9.0 | "Build for the medium" template change |
| Sprint 2 (Vercel) | 8.5 | Live URL delivery works |
| Sprint 2 (all) | 7.0 | Inconsistency across channels |
| Sprint 2.5 | 8.9 | 3 delivery channels working |
| Sprint 3 | 7.9 | Harder test suite, new dimensions |

### 3.4 Per-test scoring template

Each test in the UX report follows this format:

```markdown
### S2: Streaming -- Simple Build

**Prompt:** "rebuild the landing page from scratch"

| Dimension | Score | Notes |
|-----------|-------|-------|
| Speed to Magic | 8 | 3 min total |
| Accompaniment | 5 | 2 min gap, 1 nudge |
| Intelligence | 9 | Correct build, rich embed |
| Autonomy | 10 | Zero questions |

**Composite: 7.4** (weighted)
**Verdict:** Marginal streaming improvement.
```

### 3.5 Before/After comparison pattern

Sprint reports include explicit before/after tables for fixes:

```markdown
| Test | Before Fix | After Fix | Improvement |
|------|-----------|-----------|-------------|
| S2 | 0 mid-build updates | 1 mid-build update | Marginal |
| K1 | Wrong timezone (UTC assumption) | Asks user for timezone | Fixed |
| C1 | Manual API token request | OAuth link in Discord | Complete fix |
```

### 3.6 Key UX findings (reusable insights)

1. **"Chief of staff" pattern:** The hub should keep work OFF the user, not report status. Build and show, don't ask.

2. **Silence after promise is worse than silence after message.** If the bot says "on it" and then goes dark for 3 minutes, trust drops more than if it never acknowledged at all.

3. **Inconsistency erodes trust faster than consistent mediocrity.** A user who gets a live URL one time and a file download the next trusts the system less than one who always gets file downloads.

4. **Numbers are trust signals.** "Found 847 contacts" is more trustworthy than "processing your data."

5. **Build for the medium.** If the user only has Discord, don't build CLI tools that require terminal access. Build what they can use right where they are.

6. **Anti-clarification rule.** Build and show, don't ask. Questions delay value and make the user do work. Build something reasonable and iterate.

7. **The contrast effect.** When one interaction is excellent and the next is mediocre, the mediocre one feels worse than if both had been mediocre.

---

## 4. Test Categories and When to Use Each

### 4.1 Unit tests (212 total)

**Purpose:** Verify individual functions and classes in isolation.
**Speed:** All 212 run in < 5 seconds.
**When to write:** For every new module. Before every deploy.
**Coverage focus:** Parse logic, state transitions, filesystem I/O, error handling.

### 4.2 Integration tests (embedded in unit tests)

**Purpose:** Verify component interactions (bridge + filesystem, registry + persistence).
**Example:** test_registry.py `test_persistence` creates a Registry, adds data, creates a NEW Registry from the same file, and reads back.
**When to write:** When two modules share state (files, databases, registries).

### 4.3 E2E tests (60+ via Playwright)

**Purpose:** Verify the full system from user input to bot response in Discord.
**Speed:** 30-120 seconds per test.
**When to write:** Before every sprint demo. After major architectural changes.
**Coverage focus:** Message routing, project lifecycle, hub behavior, error messages.

**Test execution order matters.** Tests are grouped into phases with dependencies:
```
Phase 1: DM commands (no state) -> Phase 2: Project creation
-> Phase 3: Channel interaction -> Phase 4: Hub DMs
-> Phase 5: Admin commands -> Phase 6: Teardown
-> Phase 7: Edge cases -> Phase 8: Fallback paths
```

### 4.4 UX research tests (per-sprint)

**Purpose:** Measure trust, identify broken UX patterns, guide product decisions.
**Speed:** 2-5 minutes per test (includes build time).
**When to write:** At each sprint boundary. When adding user-facing features.
**Coverage focus:** Subjective experience, silence gaps, delivery quality, personality.

### 4.5 Autonomous E2E (agent-driven)

**Purpose:** Claude Code agents run Playwright tests autonomously, report results.
**Team structure:** Tester agent + dev agent + UX researcher agent.
**When to use:** For long-running test suites. For overnight soak tests.

---

## 5. Behavior Map Pattern

Before writing any tests, the Delta team created a comprehensive behavior map (`tests/delta-behavior-map.md`). This 650-line document maps every code path:

### Structure

1. **DM Flow** -- what happens when a user DMs the bot
2. **Guild Channel Flow** -- messages in server channels
3. **Project Lifecycle** -- create, hibernate, wake, teardown
4. **Hub Behavior** -- command interception, snapshot loop
5. **Error/Fallback Paths** -- every failure mode
6. **Commands** -- every parsed command with expected output
7. **Background Loops** -- timers, watchers, polling intervals
8. **Startup Sequence** -- what happens on boot
9. **Data Flow Diagrams** -- ASCII flow for message routing
10. **File Paths** -- every relevant path in both modes
11. **JSON Formats** -- every message schema
12. **Thread Safety Notes** -- concurrency concerns
13. **Behavioral Details** -- nudge mechanism, prompt detection

**Reusable for Vinod:** Create a behavior map FIRST. It becomes the source of truth for both test plan and test implementation. Every entry in the behavior map should have at least one test covering it.

---

## 6. Test Plan Pattern

The test plan (`tests/delta-test-plan.md`) was derived from the behavior map. Key patterns:

### Phase-based ordering

Tests are grouped into phases that create state for later phases:
```
Phase 1 creates no state (pure queries)
Phase 2 creates projects (used by 3, 5, 6)
Phase 6 destroys projects (must come after 3, 5)
```

### Per-test specification format

```markdown
### T2.1 -- create project via DM command

**Input:** DM to Delta: `new project test-project`
**Expected output (message 1):** "Setting up **test-project**. One moment."
**Expected output (message 2):** Contains "**test-project** is live." AND a channel link
**Post-conditions to verify:**
- A new channel exists under "Delta Projects" category
- Channel is visible to the test user
```

### Assertion pattern taxonomy

| Pattern | Type | Example |
|---------|------|---------|
| Exact match | Full string equals | "Admin only." |
| Contains | Substring present | contains "Getting started" |
| Starts with | Prefix match | starts with "Setting up **" |
| Not present | Absence check | does NOT contain "error" |
| Message count | Number of bot replies | exactly 2 messages |
| Embed present | Has embed component | colored sidebar visible |
| Code block | Has ``` markers | tmux scrollback output |

---

## 7. Screenshot Naming Conventions

### Directory structure

```
test-screenshots/
    phase1-step0-delta-dm-loaded.png       # Phase-based
    sprint2-test2-01-discord-dm-start.png  # Sprint-based
    t1-step0-photo-site-empty.png          # Test-based
    round5-delivery-visible.png            # Round-based
    sprint3/                               # Subdirectory per sprint
    sprint3-rerun/                         # Re-run after fixes
    vinod-e2e/                             # Per-project subdirectory
```

### Naming patterns

```
{context}-{step_number}-{description}.png
```

Where context is one of:
- `phase{N}` -- original test plan phases
- `sprint{N}-test{N}` -- sprint test numbering
- `t{N}` -- trust score test numbering
- `round{N}` -- E2E round numbering
- `{test_name}` -- freeform

Step numbers are zero-padded: `01`, `02`, etc.

Description uses hyphens, no spaces: `delta-dm-loaded`, `vercel-link-delivered`.

---

## 8. Git Commit History and Test Evolution

The testing infrastructure evolved in clear phases:

### Phase 1: Unit tests first (commits ~7af7151)
- 109 unit tests covering all modules
- Ran before every deploy

### Phase 2: E2E via Playwright (commits ~97c35dc)
- First E2E report: 37 tests (33 PASS, 4 BLOCKED by OAuth)
- 15 bugs found and fixed during E2E

### Phase 3: UX research layer (commits ~97c35dc)
- Trust scores, scoring dimensions, before/after comparisons
- UX researcher agent analyzed screenshots and test results

### Phase 4: Sprint-based testing (commits ~7f7aeba through 63bc873)
- Sprint 2: Delivery channel testing (Vercel, Sheets, Notion)
- Sprint 2.5: Auth fix, delivery channels working
- Sprint 3: Streaming, scheduling, connections
- Each sprint: plan -> build -> test -> UX report -> fix -> retest

### Key test-related commits

```
2895720 Add 50 unit tests for schedule and followup systems
7af7151 Final test results: 43/44 E2E pass, 109 unit tests pass
97c35dc Add E2E test report, UX research report, and test screenshots
9d7b39d Session 3 test results: schedule, conversation depth, edge cases
8ce4b7f Post-test fixes: template routing, streaming, unit test
8346cfd Add Sprint 2.5 final trust report: 8.9 overall
4d9f450 Sprint 2 UX report: 8.5 Vercel / 7.0 overall
```

---

## 9. What Worked Well

1. **Behavior map before tests.** The 650-line behavior map was the best investment. Every test could be traced to a specific code path. No guessing about what to test.

2. **Fixtures using tmp_path.** Every test is fully isolated. No shared state between tests. Tests can run in any order.

3. **Screenshot-based E2E.** Screenshots provide evidence that survives test sessions. They're reviewable by humans and by UX researcher agents.

4. **Trust score as a north star.** The composite trust score gave the team a single number to optimize. Dropping from 8.9 to 7.9 was a clear signal that Sprint 3 regressed, even though individual features worked.

5. **Before/after comparison tables.** Every fix gets a before/after entry. This prevents "we think it's better" without proof.

6. **Phase-based test ordering.** Dependencies are explicit. The test plan documents which tests create state for which other tests.

7. **Bug tracking in test results.** The E2E test report includes a full bug table with root cause, fix, and deploy status. 15 bugs were found and fixed in one testing session.

8. **Playwright CDP connection to existing browser.** No need to log into Discord for every test. Connect to the user's already-authenticated Chrome session.

9. **Multi-agent testing team.** Tester agent runs Playwright, dev agent fixes bugs, UX researcher scores results. Three perspectives in one session.

10. **Scoring rubrics with specific numbers.** "Accompaniment: max gap 35s = score 8" is more actionable than "response time should be good."

---

## 10. What Didn't Work

1. **No programmatic assertion on Discord messages.** Screenshots are evidence but can't be asserted in code. Tests rely on human/agent interpretation. For Vinod, consider extracting message text via DOM queries.

2. **Polling loop tests use sleep.** `time.sleep(1.5)` in thread tests is flaky. Sometimes the loop doesn't complete a cycle in 1.5s. Use events or shorter poll intervals in tests.

3. **Module reload pattern is fragile.** The `importlib.reload()` pattern in test_bridge.py (to pick up new env vars) is error-prone. Better to pass config as constructor args rather than reading env at import time.

4. **Single-user E2E limitation.** All E2E tests ran as admin. Non-admin behavior, multi-user concurrency, and permission gating are untested. Need a second test account.

5. **Browser crashes during long waits.** Playwright MCP connection to Chrome is fragile over multi-minute waits. Round 7 was lost to a browser crash. Consider saving state between test steps.

6. **@mention automation is brittle.** Discord's autocomplete popup is timing-sensitive. Sometimes the delay isn't long enough and the mention doesn't resolve. Need retry logic.

7. **No test runner integration for E2E.** E2E tests are standalone Python scripts, not pytest tests. They can't be collected, filtered, or reported by pytest. Consider wrapping them in pytest fixtures.

8. **Screenshot directory grows unbounded.** 150+ screenshots with no cleanup strategy. Consider date-based subdirectories or automatic pruning.

9. **Timing-dependent tests are inherently flaky.** Tests that wait for Claude Code to respond (30-120s) have variable latency. A test might pass at 30s today and need 90s tomorrow. Consider exponential backoff polling instead of fixed sleeps.

10. **No test for the test infrastructure itself.** If Chrome CDP fails to connect, tests don't fail gracefully. The ensure_chrome_cdp() function handles this but the error reporting is minimal.

---

## 11. Reusable Patterns for New Projects

These patterns transfer well to any SeedForth agent project:

1. **conftest.py fixture structure.** tmp_path for filesystem isolation, monkeypatch for env vars, fixtures returning paths.
2. **Mock layering for SDK wrappers.** The connections.py pattern (mock_composio / mock_composio_none fixtures) works for any external SDK.
3. **Behavior map methodology.** Write the behavior map FIRST. Map every code path. Then derive the test plan from it.
4. **Playwright CDP boilerplate.** The ensure_chrome_cdp / get_discord_page pattern works for any browser-based E2E testing.
5. **Bug tracking in test results.** Table format: #, bug, root cause, fix, status.
