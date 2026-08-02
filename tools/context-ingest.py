#!/usr/bin/env python3
"""Lift per-project file knowledge into the graph as connected nodes.
Usage:
  python3 context-ingest.py --project seedforthing
  python3 context-ingest.py --all
  python3 context-ingest.py --all --with-llm   # use DeepSeek to parse SEED.md
  python3 context-ingest.py --all --active-only

For each project (base = /home/proj-{name}/{name}/):
  SEED.md          -> EntityMandate + EntityGoals + EntityProfiles
  memory/*.md      -> Decision nodes
  tools/ + opencode.jsonc -> Tool nodes
  data/deploy/build -> Artifact nodes
  Project node     -> context_ingested, has_mandate, *_count
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from neo4j_helper import q, ql

REGISTRY_PATH = os.environ.get("DELTA_REGISTRY_PATH", "/opt/delta/delta-registry.json")
PROJ_HOME = os.environ.get("DELTA_PROJ_HOME", "/home")
ENV_PATH = os.environ.get("DELTA_ENV_PATH", "/opt/delta/delta.env")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

EXCLUDED_DIRS = {
    ".git", "delta-config", "node_modules", "__pycache__", ".claude",
    ".github", ".vercel", "hooks", "agents", "venv", ".venv",
}
TOOL_EXTS = (".py", ".sh", ".js", ".mjs")
DATA_EXTS = (".json", ".csv", ".db")
BUILT_DIRS = ("dist", "build", "public")
DEPLOY_FILES = ("vercel.json", "netlify.toml")


# ---------------------------------------------------------------- helpers

def read_text(path, max_len=None):
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read(max_len) if max_len else f.read()
    except OSError:
        return ""


def slugify(text, maxlen=48):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:maxlen].rstrip("-") or "node"


def ensure_project(name):
    q(
        "MERGE (p:Project {node_id:$pid}) SET p.name=$name, p.project=$name",
        {"pid": f"project-{name}", "name": name},
    )


def project_base(name):
    return os.path.join(PROJ_HOME, f"proj-{name}", name)


# ---------------------------------------------------------------- deepseek

def get_deepseek_key():
    if not os.path.exists(ENV_PATH):
        return ""
    for line in open(ENV_PATH):
        line = line.strip()
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def llm_json(prompt, system=""):
    """Call DeepSeek, expect JSON. Raises on failure."""
    key = get_deepseek_key()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not found in %s" % ENV_PATH)
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system or
             "You extract structured JSON from project documents."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1500,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={"Authorization": "Bearer %s" % key,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def extract_json(text):
    """Strip fences/prose around an LLM JSON response, return dict."""
    text = text.strip()
    if text.startswith("```"):
        blocks = text.split("```")
        text = blocks[1] if len(blocks) >= 2 else text
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("no JSON object in response")
    return json.loads(m.group(0))


def basic_seed_parse(text):
    """First heading + first paragraph as a minimal mandate."""
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    ns = m.group(1).strip() if m else "project exists per SEED.md"
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    para = paras[1] if len(paras) > 1 else (paras[0] if paras else "")
    para = "\n".join(l for l in para.split("\n") if not l.startswith("#"))
    return ns, para[:2000]


# ---------------------------------------------------------------- SEED.md

def ingest_mandate(name, base, use_llm):
    seed = os.path.join(base, "SEED.md")
    if not os.path.isfile(seed):
        return {"has_mandate": False, "goals": 0, "profiles": 0, "needs_llm": False}

    text = read_text(seed)
    basic_ns, basic_para = basic_seed_parse(text)

    mid = f"mandate-{name}"
    existing = ql("MATCH (m:EntityMandate {node_id:$id}) RETURN m.needs_llm",
                  {"id": mid})
    if not use_llm and existing and not existing[0][0]:
        # A parsed (LLM) mandate already exists. A basic re-run must not
        # downgrade it -- keep the rich goals/profiles, just refresh counts.
        g = ql("MATCH (g:EntityGoal {project:$name}) RETURN count(g)",
               {"name": name})
        p = ql("MATCH (p:EntityProfile {project:$name}) RETURN count(p)",
               {"name": name})
        return {"has_mandate": True, "goals": g[0][0] if g else 0,
                "profiles": p[0][0] if p else 0, "needs_llm": False}

    # Parse-dependent nodes are rebuilt on every LLM ingest (goal text changes
    # run to run). File-derived nodes (tools/artifacts/decisions) keep stable
    # node_ids and MERGE in place.
    q("MATCH (n:EntityGoal) WHERE n.project=$name DETACH DELETE n", {"name": name})
    q("MATCH (n:EntityProfile) WHERE n.project=$name DETACH DELETE n", {"name": name})

    north_star, goals, profiles, needs_llm = basic_ns, [], [], True
    blockers, milestones, workitems = [], [], []
    if use_llm:
        try:
            prompt = (
                "Extract from this SEED.md for project %s:\n"
                "1. north_star: one sentence on why this project exists\n"
                "2. goals: 3-5 measurable goals, each with success_criteria "
                "(array of strings)\n"
                "3. profiles: people/roles/entities involved\n"
                "4. blockers: things currently blocking progress, each with "
                "a description and who/what is blocking it\n"
                "5. milestones: key dates/deadlines, each with a title, due date, "
                "and status\n"
                "6. workitems: open next-steps/action items from the Pending/Next "
                "sections, each with a title and optional goal it serves\n"
                "Return JSON: {\"north_star\": \"...\", \"goals\": "
                "[{\"goal\": \"...\", \"success_criteria\": [...]}], "
                "\"profiles\": [\"...\"], \"blockers\": "
                "[{\"description\": \"...\", \"blocked_by\": \"...\"}], "
                "\"milestones\": [{\"title\": \"...\", \"due\": \"...\", "
                "\"status\": \"...\"}], \"workitems\": [{\"title\": \"...\", "
                "\"serves_goal\": \"...\"}]}\n\nSEED.md:\n%s"
                % (name, text[:6000])
            )
            data = extract_json(llm_json(prompt, "You parse SEED.md files into "
                                      "mandate, measurable goals, blockers, "
                                      "milestones, and work items."))
            north_star = str(data.get("north_star") or basic_ns).strip()
            goals = [g for g in data.get("goals") or []
                     if isinstance(g, dict) and g.get("goal")][:5]
            profiles = [p.strip() for p in data.get("profiles") or []
                        if isinstance(p, str) and p.strip()]
            blockers = [b for b in data.get("blockers") or []
                        if isinstance(b, dict) and b.get("description")]
            milestones = [m for m in data.get("milestones") or []
                          if isinstance(m, dict) and m.get("title")]
            workitems = [w for w in data.get("workitems") or []
                         if isinstance(w, dict) and w.get("title")]
            needs_llm = False
        except Exception as e:
            print("    [llm failed for %s: %s] using basic parse" % (name, e))
            goals, profiles, needs_llm = [], [], True

    if not goals:
        goals = [{"goal": north_star, "success_criteria": [basic_para or
                 "sustain active development per SEED.md"]}]

    ensure_project(name)
    q(
        "MERGE (m:EntityMandate {node_id:$id}) "
        "SET m.north_star=$ns, m.source='SEED.md', m.status='active', "
        "m.project=$name, m.needs_llm=$nl, m.updated_at=datetime()",
        {"id": f"mandate-{name}", "ns": north_star, "name": name, "nl": needs_llm},
    )

    for i, g in enumerate(goals, 1):
        q(
            "MERGE (g:EntityGoal {node_id:$id}) "
            "SET g.goal=$goal, g.priority=$p, g.status='active', "
            "g.success_criteria=$crit, g.project=$name, g.updated_at=datetime() "
            "WITH g MATCH (m:EntityMandate {node_id:$mid}) "
            "MERGE (g)-[:DERIVED_FROM {decay_protected:true}]->(m) "
            "WITH g MATCH (p:Project {node_id:$pid}) "
            "MERGE (g)-[:SERVES {decay_protected:true}]->(p)",
            {"id": f"goal-{name}-{slugify(g['goal'])}", "goal": g["goal"],
             "p": i, "crit": [str(c) for c in (g.get("success_criteria") or [])],
             "name": name, "mid": f"mandate-{name}", "pid": f"project-{name}"},
        )

    for prof in profiles:
        q(
            "MERGE (ep:EntityProfile {node_id:$id}) "
            "SET ep.name=$pname, ep.role='mentioned in SEED.md', "
            "ep.involvement='mentioned', ep.project=$name, ep.updated_at=datetime() "
            "WITH ep MATCH (p:Project {node_id:$pid}) "
            "MERGE (ep)-[:INVOLVED_IN {decay_protected:true}]->(p)",
            {"id": f"profile-{name}-{slugify(prof)}", "pname": prof,
             "name": name, "pid": f"project-{name}"},
        )

    for i, b in enumerate(blockers):
        q(
            "MERGE (b:Blocker {node_id:$id}) "
            "SET b.description=$desc, b.blocked_by=$by, b.status='open', "
            "b.created_at=datetime(), b.project=$name "
            "WITH b MATCH (p:Project {node_id:$pid}) "
            "MERGE (b)-[:BLOCKS {decay_protected:true}]->(p)",
            {"id": f"blocker-{name}-{i}", "desc": b.get("description", ""),
             "by": b.get("blocked_by", ""), "name": name,
             "pid": f"project-{name}"},
        )

    for i, m in enumerate(milestones):
        q(
            "MERGE (m:Milestone {node_id:$id}) "
            "SET m.title=$title, m.due=$due, m.status=coalesce($st, 'pending'), "
            "m.created_at=datetime(), m.project=$name "
            "WITH m MATCH (p:Project {node_id:$pid}) "
            "MERGE (m)-[:MILESTONE_OF {decay_protected:true}]->(p)",
            {"id": f"milestone-{name}-{i}", "title": m.get("title", ""),
             "due": m.get("due", ""), "st": m.get("status"), "name": name,
             "pid": f"project-{name}"},
        )

    for i, w in enumerate(workitems):
        q(
            "MERGE (w:WorkItem {node_id:$id}) "
            "SET w.title=$title, w.status='open', w.deliverable='', "
            "w.created_at=datetime(), w.project=$name "
            "WITH w MATCH (p:Project {node_id:$pid}) "
            "MERGE (w)-[:WORK_OF {decay_protected:true}]->(p)",
            {"id": f"workitem-{name}-{i}", "title": w.get("title", ""),
             "name": name, "pid": f"project-{name}"},
        )

    return {"has_mandate": True, "goals": len(goals), "profiles": len(profiles),
            "blockers": len(blockers), "milestones": len(milestones),
            "workitems": len(workitems), "needs_llm": needs_llm}


# ---------------------------------------------------------------- memory

def ingest_decisions(name, base):
    memdir = os.path.join(base, "memory")
    if not os.path.isdir(memdir):
        return 0
    count = 0
    for f in sorted(p for p in os.listdir(memdir) if p.endswith(".md")):
        text = read_text(os.path.join(memdir, f))
        parts = re.split(r"^##\s+(.+)$", text, flags=re.M)
        # parts = [pre, title, body, title, body, ...]
        for i in range(1, len(parts) - 1, 2):
            topic = parts[i].strip()
            content = parts[i + 1].strip()[:3000]
            if not topic:
                continue
            q(
                "MERGE (d:Decision {node_id:$id}) "
                "SET d.topic=$topic, d.content=$content, d.project=$name, "
                "d.file=$file, d.created_at=datetime() "
                "WITH d MATCH (p:Project {node_id:$pid}) "
                "MERGE (d)-[:GOVERNS {decay_protected:true}]->(p)",
                {"id": f"decision-{name}-{slugify(topic)}", "topic": topic,
                 "content": content, "name": name, "file": f,
                 "pid": f"project-{name}"},
            )
            count += 1
    return count


# ---------------------------------------------------------------- tools

def ingest_tools(name, base):
    count = 0
    toolsdir = os.path.join(base, "tools")
    if os.path.isdir(toolsdir):
        for root, dirs, files in os.walk(toolsdir):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            for f in sorted(files):
                if not f.endswith(TOOL_EXTS) or f.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(root, f), base)
                q(
                    "MERGE (t:Tool {node_id:$id}) "
                    "SET t.name=$fname, t.path=$rel, t.purpose='', "
                    "t.status='present', t.project=$name, t.updated_at=datetime() "
                    "WITH t MATCH (sa:SubAgent {node_id:$aid}) "
                    "MERGE (t)-[:USED_BY {decay_protected:true}]->(sa)",
                    {"id": f"tool-{name}-{slugify(rel)}", "fname": f, "rel": rel,
                     "name": name, "aid": f"subagent-{name}"},
                )
                count += 1

    # opencode.jsonc -> configured MCP servers / tools
    oc = os.path.join(base, "opencode.jsonc")
    if os.path.isfile(oc):
        raw = read_text(oc)
        tools = {}
        try:
            cfg = json.loads(raw)
        except ValueError:
            cfg = None
        if isinstance(cfg, dict):
            for src in ("mcp", "mcpServers", "tools"):
                for k, v in (cfg.get(src) or {}).items():
                    tools[k] = f"opencode.jsonc:{src}.{k}"
            for k in tools:
                q(
                    "MERGE (t:Tool {node_id:$id}) "
                    "SET t.name=$tname, t.purpose='configured %s', "
                    "t.status='present', t.project=$name, t.updated_at=datetime() "
                    "WITH t MATCH (sa:SubAgent {node_id:$aid}) "
                    "MERGE (t)-[:USED_BY {decay_protected:true}]->(sa)"
                    % tools[k],
                    {"id": f"tool-{name}-cfg-{slugify(k)}", "tname": k,
                     "name": name, "aid": f"subagent-{name}"},
                )
                count += 1
    return count


# ---------------------------------------------------------------- artifacts

def ingest_artifacts(name, base):
    count = 0

    def add(atype, rel):
        nonlocal count
        q(
            "MERGE (a:Artifact {node_id:$id}) "
            "SET a.type=$atype, a.path=$path, a.status='present', "
            "a.project=$name, a.updated_at=datetime() "
            "WITH a MATCH (p:Project {node_id:$pid}) "
            "MERGE (a)-[:PRODUCED_BY {decay_protected:true}]->(p)",
            {"id": f"artifact-{name}-{slugify(rel)}", "atype": atype,
             "path": rel, "name": name, "pid": f"project-{name}"},
        )
        count += 1

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        rel = os.path.relpath(root, base)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        for f in sorted(files):
            if f.startswith(".") or f.endswith(".md"):
                continue
            relfile = os.path.join(rel, f) if rel != "." else f
            # data files in data/ or root
            if (f.endswith(DATA_EXTS)
                    and (rel == "." or rel == "data" or rel.startswith("data/"))):
                add("data", relfile)
        # deploy configs (any depth)
        for df in DEPLOY_FILES:
            if df in files:
                add("deploy_config", os.path.join(rel, df) if rel != "." else df)

    # built output dirs
    for bd in BUILT_DIRS:
        if os.path.isdir(os.path.join(base, bd)):
            add("built_output", bd)
    # vercel deployment marker
    if os.path.isdir(os.path.join(base, ".vercel")):
        add("deployment", ".vercel")

    return count


# ---------------------------------------------------------------- project node

def update_project(name, m, tools, artifacts, decisions):
    q(
        "MATCH (p:Project {node_id:$pid}) "
        "SET p.context_ingested=datetime(), p.has_mandate=$hm, "
        "p.goal_count=$gc, p.profile_count=$pc, p.tool_count=$tc, "
        "p.artifact_count=$ac, p.decision_count=$dc",
        {"pid": f"project-{name}", "hm": m["has_mandate"], "gc": m["goals"],
         "pc": m["profiles"], "tc": tools, "ac": artifacts, "dc": decisions},
    )


def ingest_project(name, use_llm):
    base = project_base(name)
    if not os.path.isdir(base):
        print("  %-30s skip (no dir %s)" % (name, base))
        return None
    m = ingest_mandate(name, base, use_llm)
    decisions = ingest_decisions(name, base)
    tools = ingest_tools(name, base)
    artifacts = ingest_artifacts(name, base)
    update_project(name, m, tools, artifacts, decisions)
    llm_flag = " [llm]" if (use_llm and not m["needs_llm"]) else \
               " [basic]" if m["has_mandate"] and m["needs_llm"] else ""
    print("  %-28s mandate=%s goals=%d profiles=%d decisions=%d tools=%d "
          "artifacts=%d%s" % (name, m["has_mandate"], m["goals"], m["profiles"],
                              decisions, tools, artifacts, llm_flag))
    return {"name": name, **m, "decisions": decisions, "tools": tools,
            "artifacts": artifacts}


# ---------------------------------------------------------------- verification

def verify_counts():
    print("\n=== Node counts per context type ===")
    for label in ("EntityMandate", "EntityGoal", "EntityProfile", "Tool",
                  "Artifact", "Decision"):
        rows = ql("MATCH (n:%s) RETURN count(n)" % label)
        print("  %-16s %d" % (label, rows[0][0] if rows else 0))

    print("\n=== Projects with a context map (context_ingested) ===")
    rows = ql(
        "MATCH (p:Project) WHERE p.context_ingested IS NOT NULL "
        "OPTIONAL MATCH (p)<-[:SERVES]-(g:EntityGoal) "
        "OPTIONAL MATCH (p)<-[:PRODUCED_BY]-(a:Artifact) "
        "OPTIONAL MATCH (t:Tool) WHERE t.project = p.name "
        "OPTIONAL MATCH (p)<-[:GOVERNS]-(d:Decision) "
        "RETURN p.name, p.has_mandate, count(DISTINCT g), count(DISTINCT a), "
        "count(DISTINCT t), count(DISTINCT d) ORDER BY p.name")
    if not rows:
        print("  (none)")
    for r in rows:
        print("  %-28s mandate=%-5s goals=%-3s artifacts=%-3s tools=%-3s "
              "decisions=%-3s" % (r[0], r[1], r[2], r[3], r[4], r[5]))

    complete = [r for r in rows if r[1] and (r[2] or r[3] or r[4] or r[5])]
    print("\n  Complete context maps: %d projects" % len(complete))
    for r in complete:
        print("    - %s" % r[0])


def print_project_map(name):
    print("\n=== Context map: %s ===" % name)
    rows = ql(
        "MATCH (m:EntityMandate {project:$name}) "
        "OPTIONAL MATCH (m)<-[:DERIVED_FROM]-(g:EntityGoal) "
        "RETURN m.north_star, collect(DISTINCT {goal:g.goal, priority:g.priority, "
        "criteria:g.success_criteria})",
        {"name": name})
    if rows:
        print("  north_star: %s" % rows[0][0])
        for g in rows[0][1] or []:
            if not g.get("goal"):
                continue
            crit = "; ".join(g.get("criteria") or [])[:200]
            print("  goal[%s]: %s | criteria: %s"
                  % (g.get("priority"), g.get("goal"), crit))

    for label, qry in (
        ("profiles", "MATCH (ep:EntityProfile {project:$name}) RETURN ep.name"),
        ("tools", "MATCH (t:Tool {project:$name}) RETURN t.name, t.path ORDER BY t.name"),
        ("artifacts", "MATCH (a:Artifact {project:$name}) RETURN a.type, a.path ORDER BY a.type"),
        ("decisions", "MATCH (d:Decision {project:$name}) RETURN d.topic ORDER BY d.topic"),
    ):
        rows = ql(qry, {"name": name})
        print("  %s (%d):" % (label, len(rows)))
        for r in rows:
            print("    - %s" % (" | ".join(str(x) for x in r)))


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Ingest per-project context into the graph")
    ap.add_argument("--project", help="ingest a single project by name")
    ap.add_argument("--all", action="store_true", help="ingest all registry projects")
    ap.add_argument("--active-only", action="store_true",
                    help="with --all, only status=active projects")
    ap.add_argument("--with-llm", action="store_true",
                    help="use DeepSeek to parse SEED.md")
    args = ap.parse_args()

    registry = json.load(open(REGISTRY_PATH))
    projects = registry.get("projects", {})

    if args.project:
        names = [args.project]
    elif args.all:
        names = sorted(projects)
        if args.active_only:
            names = [n for n in names if projects[n].get("status") == "active"]
    else:
        ap.error("provide --project NAME or --all")

    print("Ingesting %d project(s) (llm=%s)..." % (len(names), args.with_llm))
    results = []
    for name in names:
        r = ingest_project(name, args.with_llm)
        if r:
            results.append(r)

    if args.project:
        print_project_map(args.project)
    else:
        verify_counts()
        if "seedforthing" in [r["name"] for r in results]:
            print_project_map("seedforthing")

    print("\nDone.")


if __name__ == "__main__":
    main()
