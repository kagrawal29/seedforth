#!/usr/bin/env python3
"""
Feedback Agent — evaluates system effectiveness from LangSmith traces.

Standalone Agent SDK script. Runs daily (end of work day).
Opus: nuanced judgment on whether corrections relate to surfaced entries.
Cost: ~$3-5/run.
"""

import asyncio
import os
import sys
import yaml
from pathlib import Path
from datetime import datetime

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    return yaml.safe_load(config_path.read_text())


def build_prompt(config):
    team = config["team"]
    ls = config["langsmith"]
    date = datetime.now().strftime("%Y-%m-%d")

    team_list = "\n".join(
        f"  - {m['name']}: {m['langsmith_project']}" for m in team
    )

    return f"""You are the feedback agent for the meta intelligence system. You evaluate whether our distributed knowledge is helping the team — purely from LangSmith trace analysis.

## Your Job
Read team LangSmith traces. For each knowledge entry, determine whether it was surfaced, cited, or contradicted. Update effectiveness scores. Detect gaps where no entry exists but should. All changes are PROPOSALS — Heimdall approves.

## Data Source: LangSmith Traces

Team members:
{team_list}

API: {ls['base_url']}
Key env var: {ls['api_key_env']}

Fetch recent traces using Python urllib (same pattern as ingest agent). Use `is_root: true` and `select: ["status", "start_time", "inputs", "outputs"]`.

## Steps

### Step 1: Read team traces from LangSmith
For each team member, fetch recent traces (since last feedback run).
Read the watermarks at `signals/.watermarks.yaml` to find last processed timestamps.

### Step 2: Check delivery verification (rules-loaded traces)
Before scoring entries, check which entries were actually LOADED in team sessions.
Query `rules-loaded` custom traces for each team member:
```python
body = json.dumps({{
    "session": [project_uuid],
    "limit": 5,
    "filter": 'eq(name, "rules-loaded")',
    "select": ["start_time", "inputs"]
}}).encode()
```
The `inputs.manifest.knowledge_entries` lists exactly which entry files were present.
An entry can only be "surfaced" in a session where it was loaded. If an entry was never loaded,
its surfaced_count stays 0 — that's a delivery problem, not an effectiveness problem.

### Step 3: For each knowledge entry, search for evidence in traces
Read all entries in `knowledge/` (excluding meta/). For each entry, scan the traces:

**LOADED**: Was this entry present in the session? (from rules-loaded manifest)
If not loaded: skip scoring — this is a delivery gap, not an effectiveness signal.

**SURFACED**: In sessions where the entry WAS loaded, did Claude's response contain content matching it?
Look for: key phrases, decision names, specific facts from the entry appearing in Claude's responses.
If found: surfaced_count++

**CITED**: Did Claude explicitly reference a team decision or warning from this entry?
Look for: "the team decided", "already settled", entry-specific facts stated as team context.
If found: cited_count++ (stronger signal than surfaced)

**CORRECTION AFTER**: Did a user correct Claude on a topic this entry covers?
Look for: user frustration or correction on the same topic the entry addresses.
If found: correction_after++ (entry may be wrong or stale)

### Step 4: Compute scores and update entry metrics
For each entry where you found trace evidence, update the metrics block in the entry frontmatter:
```yaml
metrics:
  surfaced_count: N
  cited_count: N
  correction_after: N
  effectiveness_score: X.XX
```
Where: effectiveness_score = (cited_count - correction_after) / max(surfaced_count, 1)
Range: -1.0 to +1.0

### Step 5: Propose actions (Heimdall will approve)
  Score > 0.5  → propose AMPLIFY: increase confidence, widen relevant-when
  Score 0-0.5  → MONITOR: log trend, no change proposed
  Score -0.2-0 → propose REVIEW: narrow triggers, check staleness
  Score < -0.2 → propose REMOVE: archive to knowledge/meta/removed/

IMPORTANT: These are PROPOSALS. Write them to `knowledge/meta/feedback-proposals.md`.
Heimdall will review and approve/reject each one. Do NOT directly modify entry confidence or status.

### Step 6: Detect gaps
Scan traces for patterns that have NO matching knowledge entry:
- Frustration signals (user correcting Claude) that don't match any existing rule
- Repeated workflows that don't match any existing procedure
- Decision discussions that don't match any existing knowledge entry
- Topics where Claude clearly lacked team context

For each gap: propose a new entry (LOW confidence) in `knowledge/meta/feedback-proposals.md`.

### Step 7: Update system-effectiveness.md
Write a summary to `knowledge/meta/system-effectiveness.md`:
- How many entries scored, how many in each threshold band
- Which entries to amplify, review, or remove
- What gaps were detected
- Overall system health assessment

### Step 8: Git commit
```bash
git add knowledge/
git commit -m "auto-feedback: {date} — N entries scored, M gaps detected"
```

## Important
- Trace-based only. No hook logs. The directive rule means Claude reads entries voluntarily — we detect this from trace content.
- The judgment of "was this correction BECAUSE of the entry or unrelated?" requires careful reasoning — this is WHY this agent runs on Opus.
- Be conservative with REMOVE — only if clearly harmful. Default to MONITOR.
- Gaps are proposals, not actions — they get created as LOW confidence entries for Heimdall review.
- If no traces exist yet (system just deployed), note this and exit gracefully.
"""


async def main():
    config = load_config()
    prompt = build_prompt(config)

    print(f"[feedback-agent] Starting at {datetime.now().isoformat()}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],  # No Bash — invariant 5,
            permission_mode="bypassPermissions",
            cwd=str(Path(__file__).parent.parent),
            max_turns=40,
            max_budget_usd=5.0,
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
            print(f"[feedback-agent] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
