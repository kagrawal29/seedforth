"""
Synthesis manifest for delta signal processing.

Tracks which signal files have been processed by sha256 hash.
Synthesis reads manifest → computes delta → processes only new/modified files.

File: signals/.synthesis-manifest.json
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_PATH = Path("signals/.synthesis-manifest.json")
SIGNAL_DIRS = ["signals/langsmith", "signals/github", "signals/artifacts", "signals/manual"]


def load_manifest() -> dict:
    """Load the synthesis manifest. Returns empty structure if missing."""
    if not MANIFEST_PATH.exists():
        return {"last_cycle_ts": None, "processed_files": []}
    try:
        return json.loads(MANIFEST_PATH.read_text())
    except Exception:
        return {"last_cycle_ts": None, "processed_files": []}


def save_manifest(data: dict) -> None:
    """Save the manifest. Atomic write."""
    data["last_cycle_ts"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = str(MANIFEST_PATH) + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.rename(tmp_path, str(MANIFEST_PATH))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def file_sha256(filepath: str) -> str:
    """Compute sha256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def get_all_signal_files() -> list[str]:
    """Find all signal .md files across all signal directories."""
    files = []
    for d in SIGNAL_DIRS:
        p = Path(d)
        if p.exists():
            files.extend(str(f) for f in p.glob("*.md"))
    return sorted(files)


def compute_delta() -> list[dict]:
    """Compute which signal files are new or modified since last synthesis.

    Returns list of dicts: [{"path": str, "sha256": str, "status": "new"|"modified"}, ...]
    """
    manifest = load_manifest()
    processed = {f["path"]: f["sha256"] for f in manifest.get("processed_files", [])}

    all_files = get_all_signal_files()
    delta = []

    for filepath in all_files:
        current_hash = file_sha256(filepath)
        if filepath not in processed:
            delta.append({"path": filepath, "sha256": current_hash, "status": "new"})
        elif processed[filepath] != current_hash:
            delta.append({"path": filepath, "sha256": current_hash, "status": "modified"})
        # else: unchanged, skip

    return delta


def mark_files_processed(files: list[dict], entries_created: list[str] = None) -> None:
    """Mark files as processed in the manifest.

    files: list of {"path": str, "sha256": str} dicts
    entries_created: optional list of entry IDs created from these files
    """
    manifest = load_manifest()
    existing = {f["path"]: f for f in manifest.get("processed_files", [])}

    for f in files:
        existing[f["path"]] = {
            "path": f["path"],
            "sha256": f["sha256"],
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "entries_created": entries_created or [],
        }

    manifest["processed_files"] = list(existing.values())
    save_manifest(manifest)


def seed_manifest() -> None:
    """Seed the manifest with all currently existing signal files as 'already processed'.
    Use this when deploying the manifest system for the first time.
    """
    all_files = get_all_signal_files()
    files = [{"path": f, "sha256": file_sha256(f)} for f in all_files]
    mark_files_processed(files, entries_created=["seeded-on-deploy"])
