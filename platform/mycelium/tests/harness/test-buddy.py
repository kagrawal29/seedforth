#!/usr/bin/env python3
"""
Test Buddy — runs a multi-turn session with the full meta system deployed.
An actor agent (haiku) plays as a team member, doing real work.

No A/B comparison. Just run the system and observe:
- Does the hook inject at the right moments?
- Does the injected content change behavior?
- Is the work quality good?

Usage:
  python3 tests/harness/test-buddy.py --scenario abhishek-rag-research
  python3 tests/harness/test-buddy.py --scenario ankit-fix-from-audit --turns 6
  python3 tests/harness/test-buddy.py --scenario pranav-rules-testing
  python3 tests/harness/test-buddy.py --list
  python3 tests/harness/test-buddy.py --branch main --task "custom task here"
"""

import asyncio
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions, ResultMessage,
    AssistantMessage, TextBlock, ToolUseBlock, query as sdk_query
)

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = ROOT / "signals" / "test-harness"
REPO_URL = "https://github.com/Qubit-Capital/VC-AI-Assoicate.git"

sys.path.insert(0, str(ROOT))
from tests.harness.test_scenarios import SCENARIOS

DEFAULT_TASK = "Can you create a document of the issues we found? I want a proper document in docs that lists the architectural issues, what needs fixing, and priority order."


def build_actor_prompt(scenario=None):
    """Build actor system prompt from scenario or defaults."""
    if scenario:
        name = scenario["actor"]
        style = scenario["actor_style"]
        context = scenario.get("context", "")
    else:
        name = "Ankit-S"
        style = """Direct, sometimes impatient. You want Claude to understand before acting.
When frustrated: "don't jump to editing first", "tell me what you understood"
When happy: short responses — "ok", "yes continue", "looks good"
You care about quality. You push back when output doesn't match your vision."""
        context = "You're working on documenting architectural issues."

    return f"""You are {name}, a developer on VC-AI-Assoicate.

Style: {style}

Context: {context}

Your goal: make real progress on the task. This is NOT a test.

NEVER mention "knowledge base", "hooks", "meta system", or "team decisions".
You don't know any of that exists. You're just a developer.

Respond with ONLY what you'd type. No meta-commentary. One message."""


def setup_workspace(branch: str) -> Path:
    """Clone repo, sandbox, deploy meta system."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    workspace = Path(f"/tmp/test-buddy-{timestamp}")

    print(f"  Cloning {branch}...")
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, REPO_URL, str(workspace)],
        capture_output=True, text=True, timeout=120
    )

    # Sandbox — no remote, no git hooks
    subprocess.run(["git", "-C", str(workspace), "checkout", "-b", f"test/buddy-{timestamp}"], capture_output=True, text=True)
    subprocess.run(["git", "-C", str(workspace), "remote", "remove", "origin"], capture_output=True, text=True)
    for hook in (workspace / ".git" / "hooks").glob("*"):
        if hook.is_file() and not hook.name.endswith(".sample"):
            hook.unlink()

    # Deploy meta system
    print("  Deploying meta system...")

    # Knowledge
    kb_src, kb_dst = ROOT / "knowledge", workspace / ".claude" / "knowledge" / "entries"
    kb_dst.mkdir(parents=True, exist_ok=True)
    for f in kb_src.rglob("*.md"):
        rel = f.relative_to(kb_src)
        if "meta/" not in str(rel) and f.name not in ("index.md", "search-index.md"):
            dst = kb_dst / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
    shutil.copy2(kb_src / "index.md", workspace / ".claude" / "knowledge" / "index.md")
    shutil.copy2(kb_src / "search-index.md", workspace / ".claude" / "knowledge" / "search-index.md")

    # Rules (skip git-workflow — remove if cloned repo already has it)
    rules_dst = workspace / ".claude" / "rules"
    rules_dst.mkdir(parents=True, exist_ok=True)
    # Remove git-workflow if it exists from a previous push
    gw = rules_dst / "git-workflow.md"
    if gw.exists():
        gw.unlink()
    for f in (ROOT / "distribution" / "shared-rules").glob("*.md"):
        if f.name != "git-workflow.md":
            shutil.copy2(f, rules_dst / f.name)

    # Hooks — remove all invasive hooks. Rules guide the model, not hooks.
    hooks_dst = workspace / ".claude" / "hooks"
    if hooks_dst.exists():
        for stale in hooks_dst.glob("*"):
            if stale.is_file():
                stale.unlink()

    # Skills
    for s in ["team-knowledge", "architecture-validation", "feature-design"]:
        src = ROOT / ".claude" / "skills" / s
        if src.exists():
            dst = workspace / ".claude" / "skills" / s
            dst.mkdir(parents=True, exist_ok=True)
            for f in src.glob("*.md"):
                shutil.copy2(f, dst / f.name)

    # Settings — no hooks. Rules guide the model, not hooks.
    # Remove any existing settings.json that has hooks from prior pushes
    existing_settings = workspace / ".claude" / "settings.json"
    if existing_settings.exists():
        existing_settings.unlink()
    settings = {}
    (workspace / ".claude" / "settings.json").write_text(json.dumps(settings, indent=2))

    print(f"  Ready: {workspace}")
    return workspace


def extract_text(messages: list) -> str:
    """Extract readable text from AssistantMessage list."""
    parts = []
    for msg in messages:
        if not hasattr(msg, 'content'):
            continue
        for block in msg.content:
            if isinstance(block, TextBlock):
                parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                parts.append(f"[{block.name}]")
    return "\n".join(parts)


async def get_actor_reply(convo_history: str, last_response: str, actor_prompt: str = "") -> str:
    """Haiku plays the team member — reacts naturally."""
    prompt = f"""Conversation so far:
{convo_history[-2000:]}

Claude just responded:
{last_response[:2000]}

What do you say next?"""

    reply = ""
    try:
        async for msg in sdk_query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                permission_mode="bypassPermissions",
                max_turns=1,
                max_budget_usd=0.05,
                model="haiku",
                system_prompt=actor_prompt,
            ),
        ):
            if isinstance(msg, ResultMessage):
                reply = msg.result or ""
    except Exception as e:
        print(f"  [Actor error: {e}]")
        reply = "ok continue"
    return reply.strip()


async def run_session(branch: str, opening_task: str, max_turns: int, scenario: dict = None):
    """Run a multi-turn session with persistent context."""
    workspace = setup_workspace(branch)
    actor_prompt = build_actor_prompt(scenario)

    print(f"\n{'='*60}")
    print(f"  TEST BUDDY: Ankit on {branch}")
    print(f"  Task: {opening_task[:80]}...")
    print(f"{'='*60}")

    conversation = []
    convo_text = ""
    total_cost = 0.0

    async with ClaudeSDKClient(
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep", "Bash", "Write", "Edit", "Agent"],
            permission_mode="bypassPermissions",
            cwd=str(workspace),
            max_budget_usd=5.0,
            model="sonnet",
            env={"ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")},
        )
    ) as client:
        for turn in range(1, max_turns + 1):
            if turn == 1:
                user_msg = opening_task
            else:
                user_msg = await get_actor_reply(convo_text, last_response, actor_prompt)
                if not user_msg:
                    break

            conversation.append({"role": "user", "content": user_msg, "turn": turn})
            convo_text += f"\nAnkit: {user_msg}\n"
            print(f"\n[Ankit {turn}]: {user_msg}")
            print(f"[Claude working...]")

            start = time.time()
            worker_msgs = []

            await client.query(user_msg)
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    worker_msgs.append(msg)
                elif isinstance(msg, ResultMessage):
                    elapsed = time.time() - start
                    cost = msg.total_cost_usd or 0
                    total_cost += cost
                    print(f"[Done: {elapsed:.1f}s, ${cost:.4f}]")

            last_response = extract_text(worker_msgs)
            conversation.append({"role": "assistant", "content": last_response[:5000], "turn": turn})
            convo_text += f"\nClaude: {last_response[:1000]}\n"

            display = last_response[:1500]
            if len(last_response) > 1500:
                display += f"\n... ({len(last_response)} chars total)"
            print(f"\n[Claude]: {display}")

    # Collect hook logs
    hook_logs = []
    log_dir = workspace / "signals" / "hook-effectiveness"
    if log_dir.exists():
        for f in log_dir.glob("*.jsonl"):
            for line in f.read_text().strip().split("\n"):
                if line.strip():
                    try:
                        hook_logs.append(json.loads(line))
                    except:
                        pass

    # Save results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    result_file = RESULTS_DIR / f"{ts}-buddy.json"
    result_file.write_text(json.dumps({
        "branch": branch, "actor": "Ankit-S",
        "opening_task": opening_task,
        "turns": len([m for m in conversation if m["role"] == "user"]),
        "total_cost": total_cost,
        "conversation": conversation,
        "hook_injections": hook_logs,
        "workspace": str(workspace),
    }, indent=2, default=str))

    print(f"\n{'='*60}")
    print(f"  DONE")
    print(f"  Turns: {len([m for m in conversation if m['role'] == 'user'])}")
    print(f"  Cost: ${total_cost:.4f}")
    print(f"  Hooks: {len(hook_logs)} injections")
    if hook_logs:
        print(f"  Injections:")
        for inj in hook_logs:
            q = inj.get('query','')[:40]
            entries = [e.split('/')[-1].replace('.md','') for e in inj.get('injected_entries',[])]
            print(f"    \"{q}\" → {entries}")
    print(f"  Saved: {result_file}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Test buddy — run system with actor doing real work")
    parser.add_argument("--scenario", type=str, help="Named scenario from test-scenarios.py")
    parser.add_argument("--branch", default=None)
    parser.add_argument("--turns", type=int, default=5)
    parser.add_argument("--task", type=str, default=None)
    parser.add_argument("--list", action="store_true", help="List available scenarios")
    args = parser.parse_args()

    if args.list:
        from tests.harness.test_scenarios import list_scenarios
        list_scenarios()
        return

    if args.scenario:
        if args.scenario not in SCENARIOS:
            print(f"Unknown scenario: {args.scenario}")
            print(f"Available: {', '.join(SCENARIOS.keys())}")
            return
        scenario = SCENARIOS[args.scenario]
        branch = args.branch or scenario["branch"]
        task = args.task or scenario["opening"]
        asyncio.run(run_session(branch, task, args.turns, scenario))
    else:
        branch = args.branch or "main"
        task = args.task or DEFAULT_TASK
        asyncio.run(run_session(branch, task, args.turns))


if __name__ == "__main__":
    main()
