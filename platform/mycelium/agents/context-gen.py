#!/usr/bin/env python3
"""
Context Generation Agent -- builds per-person context files from demand profiles,
cross-person connections, community map, and dream proposals.

Runs on Sonnet. Generates ~500-token context blocks that make Claude sessions
aware of cross-person connections without anyone querying the graph.

Cost: ~$0.50-1.00/run (Sonnet, 6 people).
"""

import asyncio
import json
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    return yaml.safe_load(config_path.read_text())


# Hardcoded fallback from issue #17 demand analysis.
# Used when signals/demand/ files don't exist yet.
FALLBACK_DEMANDS = {
    "Pranav": {
        "person": "Pranav",
        "question_clusters": [
            {
                "id": "rule-testing-operations",
                "representative_question": "How do I test rules against real data?",
                "frequency": 7,
                "frustration": "high",
                "domain": "rule-builder",
                "matched_entries": [
                    {"entry_id": "rule-builder-group-logic", "coverage_score": 0.3, "gap": "no testing workflow"}
                ],
                "gap_signal": True,
            }
        ],
        "summary": {
            "total_questions": 7,
            "gaps": 1,
            "cross_person_connections": [
                "rule conditions use category scoping that connects to Sahiram's memory schema work"
            ],
        },
    },
    "Abhishek": {
        "person": "Abhishek",
        "question_clusters": [
            {
                "id": "tech-stack-extensions",
                "representative_question": "How do I extend the notification system for new channels?",
                "frequency": 10,
                "frustration": "medium",
                "domain": "tech-stack",
                "matched_entries": [],
                "gap_signal": True,
            }
        ],
        "summary": {
            "total_questions": 10,
            "gaps": 1,
            "cross_person_connections": [
                "notification architecture connects to Sahiram's continuity and memory work"
            ],
        },
    },
    "Sahiram": {
        "person": "Sahiram",
        "question_clusters": [
            {
                "id": "memory-spec",
                "representative_question": "What is the memory schema structure?",
                "frequency": 5,
                "frustration": "medium",
                "domain": "memory",
                "matched_entries": [],
                "gap_signal": False,
            },
            {
                "id": "continuity-patterns",
                "representative_question": "How do we maintain session continuity?",
                "frequency": 4,
                "frustration": "medium",
                "domain": "continuity",
                "matched_entries": [],
                "gap_signal": False,
            },
        ],
        "summary": {
            "total_questions": 9,
            "gaps": 0,
            "cross_person_connections": [
                "memory schema must align with Ankit-S's frontend data structures",
                "continuity layer connects to Sahil's agent harness",
            ],
        },
    },
    "Ankit-S": {
        "person": "Ankit-S",
        "question_clusters": [
            {
                "id": "frontend-architecture",
                "representative_question": "How should frontend components structure their data layer?",
                "frequency": 4,
                "frustration": "medium",
                "domain": "frontend",
                "matched_entries": [],
                "gap_signal": False,
            }
        ],
        "summary": {
            "total_questions": 4,
            "gaps": 0,
            "cross_person_connections": [
                "frontend data structures must match Sahiram's memory schema"
            ],
        },
    },
    "Sahil": {
        "person": "Sahil",
        "question_clusters": [
            {
                "id": "agent-harness",
                "representative_question": "How does the agent harness manage tool access?",
                "frequency": 3,
                "frustration": "low",
                "domain": "agent-harness",
                "matched_entries": [],
                "gap_signal": False,
            }
        ],
        "summary": {
            "total_questions": 3,
            "gaps": 0,
            "cross_person_connections": [
                "agent harness continuity connects to Sahiram's memory layer"
            ],
        },
    },
}

FALLBACK_CROSS_PERSON = {
    "connections": [
        {
            "persons": ["Ankit-S", "Sahiram"],
            "topic": "frontend data structures must match memory schema",
            "strength": "strong",
            "direction": "bidirectional",
        },
        {
            "persons": ["Sahiram", "Sahil"],
            "topic": "memory layer + continuity patterns",
            "strength": "medium",
            "direction": "bidirectional",
        },
        {
            "persons": ["Abhishek", "Sahiram"],
            "topic": "notifications + tech stack depends on memory/continuity",
            "strength": "medium",
            "direction": "Abhishek -> Sahiram",
        },
        {
            "persons": ["Pranav", "Sahiram"],
            "topic": "rule conditions use category scoping tied to memory schema",
            "strength": "medium",
            "direction": "Pranav -> Sahiram",
        },
    ],
    "generated": "2026-04-10",
    "source": "issue-17-analysis",
}


def load_demand_profile(person_name: str, root: Path) -> dict:
    """Load demand profile from file, falling back to hardcoded data."""
    demand_file = root / "signals" / "demand" / f"{person_name}-demand.json"
    if demand_file.exists():
        return json.loads(demand_file.read_text())
    return FALLBACK_DEMANDS.get(person_name, {})


def load_cross_person_demands(root: Path) -> dict:
    """Load cross-person demands from file, falling back to hardcoded data."""
    cross_file = root / "signals" / "demand" / "cross-person-demands.json"
    if cross_file.exists():
        return json.loads(cross_file.read_text())
    return FALLBACK_CROSS_PERSON


def build_prompt(config: dict, root: Path) -> str:
    team = config["team"]
    date = datetime.now().strftime("%Y-%m-%d")

    # Load all demand data
    demands = {}
    for member in team:
        name = member["name"]
        profile = load_demand_profile(name, root)
        if profile:
            demands[name] = profile

    cross_demands = load_cross_person_demands(root)

    # Build the data context for the agent
    demand_json = json.dumps(demands, indent=2)
    cross_json = json.dumps(cross_demands, indent=2)

    person_list = ", ".join(m["name"] for m in team)

    return f"""You are the context generation agent for Mycelium. You produce per-person context files that make Claude sessions aware of cross-person connections.

## Your Job

For each team member, generate a concise context block (~500 tokens max) that surfaces:
1. Recent decisions that affect their work
2. Cross-person connections they don't know about
3. Question expansions -- their question connects to something broader

## Team Members
{person_list}

## Demand Profiles (per person)
{demand_json}

## Cross-Person Connections
{cross_json}

## Additional Context Sources

Read these files if they exist (skip gracefully if missing):
- `distribution/shared-rules/knowledge-graph-map.md` -- community map showing clusters and bridges
- `knowledge/meta/dream-proposals.md` -- structural analysis (missing triangles, fragile bridges)
- Knowledge entries in `knowledge/` -- check any entry_ids referenced in matched_entries

## Output Format

For each person who has demand data, write a file to `distribution/person-context/{{name}}.md` with this exact format:

```markdown
---
paths:
  - "**/*"
---

# Context for {{Person}} -- {date}

## Decisions that affect your current work
- [Decision]: [brief] -- settled by [person] on [date]. Relevant because [connection].

## Cross-team connections
- Your work on [X] connects to [Person B]'s work on [Y]. [Why this matters].
- [Person C] resolved [topic] -- the answer is [brief]. This affects your [domain].

## Expanding your questions
- You've been asking about [representative_question]. Related: [entry/decision/exploration].
- [Question] connects to [community bridge] -- consider checking [entry_id].
```

## Rules

- CONCISE. ~500 tokens max per file. Claude loads this every session -- bloat kills value.
- Direct, factual tone. "Sahiram settled the memory schema on Apr 8" not "exciting cross-pollination opportunity."
- No marketing language. No "synergy", "leverage", "exciting".
- Only include connections that are genuinely useful. Skip a section if empty rather than padding.
- The frontmatter `paths: ["**/*"]` is required -- it tells the distribution system this is a Level 0 rule.
- If a person has no demand data (like Kshitiz), skip them.
- Read knowledge entries referenced in matched_entries to ground your connections in actual content.

## Steps

1. Read any available context files (community map, dream proposals, relevant knowledge entries)
2. For each person with demand data, synthesize their context
3. Write each file to `distribution/person-context/{{name}}.md`
4. Print a summary of what was generated

Do NOT modify any existing files. Only create new files in `distribution/person-context/`.
"""


async def main():
    config = load_config()
    root = Path(__file__).parent.parent
    prompt = build_prompt(config, root)

    print(f"[context-gen] Starting at {datetime.now().isoformat()}")
    print(f"[context-gen] Root: {root}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Glob", "Grep"],  # No Bash/Edit — invariant 5: reads graph, writes context files
            permission_mode="bypassPermissions",
            cwd=str(root),
            max_turns=30,
            max_budget_usd=2.0,
            model="sonnet",
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"[context-gen] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(
                f"  Cost: ${message.total_cost_usd:.4f}"
                if message.total_cost_usd
                else "  Cost: unknown"
            )
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
