#!/usr/bin/env python3
"""
Intent Engine (L5) — extracts the question beneath the question.

Reads demand engine output (per-person demand files) and LangSmith signal files.
For each demand cluster, identifies the latent intent — what the person is actually
trying to figure out, not just what they asked.

Output: signals/demand/{person}-intents.json + cross-person-intents.json
Model: Sonnet.
"""

import asyncio
import json
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    return yaml.safe_load(config_path.read_text())


def get_demand_files(demand_dir: Path) -> list[str]:
    """Return paths to per-person demand JSON files."""
    if not demand_dir.exists():
        return []
    return sorted(str(f) for f in demand_dir.glob("*-demand.json") if f.name != "cross-person-demands.json")


def get_signal_files(signals_dir: Path, limit: int = 4) -> list[str]:
    """Return paths to the most recent LangSmith signal files."""
    ls_dir = signals_dir / "langsmith"
    if not ls_dir.exists():
        return []
    files = sorted(ls_dir.glob("*.md"), reverse=True)
    return [str(f) for f in files[:limit]]


def build_prompt(config, demand_files: list[str], signal_files: list[str]):
    team = config["team"]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    team_names = ", ".join(m["name"] for m in team)

    demand_list = "\n".join(f"  - {f}" for f in demand_files) if demand_files else "  (none)"
    signal_list = "\n".join(f"  - {f}" for f in signal_files) if signal_files else "  (none)"

    cross_demands_path = Path(demand_files[0]).parent / "cross-person-demands.json" if demand_files else None
    cross_demands_line = f"  - {cross_demands_path}" if cross_demands_path and cross_demands_path.exists() else "  (none)"

    return f"""You are the intent extraction engine for the meta intelligence system. Your job is to look beneath surface-level questions and extract the underlying information needs — the question beneath the question.

## Context

The demand engine has already extracted and clustered surface questions from LangSmith traces. You go deeper: for each demand cluster, you identify what the person is ACTUALLY trying to figure out.

Example:
- Surface demand: "how do I test rules against data?" (asked 7 times)
- Underlying intent: "I don't trust the system to maintain category coherence when I'm not watching" — the person needs a validation/confidence mechanism, not just a test command.

Team members: {team_names}
Current timestamp: {date}

## Inputs

### Per-person demand files (from demand engine):
{demand_list}

### Cross-person demands:
{cross_demands_line}

### LangSmith signal files (raw traces for deeper analysis):
{signal_list}

## What to Do

### Step 1: Read all demand files
Read each per-person demand JSON. Note the question clusters, frustration levels, and gaps.

### Step 2: Read signal files for context
For each person with demand clusters, read their trace sections in the signal files.
Look for:
- **Patterns of behavior** around the questions — what did they try before asking?
- **Emotional trajectory** — did frustration build? Did they give up? Did they pivot?
- **What they stopped asking about** — abandoned questions indicate either resolution or resignation
- **Repeated context-setting** — when someone keeps re-explaining their situation to Claude, the real question is something Claude keeps missing

### Step 3: Extract intents per person

For each demand cluster, produce an intent:

```json
{{
  "intent_id": "kebab-case-id",
  "source_cluster_id": "the-demand-cluster-id-this-came-from",
  "surface_question": "What they literally asked",
  "underlying_intent": "What they're actually trying to figure out (1-2 sentences)",
  "intent_domain": "architecture|workflow|tooling|integration|debugging|process",
  "evidence": "Why you believe this is the real intent (cite specific trace behavior)",
  "frustration_driver": "What specifically is causing frustration, if any",
  "recurrence_count": 3,
  "graph_region": "Which knowledge graph community/domain this maps to"
}}
```

Some demand clusters may share the same underlying intent. Merge them.
Some may have NO deeper intent — the surface question IS the real question. Mark these with `"underlying_intent": null`.

### Step 4: Detect cross-person intent alignment

This is the critical step. Compare intents ACROSS people:

For each pair of intents from different people, check:
1. Do they point at the same knowledge gap? (same graph region, related domains)
2. Are they approaching the same problem from different angles?
3. Would resolving one intent help the other person?

Write alignment signals — these are proto-convergence events:

```json
{{
  "alignment_id": "kebab-case",
  "persons": ["Person1", "Person2"],
  "person1_intent": "their-intent-id",
  "person2_intent": "their-intent-id",
  "shared_gap": "The underlying need they share (1 sentence)",
  "confidence": "high|medium|low",
  "graph_region": "Where in the graph this gap lives"
}}
```

### Step 5: Write output files

For each person, write `signals/demand/{{name}}-intents.json`:

```json
{{
  "person": "Name",
  "computed_at": "{date}",
  "intents": [
    {{
      "intent_id": "string",
      "source_cluster_id": "string",
      "surface_question": "string",
      "underlying_intent": "string or null",
      "intent_domain": "string",
      "evidence": "string",
      "frustration_driver": "string or null",
      "recurrence_count": 1,
      "graph_region": "string"
    }}
  ]
}}
```

Write `signals/demand/cross-person-intents.json`:

```json
{{
  "computed_at": "{date}",
  "alignments": [
    {{
      "alignment_id": "string",
      "persons": ["Person1", "Person2"],
      "person1_intent": "intent-id",
      "person2_intent": "intent-id",
      "shared_gap": "string",
      "confidence": "high|medium|low",
      "graph_region": "string"
    }}
  ],
  "summary": {{
    "total_intents": 10,
    "intents_with_deeper_meaning": 6,
    "cross_person_alignments": 3,
    "highest_alignment_region": "domain-name"
  }}
}}
```

If a person has no demand clusters, write an empty intents file.

## Important

- Be honest. If a surface question IS the real question, say so. Don't fabricate depth.
- Evidence matters. Every intent must cite specific behavior from the traces.
- Cross-person alignment is the highest-value output. Look hard for it.
- Use graph regions that match the community structure (check knowledge/search-index.md or the community map if available).
- Write valid JSON with indent=2.
"""


async def main():
    config = load_config()
    root = Path(__file__).parent.parent

    demand_dir = root / "signals" / "demand"
    demand_files = get_demand_files(demand_dir)
    signal_files = get_signal_files(root / "signals")

    if not demand_files:
        print("[intent-engine] No demand files found. Run demand engine first.")
        # Write empty intent files
        demand_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        for member in config["team"]:
            empty = {"person": member["name"], "computed_at": now, "intents": []}
            out = demand_dir / f"{member['name']}-intents.json"
            out.write_text(json.dumps(empty, indent=2))
        cross = {"computed_at": now, "alignments": [], "summary": {"total_intents": 0, "intents_with_deeper_meaning": 0, "cross_person_alignments": 0, "highest_alignment_region": None}}
        (demand_dir / "cross-person-intents.json").write_text(json.dumps(cross, indent=2))
        print("  Wrote empty intent files.")
        return

    prompt = build_prompt(config, demand_files, signal_files)

    print(f"[intent-engine] Starting at {datetime.now().isoformat()}")
    print(f"  Demand files: {len(demand_files)}")
    print(f"  Signal files: {len(signal_files)}")
    print(f"  Team members: {len(config['team'])}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Glob", "Grep"],  # No Bash — invariant 5,
            permission_mode="bypassPermissions",
            cwd=str(root),
            max_turns=40,
            max_budget_usd=3.0,
            model="sonnet",
            env={
                "CLAUDE_CODE_ENABLE_TELEMETRY": "true",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "https://api.smith.langchain.com/otel",
                "OTEL_EXPORTER_OTLP_HEADERS": f"x-api-key={os.environ.get('CC_LANGSMITH_API_KEY', '')}",
                "OTEL_TRACES_EXPORTER": "otlp",
                "OTEL_LOGS_EXPORTER": "otlp",
                "LANGSMITH_PROJECT": "maverick-meta-agents",
            },
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"[intent-engine] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
