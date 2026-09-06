#!/usr/bin/env python3
"""Observability collector (P3.4) — writes :Metric nodes from opencode stats.

Runs `opencode stats --project <name> --days 7` for each active project and
parses the ASCII table into :Metric nodes in the graph. The SuperAgent can
then query spend/latency per agent:
  MATCH (m:Metric {metric:'cost_usd'}) RETURN m.agent, m.value, m.created_at

Metrics written per agent: sessions, messages, input_tokens, output_tokens,
cache_read, cache_write, cost_usd.

Runs in the deep cycle (daily). Uses the fast HTTP API.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q

REGISTRY_PATH = "/opt/delta/delta-registry.json"
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 7


def parse_table(output):
    """Parse opencode's box-drawing table into a dict of label->value."""
    data = {}
    for line in output.splitlines():
        raw = line
        if "│" in line:
            # strip box-drawing vertical bars and edges
            line = line.split("│")
            # keep the middle content cells
            cells = [c for c in line if c.strip()]
            if cells:
                line = cells[0] if len(cells) == 1 else "   ".join(cells)
            else:
                continue
        line = line.strip()
        if not line or line.startswith(("┌", "├", "└", "─")):
            continue
        # e.g. "Total Cost                                        $0.00"
        # label = leading letters/spaces/slash, value = trailing token.
        m = re.match(r"^([A-Za-z /]+?)\s{2,}(\S.*)$", line)
        if m:
            data[m.group(1).strip()] = m.group(2).strip()
    return data


def _num(v):
    if not v:
        return None
    v = v.replace(",", "")
    if v.endswith("K"):
        try:
            return float(v[:-1]) * 1000
        except ValueError:
            return None
    m = re.search(r"[\d.]+", v)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def collect(project_name):
    try:
        r = subprocess.run(
            ["opencode", "stats", "--project", project_name, "--days", str(DAYS)],
            capture_output=True, text=True, timeout=60,
        )
        output = r.stdout or r.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  {project_name}: stats failed ({e})")
        return
    data = parse_table(output)
    if not data:
        print(f"  {project_name}: no parseable stats")
        return

    metrics = {
        "sessions": _num(data.get("Sessions")),
        "messages": _num(data.get("Messages")),
        "cost_usd": _num(data.get("Total Cost")),
        "input_tokens": _num(data.get("Input")),
        "output_tokens": _num(data.get("Output")),
        "cache_read": _num(data.get("Cache Read")),
        "cache_write": _num(data.get("Cache Write")),
    }
    ts = int(time.time() * 1000)
    for metric, value in metrics.items():
        if value is None:
            continue
        q(
            "CREATE (m:Metric {node_id:$nid, agent:$ag, metric:$metric, "
            "value:$val, window_days:$days, created_at:datetime(), project:'system'})",
            {"nid": f"metric-{metric}-{project_name}-{ts}", "ag": project_name,
             "metric": metric, "val": value, "days": DAYS},
        )
    print(f"  {project_name}: {metrics.get('cost_usd')} cost, "
          f"{metrics.get('input_tokens', 0)} in / {metrics.get('output_tokens', 0)} out")


def main():
    print(f"=== OBSERVABILITY COLLECTOR ({DAYS}d) ===")
    registry = json.load(open(REGISTRY_PATH))
    for name, proj in sorted(registry.get("projects", {}).items()):
        if proj.get("status") != "active":
            continue
        collect(name)
    print("=== COMPLETE ===")


if __name__ == "__main__":
    main()
