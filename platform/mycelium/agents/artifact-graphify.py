#!/usr/bin/env python3
"""
Artifact Graphify — pulls team docs from repos and extracts graph structure.

Reads signals/artifacts/ to find recently changed docs, pulls content via
GitHub API, uses Sonnet to extract entities + relationships, and writes
Document nodes to Neo4j.

The extracted concepts connect to existing Knowledge nodes — team docs
become semantically queryable through the same MCP tools.

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

    # Get existing node labels for linking
    existing_nodes = []
    try:
        from neo4j import GraphDatabase

        def _get_neo4j_uri():
            """Get Neo4j bolt URI, with deprecation path for legacy FALKORDB_HOST."""
            neo4j_bolt = os.environ.get("NEO4J_BOLT")
            if neo4j_bolt:
                return neo4j_bolt
            falkordb_host = os.environ.get("FALKORDB_HOST")
            if falkordb_host:
                print(f"[artifact-graphify] WARNING: FALKORDB_HOST is deprecated. Use NEO4J_BOLT instead.")
                return f"bolt://{falkordb_host}:7687"
            return "bolt://localhost:7687"

        uri = _get_neo4j_uri()
        user = os.environ.get("NEO4J_USER", "neo4j")
        pw = os.environ.get("NEO4J_PASS", "localtest12")
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        session = driver.session()
        result = session.run("MATCH (n:Knowledge) RETURN n.node_id LIMIT 100")
        existing_nodes = [row[0] for row in result]
        driver.close()
    except Exception:
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


def snapshot_and_clear_docs(session):
    """Snapshot current Document + Concept nodes, then wipe them.

    Same pattern as Demand: wipe and replace each cycle.
    Previous state lives in the JSONL snapshots (sync-layers handles those
    for Intent/Convergence/Phase; we handle Doc/Concept here).
    """
    snapshot_dir = Path(__file__).parent.parent / "knowledge" / "meta" / "layer-snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snapshot_file = snapshot_dir / f"{date_str}.jsonl"

    # Snapshot
    records = 0
    try:
        result = session.run(
            "MATCH (d:Document) "
            "OPTIONAL MATCH (d)-[:CONTAINS_CONCEPT]->(c:Concept) "
            "RETURN d.node_id, d.label, d.source, collect(c.node_id) AS concepts"
        )
        with open(snapshot_file, "a") as f:
            ts = datetime.now(timezone.utc).isoformat()
            for row in result:
                record = {
                    "snapshot_ts": ts, "node_type": "Document",
                    "node_id": row[0], "label": row[1],
                    "source": row[2], "concepts": row[3],
                }
                f.write(json.dumps(record, default=str) + "\n")
                records += 1
    except Exception:
        pass

    # Wipe Document and Concept nodes (they get recreated from fresh extraction)
    try:
        session.run("MATCH (c:Concept) DETACH DELETE c")
        session.run("MATCH (d:Document) DETACH DELETE d")
    except Exception:
        pass

    return records


def sync_to_graph(output_file: Path):
    """Sync extracted document concepts to Neo4j as Document nodes.

    Wipes previous Document + Concept nodes first (snapshot preserved in JSONL).
    """
    try:
        from neo4j import GraphDatabase

        def _get_neo4j_uri():
            """Get Neo4j bolt URI, with deprecation path for legacy FALKORDB_HOST."""
            neo4j_bolt = os.environ.get("NEO4J_BOLT")
            if neo4j_bolt:
                return neo4j_bolt
            falkordb_host = os.environ.get("FALKORDB_HOST")
            if falkordb_host:
                print(f"[artifact-graphify] WARNING: FALKORDB_HOST is deprecated. Use NEO4J_BOLT instead.")
                return f"bolt://{falkordb_host}:7687"
            return "bolt://localhost:7687"

        uri = _get_neo4j_uri()
        user = os.environ.get("NEO4J_USER", "neo4j")
        pw = os.environ.get("NEO4J_PASS", "localtest12")
        driver = GraphDatabase.driver(uri, auth=(user, pw))
        session = driver.session()
    except Exception as e:
        print(f"  Neo4j unavailable: {e}. Skipping graph sync.")
        return

    # Snapshot and clear previous docs/concepts
    snapped = snapshot_and_clear_docs(session)
    if snapped:
        print(f"  Snapshot: {snapped} doc nodes archived before replacement")

    data = json.loads(output_file.read_text())
    total_concepts = 0
    total_rels = 0
    total_links = 0

    def esc(s):
        if s is None:
            return ""
        return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")

    for doc in data.get("documents", []):
        source = esc(doc.get("source", ""))
        title = esc(doc.get("title", ""))

        # Create Document node
        doc_id = esc(re.sub(r'[^a-z0-9-]', '-', doc.get("source", "").lower().replace("/", "-")))
        session.run(
            f"MERGE (d:Document {{node_id: '{doc_id}'}}) "
            f"SET d.label = '{title[:200]}', "
            f"d.source = '{source}', "
            f"d.file_type = 'document'"
        )

        # Create concept nodes and link to document
        for concept in doc.get("concepts", []):
            cid = esc(concept.get("id", ""))
            if not cid:
                continue
            clabel = esc(concept.get("label", ""))
            ctype = esc(concept.get("type", ""))
            csummary = esc(concept.get("summary", "")[:300])

            session.run(
                f"MERGE (c:Concept {{node_id: '{cid}'}}) "
                f"SET c.label = '{clabel}', "
                f"c.concept_type = '{ctype}', "
                f"c.summary = '{csummary}', "
                f"c.file_type = 'concept'"
            )

            # Link document → concept
            try:
                session.run(
                    f"MATCH (d:Document {{node_id: '{doc_id}'}}), "
                    f"(c:Concept {{node_id: '{cid}'}}) "
                    f"MERGE (d)-[:CONTAINS_CONCEPT]->(c)"
                )
            except Exception:
                pass

            total_concepts += 1

        # Create inter-concept relationships
        for rel in doc.get("relationships", []):
            src = esc(rel.get("source", ""))
            tgt = esc(rel.get("target", ""))
            rtype = esc(rel.get("relation", "RELATES_TO"))
            if src and tgt:
                try:
                    session.run(
                        f"MATCH (a:Concept {{node_id: '{src}'}}), "
                        f"(b:Concept {{node_id: '{tgt}'}}) "
                        f"MERGE (a)-[r:{rtype}]->(b)"
                    )
                    total_rels += 1
                except Exception:
                    pass

        # Link concepts to existing Knowledge nodes
        for link in doc.get("links_to_existing", []):
            cid = esc(link.get("concept_id", ""))
            existing = esc(link.get("existing_node_id", ""))
            ltype = esc(link.get("relation", "REFERENCES"))
            if cid and existing:
                try:
                    session.run(
                        f"MATCH (c:Concept {{node_id: '{cid}'}}), "
                        f"(k:Knowledge {{node_id: '{existing}'}}) "
                        f"MERGE (c)-[r:{ltype}]->(k)"
                    )
                    total_links += 1
                except Exception:
                    pass

    driver.close()
    print(f"  Graph sync: {total_concepts} concepts, {total_rels} relationships, {total_links} links to existing nodes")


if __name__ == "__main__":
    asyncio.run(main())
