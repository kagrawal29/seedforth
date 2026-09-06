"""Per-project bridge wrapper -- parameterized on instance, not module-level config.

Each project gets its own ProjectBridge with HTTP delivery to opencode serve.
Sole runtime after Phase 5 migration. No tmux/Claude Code paths remain.
"""

import json
import os
import string
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from random import choices
from typing import Callable


class ProjectBridge:
    """Bridge instance for a single project."""

    def __init__(self, name: str, data_dir: str,
                 nudge_prefix: str = "", outbox_poll_interval: int = 1,
                 serve_port: int = 0, session_id: str = "",
                 session_persist: Callable[[str, str], None] | None = None):
        self.name = name
        self.data_dir = Path(data_dir)
        self.nudge_prefix = nudge_prefix or "delta-config/inbox"
        self.outbox_poll_interval = outbox_poll_interval
        self.serve_port = serve_port
        self.session_id = session_id
        self._session_persist = session_persist

        # Shutdown coordination
        self._shutdown_event = threading.Event()
        self.last_activity = datetime.now(timezone.utc)

        # Silence tracking -- detect when agent goes dark after receiving a message
        self.last_inbox_time: float = 0  # time.time() of last inbox write
        self.last_outbox_time: float = 0  # time.time() of last outbox file processed
        self.connection_pending: bool = False  # True while waiting for OAuth completion

        # Directories
        self.inbox_dir = self.data_dir / "inbox"
        self.outbox_dir = self.data_dir / "outbox"
        self.logs_dir = self.data_dir / "logs"
        self.progress_dir = self.data_dir / "progress"
        self.last_progress_time: float = 0  # time.time() of last progress file

        # Track completed schedule tasks for Neo4j WorkItem writes
        self._seen_completed_tasks: set[str] = set()

        # Ensure dirs exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.progress_dir.mkdir(parents=True, exist_ok=True)

    def _random_id(self) -> str:
        chars = string.ascii_lowercase + string.digits
        suffix = "".join(choices(chars, k=4))
        return f"msg-{int(time.time())}-{suffix}"

    def _log_exchange(self, direction: str, user: str, text: str,
                      msg_id: str, channel: str = "",
                      thread_ts: str = "") -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.jsonl"
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "direction": direction,
            "user": user,
            "msg_id": msg_id,
            "channel": channel,
            "thread_ts": thread_ts,
            "text": text[:2000],
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def write_inbox(self, channel: str, user: str, text: str,
                    thread_ts: str | None = None, **extra) -> str:
        """Write a message to the project's inbox. Returns msg_id.

        Extra kwargs (e.g. channel_name, channel_type) are merged into
        the inbox JSON so the receiving agent gets richer context.
        """
        msg_id = self._random_id()
        payload = {
            "id": msg_id,
            "channel": channel,
            "user": user,
            "text": text,
            "thread_ts": thread_ts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload.update(extra)
        path = self.inbox_dir / f"{msg_id}.json"
        path.write_text(json.dumps(payload, indent=2))
        self._log_exchange("in", user, text, msg_id, channel, thread_ts or "")
        # Track for silence detection -- only for real user messages
        if not user.startswith("delta:"):
            self.last_inbox_time = time.time()
        # Reset idle timer so resource manager sees activity from both
        # Discord messages and bridge-injected test messages
        self.touch_activity()
        return msg_id

    def _get_or_create_session(self) -> str:
        """Return the opencode session ID, creating one if needed."""
        if self.session_id:
            return self.session_id
        payload = json.dumps({"title": self.name})
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.serve_port}/session",
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            self.session_id = data.get("id", "")
        # Persist so a bridge restart (opencode reboot) restores the same
        # conversation instead of starting a fresh context.
        if self.session_id and self._session_persist:
            try:
                self._session_persist(self.name, self.session_id)
            except Exception:
                pass
        return self.session_id

    def deliver_message(self, channel_id: str, user_name: str, text: str,
                        msg_id: str = "", callback: Callable | None = None) -> None:
        """Deliver message to opencode agent via HTTP. Response delivered via callback."""
        if not self.serve_port:
            return

        if not msg_id:
            msg_id = self._random_id()

        def _deliver():
            try:
                sid = self._get_or_create_session()
                prompt = (
                    f"[Discord message from {user_name}]\n{text}\n\n"
                    f"Read SEED.md and memory/* for project context before responding."
                )
                payload = json.dumps({"parts": [{"type": "text", "text": prompt}]})
                req = urllib.request.Request(
                    f"http://127.0.0.1:{self.serve_port}/session/{sid}/message",
                    data=payload.encode(),
                    headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = json.loads(resp.read())
                    resp_text = ""
                    for p in data.get("parts", []):
                        if p.get("type") == "text":
                            resp_text += p["text"]
                    if resp_text and callback:
                        callback(channel_id, resp_text)
                    if resp_text:
                        try:
                            import time as _t
                            import urllib.request as _ur, json as _json, base64 as _b64
                            node_id = f"trace-{int(_t.time() * 1000)}"
                            safe_text = text[:100].replace('"', '\\"')
                            body = _json.dumps({"statements": [{"statement":
                                "CREATE (st:SessionTrace {node_id:$nid, agent:$ag, "
                                "project:$pr, user:$usr, text_preview:$txt, created_at:datetime()})",
                                "parameters": {"nid": node_id, "ag": self.name,
                                               "pr": self.name, "usr": user_name,
                                               "txt": safe_text}}]}).encode()
                            auth = _b64.b64encode(
                                f"neo4j:{os.environ.get('NEO4J_PASSWORD', '')}".encode()
                            ).decode()
                            req = _ur.Request(
                                "http://127.0.0.1:7474/db/neo4j/tx/commit",
                                data=body, headers={"Content-Type": "application/json",
                                                    "Authorization": f"Basic {auth}"})
                            with _ur.urlopen(req, timeout=5) as r:
                                r.read()
                        except Exception as e2:
                            print(f"session trace write failed: {e2}")
            except Exception as e:
                print(f"HTTP delivery failed for {self.name}: {e}")

        # HTTP path is the primary pipe — track for silence detection and log
        if not user_name.startswith("delta:"):
            self.last_inbox_time = time.time()
        self._log_exchange("in", user_name, text, msg_id, channel_id or "")
        self.touch_activity()

        threading.Thread(target=_deliver, daemon=True).start()

    def touch_activity(self) -> None:
        """Update last_activity to now."""
        self.last_activity = datetime.now(timezone.utc)

    def is_idle(self, timeout_minutes: int = 10) -> bool:
        """Check if bridge has been idle longer than timeout_minutes."""
        from datetime import timedelta
        elapsed = datetime.now(timezone.utc) - self.last_activity
        return elapsed > timedelta(minutes=timeout_minutes)

    def has_pending_work(self) -> bool:
        """Return True if followups exist or schedule has active/recurring tasks."""
        followup_dir = self.data_dir / "followups"
        if followup_dir.exists() and list(followup_dir.glob("*.json")):
            return True

        schedule = self.get_schedule()
        for task in schedule:
            if task.get("status") == "done" and task.get("id") not in self._seen_completed_tasks:
                self._write_work_item(task)
                self._seen_completed_tasks.add(task.get("id"))
            if task.get("status") in ("in_progress", "recurring"):
                return True
        return False

    def peek(self, lines: int = 40) -> str:
        """Return recent conversation tail from log files."""
        logs = list(sorted(self.logs_dir.glob("*.jsonl")))
        if logs:
            tail = []
            for line in logs[-1].read_text(errors="replace").strip().splitlines()[-lines:]:
                try:
                    entry = json.loads(line)
                    tail.append(
                        f"{entry.get('direction', '?')} {entry.get('user', '')}: "
                        f"{entry.get('text', '')[:180]}"
                    )
                except (json.JSONDecodeError, OSError):
                    tail.append(line[:180])
            return "\n".join(tail) or "(no recent exchanges)"
        out_log = self.data_dir / "logs" / "opencode-stdout.log"
        if out_log.exists():
            tail = out_log.read_text(errors="replace").strip().splitlines()[-lines:]
            return "\n".join(tail) or "(empty)"
        return "(no logs yet)"

    def capture_tmux_scrollback(self, lines: int = 40) -> str:
        """Compatibility shim for opencode runtime: same as peek()."""
        return self.peek(lines)

    def shutdown(self) -> None:
        """Signal all watcher threads to stop. They exit within one poll cycle."""
        self._shutdown_event.set()

    def send_to_lead(self, msg_id: str) -> None:
        """Send a tmux nudge to process an inbox file."""
        self._nudge(msg_id)

    def _nudge(self, msg_id: str) -> None:
        """Nudge the agent via HTTP health ping."""
        if self.serve_port:
            nudge_file = self.data_dir / ".nudge"
            nudge_file.touch()
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{self.serve_port}/global/health",
                    timeout=3,
                )
            except Exception:
                pass

    def watch_followups(self, callback: Callable[[dict], None]) -> None:
        """Poll followups/ for messages whose deliver_after time has passed.

        Follow-up files are JSON with: id, channel, text/embed, deliver_after (ISO timestamp).
        Cancelled if a new inbox message arrives before delivery (agent deletes the file).
        """
        followup_dir = self.data_dir / "followups"
        followup_dir.mkdir(parents=True, exist_ok=True)

        while not self._shutdown_event.is_set():
            try:
                now = datetime.now(timezone.utc)
                for path in sorted(followup_dir.glob("*.json")):
                    try:
                        data = json.loads(path.read_text())
                        deliver_after = data.get("deliver_after", "")
                        if not deliver_after:
                            continue
                        deliver_time = datetime.fromisoformat(deliver_after)
                        if now >= deliver_time:
                            callback(data)
                            self._log_exchange(
                                "out", "delta:followup", data.get("text", ""),
                                data.get("id", ""), data.get("channel", ""),
                            )
                            path.unlink()
                    except (json.JSONDecodeError, OSError, ValueError):
                        pass
            except OSError:
                pass
            self._shutdown_event.wait(10)

    def cancel_pending_followups(self) -> int:
        """Cancel all pending follow-ups. Returns count cancelled."""
        followup_dir = self.data_dir / "followups"
        count = 0
        if followup_dir.exists():
            for path in followup_dir.glob("*.json"):
                try:
                    path.unlink()
                    count += 1
                except OSError:
                    pass
        return count

    def watch_inbox(self, nudge_interval: int = 8) -> None:
        """Poll inbox for unprocessed messages and re-nudge.

        Runs forever. Catches messages whose nudge was lost because
        the agent was busy when the nudge arrived.
        Batch-nudges up to 5 pending messages.
        """
        while not self._shutdown_event.is_set():
            try:
                if not self.is_project_active():
                    self._shutdown_event.wait(nudge_interval)
                    continue

                pending = sorted(self.inbox_dir.glob("*.json"))
                if pending:
                    for msg_file in pending[:5]:
                        try:
                            self._nudge(msg_file.stem)
                        except Exception:
                            break
            except OSError:
                pass
            self._shutdown_event.wait(nudge_interval)

    def watch_outbox(self, callback: Callable[[dict], None]) -> None:
        """Poll outbox/ for new JSON files. Runs forever."""
        seen: set[str] = set()
        dead_letter = self.outbox_dir / "dead-letter"
        while not self._shutdown_event.is_set():
            try:
                for path in sorted(self.outbox_dir.glob("*.json")):
                    if path.name in seen:
                        continue
                    try:
                        data = json.loads(path.read_text())
                        callback(data)
                        self.last_outbox_time = time.time()
                        self.touch_activity()
                        self._log_exchange(
                            "out", "delta", data.get("text", ""),
                            data.get("id", ""), data.get("channel", ""),
                            data.get("thread_ts", ""),
                        )
                        path.unlink()
                    except (json.JSONDecodeError, OSError) as exc:
                        print(f"[outbox:{self.name}] Error processing {path.name}: {exc}")
                        # Move malformed files to dead-letter to prevent accumulation
                        try:
                            dead_letter.mkdir(exist_ok=True)
                            path.rename(dead_letter / path.name)
                        except OSError:
                            pass
                    seen.add(path.name)
            except OSError:
                pass
            self._shutdown_event.wait(self.outbox_poll_interval)

    def is_project_active(self) -> bool:
        """Check if the opencode agent is reachable."""
        if self.serve_port:
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{self.serve_port}/global/health",
                    timeout=3,
                )
                return True
            except Exception:
                return False
        return False

    def check_silence(self, timeout: int = 25) -> bool:
        """Check if agent has been silent for `timeout` seconds.

        Returns True whenever enough time has passed since the last activity
        (outbox write or inbox message, whichever is later). This is a
        repeating check -- it returns True every time the timeout elapses,
        not just once. The caller is responsible for cooldown/cap logic.
        """
        if self.last_inbox_time == 0:
            return False
        if self.connection_pending:
            return False
        now = time.time()
        # No user message recently -- nothing to be silent about
        if now - self.last_inbox_time > 300:
            return False
        # Agent has written outbox files the watcher hasn't picked up yet
        try:
            if list(self.outbox_dir.glob("*.json")):
                return False
        except OSError:
            pass
        # Compare against the later of last_outbox or last_inbox
        last_activity = max(self.last_outbox_time, self.last_inbox_time)
        # Timeout elapsed since last activity
        if now - last_activity >= timeout:
            return True
        return False

    def watch_progress(self, callback: Callable[[str], None],
                        rate_limit: int = 25) -> None:
        """Poll progress signals and synthesize human messages."""
        if self.serve_port:
            self._watch_progress_opencode(callback, rate_limit)
            return

        pending_signals: list[dict] = []
        last_send: float = 0
        last_message: str = ""
        send_count: int = 0
        tracked_inbox_time: float = 0

        while not self._shutdown_event.is_set():
            try:
                # Consume all progress files (prevents accumulation even when not sending)
                for path in sorted(self.progress_dir.glob("*.json")):
                    try:
                        data = json.loads(path.read_text())
                        pending_signals.append(data)
                        self.last_progress_time = time.time()
                        path.unlink()
                    except (json.JSONDecodeError, OSError):
                        try:
                            path.unlink()
                        except OSError:
                            pass

                now = time.time()

                # Reset counter when a new user message arrives
                if self.last_inbox_time != tracked_inbox_time:
                    send_count = 0
                    last_message = ""
                    tracked_inbox_time = self.last_inbox_time

                # Only send if a real user message arrived in the last 5 min
                user_watching = (self.last_inbox_time > 0
                                 and now - self.last_inbox_time < 300)

                if pending_signals and (now - last_send) >= rate_limit:
                    if user_watching and send_count < 8:
                        message = self._synthesize_progress(pending_signals)
                        if message and message != last_message:
                            callback(message)
                            last_send = now
                            last_message = message
                            send_count += 1
                    pending_signals.clear()

            except OSError:
                pass
            self._shutdown_event.wait(2)

    def _watch_progress_opencode(self, callback: Callable[[str], None],
                                  rate_limit: int = 25) -> None:
        """Poll opencode HTTP todo endpoint for progress signals."""
        last_in_progress: set[str] = set()
        last_send: float = 0
        last_message: str = ""
        send_count: int = 0
        tracked_inbox_time: float = 0

        url = f"http://127.0.0.1:{self.serve_port}/session/{self.session_id}/todo"

        while not self._shutdown_event.is_set():
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode())

                in_progress = data.get("in_progress", []) if isinstance(data, dict) else []
                current_items = set(
                    str(item) for item in in_progress
                )

                if current_items != last_in_progress:
                    last_in_progress = current_items
                    self.last_progress_time = time.time()

                    now = time.time()

                    if self.last_inbox_time != tracked_inbox_time:
                        send_count = 0
                        last_message = ""
                        tracked_inbox_time = self.last_inbox_time

                    user_watching = (self.last_inbox_time > 0
                                     and now - self.last_inbox_time < 300)

                    if (user_watching and send_count < 8
                            and (now - last_send) >= rate_limit):
                        if in_progress:
                            item = in_progress[0]
                            if isinstance(item, dict):
                                message = item.get("content", str(item))
                            else:
                                message = str(item)
                            if message and message != last_message:
                                callback(f"working... ({message[:60]})")
                                last_send = now
                                last_message = message
                                send_count += 1

            except (urllib.error.URLError, OSError, json.JSONDecodeError):
                pass

            self._shutdown_event.wait(5)

    def _synthesize_progress(self, signals: list[dict]) -> str:
        """Turn accumulated progress signals into a short human message.

        Only produces output when there's at least one high-signal event.
        Medium-only batches are silently consumed (not interesting enough
        to message the user about).
        """
        if not signals:
            return ""

        high = [s for s in signals if s.get("signal") == "high"]

        # Medium-only batches: not worth a Discord message
        if not high:
            return ""

        latest = high[-1]
        summary = latest.get("summary", latest.get("tool", "working"))
        tool = latest.get("tool", "")

        if "deploy" in summary.lower() or "vercel" in summary.lower():
            return f"deploying... ({summary[:60]})"
        elif "npm" in summary.lower() or "build" in summary.lower():
            return f"building... ({summary[:60]})"
        elif tool in ("Write", "NotebookEdit"):
            return f"writing code... ({summary[:60]})"
        elif tool == "Edit":
            return f"editing... ({summary[:60]})"
        elif "mcp" in tool.lower() or "RUBE" in tool.lower():
            return f"using {tool}... ({summary[:60]})"
        else:
            return f"working... ({summary[:60]})"

    def has_recent_progress(self, window: int = 30) -> bool:
        """Return True if a progress signal arrived within the last `window` seconds."""
        if self.last_progress_time == 0:
            return False
        return (time.time() - self.last_progress_time) < window

    def pending_inbox_count(self) -> int:
        """Count unprocessed inbox messages."""
        try:
            return len(list(self.inbox_dir.glob("*.json")))
        except OSError:
            return 0

    def _write_work_item(self, task: dict) -> None:
        import subprocess, time
        try:
            task_id = task.get("id", "unknown")
            node_id = f"workitem-{task_id}-{int(time.time())}"
            what = task.get("what", "")[:100].replace('"', '\\"')
            status = task.get("status", "unknown")
            cypher = (
                f'CREATE (wi:WorkItem {{'
                f'node_id:"{node_id}", '
                f'project:"{self.name}", '
                f'task_id:"{task_id}", '
                f'what:"{what}", '
                f'status:"{status}", '
                f'created_at:datetime()'
                f'}})'
            )
            subprocess.run(
                ["docker", "exec", "mycelium-neo4j", "cypher-shell",
                 "-u", "neo4j", "-p", os.environ.get("NEO4J_PASSWORD", ""),
                 "--format", "plain", cypher],
                capture_output=True, text=True, timeout=10
            )
        except Exception as e:
            print(f"work item write failed: {e}")

    def get_schedule(self) -> list[dict]:
        """Read the project's task schedule."""
        schedule_file = self.data_dir / "schedule.json"
        if not schedule_file.exists():
            return []
        try:
            data = json.loads(schedule_file.read_text())
            return data.get("tasks", [])
        except (json.JSONDecodeError, OSError):
            return []

    def get_recent_logs(self, max_lines: int = 20) -> list[dict]:
        """Read the most recent log entries across today and yesterday."""
        entries = []
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        from datetime import timedelta
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")

        for date_str in [yesterday, today]:
            log_file = self.logs_dir / f"{date_str}.jsonl"
            if not log_file.exists():
                continue
            try:
                lines = log_file.read_text().strip().split("\n")
                for line in lines:
                    if line:
                        entries.append(json.loads(line))
            except (json.JSONDecodeError, OSError):
                pass

        return entries[-max_lines:]

    def check_auth_error(self, lines: int = 50) -> str | None:
        """Check error files for auth errors. Returns message or None."""
        errors_dir = self.data_dir / "errors"
        if errors_dir.exists():
            error_files = sorted(
                errors_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for error_file in error_files:
                try:
                    data = json.loads(error_file.read_text())
                    if data.get("type") == "auth_error":
                        return data.get("message", str(data))
                except (json.JSONDecodeError, OSError):
                    pass
        return None
