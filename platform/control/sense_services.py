"""Observe the outcome of allowlisted SeedForth systemd units.

Process sensing answers whether a product process exists. This adapter answers
whether the scheduled control-loop units themselves last succeeded. It stores
only deterministic unit status, exit code and timestamps; systemd output never
becomes executable graph content.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
from uuid import uuid4

from control.graph import Graph

ACTOR = "principal-service-sensor"
SCOPE = "seedforth-platform"
ADAPTER = "systemd-unit-health-v1"


def show_unit(unit: str, runner=subprocess.run) -> dict[str, str]:
    if not isinstance(unit, str) or not unit.endswith(".service") or "/" in unit or ".." in unit:
        raise ValueError("unapproved_unit")
    result = runner(
        ["/usr/bin/systemctl", "show", unit,
         "--property=ActiveState,SubState,Result,ExecMainStatus,ExecMainExitTimestamp"],
        capture_output=True, text=True, timeout=10, check=True,
        env={"PATH": "/usr/bin:/bin", "SYSTEMD_COLORS": "0"},
    )
    values = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"ActiveState", "SubState", "Result", "ExecMainStatus", "ExecMainExitTimestamp"}:
            values[key] = value[:256]
    if set(values) != {"ActiveState", "SubState", "Result", "ExecMainStatus", "ExecMainExitTimestamp"}:
        raise ValueError("incomplete_unit_status")
    if not values["ExecMainStatus"].isdigit() or int(values["ExecMainStatus"]) < 0:
        raise ValueError("invalid_unit_exit_status")
    return values


def collect(graph: Graph, revision: str, runner=subprocess.run):
    sources = graph.query(
        "MATCH (s:SourceStream {adapter:$adapter,enabled:true,scope_id:$scope}) "
        "RETURN s.node_id AS id,s.unit AS unit", {"adapter": ADAPTER, "scope": SCOPE}
    )
    outcomes = []
    for source in sources:
        observed_at = datetime.now(timezone.utc).isoformat()
        status = "success"
        values = {"ActiveState": "unknown", "SubState": "unknown", "Result": "unknown",
                  "ExecMainStatus": "1", "ExecMainExitTimestamp": ""}
        try:
            values = show_unit(source["unit"], runner)
            if values["Result"] != "success":
                status = "failed"
        except (OSError, ValueError, subprocess.SubprocessError):
            status = "collection_failed"
        payload = {"source": source["id"], "unit": source["unit"],
                   "observed_at": observed_at, "status": status,
                   "adapter_revision": revision,
                   "active_state": values["ActiveState"],
                   "sub_state": values["SubState"],
                   "result": values["Result"],
                   "exec_main_status": values["ExecMainStatus"],
                   "exit_timestamp": values["ExecMainExitTimestamp"]}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        rows = graph.operation("record-service-observation", ACTOR, SCOPE,
                               **payload, event_id="obs-" + str(uuid4()), payload_hash=digest)
        if len(rows) != 1:
            raise RuntimeError("observation_not_persisted")
        outcomes.append({"unit": source["unit"], "status": rows[0]["status"]})
    if not sources:
        raise RuntimeError("no_registered_sources")
    return outcomes


if __name__ == "__main__":
    print(json.dumps(collect(Graph(), os.environ["SEEDFORTH_RELEASE_SHA"])))
