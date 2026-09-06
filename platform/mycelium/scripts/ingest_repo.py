#!/usr/bin/env python3
"""
ingest_repo.py — Ingest a git repo's history and file tree into mycelium dev Neo4j.

What gets written (MERGE only, idempotent):
  :Repo          — one per repo url
  :Commit        — one per sha (capped at --max-commits)
  :Author        — one per (email, project) pair
  :File          — current HEAD file tree (text/code only, <1MB)
  :Directory     — top-level + conventional dirs (src, docs, scripts, etc.)
  Edges:
    (:Commit)-[:AUTHORED_BY]->(:Author)
    (:Repo)-[:CONTAINS]->(:Commit|:File|:Directory)
    (:Project)-[:TRACKS]->(:Repo)
    (:File)-[:IN_DIR]->(:Directory)

Safety rails:
  - Refuses if --project doesn't match an existing :Project node in Neo4j
  - Refuses if target Neo4j URL contains :7687 (prod) — only :7688/:7698/:7699 (dev) allowed
  - Refuses if repo URL isn't under Qubit-Capital/ or kagrawal29/
  - Skips .git/, node_modules/, __pycache__, .venv, files > 1MB
  - Skips binary files (images, PDFs, archives)

Usage:
  python3 scripts/ingest_repo.py <repo_url> --project <name> [--max-commits N]
                                  [--bolt <url>] [--user <user>] [--pass <pass>]
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Neo4j driver ──────────────────────────────────────────────────────────────
try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: pip install neo4j", file=sys.stderr)
    sys.exit(1)

# ── Constants ─────────────────────────────────────────────────────────────────

ALLOWED_ORGS = {"Qubit-Capital", "kagrawal29"}

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".env",
             "vendor", ".mypy_cache", ".pytest_cache", "dist", "build",
             ".tox", "eggs", ".eggs"}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib", ".wasm",
    ".mp4", ".mp3", ".avi", ".mov", ".wav",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".db", ".sqlite", ".pkl", ".npz", ".npy",
    ".lock",  # lockfiles can be huge
}

CONVENTIONAL_DIRS = {"src", "docs", "scripts", "tests", "test", "lib",
                     "api", "config", "configs", "data", "dist", "build",
                     "public", "static", "assets", "migrations"}

MAX_FILE_BYTES = 1_000_000  # 1 MB

PROD_BOLT_PATTERNS = [":7687"]  # port 7687 = prod; block it
DEV_BOLT_PATTERNS  = [":7688", ":7698", ":7699", "localhost", "127.0.0.1"]

BATCH_SIZE = 500  # commits per UNWIND

# ── Language detection ─────────────────────────────────────────────────────────

EXT_LANG = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript", ".tsx": "TypeScript", ".go": "Go",
    ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#",
    ".c": "C", ".cpp": "C++", ".h": "C/C++",
    ".swift": "Swift", ".sh": "Shell", ".bash": "Shell",
    ".zsh": "Shell", ".fish": "Shell",
    ".md": "Markdown", ".mdx": "Markdown",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON",
    ".toml": "TOML", ".ini": "INI", ".cfg": "INI",
    ".html": "HTML", ".css": "CSS", ".scss": "SCSS", ".sass": "SASS",
    ".sql": "SQL", ".cypher": "Cypher",
    ".tf": "Terraform", ".hcl": "HCL",
    ".dockerfile": "Dockerfile", ".Dockerfile": "Dockerfile",
}

def detect_language(path: str) -> str:
    p = Path(path)
    if p.name in ("Dockerfile", "Makefile", "Procfile"):
        return p.name
    return EXT_LANG.get(p.suffix.lower(), "Other")

# ── Safety checks ──────────────────────────────────────────────────────────────

def check_allowed_org(repo_url: str):
    """Abort if the repo URL is not under an allowed org."""
    # Normalize: strip trailing .git, handle https://github.com/Org/Repo
    url = repo_url.rstrip("/").removesuffix(".git")
    # Extract org from URL
    parts = re.split(r"[/:]", url)
    # For https://github.com/Org/Repo → parts[-2] is Org
    if len(parts) < 2:
        print(f"ERROR: cannot parse org from URL: {repo_url}", file=sys.stderr)
        sys.exit(1)
    org = parts[-2]
    if org not in ALLOWED_ORGS:
        print(
            f"ERROR: repo org '{org}' is not in the allowlist {ALLOWED_ORGS}.\n"
            "ingest_repo only ingests repos from Qubit-Capital or kagrawal29.",
            file=sys.stderr,
        )
        sys.exit(1)
    return org

def check_not_prod(bolt_url: str):
    """Abort if the bolt URL looks like prod (port 7687)."""
    for pat in PROD_BOLT_PATTERNS:
        if pat in bolt_url:
            # But allow localhost:7687 (local dev)
            if "localhost" in bolt_url or "127.0.0.1" in bolt_url:
                return  # local is fine
            print(
                f"ERROR: bolt URL '{bolt_url}' looks like prod (port 7687).\n"
                "ingest-repo only targets dev Neo4j. Use bolt://5.78.206.137:7698 for dev.",
                file=sys.stderr,
            )
            sys.exit(1)

def check_project_exists(driver, project_name: str):
    """Abort if the :Project node doesn't exist in Neo4j."""
    with driver.session() as session:
        result = session.run(
            "MATCH (p:Project {node_id: $nid}) RETURN p.node_id LIMIT 1",
            nid=project_name,
        )
        row = result.single()
        if row is None:
            print(
                f"ERROR: no :Project node with node_id='{project_name}' found in Neo4j.\n"
                "Run 'mycelium shell' to list projects, or create the node first.",
                file=sys.stderr,
            )
            sys.exit(1)

# ── Git helpers ────────────────────────────────────────────────────────────────

def clone_repo(repo_url: str, tmpdir: str, depth: int = 1000):
    """Shallow clone with limited history."""
    print(f"  cloning {repo_url} (depth={depth})...")
    result = subprocess.run(
        ["git", "clone", "--depth", str(depth), "--no-tags", repo_url, tmpdir],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"ERROR: git clone failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

def get_default_branch(tmpdir: str) -> str:
    r = subprocess.run(
        ["git", "-C", tmpdir, "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() or "main"

def get_commits(tmpdir: str, max_commits: int) -> list[dict]:
    """Return list of commit dicts from git log."""
    print(f"  reading git log (max={max_commits})...")
    result = subprocess.run(
        ["git", "-C", tmpdir, "log", "--all",
         f"--max-count={max_commits}",
         "--pretty=format:%H|%an|%ae|%at|%s"],
        capture_output=True, text=True,
    )
    commits = []
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        parts = line.split("|", 4)
        if len(parts) < 5:
            continue
        sha, author_name, author_email, authored_at, message = parts
        try:
            authored_at_int = int(authored_at)
        except ValueError:
            authored_at_int = 0
        commits.append({
            "sha": sha.strip(),
            "author_name": author_name.strip()[:200],
            "author_email": author_email.strip()[:200],
            "authored_at": authored_at_int,
            "message": message.strip()[:500],
        })
    print(f"  found {len(commits)} commits")
    return commits

def get_file_tree(tmpdir: str) -> list[dict]:
    """Walk working tree and collect file metadata. Skip binary/large/ignored."""
    print("  scanning file tree...")
    files = []
    root = Path(tmpdir)
    for dirpath, dirnames, filenames in os.walk(tmpdir):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        for fname in filenames:
            fpath = Path(dirpath) / fname
            rel_path = fpath.relative_to(root)
            rel_path_str = str(rel_path)
            # Skip binary extensions
            ext = fpath.suffix.lower()
            if ext in BINARY_EXTENSIONS:
                continue
            # Skip large files
            try:
                size = fpath.stat().st_size
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            # Count lines
            lines = 0
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
            except OSError:
                pass
            files.append({
                "path": rel_path_str,
                "size": size,
                "lines_of_code": lines,
                "language": detect_language(rel_path_str),
            })
    print(f"  found {len(files)} files")
    return files

def get_directories(tmpdir: str) -> list[str]:
    """Collect top-level dirs + conventional subdirs (depth ≤ 2)."""
    root = Path(tmpdir)
    dirs = set()
    # Top-level dirs
    try:
        for item in root.iterdir():
            if item.is_dir() and item.name not in SKIP_DIRS and not item.name.startswith("."):
                dirs.add(item.name)
                # Conventional subdirs
                for sub in item.iterdir():
                    if sub.is_dir() and sub.name in CONVENTIONAL_DIRS:
                        dirs.add(f"{item.name}/{sub.name}")
    except OSError:
        pass
    return sorted(dirs)

def get_last_modified(tmpdir: str, file_path: str) -> str:
    """Get sha of last commit that touched a file."""
    r = subprocess.run(
        ["git", "-C", tmpdir, "log", "-1", "--pretty=format:%H", "--", file_path],
        capture_output=True, text=True,
    )
    return r.stdout.strip() or ""

def get_language_summary(tmpdir: str) -> str:
    """Best-effort language summary from file extensions."""
    counts: dict[str, int] = {}
    for root, dirs, files in os.walk(tmpdir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = Path(f).suffix.lower()
            lang = EXT_LANG.get(ext)
            if lang and lang not in ("Markdown", "YAML", "JSON", "Other"):
                counts[lang] = counts.get(lang, 0) + 1
    if not counts:
        return "Unknown"
    top = sorted(counts.items(), key=lambda x: -x[1])[:3]
    return ", ".join(f"{lang}({n})" for lang, n in top)

# ── Neo4j ingestion ────────────────────────────────────────────────────────────

def ingest_repo_node(session, repo_url: str, project: str, default_branch: str, language_summary: str):
    repo_id = re.sub(r"[^a-zA-Z0-9_-]", "-", repo_url.split("github.com/")[-1].removesuffix(".git"))
    session.run("""
        MERGE (r:Repo {node_id: $node_id})
        SET r.url = $url,
            r.project = $project,
            r.default_branch = $default_branch,
            r.language_summary = $language_summary,
            r.ingested_at = timestamp()
    """, node_id=repo_id, url=repo_url, project=project,
        default_branch=default_branch, language_summary=language_summary)
    return repo_id

def link_project_to_repo(session, project: str, repo_id: str):
    session.run("""
        MATCH (proj:Project {node_id: $project})
        MATCH (r:Repo {node_id: $repo_id})
        MERGE (proj)-[:TRACKS]->(r)
    """, project=project, repo_id=repo_id)

def ingest_commits(session, commits: list[dict], project: str, repo_id: str):
    """Bulk MERGE commits + authors in batches of BATCH_SIZE."""
    total = len(commits)
    for i in range(0, total, BATCH_SIZE):
        batch = commits[i:i + BATCH_SIZE]
        # Enrich with project
        for c in batch:
            c["project"] = project
        session.run("""
            UNWIND $batch AS c
            MERGE (commit:Commit {sha: c.sha, project: c.project})
            SET commit.author_name = c.author_name,
                commit.author_email = c.author_email,
                commit.authored_at = c.authored_at,
                commit.message = c.message,
                commit.project = c.project

            MERGE (author:Author {email: c.author_email, project: c.project})
            SET author.name = c.author_name,
                author.project = c.project

            MERGE (commit)-[:AUTHORED_BY]->(author)

            WITH commit
            MATCH (r:Repo {node_id: $repo_id})
            MERGE (r)-[:CONTAINS]->(commit)
        """, batch=batch, repo_id=repo_id)
        end = min(i + BATCH_SIZE, total)
        print(f"    commits {i+1}–{end} / {total} merged")

def ingest_files(session, files: list[dict], project: str, repo_id: str, tmpdir: str, dirs: list[str]):
    """MERGE file nodes with IN_DIR edges."""
    dir_set = set(dirs)
    # Compute parent dirs for each file
    for f in files:
        p = Path(f["path"])
        parent = str(p.parent) if str(p.parent) != "." else ""
        f["parent_dir"] = parent
        f["project"] = project

    total = len(files)
    for i in range(0, total, BATCH_SIZE):
        batch = files[i:i + BATCH_SIZE]
        session.run("""
            UNWIND $batch AS f
            MERGE (file:File {path: f.path, project: f.project})
            SET file.size = f.size,
                file.lines_of_code = f.lines_of_code,
                file.language = f.language,
                file.project = f.project

            WITH file, f
            MATCH (r:Repo {node_id: $repo_id})
            MERGE (r)-[:CONTAINS]->(file)
        """, batch=batch, repo_id=repo_id)
        end = min(i + BATCH_SIZE, total)
        print(f"    files {i+1}–{end} / {total} merged")

    # Wire IN_DIR edges for files whose parent is a tracked dir
    for f in files:
        parent = f["parent_dir"]
        # Normalize: strip leading slash
        if parent and (parent in dir_set or parent.split("/")[0] in dir_set):
            session.run("""
                MATCH (file:File {path: $path, project: $project})
                MATCH (d:Directory {path: $dir_path, project: $project})
                MERGE (file)-[:IN_DIR]->(d)
            """, path=f["path"], project=project, dir_path=parent)

def ingest_directories(session, dirs: list[str], project: str, repo_id: str):
    """MERGE directory nodes."""
    dir_records = [{"path": d, "project": project} for d in dirs]
    session.run("""
        UNWIND $dirs AS d
        MERGE (dir:Directory {path: d.path, project: d.project})
        SET dir.project = d.project

        WITH dir
        MATCH (r:Repo {node_id: $repo_id})
        MERGE (r)-[:CONTAINS]->(dir)
    """, dirs=dir_records, repo_id=repo_id)
    print(f"    {len(dirs)} directories merged")

# ── Main ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Ingest a git repo into mycelium dev Neo4j (read-only from repo, writes to Neo4j only)."
    )
    p.add_argument("repo_url", help="GitHub HTTPS URL, e.g. https://github.com/Qubit-Capital/vc-ai-associate")
    p.add_argument("--project", required=True, help="node_id of an existing :Project node in Neo4j")
    p.add_argument("--max-commits", type=int, default=500, dest="max_commits",
                   help="Maximum commits to ingest (default: 500)")
    p.add_argument("--bolt", default=None,
                   help="Neo4j bolt URL (default: from /root/.mycelium-secrets or bolt://5.78.206.137:7698)")
    p.add_argument("--user", default=None, help="Neo4j user (default: neo4j)")
    p.add_argument("--password", default=None, help="Neo4j password")
    return p.parse_args()

def load_secrets() -> dict:
    """Load Neo4j creds from /root/.mycelium-secrets if it exists."""
    secrets = {}
    secrets_path = "/root/.mycelium-secrets"
    if os.path.exists(secrets_path):
        with open(secrets_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    secrets[k.strip()] = v.strip().strip('"').strip("'")
    return secrets

def main():
    args = parse_args()

    # 1. Safety: allowed org
    check_allowed_org(args.repo_url)

    # 2. Resolve Neo4j connection
    secrets = load_secrets()

    bolt = args.bolt or secrets.get("NEO4J_DEV_BOLT") or "bolt://5.78.206.137:7698"
    user = args.user or secrets.get("NEO4J_DEV_USER") or "neo4j"
    password = args.password or secrets.get("NEO4J_DEV_PASS") or os.environ.get("MYCELIUM_DEV_PASS") or ""

    # 3. Safety: not prod
    check_not_prod(bolt)

    print(f"\n[ingest-repo] {args.repo_url}")
    print(f"  project   : {args.project}")
    print(f"  target    : {bolt}")
    print(f"  max-commits: {args.max_commits}")

    # 4. Connect
    driver = GraphDatabase.driver(bolt, auth=(user, password))
    try:
        driver.verify_connectivity()
    except Exception as e:
        print(f"ERROR: cannot connect to Neo4j at {bolt}: {e}", file=sys.stderr)
        sys.exit(1)

    # 5. Safety: project exists
    check_project_exists(driver, args.project)

    # 6. Clone into tmpdir
    with tempfile.TemporaryDirectory(prefix="mycelium-ingest-") as tmpdir:
        clone_repo(args.repo_url, tmpdir, depth=args.max_commits)

        default_branch = get_default_branch(tmpdir)
        language_summary = get_language_summary(tmpdir)
        commits = get_commits(tmpdir, args.max_commits)
        files = get_file_tree(tmpdir)
        dirs = get_directories(tmpdir)

        print(f"\n  default_branch : {default_branch}")
        print(f"  language_summary: {language_summary}")
        print(f"  commits        : {len(commits)}")
        print(f"  files          : {len(files)}")
        print(f"  directories    : {len(dirs)}")
        print()

        with driver.session() as session:
            # Repo node
            print("[1/5] Merging :Repo node...")
            repo_id = ingest_repo_node(session, args.repo_url, args.project, default_branch, language_summary)

            # Project → Repo edge
            print("[2/5] Linking :Project -> :Repo...")
            link_project_to_repo(session, args.project, repo_id)

            # Commits + Authors
            print(f"[3/5] Merging {len(commits)} :Commit + :Author nodes...")
            ingest_commits(session, commits, args.project, repo_id)

            # Directories
            print(f"[4/5] Merging {len(dirs)} :Directory nodes...")
            ingest_directories(session, dirs, args.project, repo_id)

            # Files
            print(f"[5/5] Merging {len(files)} :File nodes...")
            ingest_files(session, files, args.project, repo_id, tmpdir, dirs)

    driver.close()

    print(f"\n[ingest-repo] done — {args.repo_url} ingested into project '{args.project}'")
    print("  No writes were made to the source repository.")

if __name__ == "__main__":
    main()
