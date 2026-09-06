#!/usr/bin/env python3
"""Team activity dashboard — LangSmith traces + GitHub pushes."""
import json, os, sys, subprocess, time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))

ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE = ROOT / "signals" / "dashboard-cache.json"
CACHE_TTL = 300  # 5 minutes

API_KEY = os.environ.get("CC_LANGSMITH_API_KEY", "")
LS_BASE = "https://api.smith.langchain.com/api/v1"

TEAM = {
    "Pranav":   "7d991519-fad6-4ede-bed1-9be395152ebe",
    "Ankit-S":  "3473bc94-aa22-40ab-80bd-8588c9b00861",
    "Kshitiz":  "ce70362b-3f8f-499b-b90c-a09f45bb000b",
    "Sahiram":  "f6b7d95f-ebda-48e6-81f9-9cfdbe28294c",
    "Abhishek": "43265e84-4cad-452b-b2d2-65859553e043",
    "Sahil":    "bf63ca28-62c6-4466-9c3b-97e6f6bbc32a",
}

REPOS = [
    "Qubit-Capital/VC-AI-Assoicate",
    "Qubit-Capital/maverick-market-research",
]


def fetch_langsmith(limit=3):
    """Fetch recent traces per team member, return extracted summaries."""
    results = {}
    for name, pid in TEAM.items():
        body = json.dumps({
            "session": [pid], "limit": limit, "is_root": True,
            "select": ["status", "start_time", "end_time", "total_tokens", "inputs", "outputs"],
        }).encode()
        req = Request(f"{LS_BASE}/runs/query", data=body,
                      headers={"x-api-key": API_KEY, "Content-Type": "application/json"})
        try:
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())
        except Exception as e:
            # Retry once on failure
            try:
                time.sleep(1)
                resp = urlopen(req, timeout=15)
                data = json.loads(resp.read())
            except Exception as e2:
                results[name] = {"error": str(e2), "traces": []}
                continue

        traces = []
        for r in data.get("runs", []):
            user_msg = _extract_user_msg(r.get("inputs", {}))
            claude_msg = _extract_claude_msg(r.get("outputs") or {})
            traces.append({
                "status": r.get("status", "?"),
                "start": (r.get("start_time") or "?")[:19],
                "tokens": r.get("total_tokens", 0) or 0,
                "user": user_msg[:200],
                "claude": claude_msg[:200],
            })
        results[name] = {"traces": traces}
    return results


def _extract_user_msg(inputs):
    if not isinstance(inputs, dict):
        return ""
    msgs = inputs.get("messages", [])
    if not isinstance(msgs, list):
        return ""
    for m in reversed(msgs):
        if isinstance(m, dict) and m.get("role") == "user":
            c = m.get("content", "")
            if isinstance(c, str):
                if c.startswith("<task-notification>"):
                    return "[subagent task]"
                return c[:200]
            if isinstance(c, list):
                for part in c:
                    if isinstance(part, dict) and part.get("type") == "text":
                        txt = part.get("text", "")[:200]
                        if txt.startswith("<task-notification>"):
                            return "[subagent task]"
                        return txt
    return ""


def _extract_claude_msg(outputs):
    if not isinstance(outputs, dict):
        return ""
    msgs = outputs.get("messages", [])
    if not isinstance(msgs, list) or not msgs:
        return ""
    last = msgs[-1]
    if isinstance(last, dict):
        c = last.get("content", "")
        return str(c)[:200] if isinstance(c, str) else ""
    return ""


def fetch_github():
    """Get latest commit per non-main branch across repos."""
    pushes = {}
    for repo in REPOS:
        try:
            out = subprocess.run(
                ["gh", "api", f"repos/{repo}/branches", "--paginate",
                 "--jq", '.[] | select(.name != "main") | "\(.name)|\(.commit.sha)"'],
                capture_output=True, text=True, timeout=15
            )
            if out.returncode != 0:
                continue
            for line in out.stdout.strip().split("\n"):
                if not line or "|" not in line:
                    continue
                branch = line.split("|", 1)[0]
                # Get latest commit as JSON
                out2 = subprocess.run(
                    ["gh", "api", f"repos/{repo}/commits?sha={branch}&per_page=1",
                     "--jq", '.[0] | {author: .commit.author.name, date: .commit.author.date[:19], msg: (.commit.message | split("\n")[0])}'],
                    capture_output=True, text=True, timeout=10
                )
                if out2.returncode == 0 and out2.stdout.strip():
                    try:
                        info = json.loads(out2.stdout.strip())
                    except json.JSONDecodeError:
                        continue
                    author = info.get("author", "")
                    date = info.get("date", "")
                    msg = info.get("msg", "")
                    # Skip commits that are just our rule distribution
                    if "meta: add shared rule" in msg or "meta: update shared rule" in msg:
                        continue
                    key = author.strip()
                    if key not in pushes or date > pushes[key]["date"]:
                        pushes[key] = {
                            "date": date,
                            "branch": branch,
                            "msg": msg[:80],
                            "repo": repo.split("/")[1],
                        }
        except Exception:
            continue
    return pushes


def load_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        data = json.loads(CACHE_FILE.read_text())
        age = time.time() - data.get("fetched_at", 0)
        if age < CACHE_TTL:
            return data
    except Exception:
        pass
    return None


def save_cache(langsmith, github):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps({
        "fetched_at": time.time(),
        "fetched_at_human": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "langsmith": langsmith,
        "github": github,
    }, indent=2))


def _utc_to_ist(utc_str):
    """Convert a UTC time string (HH:MM or YYYY-MM-DDTHH:MM:SS) to IST HH:MM."""
    try:
        if len(utc_str) >= 19:
            t = datetime.fromisoformat(utc_str + "+00:00")
        elif len(utc_str) == 5:  # HH:MM
            today = datetime.now(timezone.utc).date()
            t = datetime(today.year, today.month, today.day,
                         int(utc_str[:2]), int(utc_str[3:5]), tzinfo=timezone.utc)
        else:
            return utc_str
        return t.astimezone(IST).strftime("%H:%M")
    except Exception:
        return utc_str


def render(langsmith, github, cache_hit=False):
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    print(f"\nTEAM DASHBOARD — {now}")
    if cache_hit:
        print("(from cache)")
    print("=" * 70)
    print(f"  {'Name':<12} {'Status':<8} {'Last Seen':<12} {'Working On':<30} {'Pushed'}")
    print(f"  {'-'*10:<12} {'-'*6:<8} {'-'*10:<12} {'-'*28:<30} {'-'*20}")

    rows = []
    for name in TEAM:
        info = langsmith.get(name, {})
        traces = info.get("traces", [])

        if not traces:
            rows.append((name, "IDLE", "--", "--", "--"))
            continue

        latest = traces[0]
        status = "ACTIVE" if latest["status"] == "pending" else "idle"
        if status == "idle":
            # Check if last activity was within 30 min
            try:
                t = datetime.fromisoformat(latest["start"] + "+00:00")
                age_min = (datetime.now(timezone.utc) - t).total_seconds() / 60
                if age_min < 30:
                    status = "RECENT"
            except Exception:
                pass

        last_seen_utc = latest["start"][11:16] if len(latest["start"]) >= 16 else latest["start"]
        last_seen = _utc_to_ist(last_seen_utc)
        user_msg = latest["user"][:50].replace("\n", " ")

        # Find github push
        push = "--"
        # Match by name variations
        name_variants = [name, name.replace("-", " "), name.split("-")[0]]
        for author, pinfo in github.items():
            if any(v.lower() in author.lower() for v in name_variants):
                push_time = _utc_to_ist(pinfo['date'])
                push = f"{push_time} ({pinfo['branch'][:25]})"
                break

        rows.append((name, status, last_seen, user_msg, push))

    # Sort: ACTIVE first, then RECENT, then idle
    order = {"ACTIVE": 0, "RECENT": 1, "idle": 2, "IDLE": 3}
    rows.sort(key=lambda r: order.get(r[1], 9))

    for name, status, seen, work, push in rows:
        print(f"  {name:<12} {status:<8} {seen:<12} {work:<30} {push}")

    print()


def main():
    args = sys.argv[1:]
    fresh = "--fresh" in args
    quick = "--quick" in args
    limit = 1 if quick else 3

    if not fresh:
        cached = load_cache()
        if cached:
            render(cached["langsmith"], cached.get("github", {}), cache_hit=True)
            return

    langsmith = fetch_langsmith(limit=limit)
    github = {} if quick else fetch_github()
    save_cache(langsmith, github)
    render(langsmith, github)


if __name__ == "__main__":
    main()
