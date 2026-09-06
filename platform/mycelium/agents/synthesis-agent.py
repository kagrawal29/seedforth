#!/usr/bin/env python3
"""
Synthesis Agent — classifies signals into 8 knowledge types, creates entries.

Standalone Agent SDK script. Runs after ingest-agent.
Heavy AI: classification, extraction, judgment, abstraction.
Cost: ~$1-5/run.
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
    settings = config["settings"]
    date = datetime.now().strftime("%Y-%m-%d")

    return f"""You are the synthesis agent for the meta intelligence system. You read raw signals and produce structured knowledge entries.

## Your Job
Read today's signal files from signals/ and the existing knowledge base in knowledge/.
For each signal, classify it and produce the right output.

## 8 Knowledge Types

T1: SETTLED DECISIONS — "we decided X", "lock this", "go ahead with X"
  → Create knowledge entry in knowledge/architecture/ or knowledge/patterns/
  → Inline the decision + rationale
  → Tag: confidence based on how explicit the decision was

T2: EVALUATED ALTERNATIVES — "X vs Y, chose X because..."
  → Create knowledge entry with FULL comparison rationale
  → Include: what was evaluated, why one was chosen, when to reconsider the other
  → This is the HIGHEST VALUE type — prevents duplicate evaluation work

T3: WORKING KNOWLEDGE — "this is how X currently works"
  → Create or update knowledge entry
  → Usually from code changes or codebase exploration

T4: ACTIVE EXPLORATIONS — someone is researching, NOT YET DECIDED
  → Create entry with type: exploration
  → Format: who, topic, started date, "coordinate before deciding"
  → DO NOT present as decided. This is a coordination signal.

T5: OPERATIONAL STATUS — runtime state, batch progress, metrics
  → SKIP. Do not store. This is ephemeral.

T6: USER CORRECTIONS — "DO NOT do X", repeated frustration, "wait, stop"
  → Draft a RULE in distribution/shared-rules/
  → POSITIVELY FRAMED: "do X because Y" not "don't do Z"
  → Include reasoning — WHY this matters
  → Start at LOW confidence unless seen from 2+ people

T7: LEARNINGS / INSIGHTS — "I learned that...", meta-knowledge
  → Create knowledge entry or procedure depending on content
  → If it's about process → procedure
  → If it's about a fact → knowledge entry

T8: COMPLEX WORKFLOWS — multi-step orchestrated processes with REAL ORCHESTRATION
  → ONLY classify as T8 if ALL of these are present:
    1. Phase gates (entry/exit criteria that must pass before proceeding)
    2. Track selection or decision branching (different paths based on conditions)
    3. Autonomous execution between human touchpoints (not just "follow these tips")
    4. NO-SKIP enforcement (specific steps that cannot be skipped regardless of reasoning)
    5. Verification at each stage (not just a final check)
  → If it's behavioral advice ("explain before editing", "check existing patterns") → T6 rule or T7 learning, NOT T8
  → If it's a reference guide ("how to search X", "how to use tool Y") → T3 working knowledge, NOT T8
  → If it's a checklist without decision branching or phase gates → T7 learning, NOT T8
  → Draft a skill SKILL.md in .claude/skills/ ONLY for true T8 signals
  → Include: description with positive AND negative triggers
  → Include: full workflow steps with phase gates, track selection, NO-SKIP markers, verification

## Entry Format
Every knowledge entry MUST have this frontmatter:
```yaml
---
id: category-kebab-name
category: patterns | anti-patterns | architecture | workflows | tool-configs
type: knowledge | procedure | exploration
discovered: {date}
last-validated: {date}
confidence: low | medium | high
source: specific trace/commit reference
tags: [searchable, keywords]
relevant-when: comma-separated situations
related: [entry-id-1, entry-id-2]
distributed-to: []
effectiveness: null
metrics:
  surfaced_count: 0
  cited_count: 0
  correction_after: 0
  effectiveness_score: 0.0
---
```

## Rules for Quality
- POSITIVE FRAMING always: "do X because Y" not "don't do Z"
- Include REASONING, not just the constraint
- One insight per entry. Don't combine unrelated things.
- Start at LOW confidence unless 2+ independent sources confirm
- Check existing entries for CONTRADICTIONS before creating new ones
- If new info contradicts an existing entry, UPDATE the existing entry (don't create duplicate)
- Preserve attribution: source field links to specific trace/commit
- Max {settings['max_procedure_chars']} chars for procedures
- Never distribute entries below {settings['confidence_gate']} confidence

## What to Do Now

### Step 0: Sense the graph (on demand, not forced)

Asgard (the knowledge graph) holds the team's structural memory. You can
sense it when you need context — but only when it's relevant.

**When to sense:**
- Before creating a T1 (decision) or T2 (evaluation) entry: read `knowledge/meta/graph-context.md`
  to check which community this belongs to and what related nodes exist.
- When a signal mentions a topic with possible demand: read `knowledge/meta/graph-demand.md`
  to check if the team is actively asking about this.
- When populating the `related:` field: the graph knows what connects to what.

**When NOT to sense:**
- T5 (operational, skip) or T7 (simple learning) — don't bother.
- If the files don't exist — proceed without. The pipeline works without the graph.

**What you get:**
- `graph-context.md`: communities, god nodes (most connected), cross-person connections
- `graph-demand.md`: what the team is actively asking about (demand signals)

Use these to populate `related:` fields, detect cross-pollination, avoid duplicates,
and strengthen evidence for entries that answer active demand.

### Step 1: Compute delta (only process NEW signals)
Read the synthesis manifest to find unprocessed signal files:
```python
import json, hashlib
from pathlib import Path

manifest_path = Path("signals/.synthesis-manifest.json")
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {{"processed_files": []}}
processed = {{f["path"]: f["sha256"] for f in manifest.get("processed_files", [])}}

# Find all signal files
import glob
all_files = sorted(glob.glob("signals/**/*.md", recursive=True))

# Compute delta
delta = []
for f in all_files:
    h = hashlib.sha256(open(f, "rb").read()).hexdigest()
    if f not in processed or processed[f] != h:
        delta.append({{"path": f, "sha256": h}})

print(f"Delta: {{len(delta)}} files to process ({{len(all_files)}} total)")
```

If delta is empty → print "No new signals" and exit.

### Step 2: Read delta signal files
Read ONLY the delta files identified in Step 1.

### Step 3: Read existing knowledge base
Read all files in `knowledge/` (excluding meta/). For each delta signal, check:
- Does it VALIDATE an existing entry? → bump last-validated, add evidence
- Does it CONTRADICT an existing entry? → update the entry, lower confidence
- Does it EXTEND an existing entry? → add information, update
- Is it entirely NEW? → create new entry

### Step 4: Classify and create entries
For each signal, classify → extract → write entry.
Read `.claude/rules/knowledge-format.md` for the schema.

### Step 5: Update synthesis manifest
After ALL entries are written successfully:
```python
import json
from datetime import datetime, timezone

manifest = json.loads(open("signals/.synthesis-manifest.json").read()) if Path("signals/.synthesis-manifest.json").exists() else {{"processed_files": []}}
existing = {{f["path"]: f for f in manifest.get("processed_files", [])}}

for d in delta:
    existing[d["path"]] = {{"path": d["path"], "sha256": d["sha256"], "processed_at": datetime.now(timezone.utc).isoformat()}}

manifest["processed_files"] = list(existing.values())
manifest["last_cycle_ts"] = datetime.now(timezone.utc).isoformat()
with open("signals/.synthesis-manifest.json", "w") as f:
    json.dump(manifest, f, indent=2)
```

### Step 6: Lint and index
```bash
python3 scripts/lint-knowledge.py
python3 scripts/build-search-index.py
```

### Step 7: Git commit
```bash
git add knowledge/ distribution/shared-rules/ .claude/skills/ signals/.synthesis-manifest.json
git commit -m "auto-synthesis: {date} — N new entries, M updated"
```

## Important
- ONLY process delta signals (Step 1). Never reprocess already-consumed files.
- Cross-cycle connections (Step 3) are the HIGHEST VALUE: new signal validates/contradicts/extends existing knowledge.
- Cross-pollination: when person A's work helps person B.
- Frustration signals (T6) → rules. Highest ROI extraction.
- If you find a contradiction with an existing entry, UPDATE the existing entry (don't create a duplicate).
"""


async def main():
    config = load_config()
    prompt = build_prompt(config)

    print(f"[synthesis-agent] Starting at {datetime.now().isoformat()}")

    # Use traced_query for real-time conversation logging
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from scripts.lib.agent_trace import traced_query
        query_fn = lambda **kw: traced_query(**kw, trace_name="synthesis")
    except ImportError:
        from claude_agent_sdk import query as _q
        query_fn = lambda **kw: _q(**{k: v for k, v in kw.items() if k != 'trace_name'})

    async for message in query_fn(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],  # No Bash — invariant 5: prompt injection risk from untrusted signals
            permission_mode="bypassPermissions",
            cwd=str(Path(__file__).parent.parent),
            max_turns=50,
            max_budget_usd=10.0,
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
            print(f"[synthesis-agent] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
