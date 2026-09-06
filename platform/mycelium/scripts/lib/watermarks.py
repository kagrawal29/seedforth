"""
Watermark system for signal deduplication.

Tracks the last-processed position per signal source.
Ingest reads watermarks → fetches only NEW signals → updates watermarks.

File: signals/.watermarks.yaml
Atomic writes via temp file + os.rename (POSIX-safe).
"""

import os
import yaml
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

WATERMARKS_PATH = Path("signals/.watermarks.yaml")


def load_watermarks() -> dict:
    """Load watermarks from file. Returns empty structure if missing (first run)."""
    if not WATERMARKS_PATH.exists():
        return {
            "langsmith": {},
            "github": {},
            "artifacts": {},
            "demand": {},
            "manual": {"last_processed_time": None},
            "_meta": {"last_updated": None, "last_cycle_status": None},
        }
    try:
        return yaml.safe_load(WATERMARKS_PATH.read_text()) or {}
    except Exception:
        return {"langsmith": {}, "github": {}, "artifacts": {}, "manual": {}, "_meta": {}}


def get_watermark(source: str, key: str) -> dict | None:
    """Get watermark for a specific source + key. Returns None if not found."""
    wm = load_watermarks()
    return wm.get(source, {}).get(key)


def save_watermarks(data: dict) -> None:
    """Atomic write: write to temp file, then rename over real file."""
    data["_meta"] = data.get("_meta", {})
    data["_meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()

    WATERMARKS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory (same filesystem for atomic rename)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(WATERMARKS_PATH.parent),
        suffix=".yaml.tmp"
    )
    try:
        with os.fdopen(fd, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        os.rename(tmp_path, str(WATERMARKS_PATH))
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def default_since(hours: int = 24) -> str:
    """Returns ISO timestamp for 'now minus N hours'. Bootstrap fallback."""
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def update_langsmith_watermark(project_uuid: str, member_name: str,
                                last_run_id: str = None, last_start_time: str = None) -> None:
    """Update watermark for a specific LangSmith project."""
    wm = load_watermarks()
    if "langsmith" not in wm:
        wm["langsmith"] = {}
    wm["langsmith"][project_uuid] = {
        "member": member_name,
        "last_run_id": last_run_id,
        "last_start_time": last_start_time,
    }
    save_watermarks(wm)


def update_github_watermark(repo_slug: str, last_commit_sha: str = None,
                            last_commit_time: str = None) -> None:
    """Update watermark for a specific GitHub repo."""
    wm = load_watermarks()
    if "github" not in wm:
        wm["github"] = {}
    wm["github"][repo_slug] = {
        "last_commit_sha": last_commit_sha,
        "last_commit_time": last_commit_time,
    }
    # Artifacts share GitHub's watermark
    if "artifacts" not in wm:
        wm["artifacts"] = {}
    wm["artifacts"][repo_slug] = wm["github"][repo_slug]
    save_watermarks(wm)


def get_langsmith_since(project_uuid: str, default_hours: int = 24) -> str:
    """Get the 'since' timestamp for a LangSmith query. Falls back to default_since."""
    wm = get_watermark("langsmith", project_uuid)
    if wm and wm.get("last_start_time"):
        return wm["last_start_time"]
    return default_since(default_hours)


def get_github_since(repo_slug: str, default_hours: int = 24) -> str:
    """Get the 'since' timestamp for a GitHub query. Falls back to default_since."""
    wm = get_watermark("github", repo_slug)
    if wm and wm.get("last_commit_time"):
        return wm["last_commit_time"]
    return default_since(default_hours)


def mark_cycle_status(status: str) -> None:
    """Mark the overall cycle status (success, partial_failure, failed)."""
    wm = load_watermarks()
    wm["_meta"]["last_cycle_status"] = status
    save_watermarks(wm)


# --- Demand engine watermarks ---


def get_demand_watermark() -> dict | None:
    """Get the last demand engine run info. Returns None if never run."""
    return get_watermark("demand", "last_run")


def update_demand_watermark(
    signal_files_processed: list[str],
    persons_analyzed: list[str],
    status: str = "success",
) -> None:
    """Update watermark after a demand engine run."""
    wm = load_watermarks()
    if "demand" not in wm:
        wm["demand"] = {}
    wm["demand"]["last_run"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signal_files_processed": signal_files_processed,
        "persons_analyzed": persons_analyzed,
        "status": status,
    }
    save_watermarks(wm)


def get_demand_since() -> str | None:
    """Get the timestamp of the last demand engine run. None if never run."""
    dw = get_demand_watermark()
    if dw and dw.get("timestamp"):
        return dw["timestamp"]
    return None
