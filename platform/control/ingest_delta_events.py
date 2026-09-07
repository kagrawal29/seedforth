"""Delta event ingestion bridge.

Reads write-only Delta event streams and records them into Mycelium via control
operations. This turns project/CLI-side events into graph-trace rows and keeps
event IDs deterministic for replay/idempotence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from control.graph import Graph


TS_DEFAULT_UTC = "1970-01-01T00:00:00+00:00"
TS_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
PRINCIPAL = os.environ.get("SEEDFORTH_DELTA_INGESTOR_PRINCIPAL", "principal-delta-ingestor")
SHARED_DIR = Path(os.environ.get("SEEDFORTH_SHARED_DIR", "/opt/seedforth/shared"))
STATE_FILE = Path(os.environ.get(
    "SEEDFORTH_DELTA_INGEST_STATE",
    str(SHARED_DIR / "delta-event-ingest-state.json"),
))
REGISTRY_PATH = Path(os.environ.get("SEEDFORTH_DELTA_REGISTRY", "/opt/delta/delta-registry.json"))
PROVISION_SOURCE_ID = "source-delta-provision-events"
PROJECT_EVENT_SOURCE_PREFIX = "source-delta-project-events-"
PROVISION_STREAM_ID = "delta-provision-events-v1"
PROJECT_STREAM_ID = "delta-project-events-v1"


@dataclass
class EventSource:
    path: Path
    scope: str
    stream: str
    adapter: str


def _normalize_scope(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    if 0 < len(value) <= 64 and re.match(r"^[a-z0-9][a-z0-9-]*$", value):
        return value
    return None


def _normalize_ts(ts: Any) -> str:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    if not isinstance(ts, str):
        raise ValueError("invalid_ts")
    text = ts.strip()
    if not text:
        raise ValueError("invalid_ts")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        raise ValueError("invalid_ts")


def _stable_payload(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _payload_hash(data: Any) -> str:
    return hashlib.sha256(_stable_payload(data).encode()).hexdigest()


def _event_id(source: str, scope: str, raw_offset: int, event: dict[str, Any], ts: str) -> str:
    explicit = event.get("event_id")
    if isinstance(explicit, str) and 1 <= len(explicit) <= 200:
        return _payload_hash({"source": source, "scope": scope, "event_id": explicit})
    material = {
        "source": source,
        "scope": scope,
        "event_type": event.get("event_type"),
        "raw_offset": raw_offset,
        "project": event.get("project"),
        "ts": ts,
        "payload": event.get("payload") or {},
    }
    return _payload_hash(material)


def discover_project_sources(registry_path: Path = REGISTRY_PATH) -> list[EventSource]:
    sources: list[EventSource] = []
    if not registry_path.exists():
        return sources
    try:
        data = json.loads(registry_path.read_text())
    except (json.JSONDecodeError, OSError):
        return sources

    projects = data.get("projects", {})
    if not isinstance(projects, dict):
        return sources

    for name, info in projects.items():
        if not isinstance(info, dict):
            continue
        scope = _normalize_scope(name) or _normalize_scope(info.get("name"))
        if not scope:
            continue
        data_dir = info.get("data_dir")
        if not isinstance(data_dir, str) or not data_dir:
            continue
        path = Path(data_dir).expanduser() / "graph-events.jsonl"
        sources.append(EventSource(
            path=path,
            scope=scope,
            stream=PROJECT_EVENT_SOURCE_PREFIX + scope,
            adapter=PROJECT_STREAM_ID,
        ))
    return sources


def build_event_sources() -> list[EventSource]:
    provision = EventSource(
        path=SHARED_DIR / "provision-events.jsonl",
        scope="seedforth-platform",
        stream=PROVISION_SOURCE_ID,
        adapter=PROVISION_STREAM_ID,
    )
    return [provision] + discover_project_sources()


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sources": {}}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"sources": {}}


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _load_cursor(state: dict[str, Any], source_path: Path) -> int:
    cursor = state.get("sources", {}).get(str(source_path), {}).get("cursor", 0)
    if isinstance(cursor, int) and cursor >= 0:
        return cursor
    return 0


def _store_cursor(state: dict[str, Any], source_path: Path, cursor: int) -> None:
    state.setdefault("sources", {})
    state["sources"][str(source_path)] = {"cursor": cursor}


def _parse_line(raw: str) -> dict[str, Any]:
    if not raw.strip():
        raise ValueError("empty_line")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("invalid_event")
    if not isinstance(data.get("event_type"), str):
        raise ValueError("invalid_event_type")
    return data


def _quarantine(path: Path, source: EventSource, offset: int, raw: str, reason: str) -> None:
    """Keep malformed/unsupported input auditable while allowing the stream to progress."""
    quarantine = path.with_name(path.name + ".quarantine.jsonl")
    entry = {
        "source": source.stream,
        "scope": source.scope,
        "offset": offset,
        "reason": reason[:120],
        "raw": raw[:10000],
        "quarantined_at": datetime.now(timezone.utc).isoformat(),
    }
    with quarantine.open("a", encoding="utf-8") as handle:
        handle.write(_stable_payload(entry) + "\n")
    os.chmod(quarantine, 0o600)


def _dispatch_session_trace(graph: Graph, principal: str, source: EventSource, ts: str, event: dict[str, Any], event_id: str, event_hash: str) -> list[dict[str, Any]]:
    payload = event.get("payload") or {}
    params = {
        "event_id": event_id,
        "payload_hash": event_hash,
        "source": source.stream,
        "observed_at": ts,
        "project": _normalize_scope(event.get("project")) or source.scope,
        "msg_id": str(payload.get("msg_id", ""))[:120],
        "user": str(payload.get("user", ""))[:128],
        "text_preview": str(payload.get("text_preview", ""))[:240],
        "session_id": str(payload.get("session_id", ""))[:120],
        "channel_id": str(payload.get("channel_id", ""))[:120],
    }
    return graph.operation("record-session-trace", principal, source.scope, **params)


def _dispatch_work_item(graph: Graph, principal: str, source: EventSource, ts: str, event: dict[str, Any], event_id: str, event_hash: str) -> list[dict[str, Any]]:
    payload = event.get("payload") or {}
    what = payload.get("what")
    if isinstance(what, str):
        what = what[:500]
    params = {
        "event_id": event_id,
        "payload_hash": event_hash,
        "source": source.stream,
        "observed_at": ts,
        "project": _normalize_scope(event.get("project")) or source.scope,
        "task_id": str(payload.get("task_id", ""))[:120],
        "status": str(payload.get("status", ""))[:80],
        "what": what if what else "",
        "msg_id": str(payload.get("msg_id", ""))[:120],
    }
    return graph.operation("record-work-item-event", principal, source.scope, **params)


def _dispatch_provision(graph: Graph, principal: str, source: EventSource, ts: str, event: dict[str, Any], event_id: str, event_hash: str) -> list[dict[str, Any]]:
    payload = event.get("payload") or {}
    params = {
        "event_id": event_id,
        "payload_hash": event_hash,
        "source": source.stream,
        "observed_at": ts,
        "project": _normalize_scope(event.get("project")) or source.scope,
        "provision_type": event.get("event_type"),
        "payload": _stable_payload(payload),
        "role": str(payload.get("role", ""))[:120],
        "model": str(payload.get("model", ""))[:120],
    }
    return graph.operation("record-provision-event", principal, source.scope, **params)


def dispatch_event(graph: Graph, principal: str, source: EventSource, raw_offset: int, record: dict[str, Any]) -> list[dict[str, Any]]:
    ts = _normalize_ts(record.get("ts", TS_DEFAULT_UTC))
    normalized_scope = _normalize_scope(source.scope)
    if not normalized_scope:
        return []
    scope_event_id = _event_id(source.stream, normalized_scope, raw_offset, record, ts)
    event_hash = _payload_hash({
        "scope": normalized_scope,
        "event": record.get("event_type"),
        "project": record.get("project"),
        "payload": record.get("payload"),
        "ts": ts,
    })
    event_type = str(record.get("event_type"))
    if event_type == "session_trace":
        return _dispatch_session_trace(graph, principal, source, ts, record, scope_event_id, event_hash)
    if event_type == "work_item":
        return _dispatch_work_item(graph, principal, source, ts, record, scope_event_id, event_hash)
    if event_type in {"provisioned", "hibernated", "restored", "torn_down", "subagent_role_sync"}:
        return _dispatch_provision(graph, principal, source, ts, record, scope_event_id, event_hash)
    raise ValueError("unsupported_event_type")


def collect_and_dispatch(
    graph: Graph,
    principal: str = PRINCIPAL,
    sources: list[EventSource] | None = None,
    state_file: Path = STATE_FILE,
) -> dict[str, int]:
    state = _read_state(state_file)
    sources = sources or build_event_sources()
    stats = {"files": 0, "lines": 0, "events": 0, "dispatched": 0, "skipped": 0, "failed": 0}
    for source in sources:
        if not source.path.exists():
            continue
        stats["files"] += 1
        try:
            cursor = _load_cursor(state, source.path)
            size = source.path.stat().st_size
            if size < cursor:
                cursor = 0
            with source.path.open("r", encoding="utf-8") as handle:
                handle.seek(cursor)
                next_cursor = cursor
                current = cursor
                while True:
                    current = handle.tell()
                    raw = handle.readline()
                    if not raw:
                        break
                    # Writers may still be appending the final record. Leave it
                    # at the cursor until a newline makes the record durable.
                    if not raw.endswith("\n"):
                        break
                    stats["lines"] += 1
                    try:
                        record = _parse_line(raw)
                    except (ValueError, json.JSONDecodeError) as exc:
                        _quarantine(source.path, source, current, raw, str(exc))
                        stats["failed"] += 1
                        next_cursor = handle.tell()
                        continue
                    try:
                        rows = dispatch_event(graph, principal, source, current, record)
                    except ValueError as exc:
                        _quarantine(source.path, source, current, raw, str(exc))
                        stats["failed"] += 1
                        next_cursor = handle.tell()
                        continue
                    # Transport/graph errors intentionally escape. The cursor
                    # remains before this event, so the next run retries it.
                    stats["events"] += 1
                    if rows:
                        stats["dispatched"] += 1
                    else:
                        stats["skipped"] += 1
                    _store_cursor(state, source.path, handle.tell())
                    next_cursor = handle.tell()
                    state["updated_at"] = datetime.now(timezone.utc).isoformat()
                    _write_state(state_file, state)
                cursor = next_cursor
            _store_cursor(state, source.path, cursor)
        except OSError:
            stats["failed"] += 1
    if stats["files"] or stats["lines"] or stats["events"]:
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        _write_state(state_file, state)
    return stats


def main() -> int:
    try:
        stats = collect_and_dispatch(Graph(), principal=PRINCIPAL, state_file=STATE_FILE)
        # Keep output to service logs minimal and machine-actionable.
        print(json.dumps(stats, sort_keys=True))
        return 0
    except Exception as exc:
        print("delta-event-ingest-fatal", repr(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
