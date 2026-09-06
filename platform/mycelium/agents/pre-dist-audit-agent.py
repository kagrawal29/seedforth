#!/usr/bin/env python3
"""
Pre-Distribution Audit Agent — Gate 2.

System-level review before anything ships to team repos.
Opus: requires holistic reasoning about system coherence.
Cost: ~$2-5/run.

Runs before every distribute step. Output: go/no-go with specific findings.
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

    return f"""You are the pre-distribution audit agent (Gate 2) for the meta intelligence system. You review the ENTIRE system state before anything ships to team repos.

## Your Job

This is the last gate before distribution. Heimdall (Gate 1) already approved individual entries. Your job is different — you check whether the WHOLE SYSTEM is coherent, not whether individual pieces are good.

**Output:** A go/no-go decision written to `knowledge/meta/pre-dist-audit.md`. If no-go, list exactly what needs fixing.

## Sensing the graph (on demand)

If `knowledge/meta/pre-dist-graph-context.md` exists, read it as part of your audit.
It contains graph health metrics that supplement your other checks.

Add to your audit if available:
- Demand coverage: what % of knowledge has active demand? (target: > 50%)
- Edge ratio: edges per node (target: 1.5-3.0)
- Orphan nodes: entries with zero graph connections (flag for review)
- Oscillation: is the graph only growing? Healthy systems also prune.
- Pruning candidates: entries surfaced but never cited (consider dropping)

If the file doesn't exist, audit without graph health — the core checks still apply.

## What to Check

### 1. Rule Health
Read ALL files in `distribution/shared-rules/` and `.claude/rules/`.

Check:
- Count within cap? (max: {settings['max_rules']} rules)
- Any two rules that say the same thing differently? (redundancy)
- Any two rules that contradict each other?
- All positively framed? ("do X because Y" not "don't do Z")
- Each rule has clear reasoning (WHY, not just WHAT)?
- Any rule that's actually a fact/decision? (facts belong in knowledge entries, not rules)

### 2. Skill Validity
Read ALL SKILL.md files in `.claude/skills/`.

For each skill that is a team workflow (NOT operational skills like cycle, ingest, synthesize), verify it meets ALL 5 T8 criteria:
1. Phase gates (entry/exit criteria)
2. Track selection or decision branching
3. Autonomous execution between human touchpoints
4. NO-SKIP enforcement on critical steps
5. Verification at each stage

If a skill fails T8 criteria → flag it. It should be demoted to a rule (if behavioral) or knowledge entry (if reference).

Operational skills (cycle, ingest, synthesize, distribute, report, retro, status) are exempt from T8 — they're meta system tools, not team workflows.

### 3. Entry Health
Run: `python3 scripts/lint-knowledge.py`

Additionally check:
- Any entries with effectiveness_score < -0.2 that haven't been flagged for removal?
- Any entries with correction_after > cited_count? (harmful — being wrong more than right)
- Category balance — is one category growing disproportionately?
- Any entries that are essentially duplicates (same decision from different angles)?
- Any explorations (T4) that should have been resolved by now?

### 4. Distribution Diff
Run: `git diff HEAD~1 -- knowledge/ distribution/ .claude/rules/ .claude/skills/`

Review what changed since last distribution:
- Any surprising additions?
- Any deletions that might break things?
- Any entries that went from LOW to HIGH confidence without evidence?

If this is the first distribution (no prior diff), note that and be extra careful.

### 5. Metrics Trends
Read `knowledge/meta/system-effectiveness.md` and `knowledge/meta/feedback-proposals.md` if they exist.

Check:
- Overall effectiveness trending up, down, or flat?
- Any entries with consistently zero surfaced_count? (orphans)
- Any spike in correction_after across multiple entries? (systemic issue)

### 6. Delivery Verification
Check `signals/delivery/` for the latest delivery report (written by ingest agent).
If it exists, review:
- How many team members have the latest rules loaded?
- How many are stale (loaded an older version)?
- How many have no `rules-loaded` traces at all (hook not deployed or no new session)?

If delivery coverage is below 50% of active team members, flag as a concern.

### 7. Cross-Check Rules vs Knowledge
- Is every rule backed by 2+ independent signals? (check the source field in knowledge entries)
- Are there knowledge entries that should be rules? (e.g., high-confidence entries about behavioral constraints)
- Are there rules that should be knowledge entries? (e.g., rules that contain facts rather than behavioral guidance)

## Output Format

Write your audit to `knowledge/meta/pre-dist-audit.md`:

```markdown
# Pre-Distribution Audit — {date}

## Decision: GO / NO-GO

## Findings

### Rules (N files)
- [PASS/ISSUE] ...

### Skills (N workflow skills)
- [PASS/ISSUE] ...

### Entries (N entries)
- [PASS/ISSUE] ...

### Distribution Diff
- [PASS/ISSUE] ...

### Metrics Trends
- [PASS/ISSUE] ...

### Delivery Verification
- [PASS/ISSUE] ...

### Cross-Check
- [PASS/ISSUE] ...

## Blockers (if NO-GO)
1. ...

## Recommendations (if GO)
1. ...
```

## Decision Criteria

**GO** if:
- All rules positively framed and non-redundant
- All workflow skills meet T8 criteria
- Lint passes clean
- No entries with effectiveness_score < -0.2 still active
- No surprising changes in the diff

**NO-GO** if ANY of:
- A rule contradicts another rule
- A workflow skill fails T8 criteria
- Lint fails
- An entry with effectiveness_score < -0.2 is still active and unflagged
- The diff contains changes that could harm team sessions

## Important
- Be thorough but fair. The goal is catching real problems, not finding theoretical issues.
- A GO with recommendations is fine — not everything needs to be perfect, just safe.
- A NO-GO must have specific, actionable blockers — not vague concerns.
- This gate must be harder on the system than we are on ourselves (creator separation principle).
- Do NOT modify any files except `knowledge/meta/pre-dist-audit.md`. You are an auditor, not a fixer.
"""


async def main():
    config = load_config()
    prompt = build_prompt(config)

    print(f"[pre-dist-audit] Starting at {datetime.now().isoformat()}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],  # Read-only — invariant 5: should not modify what it evaluates,
            permission_mode="bypassPermissions",
            cwd=str(Path(__file__).parent.parent),
            max_turns=30,
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
            print(f"[pre-dist-audit] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)

            # Check the audit result
            audit_path = Path(__file__).parent.parent / "knowledge" / "meta" / "pre-dist-audit.md"
            if audit_path.exists():
                content = audit_path.read_text()
                if "NO-GO" in content.split("\n## Findings")[0] if "## Findings" in content else content[:200]:
                    print("  RESULT: NO-GO — distribution blocked")
                    sys.exit(2)  # Exit code 2 = no-go (distinct from error)
                else:
                    print("  RESULT: GO — safe to distribute")
            else:
                print("  WARNING: No audit file written")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
