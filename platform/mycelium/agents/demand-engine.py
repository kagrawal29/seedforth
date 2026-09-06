#!/usr/bin/env python3
"""
Demand Engine — extracts question clusters from LangSmith traces per team member.

Standalone Agent SDK script. Reads ingested signal files, identifies questions
(explicit and implicit), clusters them, scores frustration, and maps against
existing knowledge entries to find gaps.

Output: signals/demand/{person}-demand.json + cross-person-demands.json
Model: Sonnet (mechanical extraction + clustering).
Cost: ~$1-2/run.
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


def get_latest_signal_files(signals_dir: Path, limit: int = 4) -> list[str]:
    """Return paths to the most recent LangSmith signal files."""
    ls_dir = signals_dir / "langsmith"
    if not ls_dir.exists():
        return []
    files = sorted(ls_dir.glob("*.md"), reverse=True)
    return [str(f) for f in files[:limit]]


def get_mcp_trace_file(root: Path) -> str | None:
    """Return path to MCP trace JSONL if it has content."""
    trace = root / "knowledge" / "meta" / "asgard-graph-traces.jsonl"
    if trace.exists() and trace.stat().st_size > 10:
        return str(trace)
    return None


def list_knowledge_entries(knowledge_dir: Path) -> list[str]:
    """Return all knowledge entry paths (excluding meta/)."""
    entries = []
    for subdir in ["architecture", "patterns", "anti-patterns", "workflows", "tool-configs"]:
        d = knowledge_dir / subdir
        if d.exists():
            entries.extend(str(f) for f in d.glob("*.md"))
    return sorted(entries)


def build_prompt(config, signal_files: list[str], knowledge_entries: list[str], mcp_trace_file: str | None = None):
    team = config["team"]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    date_short = datetime.now().strftime("%Y-%m-%d")

    team_names = ", ".join(m["name"] for m in team)

    signal_file_list = "\n".join(f"  - {f}" for f in signal_files) if signal_files else "  (no signal files found)"
    entry_list = "\n".join(f"  - {e}" for e in knowledge_entries) if knowledge_entries else "  (no knowledge entries found)"

    mcp_section = ""
    if mcp_trace_file:
        mcp_section = f"""
## Input: Asgard Graph MCP Traces

The team also queries the knowledge graph directly via MCP tools. These are LIVE demand signals — the person chose to ask the graph, which means it's a real need.

Read this JSONL file:
  - {mcp_trace_file}

Each line is a JSON object with: timestamp, tool, query, person (forest alias), num_results, latency_ms.
Map forest aliases to team members: Banyan=Sahiram, Sequoia=Abhishek, Birch=Ankit-S, Cedar=Sahil, Oak=Pranav, Mycelium=Kshitiz.
Extract questions from the "query" field and include them in the person's demand clusters.
MCP queries are HIGH-SIGNAL — someone actively searched the graph. Weight them higher than passive trace questions.
"""

    return f"""You are the demand engine for the meta intelligence system. Your job is to extract questions and demand patterns from LangSmith trace signals AND Asgard Graph MCP traces, cluster them per person, and map them against existing knowledge entries to find gaps.

## Configuration

Team members: {team_names}
Current timestamp: {date}

## Input: LangSmith Signal Files

Read these signal files (most recent first):
{signal_file_list}

Each file has sections per team member with their conversation turns (User/Claude pairs).
{mcp_section}
## Input: Knowledge Entries

These are the existing knowledge entries to check coverage against:
{entry_list}

Also read `knowledge/search-index.md` for keyword-to-entry mapping.

## What to Do

### Step 1: Read all signal files
Read each signal file listed above. Parse out each team member's turns.

### Step 2: For each team member, extract QUESTIONS

Scan every user message for:

1. **Explicit questions**: "how do I...", "what is...", "should we...", "can you explain...", "what about..."
2. **Implicit questions** (repeated attempts): User tries the same thing multiple times across turns, rephrases, goes in circles. The underlying question is "how do I actually do X?"
3. **Frustration signals**: Corrections ("no, I said...", "that's wrong"), anger ("DO NOT", "stop doing X", "you keep..."), exasperation. These indicate a question the system failed to answer.
4. **Architecture/decision probes**: "is X decided?", "what about Y?", "have we settled on...", "what's the plan for..."
5. **Gap signals**: User asks about something and Claude clearly lacks context or gives a generic answer.

For each extracted question, note:
- The raw question text (or your summary of the implicit question)
- Which signal file and approximate timestamp
- Question type (explicit/implicit/frustration/probe)
- Frustration level: low (simple ask), medium (rephrased/repeated), high (corrections/anger)

### Step 3: Cluster similar questions per person

Group related questions into clusters. For example:
- "how to test rules" + "run rules against data" + "debug rule conditions" -> cluster: "rule-testing-operations"

For each cluster compute:
- `id`: kebab-case identifier
- `representative_question`: the clearest formulation
- `all_questions`: list of raw question texts
- `frequency`: number of questions in the cluster
- `frustration`: highest frustration level in the cluster
- `first_asked` and `last_asked`: date range
- `domain`: which product/technical domain this falls in

### Step 4: Match clusters against knowledge entries

For each cluster:
1. Read `knowledge/search-index.md` and find entries whose keywords overlap with the cluster's domain
2. Read the matched knowledge entry files to check actual content coverage
3. Score coverage:
   - 0.0 = no relevant entry exists
   - 0.1-0.3 = entry exists but barely covers this question
   - 0.4-0.6 = entry partially covers it
   - 0.7-0.9 = entry mostly covers it
   - 1.0 = fully answered by existing entry
4. Note the gap: what specifically is NOT covered

A cluster is a `gap_signal: true` if max coverage_score < 0.5.

### Step 5: Write per-person demand files

For each team member, write `signals/demand/{{name}}-demand.json` with this structure:

```json
{{
  "person": "Name",
  "computed_at": "{date}",
  "question_clusters": [
    {{
      "id": "kebab-case-cluster-id",
      "representative_question": "The clearest formulation of this question",
      "all_questions": ["raw question 1", "raw question 2"],
      "frequency": 3,
      "frustration": "low|medium|high",
      "first_asked": "2026-04-08",
      "last_asked": "2026-04-10",
      "domain": "domain-name",
      "matched_entries": [
        {{
          "entry_id": "category-entry-name",
          "coverage_score": 0.3,
          "gap": "What specifically is not covered"
        }}
      ],
      "gap_signal": true
    }}
  ],
  "summary": {{
    "total_questions": 7,
    "gaps": 1,
    "highest_frustration_domain": "domain-name",
    "cross_person_connections": ["Person (reason for overlap)"]
  }}
}}
```

If a person has no traces or no extractable questions, write an empty demand file:
```json
{{
  "person": "Name",
  "computed_at": "{date}",
  "question_clusters": [],
  "summary": {{
    "total_questions": 0,
    "gaps": 0,
    "highest_frustration_domain": null,
    "cross_person_connections": []
  }}
}}
```

### Step 6: Write cross-person demands

After all individual files are written, analyze across people for shared themes.
Write `signals/demand/cross-person-demands.json`:

```json
{{
  "computed_at": "{date}",
  "cross_demands": [
    {{
      "persons": ["Person1", "Person2"],
      "shared_concept": "kebab-case-concept",
      "person1_question": "Their representative question",
      "person2_question": "Their representative question",
      "connection": "Why these are related (one sentence)",
      "knowledge_bridge": "entry-id-that-could-serve-both or null"
    }}
  ]
}}
```

### Step 7: Update demand watermark

After writing all files, update the watermarks file to record this demand run.
Read `signals/.watermarks.yaml`, add a `demand` section:

```python
import yaml
from pathlib import Path
from datetime import datetime, timezone

wm_path = Path("signals/.watermarks.yaml")
wm = yaml.safe_load(wm_path.read_text())

wm["demand"] = {{
    "last_run": datetime.now(timezone.utc).isoformat(),
    "signal_files_processed": {json.dumps(signal_files)},
    "persons_analyzed": {json.dumps([m['name'] for m in team])},
    "status": "success"
}}

import tempfile, os
fd, tmp = tempfile.mkstemp(dir=str(wm_path.parent), suffix=".yaml.tmp")
with os.fdopen(fd, "w") as f:
    yaml.dump(wm, f, default_flow_style=False, sort_keys=False)
os.rename(tmp, str(wm_path))
```

## Important

- Handle missing data gracefully. If a person has no traces, write an empty demand file.
- If signal files don't exist or are empty, write empty demand files for all and exit cleanly.
- Be thorough in question extraction. Read the FULL user messages, not just the first line.
- Cluster aggressively -- "how to test rules" and "debug rule conditions" are the same demand cluster.
- Frustration scoring matters. Look for tone: ALL CAPS, exclamation marks, "you keep doing X", "I already told you", corrections.
- The domain field should be product-meaningful: "rule-builder", "notification-system", "memory-layer", "agent-harness", etc.
- Write valid JSON. Use Python json.dumps with indent=2 for output files.
"""


async def main():
    config = load_config()
    root = Path(__file__).parent.parent

    signal_files = get_latest_signal_files(root / "signals")
    knowledge_entries = list_knowledge_entries(root / "knowledge")
    mcp_trace = get_mcp_trace_file(root)

    if not signal_files and not mcp_trace:
        print("[demand-engine] No signal files or MCP traces found. Nothing to process.")
        # Write empty demand files for all team members
        demand_dir = root / "signals" / "demand"
        demand_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        for member in config["team"]:
            empty = {
                "person": member["name"],
                "computed_at": now,
                "question_clusters": [],
                "summary": {
                    "total_questions": 0,
                    "gaps": 0,
                    "highest_frustration_domain": None,
                    "cross_person_connections": [],
                },
            }
            out = demand_dir / f"{member['name']}-demand.json"
            out.write_text(json.dumps(empty, indent=2))
            print(f"  Wrote empty demand: {out.name}")

        cross = {
            "computed_at": now,
            "cross_demands": [],
        }
        (demand_dir / "cross-person-demands.json").write_text(json.dumps(cross, indent=2))
        print("  Wrote empty cross-person-demands.json")
        return

    prompt = build_prompt(config, signal_files, knowledge_entries, mcp_trace)

    print(f"[demand-engine] Starting at {datetime.now().isoformat()}")
    print(f"  Signal files: {len(signal_files)}")
    print(f"  MCP trace file: {'yes' if mcp_trace else 'no'}")
    print(f"  Knowledge entries: {len(knowledge_entries)}")
    print(f"  Team members: {len(config['team'])}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Glob", "Grep"],  # No Bash — invariant 5,
            permission_mode="bypassPermissions",
            cwd=str(root),
            max_turns=40,
            max_budget_usd=2.0,
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
            print(f"[demand-engine] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
