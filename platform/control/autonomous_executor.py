"""Run one bounded autonomous work cycle through the protected worker surface.

Selection and authority remain graph operations; this module only supplies
fresh attempt identifiers and transports the selected job to the isolated
worker. A missing/held/ambiguous graph state produces no external effect.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from uuid import uuid4

from control.graph import Graph
from control.isolated_worker import execute
from control.worker_transport import WorkerClient


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def run_once(graph: Graph, worker: WorkerClient, principal: str, scope: str) -> dict:
    candidates = graph.operation("select-ready-work", principal, scope)
    if not candidates:
        return {"status": "idle", "scope": scope}
    candidate = candidates[0]
    if not isinstance(candidate.get("id"), str) or not isinstance(candidate.get("version"), int):
        raise RuntimeError("invalid_selected_work")
    job = {
        "scope": scope,
        "work": candidate["id"],
        "attempt": _id("attempt"),
        "invocation": _id("invocation"),
    }
    result = execute(job, worker.request)
    return {"status": result["status"], "scope": scope, "work": job["work"],
            "attempt": job["attempt"], "invocation": job["invocation"],
            "receipt": result["receipt"], "accepted": False}


def main() -> int:
    scope = os.environ.get("SEEDFORTH_AUTONOMOUS_SCOPE", "")
    principal = os.environ.get("SEEDFORTH_AUTONOMOUS_PRINCIPAL", "")
    token_file_value = os.environ.get("SEEDFORTH_WORKER_TOKEN_FILE", "")
    token_file = Path(token_file_value) if token_file_value else None
    socket_path = os.environ.get("SEEDFORTH_WORKER_SOCKET", "/run/seedforth-worker/broker.sock")
    if not scope or not principal or token_file is None:
        print(json.dumps({"status": "not_configured"}))
        return 2
    token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        print(json.dumps({"status": "credential_unavailable", "scope": scope}))
        return 2
    worker = WorkerClient(socket_path, token, scope)
    print(json.dumps(run_once(Graph(), worker, principal, scope), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
