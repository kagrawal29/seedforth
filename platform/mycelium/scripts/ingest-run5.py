#!/usr/bin/env python3
"""
Ingest run 5 - 2026-04-10
Fetches LangSmith traces and GitHub signals, writes signal files, updates watermarks.
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
import urllib.error

# ── Config ──────────────────────────────────────────────────────────────────
WORKDIR = Path("/workspace/maverick-meta")
SIGNALS_DIR = WORKDIR / "signals"
WATERMARKS_FILE = SIGNALS_DIR / ".watermarks.yaml"

API_KEY = os.environ.get("CC_LANGSMITH_API_KEY", "")
BASE_URL = "https://api.smith.langchain.com/api/v1"

TEAM = [
    {"name": "Sahiram",   "uuid": "f6b7d95f-ebda-48e6-81f9-9cfdbe28494c", "since": "2026-04-09T07:30:00Z"},
    {"name": "Abhishek",  "uuid": "43265e84-4cad-452b-b2d2-65859553e043", "since": "2026-04-10T12:13:33.078000"},
    {"name": "Ankit-S",   "uuid": "3473bc94-aa22-40ab-80bd-8588c9b00861", "since": "2026-04-10T12:00:16.563000"},
    {"name": "Sahil",     "uuid": "bf63ca28-62c6-4466-9c3b-97e6f6bbc32a", "since": "2026-04-09T12:39:03.771000"},
    {"name": "Pranav",    "uuid": "7d991519-fad6-4ede-bed1-9be395152ebe", "since": "2026-04-10T06:45:11.695831+00:00"},
    {"name": "Kshitiz",   "uuid": "ce70362b-3f8f-499b-b90c-a09f45bb000b", "since": "2026-04-10T12:16:20.486000"},
]

GITHUB_REPOS = [
    {"repo": "Qubit-Capital/VC-AI-Assoicate",           "since": "2026-04-10T11:59:04Z"},
    {"repo": "Qubit-Capital/maverick-market-research",  "since": "2026-04-10T11:59:08Z"},
]

ARTIFACT_PATTERNS = [
    "playbook", "learnings", "CLAUDE.md", "AGENTS.md",
    "rules", "guide", "docs/research", "docs/architecture",
]

DATE_LABEL = "2026-04-10"

# ── Helpers ──────────────────────────────────────────────────────────────────

def http_post(url, payload, headers):
    """HTTP POST with retry on 429."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  429 rate-limit, sleeping 5s (attempt {attempt+1})")
                time.sleep(5)
                continue
            body = e.read().decode(errors="replace")
            print(f"  HTTP {e.code}: {body[:200]}")
            return None
        except Exception as ex:
            print(f"  Request error: {ex}")
            return None
    return None


def extract_content(content):
    """Extract text from message content (string or list of parts)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
            elif isinstance(part, str):
                parts.append(part)
        return " ".join(parts).strip()
    return str(content).strip()


def extract_messages(run):
    """Return (user_msg, claude_msg) from a run."""
    user_msg = ""
    claude_msg = ""

    inputs = run.get("inputs") or {}
    messages = inputs.get("messages", [])
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            c = extract_content(m.get("content", ""))
            if c and not c.startswith("<task-notification>"):
                user_msg = c[:600]
                break

    outputs = run.get("outputs") or {}
    out_messages = outputs.get("messages", [])
    if out_messages:
        last = out_messages[-1]
        if isinstance(last, dict):
            c = extract_content(last.get("content", ""))
            claude_msg = c[:600]

    return user_msg, claude_msg


def gh_api(path):
    """Run gh api and return parsed JSON."""
    try:
        result = subprocess.run(
            ["gh", "api", path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"  gh api error: {result.stderr[:200]}")
            return None
        return json.loads(result.stdout)
    except Exception as ex:
        print(f"  gh api exception: {ex}")
        return None


def gh_file_content(repo, filepath, ref="HEAD"):
    """Fetch raw file content from a GitHub repo."""
    try:
        result = subprocess.run(
            ["gh", "api", f"/repos/{repo}/contents/{filepath}?ref={ref}",
             "--jq", ".content"],
            capture_output=True, text=True, timeout=20
        )
        if result.returncode != 0:
            return None
        import base64
        raw = result.stdout.strip()
        decoded = base64.b64decode(raw).decode(errors="replace")
        return decoded[:2000]
    except Exception:
        return None


def truncate(s, n=400):
    s = s.strip()
    return s[:n] + "…" if len(s) > n else s


# ── Step 2: LangSmith ────────────────────────────────────────────────────────

def fetch_langsmith():
    print("\n=== Step 2: LangSmith Traces ===")
    if not API_KEY:
        print("ERROR: CC_LANGSMITH_API_KEY not set")
        return {}, ""

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }

    sections = []
    new_watermarks = {}  # uuid -> newest start_time string

    for member in TEAM:
        name = member["name"]
        uuid = member["uuid"]
        since = member["since"]
        print(f"  Fetching {name} ({uuid}) since {since}...")

        payload = {
            "session": [uuid],
            "start_time": since,
            "is_root": True,
            "limit": 100,
            "select": ["status", "start_time", "total_tokens", "inputs", "outputs"],
        }

        data = http_post(f"{BASE_URL}/runs/query", payload, headers)
        time.sleep(3)

        if data is None:
            print(f"  FAILED for {name}")
            sections.append(f"### {name}\n_Fetch failed._\n")
            continue

        runs = data.get("runs", [])
        print(f"  Got {len(runs)} runs for {name}")

        # Track newest timestamp
        newest_ts = since
        for r in runs:
            ts = r.get("start_time", "")
            if ts and ts > newest_ts:
                newest_ts = ts
        if runs:
            new_watermarks[uuid] = {"member": name, "last_start_time": newest_ts}

        if not runs:
            sections.append(f"### {name}\n_No new traces since {since}._\n")
            continue

        lines = [f"### {name}", f"_Since {since} — {len(runs)} new traces_\n"]
        for r in runs:
            ts = r.get("start_time", "unknown")
            tokens = r.get("total_tokens", 0)
            status = r.get("status", "?")
            user_msg, claude_msg = extract_messages(r)

            lines.append(f"**Turn** `{ts}` | status={status} | tokens={tokens}")
            if user_msg:
                lines.append(f"- **User:** {truncate(user_msg)}")
            if claude_msg:
                lines.append(f"- **Claude:** {truncate(claude_msg)}")
            lines.append("")

        sections.append("\n".join(lines))

    content = f"# LangSmith Signals — {DATE_LABEL} (run 5)\n\n_Generated: {datetime.now(timezone.utc).isoformat()}_\n\n"
    content += "\n\n".join(sections)

    return new_watermarks, content


# ── Step 3: GitHub ───────────────────────────────────────────────────────────

def fetch_github():
    print("\n=== Step 3: GitHub Activity ===")
    sections = []
    new_watermarks = {}

    for repo_cfg in GITHUB_REPOS:
        repo = repo_cfg["repo"]
        since = repo_cfg["since"]
        print(f"  Fetching {repo}...")

        # Commits
        commits = gh_api(f"/repos/{repo}/commits?since={since}&per_page=50") or []
        # PRs
        prs = gh_api(f"/repos/{repo}/pulls?state=all&sort=updated&direction=desc&per_page=20") or []
        # Issues
        issues = gh_api(f"/repos/{repo}/issues?state=all&sort=updated&direction=desc&per_page=20&since={since}") or []

        # Track newest commit
        if commits:
            newest = commits[0]
            sha = newest.get("sha", "")[:8]
            ts = newest.get("commit", {}).get("committer", {}).get("date", since)
            new_watermarks[repo] = {"last_commit_sha": sha, "last_commit_time": ts}

        lines = [f"### {repo}", f"_Since {since}_\n"]

        # Commits
        lines.append(f"**Commits ({len(commits)})**")
        for c in commits[:20]:
            sha = c.get("sha", "")[:7]
            msg = c.get("commit", {}).get("message", "").split("\n")[0]
            author = c.get("commit", {}).get("author", {}).get("name", "?")
            ts = c.get("commit", {}).get("committer", {}).get("date", "?")
            lines.append(f"- `{sha}` {truncate(msg, 100)} — {author} @ {ts}")
        lines.append("")

        # PRs (filter to updated after since)
        recent_prs = [p for p in prs if p.get("updated_at", "") >= since[:10]]
        lines.append(f"**Pull Requests ({len(recent_prs)} recent)**")
        for pr in recent_prs[:10]:
            num = pr.get("number")
            title = pr.get("title", "")
            state = pr.get("state", "?")
            user = pr.get("user", {}).get("login", "?")
            updated = pr.get("updated_at", "?")
            lines.append(f"- #{num} [{state}] {truncate(title, 80)} — {user} @ {updated}")
        lines.append("")

        # Issues (exclude PRs)
        real_issues = [i for i in issues if "pull_request" not in i]
        lines.append(f"**Issues ({len(real_issues)} recent)**")
        for iss in real_issues[:10]:
            num = iss.get("number")
            title = iss.get("title", "")
            state = iss.get("state", "?")
            user = iss.get("user", {}).get("login", "?")
            updated = iss.get("updated_at", "?")
            lines.append(f"- #{num} [{state}] {truncate(title, 80)} — {user} @ {updated}")
        lines.append("")

        sections.append("\n".join(lines))

    content = f"# GitHub Signals — {DATE_LABEL} (run 5)\n\n_Generated: {datetime.now(timezone.utc).isoformat()}_\n\n"
    content += "\n\n".join(sections)

    return new_watermarks, content


# ── Step 4: Artifacts ────────────────────────────────────────────────────────

def fetch_artifacts(github_commits_per_repo):
    print("\n=== Step 4: Artifact Detection ===")
    sections = []

    for repo_cfg in GITHUB_REPOS:
        repo = repo_cfg["repo"]
        since = repo_cfg["since"]
        print(f"  Scanning artifacts in {repo}...")

        # Get recent commits to find changed files
        commits = gh_api(f"/repos/{repo}/commits?since={since}&per_page=20") or []
        artifact_files = set()

        for c in commits[:10]:
            sha = c.get("sha", "")
            detail = gh_api(f"/repos/{repo}/commits/{sha}") or {}
            files = detail.get("files", [])
            for f in files:
                filename = f.get("filename", "")
                for pattern in ARTIFACT_PATTERNS:
                    if pattern.lower() in filename.lower():
                        artifact_files.add(filename)
                        break

        lines = [f"### {repo}", f"_Artifact files changed since {since}_\n"]

        if not artifact_files:
            lines.append("_No artifact files detected in recent commits._\n")
        else:
            for filepath in sorted(artifact_files):
                print(f"    Fetching {filepath}...")
                content = gh_file_content(repo, filepath)
                lines.append(f"**{filepath}**")
                if content:
                    lines.append(f"```\n{content[:1500]}\n```")
                else:
                    lines.append("_Could not fetch content._")
                lines.append("")

        sections.append("\n".join(lines))

    content = f"# Artifact Signals — {DATE_LABEL} (run 5)\n\n_Generated: {datetime.now(timezone.utc).isoformat()}_\n\n"
    content += "\n\n".join(sections)
    return content


# ── Step 5: Watermarks ───────────────────────────────────────────────────────

def update_watermarks(ls_watermarks, gh_watermarks):
    print("\n=== Step 5: Updating Watermarks ===")

    # Read existing watermarks
    existing = {}
    if WATERMARKS_FILE.exists():
        import re
        # Simple YAML parser for our known structure
        text = WATERMARKS_FILE.read_text()
        # We'll just re-read and merge using our known structure
        existing_text = text

    now = datetime.now(timezone.utc).isoformat()

    # Build new content
    lines = ["_meta:"]
    lines.append(f"  last_updated: '{now}'")
    lines.append("  last_cycle_status: success")

    summary_parts = []
    for uuid, info in ls_watermarks.items():
        summary_parts.append(f"{info['member']}: updated")
    note = f"Auto-ingest 2026-04-10 (run 5). " + ", ".join(summary_parts)
    lines.append(f"  note: '{note}'")
    lines.append("")

    # Preserve demand section from existing
    import re
    demand_match = re.search(r'^demand:.*?(?=^\w|\Z)', existing_text if WATERMARKS_FILE.exists() else "", re.MULTILINE | re.DOTALL)
    if demand_match:
        lines.append(demand_match.group(0).rstrip())
        lines.append("")

    # GitHub watermarks
    lines.append("github:")
    # Merge old github entries with new
    old_gh = {}
    gh_match = re.findall(r'  (Qubit-Capital/[^:]+):\n    last_commit_sha: ([^\n]+)\n    last_commit_time: ([^\n]+)', existing_text if WATERMARKS_FILE.exists() else "")
    for repo, sha, ts in gh_match:
        old_gh[repo] = {"last_commit_sha": sha.strip("'"), "last_commit_time": ts.strip("'")}

    # Update with new
    for repo, info in gh_watermarks.items():
        old_gh[repo] = info

    for repo, info in sorted(old_gh.items()):
        lines.append(f"  {repo}:")
        lines.append(f"    last_commit_sha: {info['last_commit_sha']}")
        lines.append(f"    last_commit_time: '{info['last_commit_time']}'")

    lines.append("")

    # LangSmith watermarks
    lines.append("langsmith:")
    # Read existing
    old_ls = {}
    ls_matches = re.findall(r'  ([a-f0-9\-]+):\n    last_start_time: ([^\n]+)\n    member: ([^\n]+)', existing_text if WATERMARKS_FILE.exists() else "")
    for uuid, ts, member in ls_matches:
        old_ls[uuid] = {"last_start_time": ts.strip("'"), "member": member.strip()}

    # Update with new
    for uuid, info in ls_watermarks.items():
        old_ls[uuid] = info

    for uuid, info in sorted(old_ls.items()):
        lines.append(f"  {uuid}:")
        lines.append(f"    last_start_time: '{info['last_start_time']}'")
        lines.append(f"    member: {info['member']}")

    lines.append("")

    new_content = "\n".join(lines)

    # Atomic write
    tmp = str(WATERMARKS_FILE) + ".tmp"
    with open(tmp, "w") as f:
        f.write(new_content)
    shutil.move(tmp, str(WATERMARKS_FILE))
    print(f"  Watermarks updated.")


# ── Step 6: Delivery ─────────────────────────────────────────────────────────

def check_delivery():
    print("\n=== Step 6: Delivery Verification ===")
    if not API_KEY:
        return "# Delivery Status — 2026-04-10 (run 5)\n\n_API key not available._\n"

    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
    }

    lines = [f"# Delivery Status — {DATE_LABEL} (run 5)", f"_Generated: {datetime.now(timezone.utc).isoformat()}_\n"]
    lines.append("| Member | Latest Rules-Loaded | Status |")
    lines.append("|--------|---------------------|--------|")

    for member in TEAM:
        name = member["name"]
        uuid = member["uuid"]

        payload = {
            "session": [uuid],
            "limit": 3,
            "filter": 'eq(name, "rules-loaded")',
            "select": ["start_time", "inputs", "outputs"],
        }
        data = http_post(f"{BASE_URL}/runs/query", payload, headers)
        time.sleep(2)

        if data is None:
            lines.append(f"| {name} | ERROR | fetch failed |")
            continue

        runs = data.get("runs", [])
        if not runs:
            lines.append(f"| {name} | — | no rules-loaded traces |")
            continue

        latest = runs[0].get("start_time", "unknown")
        # Determine staleness
        try:
            ts = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            hours_ago = (now - ts).total_seconds() / 3600
            if hours_ago < 4:
                status = "current"
            elif hours_ago < 24:
                status = "recent"
            else:
                status = "stale"
        except Exception:
            status = "unknown"

        lines.append(f"| {name} | {latest} | {status} |")

    lines.append("")
    lines.append("## Notes")
    lines.append("- current: rules loaded within 4h")
    lines.append("- recent: loaded within 24h")
    lines.append("- stale: last load >24h ago")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Ingest run 5 — {DATE_LABEL}")

    # Step 2: LangSmith
    ls_watermarks, ls_content = fetch_langsmith()

    # Step 3: GitHub
    gh_watermarks, gh_content = fetch_github()

    # Step 4: Artifacts
    artifact_content = fetch_artifacts(gh_watermarks)

    # Write signal files (append mode for run 5 — add RUN 5 header)
    ls_file = SIGNALS_DIR / "langsmith" / f"{DATE_LABEL}-auto.md"
    gh_file = SIGNALS_DIR / "github" / f"{DATE_LABEL}-auto.md"
    art_file = SIGNALS_DIR / "artifacts" / f"{DATE_LABEL}-auto.md"

    # Append run 5 section
    run5_header = "\n\n---\n## Run 5\n\n"

    for filepath, content in [(ls_file, ls_content), (gh_file, gh_content), (art_file, artifact_content)]:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        existing = filepath.read_text() if filepath.exists() else ""
        with open(filepath, "w") as f:
            f.write(existing + run5_header + content)
        print(f"  Written: {filepath}")

    # Step 5: Watermarks
    update_watermarks(ls_watermarks, gh_watermarks)

    # Step 6: Delivery
    delivery_content = check_delivery()
    delivery_file = SIGNALS_DIR / "delivery" / f"{DATE_LABEL}.md"
    existing_delivery = delivery_file.read_text() if delivery_file.exists() else ""
    with open(delivery_file, "w") as f:
        f.write(existing_delivery + "\n\n---\n## Run 5\n\n" + delivery_content)
    print(f"  Written: {delivery_file}")

    print("\nIngest run 5 complete.")


if __name__ == "__main__":
    main()
