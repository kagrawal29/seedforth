"""Sprint-prep file monitor hook for AudioWorld.

Watches the sprint-prep/ directory for new or modified .md files
and notifies the Slack channel.

This hook is loaded by Charlie's hook loader. It must define a
start(app, config) function that launches a background thread.
"""

import logging
import time
from pathlib import Path
from threading import Thread

logger = logging.getLogger(__name__)

# Polling interval in seconds
POLL_INTERVAL = 30

# sprint-prep dir relative to the project root
SPRINT_PREP_SUBDIR = "sprint-prep"


def _monitor(app, config):
    """Watch sprint-prep/ for new or modified .md files and notify Slack."""
    project_root = config.CONFIG_DIR.parent
    sprint_prep_dir = project_root / SPRINT_PREP_SUBDIR

    mtimes: dict[str, float] = {}
    channel = config.SLACK_CHANNEL_ID

    # Seed initial mtimes
    if sprint_prep_dir.exists():
        for f in sprint_prep_dir.glob("*.md"):
            mtimes[str(f)] = f.stat().st_mtime

    while True:
        time.sleep(POLL_INTERVAL)
        if not channel or not sprint_prep_dir.exists():
            continue
        try:
            for f in sprint_prep_dir.glob("*.md"):
                key = str(f)
                mtime = f.stat().st_mtime
                if key not in mtimes:
                    app.client.chat_postMessage(
                        channel=channel,
                        text=f"New sprint-prep sheet: `{f.name}`",
                    )
                elif mtime > mtimes[key]:
                    app.client.chat_postMessage(
                        channel=channel,
                        text=f"Sprint-prep sheet updated: `{f.name}`",
                    )
                mtimes[key] = mtime
        except OSError:
            pass


def start(app, config):
    """Launch the sprint-prep monitor as a daemon thread."""
    t = Thread(target=_monitor, args=(app, config), daemon=True)
    t.start()
    logger.info(f"Sprint-prep monitor started (polling every {POLL_INTERVAL}s)")
