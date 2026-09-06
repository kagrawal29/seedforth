#!/usr/bin/env python3
"""
Ingest Agent — pulls signals from LangSmith, GitHub, and team artifacts.

Standalone Agent SDK script. Runs every 3h during work hours (10am-10pm IST).
Light AI (Sonnet): mostly API calls + formatting.
Cost: ~$0.50/run.
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
    repos = config["repos"]
    ls = config["langsmith"]
    patterns = config.get("artifact_patterns", [])

    # Load watermarks for delta fetching
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.lib.watermarks import load_watermarks, get_langsmith_since, get_github_since

    wm = load_watermarks()

    team_list = "\n".join(
        f"  - {m['name']}: {m['langsmith_project']} (since: {get_langsmith_since(m['langsmith_project'])})" for m in team
    )
    repo_list = "\n".join(
        f"  - {r['org']}/{r['name']} (since: {get_github_since(r['org'] + '/' + r['name'])})" for r in repos
    )
    pattern_list = "\n".join(f"  - {p}" for p in patterns)
    date = datetime.now().strftime("%Y-%m-%d")

    return f"""You are the ingest agent for the meta intelligence system. Your job is to pull fresh signals from all sources and write them as structured signal files.

## Configuration
Team members (LangSmith project UUIDs):
{team_list}

Target repos:
{repo_list}

LangSmith API: {ls['base_url']}
API key env var: {ls['api_key_env']}
Today's date: {date}

Artifact detection patterns:
{pattern_list}

## What to do

### Step 1: Fetch LangSmith traces (DELTA ONLY)
For each team member, fetch traces SINCE their watermark timestamp (shown in config above as "since:").
Use Python (NOT bash — macOS bash lacks associative arrays).

Use this Python pattern:
```python
import json, urllib.request, os

API_KEY = os.environ.get("{ls['api_key_env']}", "")
BASE = "{ls['base_url']}"

# For each team member, use their "since" timestamp from the config above:
body = json.dumps({{
    "session": ["<project-uuid>"],
    "start_time": "<the 'since' timestamp from config above>",
    "is_root": True,
    "limit": 100,
    "select": ["status", "start_time", "total_tokens", "inputs", "outputs"]
}}).encode()

req = urllib.request.Request(
    f"{{BASE}}/runs/query",
    data=body,
    headers={{"x-api-key": API_KEY, "Content-Type": "application/json"}}
)
```

Extract user messages and Claude responses from each turn.
Handle 429 rate limits with a 3-second sleep between requests.
Write output to: `signals/langsmith/{date}-auto.md`

### Step 2: Fetch GitHub activity
For each repo, fetch commits since last cycle:
```bash
gh api "/repos/<org>/<repo>/commits?since=<24h-ago>&per_page=50"
```
Also fetch recent PRs and issues.
Write output to: `signals/github/{date}-auto.md`

### Step 3: Detect team artifacts
For each repo, scan recent commits for files matching artifact patterns.
Use the "since" timestamp from the repo config above.
If any file matches an artifact pattern, note it with: repo, branch, file path, author, commit SHA.
Write output to: `signals/artifacts/{date}-auto.md`

### Step 4: Update watermarks
CRITICAL: After ALL signal files are written successfully, update the watermark file.

For each LangSmith member whose traces were fetched, write the newest trace's start_time.
For each GitHub repo whose commits were fetched, write the newest commit's SHA and timestamp.

```python
import yaml
from pathlib import Path
from datetime import datetime, timezone

# Load existing watermarks
wm_path = Path("signals/.watermarks.yaml")
wm = yaml.safe_load(wm_path.read_text()) if wm_path.exists() else {{"langsmith": {{}}, "github": {{}}, "artifacts": {{}}, "_meta": {{}}}}

# Update for each source that succeeded:
# wm["langsmith"]["<project-uuid>"] = {{"member": "<name>", "last_start_time": "<newest trace timestamp>"}}
# wm["github"]["<org/repo>"] = {{"last_commit_sha": "<sha>", "last_commit_time": "<timestamp>"}}

wm["_meta"] = {{"last_updated": datetime.now(timezone.utc).isoformat(), "last_cycle_status": "success"}}

# Atomic write
tmp = str(wm_path) + ".tmp"
with open(tmp, "w") as f:
    yaml.dump(wm, f, default_flow_style=False)
import os; os.rename(tmp, str(wm_path))
```

Only update watermarks for sources that SUCCEEDED. If LangSmith failed but GitHub succeeded, only update GitHub's watermark.

### Step 5: Delivery verification (rules-loaded traces)
For each team member, query LangSmith for `rules-loaded` custom traces:
```python
body = json.dumps({{
    "session": [project_uuid],
    "limit": 3,
    "filter": 'eq(name, "rules-loaded")',
    "select": ["start_time", "inputs", "outputs"]
}}).encode()
```
The `inputs.manifest` contains exactly which rules, knowledge entries, and skills were loaded.
Compare against what we last pushed. Write delivery status to: `signals/delivery/{date}.md`
Report: who has latest, who is stale, who has no data.

### Step 6: Git commit
Stage and commit all new signal files + watermarks:
```bash
git add signals/
git commit -m "auto-ingest: signals from {date}"
```

## Important
- Use Python for LangSmith (bash breaks on macOS)
- Handle 429 rate limits with retry + sleep
- If a source fails, log the error and continue to the next source — but DON'T update that source's watermark
- Write structured markdown with headers per team member / repo
- Include token counts and timestamps in trace summaries
- The "since" timestamps in the config above are your WATERMARKS — only fetch signals AFTER these timestamps
"""


async def main():
    config = load_config()
    prompt = build_prompt(config)

    print(f"[ingest-agent] Starting at {datetime.now().isoformat()}")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "Read", "Write", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            cwd=str(Path(__file__).parent.parent),
            max_turns=30,
            max_budget_usd=1.0,
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
            print(f"[ingest-agent] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
