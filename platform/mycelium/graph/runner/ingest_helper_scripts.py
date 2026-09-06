#!/usr/bin/env python3
# ============================================================================
# Runner: ingest_helper_scripts
# ============================================================================
# Brings Python/Bash helper scripts into the graph as :HelperScript nodes.
# For Python files, atomizes by AST — each function/class becomes a :CodeAtom
# linked via :HAS_CODE_ATOM.
#
# Rationale: the graph should be aware of every piece of tooling that runs
# against it, not just the cypher protocols. Helper scripts are "just piping"
# (bash/python) around graph operations. If all helper files were deleted,
# the graph should hold enough structural info to regenerate them.
#
# Idempotent: MERGE on node_id, update content/hash/atoms on match.
# ============================================================================
import ast
import base64
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")
REPO_ROOT = Path(__file__).resolve().parents[2]

# Roots to scan
SCAN_ROOTS = [REPO_ROOT / "graph" / "runner", REPO_ROOT / "tools"]
EXTENSIONS = {".py", ".sh"}


def run_cypher(statement, params=None, timeout=30):
    body = {"statements": [{"statement": statement, "parameters": params or {}}]}
    req = urllib.request.Request(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("errors"):
        raise RuntimeError(f"Neo4j errors: {result['errors']}")
    return result.get("results", [])


def extract_purpose(content, language):
    """Heuristic: first docstring (Python) or first comment block (Bash/Python header)."""
    if language == "python":
        try:
            tree = ast.parse(content)
            doc = ast.get_docstring(tree)
            if doc:
                return doc.strip().split("\n")[0][:200]
        except SyntaxError:
            pass
    # Fall back to first comment block
    lines = content.split("\n")
    comment_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#!"):
            continue
        if stripped.startswith("#") or stripped.startswith("//"):
            text = re.sub(r"^[#/=\s-]+", "", stripped).strip()
            if text:
                comment_lines.append(text)
        elif comment_lines:
            break
    if comment_lines:
        return " ".join(comment_lines)[:200]
    return ""


def atomize_python(content, helper_id):
    """Split Python source into (name, kind, source, lineno) atoms per top-level def/class."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    atoms = []
    source_lines = content.split("\n")
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start + 1
            src = "\n".join(source_lines[start:end])
            kind = "function" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else "class"
            atoms.append({
                "name": node.name,
                "kind": kind,
                "source": src,
                "lineno": node.lineno,
                "end_lineno": end,
                "atom_id": f"{helper_id}-atom-{node.name}",
            })
    return atoms


def gather_files():
    """Walk SCAN_ROOTS, return list of (abs_path, rel_path, ext)."""
    files = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in EXTENSIONS:
                rel = path.relative_to(REPO_ROOT)
                files.append((path, rel, path.suffix))
    return sorted(files, key=lambda t: str(t[1]))


def ingest_file(abs_path, rel_path, ext):
    """Ingest one helper file. Returns ('new' | 'updated' | 'unchanged', atom_count)."""
    content = abs_path.read_text(encoding="utf-8", errors="replace")
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    stem = abs_path.stem.replace(".", "_")
    helper_id = f"helper-{stem}"
    language = "python" if ext == ".py" else "bash"
    is_archived = "archive/" in str(rel_path) or "v1-pre-migration" in str(rel_path)
    kind = "archived" if is_archived else "active"
    purpose = extract_purpose(content, language)
    line_count = content.count("\n") + 1

    # Check for existing
    existing = run_cypher(
        "MATCH (h:HelperScript {node_id: $id}) RETURN h.content_hash AS hash",
        {"id": helper_id},
    )
    prior_hash = None
    if existing and existing[0].get("data"):
        prior_hash = existing[0]["data"][0]["row"][0]

    if prior_hash == content_hash:
        return "unchanged", 0

    # MERGE the helper node
    run_cypher(
        """
        MERGE (h:HelperScript {node_id: $id})
          ON CREATE SET h.created_at = $ts
        SET h.filepath = $path,
            h.filename = $fname,
            h.language = $lang,
            h.kind = $kind,
            h.content = $content,
            h.content_hash = $hash,
            h.purpose = $purpose,
            h.line_count = $lc,
            h.ingested_at = $ts
        """,
        {
            "id": helper_id,
            "path": str(rel_path),
            "fname": abs_path.name,
            "lang": language,
            "kind": kind,
            "content": content,
            "hash": content_hash,
            "purpose": purpose,
            "lc": line_count,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Atomize Python files (AST) — Bash stays whole for now
    atoms = atomize_python(content, helper_id) if language == "python" else []

    # Remove stale atoms
    run_cypher(
        "MATCH (h:HelperScript {node_id: $id})-[:HAS_CODE_ATOM]->(a:CodeAtom) DETACH DELETE a",
        {"id": helper_id},
    )

    for order, atom in enumerate(atoms):
        run_cypher(
            """
            MATCH (h:HelperScript {node_id: $hid})
            MERGE (a:CodeAtom {atom_id: $aid})
            SET a.helper_id = $hid,
                a.name = $name,
                a.kind = $kind,
                a.source = $source,
                a.lineno = $lineno,
                a.end_lineno = $end_lineno,
                a.order = $order
            MERGE (h)-[r:HAS_CODE_ATOM]->(a)
              SET r.order = $order
            """,
            {
                "hid": helper_id,
                "aid": atom["atom_id"],
                "name": atom["name"],
                "kind": atom["kind"],
                "source": atom["source"],
                "lineno": atom["lineno"],
                "end_lineno": atom["end_lineno"],
                "order": order,
            },
        )

    status = "new" if prior_hash is None else "updated"
    return status, len(atoms)


def main():
    files = gather_files()
    print(f"[ingest_helper_scripts] scanning {len(files)} files", file=sys.stderr)
    counts = {"new": 0, "updated": 0, "unchanged": 0}
    total_atoms = 0
    for abs_path, rel_path, ext in files:
        try:
            status, atom_count = ingest_file(abs_path, rel_path, ext)
            counts[status] += 1
            total_atoms += atom_count
            if status != "unchanged":
                print(f"  [{status}] {rel_path} ({atom_count} atoms)", file=sys.stderr)
        except Exception as e:
            print(f"  [err] {rel_path}: {str(e)[:150]}", file=sys.stderr)
    print(
        f"[ingest_helper_scripts] done: {len(files)} scanned, "
        f"{counts['new']} new, {counts['updated']} updated, "
        f"{counts['unchanged']} unchanged, {total_atoms} code atoms",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
