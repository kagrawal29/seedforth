#!/usr/bin/env python3
"""
Direct Graph Ingestion — traces, commits, issues → FalkorDB. Zero LLM.

Every interaction leaves a structural trace. Not an LLM-extracted summary.
An actual node with edges to what it touched.

Three sources:
1. LangSmith traces → Trace nodes (TTL: 2 days)
2. GitHub commits → Commit nodes (TTL: 14 days)
3. GitHub issues → Issue nodes (permanent, update in place)

All Cypher. All free. The graph changes shape from raw coupling.
Dream rounds consolidate patterns. Integrity rules prune decay.
"""

import json
import os
import re
import subprocess
import sys
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

# Secret redaction — strip credentials before they enter the graph
try:
    from scripts.lib.redact import redact
except ImportError:
    from lib.redact import redact

REPO_ROOT = Path(__file__).resolve().parent.parent
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"

# CM5: Rate limits per ingestion cycle
CYCLE_START = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
RATE_LIMITS = {"Trace": 100, "Commit": 50, "Issue": 50}


def _check_rate_limit(graph, label):
    """Return True if under the rate limit for this node type in the current cycle."""
    limit = RATE_LIMITS.get(label, 100)
    try:
        r = graph.query(
            f"MATCH (n:{label}) WHERE n.timestamp >= '{CYCLE_START}' RETURN count(n)"
        )
        count = r.result_set[0][0] if r.result_set else 0
        if count >= limit:
            print(f"  [CM5] Rate limit hit: {count}/{limit} {label} nodes this cycle. Skipping.")
            return False
    except Exception:
        pass  # If check fails, allow the write
    return True

# Forest aliases — fallback when graph is unavailable
ALIASES = {
    "sahiram": "Banyan", "abhishek": "Sequoia", "ankit-s": "Birch",
    "ankit": "Birch", "sahil": "Cedar", "pranav": "Oak", "kshitiz": "Mycelium",
}

# Cache for graph-based alias lookups (populated once per run)
_alias_cache = {}
_alias_cache_loaded = False


def esc(s):
    if s is None: return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")[:300]


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(GRAPH_NAME)


def load_config():
    return yaml.safe_load((REPO_ROOT / "config.yaml").read_text())


def _load_alias_cache(graph):
    """Load Person nodes from graph into alias cache (once per run).

    Builds a lookup from github_usernames and person names to forest aliases.
    Falls back silently if graph query fails.
    """
    global _alias_cache, _alias_cache_loaded
    if _alias_cache_loaded:
        return
    _alias_cache_loaded = True
    try:
        result = graph.query(
            "MATCH (p:Person) WHERE p.alias IS NOT NULL "
            "RETURN p.alias, p.github_usernames, p.label"
        )
        for row in result.result_set:
            alias = row[0]
            github_usernames = row[1] or ""
            label = row[2] or ""
            # Map each github username to the alias
            for uname in github_usernames.split(","):
                uname = uname.strip().lower()
                if uname:
                    _alias_cache[uname] = alias
            # Map the label (display name) to the alias
            if label:
                _alias_cache[label.lower().strip()] = alias
    except Exception:
        pass  # Graph unavailable — to_alias will fall back to ALIASES dict


def to_alias(name, graph=None):
    if not name: return "unknown"
    # Load graph-based cache on first call (if graph provided)
    if graph and not _alias_cache_loaded:
        _load_alias_cache(graph)
    key = name.lower().strip()
    # Try graph cache first
    if key in _alias_cache:
        return _alias_cache[key]
    # Fall back to hardcoded dict
    return ALIASES.get(key, name)


# ============================================================================
# 1. LANGSMITH TRACES → Trace nodes
# ============================================================================

def _load_watermarks():
    """Load trace watermarks — last ingested timestamp per team member."""
    wm_path = REPO_ROOT / "signals" / ".watermarks.yaml"
    if wm_path.exists():
        try:
            return yaml.safe_load(wm_path.read_text()) or {}
        except Exception:
            pass
    return {}


def _save_watermark(uuid, timestamp):
    """Save the latest trace timestamp for a team member."""
    wm_path = REPO_ROOT / "signals" / ".watermarks.yaml"
    wm = _load_watermarks()
    if "graph_ingest" not in wm:
        wm["graph_ingest"] = {}
    wm["graph_ingest"][uuid] = timestamp
    wm_path.parent.mkdir(parents=True, exist_ok=True)
    wm_path.write_text(yaml.dump(wm, default_flow_style=False))


def ingest_traces(graph, config, since_hours=12):
    """Ingest ALL new LangSmith traces as Trace nodes.

    Uses watermarks to only fetch traces newer than last ingestion.
    No limit cap — ingests everything since last watermark.
    On first run, falls back to since_hours lookback.
    """
    api_key = os.environ.get(config.get("langsmith", {}).get("api_key_env", "CC_LANGSMITH_API_KEY"), "")
    base = config.get("langsmith", {}).get("base_url", "https://api.smith.langchain.com/api/v1")

    if not api_key:
        print("  [traces] No LangSmith API key. Skipping.")
        return 0

    watermarks = _load_watermarks().get("graph_ingest", {})
    fallback_since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    team = config.get("team", [])
    ingested = 0

    for member in team:
        uuid = member.get("langsmith_project", "")
        name = member.get("name", "")
        alias = to_alias(name, graph=graph)
        if not uuid: continue

        # Use watermark if available, else fallback
        since = watermarks.get(uuid, fallback_since)

        try:
            body = json.dumps({
                "session": [uuid],
                "start_time": since,
                "is_root": True,
                "limit": 100,
                "select": ["status", "start_time", "total_tokens", "inputs", "outputs"],
            }).encode()
            req = Request(f"{base}/runs/query", data=body,
                         headers={"x-api-key": api_key, "Content-Type": "application/json"})
            resp = urlopen(req, timeout=10)
            data = json.loads(resp.read())
        except Exception as e:
            print(f"  [traces] {name}: fetch failed ({str(e)[:50]})")
            continue

        for run in data.get("runs", []):
            run_id = run.get("id", "")[:12]
            status = run.get("status", "")
            start_time = (run.get("start_time") or "")[:19]
            tokens = run.get("total_tokens", 0)

            # Extract first user message (redact secrets before graph entry)
            question = ""
            msgs = (run.get("inputs") or {}).get("messages", [])
            for m in msgs:
                if m.get("role") == "user":
                    content = m.get("content", "")
                    if isinstance(content, list):
                        content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
                    question = redact(content[:200])
                    break

            if not question or len(question) < 10:
                continue

            # Extract first 200 chars of Claude's response
            answer = ""
            out_msgs = (run.get("outputs") or {}).get("messages", [])
            if out_msgs:
                ans_content = out_msgs[-1].get("content", "")
                if isinstance(ans_content, list):
                    ans_content = " ".join(p.get("text", "") for p in ans_content if isinstance(p, dict))
                answer = redact(str(ans_content)[:200])

            # CM5: Rate limit check
            if not _check_rate_limit(graph, 'Trace'):
                break

            trace_id = f"trace-{alias}-{run_id}"

            try:
                graph.query(
                    f"MERGE (t:Trace {{node_id: '{esc(trace_id)}'}}) "
                    f"SET t.label = '{esc(question[:100])}', "
                    f"t.person = '{esc(alias)}', "
                    f"t.question = '{esc(question)}', "
                    f"t.answer = '{esc(answer)}', "
                    f"t.timestamp = '{esc(start_time)}', "
                    f"t.tokens = {tokens or 0}, "
                    f"t.status = '{esc(status)}', "
                    f"t.file_type = 'trace'"
                )

                # Link to Knowledge nodes by keyword overlap
                words = set(w.lower() for w in re.findall(r'\b\w{5,}\b', question))
                if words:
                    word_conditions = " OR ".join(
                        f"toLower(k.label) CONTAINS '{esc(w)}'" for w in list(words)[:5]
                    )
                    try:
                        graph.query(
                            f"MATCH (t:Trace {{node_id: '{esc(trace_id)}'}}), (k:Knowledge) "
                            f"WHERE {word_conditions} "
                            f"WITH t, k LIMIT 3 "
                            f"MERGE (t)-[:TOUCHES]->(k)"
                        )
                    except Exception:
                        pass

                ingested += 1
            except Exception:
                pass

        # Save watermark — newest trace timestamp for this member
        if data.get("runs"):
            newest = max((r.get("start_time") or "") for r in data["runs"])
            if newest:
                _save_watermark(uuid, newest)

    return ingested


# ============================================================================
# 2. GITHUB COMMITS → Commit nodes
# ============================================================================

def ingest_commits(graph, config, since_hours=24):
    """Ingest recent GitHub commits as Commit nodes.

    Each commit becomes a node with edges to:
    - Files modified (File nodes, linked to Feature/Screen nodes by path)
    - Author (by alias)
    """
    repos = config.get("repos", [])
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    ingested = 0

    for repo_config in repos:
        org = repo_config.get("org", "Qubit-Capital")
        repo = repo_config.get("name", "")
        if not repo: continue

        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{org}/{repo}/commits",
                 "--jq", ".[].sha + \"|\" + .[]?.commit.message + \"|\" + .[]?.commit.author.name + \"|\" + (.[]?.commit.author.date // \"\")",
                 "-q", f"per_page=20&since={since}"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                # Simpler approach
                result = subprocess.run(
                    ["gh", "api", f"repos/{org}/{repo}/commits?per_page=15&since={since}"],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode != 0:
                    continue
                commits = json.loads(result.stdout)
        except Exception:
            continue

        if isinstance(commits, str):
            continue

        for commit in commits[:15]:
            sha = commit.get("sha", "")[:7]
            message = (commit.get("commit", {}).get("message", "") or "").split("\n")[0]
            author = commit.get("commit", {}).get("author", {}).get("name", "")
            date = commit.get("commit", {}).get("author", {}).get("date", "")[:19]
            alias = to_alias(author, graph=graph)

            if not sha or not message: continue

            # CM5: Rate limit check
            if not _check_rate_limit(graph, 'Commit'):
                break

            commit_id = f"commit-{repo}-{sha}"

            try:
                graph.query(
                    f"MERGE (c:Commit {{node_id: '{esc(commit_id)}'}}) "
                    f"SET c.label = '{esc(message[:150])}', "
                    f"c.sha = '{esc(sha)}', "
                    f"c.repo = '{esc(repo)}', "
                    f"c.author = '{esc(alias)}', "
                    f"c.timestamp = '{esc(date)}', "
                    f"c.file_type = 'commit'"
                )

                # Link commit to Features by path keywords in message
                feature_keywords = {
                    "deal": "feature-create-deal", "pipeline": "feature-move-pipeline",
                    "email": "feature-compose-email", "meeting": "feature-call-prep",
                    "research": "feature-create-research", "notification": "feature-notification-center",
                    "workflow": "feature-workflow-builder", "integration": "feature-integrations",
                    "fund": "feature-fund-profile", "knowledge": "feature-knowledge-base",
                }
                msg_lower = message.lower()
                for keyword, feature_id in feature_keywords.items():
                    if keyword in msg_lower:
                        try:
                            graph.query(
                                f"MATCH (c:Commit {{node_id: '{esc(commit_id)}'}}), "
                                f"(f:Feature {{node_id: '{esc(feature_id)}'}}) "
                                f"MERGE (c)-[:MODIFIES]->(f)"
                            )
                        except Exception:
                            pass
                        break

                ingested += 1
            except Exception:
                pass

    return ingested


# ============================================================================
# 3. GITHUB ISSUES → Issue nodes
# ============================================================================

def ingest_issues(graph, config):
    """Ingest GitHub issues (all states) as Issue nodes (update in place).

    Each issue becomes a permanent node with edges to:
    - Concepts/Knowledge by keyword match
    - Scenarios/Pains by label match
    """
    repos = config.get("repos", [])
    ingested = 0

    for repo_config in repos:
        org = repo_config.get("org", "Qubit-Capital")
        repo = repo_config.get("name", "")
        if not repo: continue

        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{org}/{repo}/issues?state=all&per_page=30"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0: continue
            issues = json.loads(result.stdout)
        except Exception:
            continue

        for issue in issues:
            if issue.get("pull_request"): continue  # Skip PRs
            number = issue.get("number", 0)
            title = issue.get("title", "")
            state = issue.get("state", "open")
            labels = [l.get("name", "") for l in issue.get("labels", [])]
            assignees = [a.get("login", "") for a in issue.get("assignees", [])]
            body = (issue.get("body") or "")[:500]

            # CM5: Rate limit check
            if not _check_rate_limit(graph, 'Issue'):
                break

            issue_id = f"issue-{repo}-{number}"

            try:
                graph.query(
                    f"MERGE (i:Issue {{node_id: '{esc(issue_id)}'}}) "
                    f"SET i.label = '{esc(title[:200])}', "
                    f"i.number = {number}, "
                    f"i.repo = '{esc(repo)}', "
                    f"i.state = '{esc(state)}', "
                    f"i.labels = '{esc(', '.join(labels))}', "
                    f"i.assignees = '{esc(', '.join(assignees))}', "
                    f"i.body = '{esc(body)}', "
                    f"i.file_type = 'issue'"
                )

                # Link to Scenarios by keyword match in title
                scenario_keywords = {
                    "lp": "lp-data-collection", "narrative": "lp-narrative-writing",
                    "portfolio": "portfolio-monitoring", "deal": "sourcing-pipeline-triage",
                    "research": "market-research-deep-dive", "memo": "deal-memo-synthesis",
                    "triage": "sourcing-pipeline-triage", "meeting": "post-call-context-capture",
                }
                title_lower = title.lower()
                for keyword, scenario_id in scenario_keywords.items():
                    if keyword in title_lower:
                        try:
                            graph.query(
                                f"MATCH (i:Issue {{node_id: '{esc(issue_id)}'}}), "
                                f"(s:Scenario {{node_id: '{esc(scenario_id)}'}}) "
                                f"MERGE (i)-[:ADDRESSES_SCENARIO]->(s)"
                            )
                        except Exception:
                            pass

                # Link to Knowledge by keyword match
                words = set(w.lower() for w in re.findall(r'\b\w{5,}\b', title))
                if words:
                    word_conditions = " OR ".join(
                        f"toLower(k.label) CONTAINS '{esc(w)}'" for w in list(words)[:3]
                    )
                    try:
                        graph.query(
                            f"MATCH (i:Issue {{node_id: '{esc(issue_id)}'}}), (k:Knowledge) "
                            f"WHERE {word_conditions} "
                            f"WITH i, k LIMIT 2 "
                            f"MERGE (i)-[:RELATES_TO]->(k)"
                        )
                    except Exception:
                        pass

                ingested += 1
            except Exception:
                pass

    return ingested


# ============================================================================
# 4. ISSUES → WorkItem nodes (maverick-meta only)
# ============================================================================

def ingest_workitems(graph, config):
    """Auto-create WorkItem nodes from maverick-meta issues.

    Every open issue on maverick-meta becomes a WorkItem. Dependencies
    are inferred from issue body ("depends on #N"). Closed issues
    update WorkItem status to 'done'.

    This is how the system plans its own evolution through its own topology.
    """
    try:
        result = subprocess.run(
            ["gh", "api", "repos/Qubit-Capital/maverick-meta/issues?state=all&per_page=50"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return 0
        issues = json.loads(result.stdout)
    except Exception:
        return 0

    ingested = 0

    for issue in issues:
        if issue.get("pull_request"):
            continue
        number = issue.get("number", 0)
        title = issue.get("title", "")
        state = issue.get("state", "open")
        body = (issue.get("body") or "")[:1000]

        workitem_id = f"workitem-issue-{number}"
        workitem_status = "done" if state == "closed" else "open"

        try:
            # MERGE WorkItem — idempotent
            graph.query(
                f"MERGE (w:WorkItem {{node_id: '{esc(workitem_id)}'}}) "
                f"SET w.label = '#{number}: {esc(title[:150])}', "
                f"w.issue_number = {number}, "
                f"w.status = '{workitem_status}', "
                f"w.file_type = 'workitem'"
            )

            # Link to Issue node
            issue_id = f"issue-maverick-meta-{number}"
            graph.query(
                f"MATCH (w:WorkItem {{node_id: '{esc(workitem_id)}'}}), "
                f"(i:Issue {{node_id: '{esc(issue_id)}'}}) "
                f"MERGE (w)-[:TRACKS]->(i)"
            )

            # Infer dependencies from issue body ("depends on #N", "blocked by #N")
            dep_matches = re.findall(r'(?:depends on|blocked by|requires|after)\s*#(\d+)', body, re.IGNORECASE)
            for dep_num in dep_matches:
                dep_id = f"workitem-issue-{dep_num}"
                try:
                    graph.query(
                        f"MATCH (w:WorkItem {{node_id: '{esc(workitem_id)}'}}), "
                        f"(d:WorkItem {{node_id: '{esc(dep_id)}'}}) "
                        f"MERGE (w)-[:DEPENDS_ON]->(d)"
                    )
                except Exception:
                    pass

            # Link to Knowledge by keyword match
            words = set(w.lower() for w in re.findall(r'\b\w{5,}\b', title))
            if words:
                word_conditions = " OR ".join(
                    f"toLower(k.label) CONTAINS '{esc(w)}'" for w in list(words)[:3]
                )
                try:
                    graph.query(
                        f"MATCH (w:WorkItem {{node_id: '{esc(workitem_id)}'}}), (k:Knowledge) "
                        f"WHERE {word_conditions} "
                        f"WITH w, k LIMIT 2 "
                        f"MERGE (w)-[:RELATES_TO]->(k)"
                    )
                except Exception:
                    pass

            ingested += 1
        except Exception:
            pass

    return ingested


# ============================================================================
# Decay — prune expired signal nodes
# ============================================================================

def prune_expired(graph):
    """Prune Trace and Commit nodes past their TTL."""
    now = datetime.now(timezone.utc)

    # Traces: 2-day TTL
    trace_cutoff = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        r = graph.query(
            f"MATCH (t:Trace) WHERE t.timestamp < '{trace_cutoff}' "
            f"WITH t LIMIT 200 DETACH DELETE t RETURN count(t)"
        )
        trace_pruned = r.result_set[0][0] if r.result_set else 0
    except Exception:
        trace_pruned = 0

    # Commits: 14-day TTL
    commit_cutoff = (now - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        r = graph.query(
            f"MATCH (c:Commit) WHERE c.timestamp < '{commit_cutoff}' "
            f"WITH c LIMIT 200 DETACH DELETE c RETURN count(c)"
        )
        commit_pruned = r.result_set[0][0] if r.result_set else 0
    except Exception:
        commit_pruned = 0

    return trace_pruned, commit_pruned


# ============================================================================
# Main
# ============================================================================

def main():
    print(f"[ingest-to-graph] Direct graph ingestion — zero LLM")

    config = load_config()

    try:
        graph = get_graph()
    except Exception as e:
        print(f"  FalkorDB unavailable: {e}")
        return

    # Ingest
    traces = ingest_traces(graph, config, since_hours=12)
    print(f"  Traces ingested: {traces}")

    commits = ingest_commits(graph, config, since_hours=48)
    print(f"  Commits ingested: {commits}")

    issues = ingest_issues(graph, config)
    print(f"  Issues ingested: {issues}")

    workitems = ingest_workitems(graph, config)
    print(f"  WorkItems synced: {workitems}")

    # Decay
    trace_pruned, commit_pruned = prune_expired(graph)
    if trace_pruned or commit_pruned:
        print(f"  Pruned: {trace_pruned} traces (>2d), {commit_pruned} commits (>14d)")

    # Summary
    total = traces + commits + issues
    print(f"[ingest-to-graph] Done: {total} nodes ingested, $0 LLM cost")


if __name__ == "__main__":
    main()
