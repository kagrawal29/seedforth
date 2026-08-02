#!/usr/bin/env python3
"""Link ProgressEvents to EntityGoals via DeepSeek semantic matching.

Thin I/O boundary: reads raw events + goals from the graph, calls the LLM to
match each event to its best-fit goal, writes DIRECTED edges. The direction
protocol consumes these edges to compute goal_progress/alignment/focus.

Only matches events WITHOUT an existing DIRECTED edge. Writes the LLM's
reasoning to the edge so the SuperAgent can audit why something aligned.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import ql, q

ENV_PATH = os.environ.get("DELTA_ENV_PATH", "/opt/delta/delta.env")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"


def get_key():
    try:
        for line in open(ENV_PATH):
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def llm_text(prompt, system="You map work evidence to project goals."):
    key = get_key()
    if not key:
        return None
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 300,
    }).encode()
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={"Authorization": "Bearer %s" % key,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def main():
    # Events from the last 90 days, not yet linked, with a project that has goals
    rows = ql(
        "MATCH (pe:ProgressEvent) "
        "WHERE pe.created_at > datetime() - duration({days: 90}) "
        "AND NOT ((pe)-[:DIRECTED]->()) "
        "WITH pe ORDER BY pe.entity, pe.created_at "
        "RETURN pe.node_id, pe.entity, coalesce(pe.evidence, ''), pe.weight LIMIT 200"
    )
    if not rows:
        print("linker: no unlinked events")
        return

    # Goals per project
    goals_by_entity = {}
    for node_id, entity, evidence, weight in rows:
        if entity not in goals_by_entity:
            gs = ql(
                "MATCH (g:EntityGoal {project:$e, status:'active'}) "
                "RETURN g.node_id, g.goal ORDER BY g.priority",
                {"e": entity},
            )
            goals_by_entity[entity] = [(gid, goal) for gid, goal in gs]

    linked = skipped = 0
    for node_id, entity, evidence, weight in rows:
        goals = goals_by_entity.get(entity, [])
        if not goals:
            skipped += 1
            continue
        if not evidence or not evidence.strip():
            skipped += 1
            continue

        goal_list = "\n".join(f"{i}. {g[1][:120]}" for i, g in enumerate(goals))
        prompt = (
            f"Project: {entity}\n"
            f"Work evidence: {evidence[:300]}\n\n"
            f"Active goals:\n{goal_list}\n\n"
            f"Which goal number does this evidence best serve? "
            f"Reply with just the number, or 0 if it serves none."
        )
        answer = llm_text(prompt)
        if answer is None:
            continue
        try:
            idx = int("".join(c for c in answer if c.isdigit())[:2])
        except (ValueError, IndexError):
            continue
        if idx <= 0 or idx > len(goals):
            continue
        gid, goal = goals[idx - 1]
        q(
            "MATCH (pe:ProgressEvent {node_id:$pn}) "
            "MATCH (g:EntityGoal {node_id:$gn}) "
            "MERGE (pe)-[:DIRECTED {decay_protected:true}]->(g)",
            {"pn": node_id, "gn": gid},
        )
        linked += 1

    print(f"linker: {linked} linked, {skipped} skipped (no goals/evidence), "
          f"{len(rows) - linked - skipped} unmatched")


if __name__ == "__main__":
    main()
