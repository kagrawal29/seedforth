#!/usr/bin/env python3
"""
Artifact Graphify — pulls team docs from repos and extracts graph structure.

Reads signals/artifacts/ to find recently changed docs, pulls content via
GitHub API, uses Sonnet to extract entities + relationships, and records a
bounded, provenance-bearing observation through Mycelium's control boundary.

The extracted concepts remain untrusted facts until an explicit reviewed
promotion establishes a stronger relationship.

Model: Sonnet. Cost: ~$0.30-0.50 per changed doc.
Runs in pipeline after ingest, before demand.
"""

import asyncio
import json
import os
import re
import subprocess
import sys
import yaml
from pathlib import Path
from datetime import datetime, timezone

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    return yaml.safe_load(config_path.read_text())


def get_recent_artifacts(signals_dir: Path, limit: int = 5) -> list[dict]:
    """Parse artifact signal files and extract file references.

    Returns list of {repo, org, file_path, sha, status, additions}.
    """
    artifacts_dir = signals_dir / "artifacts"
    if not artifacts_dir.exists():
        return []

    artifacts = []
    files = sorted(artifacts_dir.glob("*.md"), reverse=True)[:limit]

    for f in files:
        text = f.read_text()
        current_repo = None
        current_org = "Qubit-Capital"

        for line in text.split("\n"):
            # Detect repo header: ## VC-AI-Assoicate or ## Qubit-Capital/VC-AI-Assoicate
            repo_match = re.match(r"^##\s+(?:(\S+)/)?(\S+)\s*$", line)
            if repo_match:
                if repo_match.group(1):
                    current_org = repo_match.group(1)
                current_repo = repo_match.group(2)
                continue

            # Detect artifact table rows — multiple formats:
            # | pattern | `file/path.md` | status | +N |
            # | sha | `file/path.md` | status | +N |
            # | sha | file/path.md | modified | N |
            row_match = re.search(r'`([^`]+\.md)`\s*\|\s*(\w+)\s*\|\s*\+?(\d+)', line)
            if not row_match:
                # Try without backticks
                row_match = re.search(r'\|\s*(\S+\.md)\s*\|\s*(\w+)\s*\|\s*\+?(\d+)', line)
            if row_match and current_repo:
                file_path = row_match.group(1)
                status = row_match.group(2)
                additions = int(row_match.group(3))

                # Only graphify substantial docs (>50 lines), skip configs and non-docs
                if additions >= 50 and file_path.endswith(".md") and not file_path.startswith("."):
                    artifacts.append({
                        "repo": current_repo,
                        "org": current_org,
                        "file_path": file_path,
                        "status": status,
                        "additions": additions,
                    })

    return artifacts


def fetch_file_content(org: str, repo: str, file_path: str, branch: str = "main") -> str | None:
    """Fetch file content from GitHub."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{org}/{repo}/contents/{file_path}",
             "--jq", ".content", "-H", "Accept: application/vnd.github.v3+json"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            # Try raw content
            result = subprocess.run(
                ["gh", "api", f"repos/{org}/{repo}/contents/{file_path}",
                 "--jq", ".download_url"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0 and result.stdout.strip():
                import urllib.request
                url = result.stdout.strip()
                return urllib.request.urlopen(url, timeout=10).read().decode()
            return None

        import base64
        return base64.b64decode(result.stdout.strip()).decode()
    except Exception:
        return None


def build_prompt(artifacts_with_content: list[dict], existing_nodes: list[str]):
    """Build the extraction prompt for Sonnet."""
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    doc_sections = []
    for i, art in enumerate(artifacts_with_content, 1):
        content_preview = art["content"][:3000]
        doc_sections.append(
            f"### Document {i}: {art['org']}/{art['repo']}/{art['file_path']}\n\n"
            f"```markdown\n{content_preview}\n```\n"
        )

    docs_text = "\n".join(doc_sections)
    nodes_text = "\n".join(f"  - {n}" for n in existing_nodes[:50]) if existing_nodes else "  (none loaded)"

    return f"""You are the artifact graphify engine. Your job is to extract entities, concepts, and relationships from team documentation and write them as graph-ready JSON.

## Input Documents

{docs_text}

## Existing Graph Nodes (for linking)

These nodes already exist in the knowledge graph. Link extracted concepts to these where relevant:
{nodes_text}

## What to Extract

For each document, extract:

1. **Concepts** — technologies, patterns, decisions, components, domain terms mentioned
2. **Relationships** — how concepts relate to each other within the doc
3. **Links to existing nodes** — which existing graph nodes this doc references or builds upon

## Output Format

Write a single JSON file to `signals/artifacts/graphify-output.json`:

```json
{{
  "extracted_at": "{date}",
  "documents": [
    {{
      "source": "org/repo/file/path.md",
      "title": "Document title from first heading",
      "concepts": [
        {{
          "id": "kebab-case-id",
          "label": "Human-readable name",
          "type": "technology|pattern|decision|component|process|constraint",
          "summary": "One sentence description from the doc"
        }}
      ],
      "relationships": [
        {{
          "source": "concept-id",
          "target": "concept-id",
          "relation": "DEPENDS_ON|IMPLEMENTS|CONSTRAINS|EVALUATES|REPLACES",
          "detail": "One sentence explaining the relationship"
        }}
      ],
      "links_to_existing": [
        {{
          "concept_id": "extracted-concept-id",
          "existing_node_id": "node-id-from-graph",
          "relation": "REFERENCES|EXTENDS|IMPLEMENTS|CONTRADICTS"
        }}
      ]
    }}
  ]
}}
```

## Rules

- Extract real substance, not filler. Skip headings that are just structure.
- Use kebab-case IDs derived from the concept name.
- Only link to existing nodes when the connection is real, not speculative.
- Keep summaries factual — quote the doc, don't interpret.
- If a document is mostly config/boilerplate with no substantial concepts, return an empty concepts array.
- Write valid JSON with indent=2.
"""


async def main():
    config = load_config()
    root = Path(__file__).parent.parent

    # Find recently changed artifacts
    artifacts = get_recent_artifacts(root / "signals")
    if not artifacts:
        print("[artifact-graphify] No substantial artifacts found. Skipping.")
        return

    print(f"[artifact-graphify] Found {len(artifacts)} artifacts to graphify")

    # Fetch content for each
    artifacts_with_content = []
    for art in artifacts[:5]:  # Cap at 5 docs per cycle
        print(f"  Fetching {art['org']}/{art['repo']}/{art['file_path']}...")
        content = fetch_file_content(art["org"], art["repo"], art["file_path"])
        if content and len(content) > 100:
            art["content"] = content
            artifacts_with_content.append(art)
            print(f"    {len(content)} chars")
        else:
            print(f"    Skipped (not found or too short)")

    if not artifacts_with_content:
        print("[artifact-graphify] No artifact content fetched. Skipping.")
        return

    # Existing graph nodes are optional context, never an implicit authority.
    # Use the same scoped operation boundary as every other client.
    existing_nodes = []
    try:
        platform_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(platform_root))
        from control.graph import Graph
        rows = Graph().operation(
            "read-scoped-graph",
            os.environ.get("SEEDFORTH_GRAPHIFY_PRINCIPAL", "principal-graphify-sensor"),
            os.environ.get("GRAPHIFY_SCOPE", "seedforth-platform"),
            cursor="",
        )
        existing_nodes = [row["id"] for row in rows if isinstance(row.get("id"), str)]
    except Exception:
        # Extraction can still produce an observation with no linking context.
        pass

    prompt = build_prompt(artifacts_with_content, existing_nodes)

    print(f"[artifact-graphify] Starting extraction ({len(artifacts_with_content)} docs)...")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Glob", "Grep"],  # No Bash — invariant 5,
            permission_mode="bypassPermissions",
            cwd=str(root),
            max_turns=20,
            max_budget_usd=2.0,
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
            print(f"[artifact-graphify] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)

    # Sync extracted concepts to FalkorDB
    output_file = root / "signals" / "artifacts" / "graphify-output.json"
    if output_file.exists():
        sync_to_graph(output_file)
    else:
        print("  No graphify output produced.")


def sync_to_graph(output_file: Path):
    """Record Graphify output through the bounded control-plane operation."""
    platform_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(platform_root))
    from control.graph import Graph
    from control.graphify_snapshot import build_snapshot, record

    snapshot = build_snapshot(
        output_file,
        os.environ.get("GRAPHIFY_REPOSITORY", "seedforth/mycelium-artifacts"),
        os.environ.get("GRAPHIFY_INPUT_REVISION", "unresolved"),
        os.environ.get("GRAPHIFY_EXTRACTOR_REVISION", "artifact-graphify-unpinned-v0"),
    )
    rows = record(
        Graph(),
        os.environ.get("SEEDFORTH_GRAPHIFY_PRINCIPAL", "principal-graphify-sensor"),
        os.environ.get("GRAPHIFY_SCOPE", "seedforth-platform"),
        snapshot,
    )
    print(f"  Graphify observation: {len(snapshot['facts'])} bounded facts, {len(snapshot['failures'])} failures")
    return rows


if __name__ == "__main__":
    asyncio.run(main())
