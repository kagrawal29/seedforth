#!/usr/bin/env python3
"""
Graphify User Layer — extract Persona, Scenario, Touchpoint, Pain nodes
from market research docs and sync to FalkorDB.

Unlike artifact-graphify (which extracts generic Concepts), this extracts
the user dimension: who the product is for, what their day looks like,
where they hurt, what they switch from, and how they interact with tools.

These nodes connect to existing Knowledge/Concept nodes via ENABLES and
GAP edges — bridging what the team built with who it's for.
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

REPO_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = REPO_ROOT / "signals" / "artifacts" / "research-docs"
OUTPUT_FILE = REPO_ROOT / "signals" / "artifacts" / "user-layer-output.json"


def build_prompt(doc_contents: dict[str, str], existing_nodes: list[str]):
    date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    doc_sections = []
    for name, content in doc_contents.items():
        preview = content[:4000]
        doc_sections.append(f"### {name}\n\n```markdown\n{preview}\n```\n")

    docs_text = "\n".join(doc_sections)
    nodes_text = "\n".join(f"  - {n}" for n in existing_nodes[:60])

    return f"""You are the user layer extraction engine. Your job is to read market research about VC analysts and extract the user dimension into graph-ready JSON.

This is NOT generic concept extraction. You are extracting the HUMAN side — who uses this product, what their day looks like, where they hurt, what moments matter.

## Research Documents

{docs_text}

## Existing Graph Nodes (for linking)

These Knowledge and Concept nodes already exist. Link user-layer nodes to these where the product decisions serve the user need:
{nodes_text}

## What to Extract

### 1. Personas
Who is the user? Not demographic — behavioral. Their workflow, pressures, constraints, tools they use today.
```json
{{"id": "kebab-case", "label": "Human name", "type": "persona", "description": "...", "workflow": "Their daily/weekly rhythm", "tools_today": ["CRM", "email", "spreadsheets"], "fund_size": "range", "deal_volume": "annual range"}}
```

### 2. Scenarios
Moments in the user's work where Maverick should be present. Not features — moments.
```json
{{"id": "kebab-case", "label": "Scenario name", "type": "scenario", "trigger": "What initiates this moment", "context": "Where they are, what just happened", "need": "What they need in this moment", "current_solution": "How they handle it today", "frustration": "What's painful about current solution"}}
```

### 3. Touchpoints
Where the product meets the user — channels, interfaces, integration points.
```json
{{"id": "kebab-case", "label": "Touchpoint name", "type": "touchpoint", "channel": "slack|email|voice|dashboard|mobile|api", "direction": "inbound|outbound|bidirectional"}}
```

### 4. Pain Points
Specific, validated pain from the research. Not assumed — cited.
```json
{{"id": "kebab-case", "label": "Pain name", "type": "pain", "severity": "high|medium|low", "evidence": "Source quote or data point", "affected_persona": "persona-id", "frequency": "daily|weekly|quarterly"}}
```

### 5. Journey Edges
How scenarios connect through the user's actual flow.
```json
{{"source": "scenario-id", "target": "scenario-id", "relation": "LEADS_TO", "detail": "Why this flows into that"}}
```

### 6. Links to Existing Nodes
Where user needs connect to product architecture decisions.
```json
{{"user_node_id": "scenario-or-pain-id", "existing_node_id": "knowledge-node-id", "relation": "ENABLES|GAP|ADDRESSES|BLOCKED_BY", "detail": "How they connect"}}
```

Use ENABLES when an existing decision/feature serves the user need.
Use GAP when the user need exists but no architecture decision addresses it.
Use ADDRESSES when a decision was specifically made for this pain.
Use BLOCKED_BY when an existing decision limits solving this need.

## Output

Write a single JSON file to `signals/artifacts/user-layer-output.json`:

```json
{{
  "extracted_at": "{date}",
  "personas": [...],
  "scenarios": [...],
  "touchpoints": [...],
  "pains": [...],
  "journey_edges": [...],
  "links_to_existing": [...]
}}
```

## Rules

- Extract from what the research SAYS, not what you assume about VCs
- Pain points must cite evidence from the docs
- Scenarios should be specific moments, not features ("got off a call and needs to capture notes" not "note-taking feature")
- Link aggressively to existing nodes — the whole point is connecting the user to the architecture
- GAP links are the most valuable output — they show where the product has a user need with no architecture backing
- Write valid JSON with indent=2
"""


async def main():
    if not RESEARCH_DIR.exists():
        print("[user-layer] No research docs found.")
        return

    doc_contents = {}
    for f in sorted(RESEARCH_DIR.glob("*.md")):
        doc_contents[f.stem] = f.read_text()

    if not doc_contents:
        print("[user-layer] No docs to process.")
        return

    print(f"[user-layer] Found {len(doc_contents)} research docs")
    for name, content in doc_contents.items():
        print(f"  {name}: {len(content)} chars")

    # Get existing nodes
    existing_nodes = []
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=os.environ.get("FALKORDB_HOST", "localhost"),
                      port=int(os.environ.get("FALKORDB_PORT", "6380")))
        g = db.select_graph("asgard")
        r = g.query("MATCH (n) WHERE n:Knowledge OR n:Concept RETURN n.node_id LIMIT 100")
        existing_nodes = [row[0] for row in r.result_set if row[0]]
    except Exception:
        pass

    prompt = build_prompt(doc_contents, existing_nodes)

    print(f"[user-layer] Starting extraction...")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Bash", "Read", "Write", "Glob", "Grep"],
            permission_mode="bypassPermissions",
            cwd=str(REPO_ROOT),
            max_turns=25,
            max_budget_usd=3.0,
            model="sonnet",
            env={
                "CLAUDE_CODE_ENABLE_TELEMETRY": "true",
                "OTEL_EXPORTER_OTLP_ENDPOINT": "https://api.smith.langchain.com/otel",
                "OTEL_EXPORTER_OTLP_HEADERS": f"x-api-key={os.environ.get('CC_LANGSMITH_API_KEY', '')}",
                "OTEL_TRACES_EXPORTER": "otlp",
                "LANGSMITH_PROJECT": "maverick-meta-agents",
            },
        ),
    ):
        if isinstance(message, ResultMessage):
            print(f"[user-layer] Complete.")
            print(f"  Duration: {message.duration_ms / 1000:.1f}s")
            print(f"  Turns: {message.num_turns}")
            print(f"  Cost: ${message.total_cost_usd:.4f}" if message.total_cost_usd else "  Cost: unknown")
            if message.is_error:
                print(f"  ERROR: {message.errors}")
                sys.exit(1)

    # Sync to graph
    if OUTPUT_FILE.exists():
        sync_user_layer(OUTPUT_FILE)
    else:
        print("  No output produced.")


def sync_user_layer(output_file: Path):
    """Sync user layer nodes to FalkorDB."""
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host=os.environ.get("FALKORDB_HOST", "localhost"),
                      port=int(os.environ.get("FALKORDB_PORT", "6380")))
        graph = db.select_graph("asgard")
    except Exception as e:
        print(f"  FalkorDB unavailable: {e}")
        return

    data = json.loads(output_file.read_text())

    def esc(s):
        if s is None: return ""
        return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")

    counts = {"personas": 0, "scenarios": 0, "touchpoints": 0, "pains": 0, "journeys": 0, "links": 0}

    # Personas
    for p in data.get("personas", []):
        pid = esc(p.get("id", ""))
        if not pid: continue
        graph.query(
            f"MERGE (n:Persona {{node_id: '{pid}'}}) "
            f"SET n.label = '{esc(p.get('label', '')[:200])}', "
            f"n.description = '{esc(p.get('description', '')[:300])}', "
            f"n.workflow = '{esc(p.get('workflow', '')[:300])}', "
            f"n.fund_size = '{esc(p.get('fund_size', ''))}', "
            f"n.deal_volume = '{esc(p.get('deal_volume', ''))}', "
            f"n.file_type = 'persona'"
        )
        counts["personas"] += 1

    # Scenarios
    for s in data.get("scenarios", []):
        sid = esc(s.get("id", ""))
        if not sid: continue
        graph.query(
            f"MERGE (n:Scenario {{node_id: '{sid}'}}) "
            f"SET n.label = '{esc(s.get('label', '')[:200])}', "
            f"n.trigger = '{esc(s.get('trigger', '')[:200])}', "
            f"n.context = '{esc(s.get('context', '')[:200])}', "
            f"n.need = '{esc(s.get('need', '')[:200])}', "
            f"n.current_solution = '{esc(s.get('current_solution', '')[:200])}', "
            f"n.frustration = '{esc(s.get('frustration', '')[:200])}', "
            f"n.file_type = 'scenario'"
        )
        # Link to persona
        persona = esc(s.get("affected_persona", ""))
        if persona:
            try:
                graph.query(
                    f"MATCH (sc:Scenario {{node_id: '{sid}'}}), (p:Persona {{node_id: '{persona}'}}) "
                    f"MERGE (p)-[:EXPERIENCES]->(sc)"
                )
            except: pass
        counts["scenarios"] += 1

    # Touchpoints
    for t in data.get("touchpoints", []):
        tid = esc(t.get("id", ""))
        if not tid: continue
        graph.query(
            f"MERGE (n:Touchpoint {{node_id: '{tid}'}}) "
            f"SET n.label = '{esc(t.get('label', '')[:200])}', "
            f"n.channel = '{esc(t.get('channel', ''))}', "
            f"n.direction = '{esc(t.get('direction', ''))}', "
            f"n.file_type = 'touchpoint'"
        )
        counts["touchpoints"] += 1

    # Pains
    for p in data.get("pains", []):
        pid = esc(p.get("id", ""))
        if not pid: continue
        graph.query(
            f"MERGE (n:Pain {{node_id: '{pid}'}}) "
            f"SET n.label = '{esc(p.get('label', '')[:200])}', "
            f"n.severity = '{esc(p.get('severity', ''))}', "
            f"n.evidence = '{esc(p.get('evidence', '')[:300])}', "
            f"n.frequency = '{esc(p.get('frequency', ''))}', "
            f"n.file_type = 'pain'"
        )
        # Link to persona
        persona = esc(p.get("affected_persona", ""))
        if persona:
            try:
                graph.query(
                    f"MATCH (pain:Pain {{node_id: '{pid}'}}), (per:Persona {{node_id: '{persona}'}}) "
                    f"MERGE (per)-[:SUFFERS]->(pain)"
                )
            except: pass
        counts["pains"] += 1

    # Journey edges
    for j in data.get("journey_edges", []):
        src = esc(j.get("source", ""))
        tgt = esc(j.get("target", ""))
        if not src or not tgt: continue
        try:
            graph.query(
                f"MATCH (a:Scenario {{node_id: '{src}'}}), (b:Scenario {{node_id: '{tgt}'}}) "
                f"MERGE (a)-[:LEADS_TO]->(b)"
            )
            counts["journeys"] += 1
        except: pass

    # Links to existing Knowledge/Concept
    for link in data.get("links_to_existing", []):
        uid = esc(link.get("user_node_id", ""))
        eid = esc(link.get("existing_node_id", ""))
        rel = esc(link.get("relation", "ENABLES"))
        if not uid or not eid: continue
        try:
            graph.query(
                f"MATCH (u {{node_id: '{uid}'}}), (e {{node_id: '{eid}'}}) "
                f"MERGE (u)-[:{rel}]->(e)"
            )
            counts["links"] += 1
        except: pass

    # Link Purpose to Personas
    try:
        graph.query(
            "MATCH (pur:Purpose {active: true}), (p:Persona) "
            "MERGE (pur)-[:SERVES]->(p)"
        )
    except: pass

    print(f"  Graph sync: {counts['personas']} personas, {counts['scenarios']} scenarios, "
          f"{counts['touchpoints']} touchpoints, {counts['pains']} pains, "
          f"{counts['journeys']} journeys, {counts['links']} links to existing")


if __name__ == "__main__":
    asyncio.run(main())
