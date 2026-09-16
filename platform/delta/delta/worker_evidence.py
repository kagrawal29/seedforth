"""Append-only worker action evidence produced after a real wakeup."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")


def append_action(path: str | Path, *, scope: str, message_id: str, workitem_id: str,
                  wakeup_id: str, worker_id: str, result: str) -> str:
    values = (scope, message_id, workitem_id, wakeup_id, worker_id, result)
    if any(not isinstance(v, str) or not v for v in values[:5]) or not isinstance(result, str):
        raise ValueError("invalid_worker_evidence")
    if any(not _ID.fullmatch(v) for v in values[:5]) or len(result) > 2000:
        raise ValueError("invalid_worker_evidence")
    record: dict[str, Any] = {
        "scope": scope,
        "conversation_message_id": message_id,
        "workitem_id": workitem_id,
        "wakeup_id": wakeup_id,
        "worker_id": worker_id,
        "action_status": "completed",
        "result": result,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    line = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    target = Path(path)
    target.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    try:
        os.write(fd, line)
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(line).hexdigest()
