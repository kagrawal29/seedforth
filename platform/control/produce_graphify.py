"""Produce a deterministic, provenance-bearing Graphify input for one project.

The producer runs as the project account and reads only its approved documents.
It emits section identifiers, not model-generated summaries or relationships.
This gives Mycelium useful, reproducible source sensing while keeping semantic
inference out of the authoritative state until a separately qualified extractor
is installed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

BINDINGS = {
    "flowing-indian": {
        "repo": "/home/proj-flowing-indian/flowing-indian",
        "repository": "kartiksahu/flowing-indian-website",
        "documents": ["README.md", "docs/architecture.md", "docs/graph-multiagent-references.md"],
        "output": "/home/proj-flowing-indian/.local/share/seedforth-graphify/output.json",
    },
    "cajon-sensei": {
        "repo": "/home/proj-cajon-sensei/cajon-sensei",
        "repository": "seedforth/cajon-sensei",
        "documents": ["CLAUDE.md", "memory/decisions.md"],
        "output": "/home/proj-cajon-sensei/.local/share/seedforth-graphify/output.json",
    },
}
ACCOUNT_SCOPES = {
    "proj-flowing-indian": "flowing-indian",
    "proj-cajon-sensei": "cajon-sensei",
}
SLUG = re.compile(r"[^a-z0-9]+")


def git_revision(repo: str) -> str:
    result = subprocess.run(
        ["/usr/bin/git", "-c", "safe.directory=" + repo, "-C", repo,
         "rev-parse", "--verify", "HEAD^{commit}"],
        capture_output=True, text=True, check=True, timeout=5,
        env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1",
             "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0"},
    )
    revision = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid_repository_revision")
    return revision


def concept_id(text: str, document: str, index: int) -> str:
    slug = SLUG.sub("-", text.lower()).strip("-")[:80] or "section"
    suffix = hashlib.sha256((document + "#" + str(index)).encode()).hexdigest()[:10]
    return f"{slug}-{suffix}"


def extract_document(repo: Path, relative: str) -> dict:
    path = repo / relative
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(relative)
    text = path.read_text(encoding="utf-8")
    concepts = []
    for index, line in enumerate(text.splitlines()):
        match = re.match(r"^#{1,3}\s+(.+?)\s*#*$", line)
        if match:
            label = match.group(1).strip()
            concepts.append({"id": concept_id(label, relative, index),
                             "label": label, "type": "source_section"})
    relationships = [{"source": concepts[i]["id"], "target": concepts[i + 1]["id"],
                      "relation": "FOLLOWS"}
                     for i in range(len(concepts) - 1)]
    return {"source": relative, "concepts": concepts, "relationships": relationships}


def produce(scope: str) -> dict:
    if scope not in BINDINGS:
        raise ValueError("unapproved_graphify_scope")
    binding = BINDINGS[scope]
    repo = Path(binding["repo"])
    revision = git_revision(str(repo))
    documents = [extract_document(repo, path) for path in binding["documents"]]
    payload = {
        "repository": binding["repository"],
        "revision": revision,
        "extractor_revision": "deterministic-markdown-sections-v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "documents": documents,
    }
    output = Path(binding["output"])
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    os.replace(temporary, output)
    return {"scope": scope, "repository": binding["repository"], "revision": revision,
            "documents": len(documents), "output": str(output)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("scope", choices=sorted(BINDINGS | ACCOUNT_SCOPES))
    selected = parser.parse_args().scope
    print(json.dumps(produce(ACCOUNT_SCOPES.get(selected, selected))))
