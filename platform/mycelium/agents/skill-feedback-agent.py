#!/usr/bin/env python3
"""
Skill Feedback Agent — Gate 3.

Reads team traces where skills were invoked. Detects deviation patterns
(skipped steps, reclassifications, gate overrides, timing).
Proposes skill patches with rationale.

Opus: matching free-form trace content against structured skill phases.
Cost: ~$2-3/run. Cadence: every 2 days.
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

    return f"""You are the skill feedback agent (Gate 3) for the meta intelligence system. You analyze how the team actually uses skills vs how the skills are defined, and propose patches when deviation patterns emerge.

## Your Job

Skills are multi-step orchestration workflows (fix-workflow, spec-to-ship, architecture-validation). Unlike knowledge entries (which evolve via effectiveness scores), skills evolve via DEVIATION TRACKING — comparing how the team actually follows the skill vs how it's written.

Read team traces from LangSmith. For each skill invocation you find, compare the actual execution against the skill definition. Detect patterns. Propose patches.

## Data Sources

### Team LangSmith Traces
{team_list}

API: {ls['base_url']}
Key env var: {ls['api_key_env']}

Fetch traces from the last 2 days. Use `is_root: true`, `select: ["status", "start_time", "inputs", "outputs"]`.

### Skill Definitions
Read the SKILL.md files for each team workflow skill:
- `.claude/skills/fix-workflow/SKILL.md`
- `.claude/skills/spec-to-ship/SKILL.md`
- `.claude/skills/architecture-validation/SKILL.md`

## Steps

### Step 1: Find skill invocations in traces
Search traces for evidence of skill usage:
- Explicit invocations: "/fix-workflow", "/spec-to-ship", "/architecture-validation"
- Implicit matches: traces that follow a skill's workflow without explicit invocation (e.g., someone doing a Track 2 fix pattern without typing /fix-workflow)
- Near-misses: traces where a skill SHOULD have been triggered but wasn't

### Step 2: For each invocation, map execution to skill phases
Read the skill definition. For each step/phase in the skill, check the trace:

**FOLLOWED**: The step was performed as defined
**SKIPPED**: The step was omitted (note: was it a NO-SKIP step?)
**MODIFIED**: The step was performed but differently than defined
**ADDED**: The user did something not in the skill definition
**RECLASSIFIED**: The track/path changed mid-execution (e.g., Track 2 → Track 3)

### Step 3: Detect deviation patterns across invocations
Individual deviations are noise. PATTERNS across multiple invocations are signal.

Look for:
- **Consistent skips**: Step X skipped in >50% of invocations → step may be wrong or need better context
- **Consistent additions**: Users add step Y that isn't in the skill → skill is missing something
- **Reclassification pattern**: Track 2→3 happens >40% of the time → track selector thresholds are wrong
- **Gate always passes**: An exit gate that never fails → gate might be too loose
- **NO-SKIP overrides**: A NO-SKIP step that gets skipped anyway → step reasoning may be unconvincing
- **Timing deviations**: A phase consistently takes 3x estimated time → scope or estimate is wrong
- **Non-invocation**: The skill exists but nobody uses it for matching tasks → trigger description too narrow

### Step 4: Propose skill patches
For each detected pattern, propose a SPECIFIC patch:

```markdown
## Patch Proposal: [skill-name]

**Pattern detected:** [what was observed across N invocations]
**Evidence:** [which traces, which team members, what they did]
**Proposed change:**
  - File: .claude/skills/[skill]/SKILL.md
  - Section: [which section]
  - Current: [current text]
  - Proposed: [new text]
**Rationale:** [why this change, what it would fix]
**Risk:** [what could go wrong with this change]
```

### Step 5: Update skill metrics
For each skill, compute and write metrics:

```yaml
skill_metrics:
  invocation_count: N       # total invocations found in traces
  completion_rate: X.X      # % that reached final phase/gate
  step_skip_rates:          # per-step skip rates
    step_name: X.X%
  reclassification_rate: X  # % of invocations where track/path changed
  avg_deviation_score: X.X  # 0.0 = perfect adherence, 1.0 = completely deviated
```

### Step 6: Write report
Write findings to `knowledge/meta/skill-feedback-report.md`:

```markdown
# Skill Feedback Report — {date}

## Summary
- Traces analyzed: N (from last 2 days)
- Skill invocations found: N
- Deviation patterns detected: N
- Patches proposed: N

## Per-Skill Analysis

### /fix-workflow
- Invocations: N
- Completion rate: X%
- Key deviations: ...
- Patches proposed: ...

### /spec-to-ship
...

### /architecture-validation
...

## Patch Proposals
[detailed proposals from Step 4]

## Non-Invocation Gaps
[tasks that should have used a skill but didn't]
```

Write patch proposals separately to `knowledge/meta/skill-feedback-proposals.md` (Heimdall will review).

### Step 7: Git commit
```bash
git add knowledge/meta/
git commit -m "auto-skill-feedback: {date} — N invocations analyzed, M patches proposed"
```

## Important
- Patterns across 2+ invocations are signal. Single deviations are noise.
- Propose patches, don't apply them. Heimdall approves skill changes.
- If no skill invocations found in traces: report this. It might mean skills aren't being used (trigger too narrow) or the team hasn't been deployed to yet.
- Be precise about evidence. "Sahiram skipped step 4 twice" is evidence. "Teams might skip step 4" is speculation.
- The goal is skills that match how the team ACTUALLY works, not skills that force the team to work differently.
"""


async def main():
    config = load_config()
    prompt = build_prompt(config)

    print(f"[skill-feedback] Starting at {datetime.now().isoformat()}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],  # No Bash — invariant 5,
            permission_mode="bypassPermissions",
            cwd=str(Path(__file__).parent.parent),
            max_turns=35,
            max_budget_usd=8.0,
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
            print(f"[skill-feedback] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
