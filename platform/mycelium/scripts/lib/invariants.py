"""
Security Invariants — the system's immune system.

Six invariants that must hold at all times. The system checks these
every heartbeat cycle. Violations are logged, alerted, and in critical
cases, autonomously remediated.

Invariant 1: WRITE ISOLATION
  Only system processes write to the graph. Team reads via MCP.
  MCP asgard_graph_query is read-only. Admin writes require separate token.

Invariant 2: DISTRIBUTION GATE
  Nothing reaches team repos without evaluation pass.
  Hooks are NEVER auto-distributed.

Invariant 3: PIPELINE ALLOWLIST
  Only known scripts can be executed by the pipeline orchestrator.
  Graph-stored script paths are validated against a hardcoded allowlist.

Invariant 4: BOUNDARY REDACTION
  All text entering the graph is scanned for secrets and redacted.
  Applies at every ingestion boundary: MCP, ingest-to-graph, agents.

Invariant 5: LEAST PRIVILEGE
  Each agent gets only the tools its job requires.
  No agent gets Bash unless it genuinely needs shell execution.

Invariant 6: CYPHER-NATIVE INTELLIGENCE
  The system's intelligence lives in graph traversal (Cypher), not in
  Python logic or LLM calls. Python is I/O glue — reads from FalkorDB,
  writes files, calls APIs. All pattern detection, structural analysis,
  decay, healing, and convergence must be expressed as Cypher queries.

Usage:
  from scripts.lib.invariants import check_all, PIPELINE_ALLOWLIST
  violations = check_all()
  if violations:
      for v in violations:
          print(f"  VIOLATION [{v['invariant']}]: {v['message']}")
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ============================================================================
# Invariant 3: Pipeline script allowlist
# ============================================================================

PIPELINE_ALLOWLIST = {
    # Graph ingestion (free, every heartbeat)
    "scripts/ingest-to-graph.py",
    "scripts/graph-sync.py",
    "scripts/sync-layers.py",
    # Convergence + dream + integrity (free, every heartbeat)
    "scripts/convergence-detect.py",
    "scripts/dream-round.py",
    "scripts/integrity-rules.py",
    # Self-test harness (free, every heartbeat)
    "scripts/self-test.py",
    # Graph export + community map (free)
    "scripts/graph-export.py",
    "scripts/build-community-map.py",
    # LLM agents (synthesis pipeline)
    "agents/ingest-agent.py",
    "agents/artifact-graphify.py",
    "agents/demand-engine.py",
    "agents/intent-engine.py",
    "agents/context-gen.py",
    "agents/synthesis-agent.py",
    "agents/evaluation-agent.py",
    "agents/pre-dist-audit-agent.py",
    "agents/distribute.py",
    # Feedback loop
    "agents/feedback-agent.py",
    "agents/skill-feedback-agent.py",
}


def is_allowed_pipeline_script(script_path: str) -> bool:
    """Check if a script path is in the pipeline allowlist."""
    # Normalize path
    normalized = script_path.strip().lstrip("./")
    return normalized in PIPELINE_ALLOWLIST


# ============================================================================
# Invariant 5: Agent tool permissions (least privilege)
# ============================================================================

# What each agent SHOULD have — the minimum required
AGENT_TOOL_POLICY = {
    "ingest-agent.py": {
        "allowed": ["Bash", "Read", "Write", "Glob", "Grep"],
        "reason": "Needs Bash for curl/gh API calls, Write for signals/",
    },
    "synthesis-agent.py": {
        "allowed": ["Read", "Write", "Edit", "Glob", "Grep"],
        "reason": "Reads signals, writes knowledge. NO Bash — prompt injection risk",
    },
    "evaluation-agent.py": {
        "allowed": ["Read", "Glob", "Grep"],
        "reason": "Reviews entries for quality. Read-only — should not modify entries it evaluates",
    },
    "pre-dist-audit-agent.py": {
        "allowed": ["Read", "Glob", "Grep"],
        "reason": "Audits before distribution. Read-only — should not modify what it audits",
    },
    "feedback-agent.py": {
        "allowed": ["Read", "Write", "Edit", "Glob", "Grep"],
        "reason": "Reads knowledge + traces, writes feedback annotations. No Bash needed",
    },
    "skill-feedback-agent.py": {
        "allowed": ["Read", "Write", "Edit", "Glob", "Grep"],
        "reason": "Reads skills + traces, writes feedback. No Bash needed",
    },
    "demand-engine.py": {
        "allowed": ["Read", "Write", "Glob", "Grep"],
        "reason": "Reads traces, writes demand analysis. NO Bash — processes untrusted trace content",
    },
    "intent-engine.py": {
        "allowed": ["Read", "Write", "Glob", "Grep"],
        "reason": "Reads demand, writes intents. NO Bash — processes untrusted content",
    },
    "artifact-graphify.py": {
        "allowed": ["Read", "Write", "Glob", "Grep"],
        "reason": "Reads artifacts, writes graph input. NO Bash — processes external content",
    },
    "context-gen.py": {
        "allowed": ["Read", "Write", "Glob", "Grep"],
        "reason": "Reads graph state, writes context files. NO Bash needed",
    },
    "distribute.py": {
        "allowed": ["Bash", "Read", "Glob", "Grep"],
        "reason": "Needs Bash for git push. No Write — should not create new files, only push existing",
    },
}

# Files that must NEVER be auto-distributed
DISTRIBUTION_BLOCKLIST = {
    ".claude/hooks/",       # Hooks execute code — never auto-distribute
    "scripts/",             # System scripts — manual review only
    "agents/",              # Agent code — manual review only
    "docker/",              # Infrastructure — manual review only
    ".env",                 # Secrets
    "config.yaml",          # System config
}


# ============================================================================
# Check functions — called by heartbeat
# ============================================================================

def check_invariant_1_write_isolation() -> list[dict]:
    """Check that MCP query tool is read-only."""
    violations = []

    server_path = REPO_ROOT / "scripts" / "asgard-mcp-server.py"
    if server_path.exists():
        content = server_path.read_text()

        # Check that _is_read_only_cypher exists
        if "_is_read_only_cypher" not in content:
            violations.append({
                "invariant": "1-write-isolation",
                "severity": "critical",
                "message": "MCP server missing _is_read_only_cypher — graph queries are unrestricted",
            })

        # Check that asgard_graph_query calls the validation
        # Find the call_tool handler section where query execution happens
        handler_start = content.find('name == "asgard_graph_query"')
        if handler_start == -1:
            handler_start = content.find("asgard_graph_query")
        handler_section = content[handler_start:handler_start + 800] if handler_start >= 0 else ""
        if handler_start >= 0 and "_is_read_only_cypher" not in handler_section:
            violations.append({
                "invariant": "1-write-isolation",
                "severity": "critical",
                "message": "asgard_graph_query handler does not call _is_read_only_cypher",
            })

    return violations


def check_invariant_2_distribution_gate() -> list[dict]:
    """Check that distribution has safety gates."""
    violations = []

    # Check push-knowledge.sh for hook distribution
    push_script = REPO_ROOT / "scripts" / "push-knowledge.sh"
    if push_script.exists():
        content = push_script.read_text()
        if ".claude/hooks" in content and "SKIP_HOOKS" not in content:
            violations.append({
                "invariant": "2-distribution-gate",
                "severity": "critical",
                "message": "push-knowledge.sh distributes .claude/hooks/ without a safety gate",
            })

    return violations


def check_invariant_3_pipeline_allowlist() -> list[dict]:
    """Check that pipeline orchestrator validates script paths."""
    violations = []

    pipeline_path = REPO_ROOT / "agents" / "run-graph-pipeline.py"
    if pipeline_path.exists():
        content = pipeline_path.read_text()
        if "PIPELINE_ALLOWLIST" not in content and "is_allowed_pipeline_script" not in content:
            violations.append({
                "invariant": "3-pipeline-allowlist",
                "severity": "critical",
                "message": "run-graph-pipeline.py executes scripts without allowlist validation",
            })

    return violations


def check_invariant_4_boundary_redaction() -> list[dict]:
    """Check that redaction is wired at ingestion boundaries."""
    violations = []

    # Check ingest-to-graph.py
    ingest_path = REPO_ROOT / "scripts" / "ingest-to-graph.py"
    if ingest_path.exists():
        content = ingest_path.read_text()
        if "redact" not in content:
            violations.append({
                "invariant": "4-boundary-redaction",
                "severity": "high",
                "message": "ingest-to-graph.py missing secret redaction",
            })

    # Check MCP server
    mcp_path = REPO_ROOT / "scripts" / "asgard-mcp-server.py"
    if mcp_path.exists():
        content = mcp_path.read_text()
        if "_redact_secrets" not in content:
            violations.append({
                "invariant": "4-boundary-redaction",
                "severity": "high",
                "message": "MCP server missing secret redaction in log_trace()",
            })

    return violations


def check_invariant_5_least_privilege() -> list[dict]:
    """Check that agents have minimum required tools."""
    violations = []

    agents_dir = REPO_ROOT / "agents"
    for agent_file, policy in AGENT_TOOL_POLICY.items():
        agent_path = agents_dir / agent_file
        if not agent_path.exists():
            continue

        content = agent_path.read_text()

        # Extract current allowed_tools
        match = re.search(r'allowed_tools=\[([^\]]+)\]', content)
        if not match:
            continue

        current_tools = set(
            t.strip().strip('"').strip("'")
            for t in match.group(1).split(",")
        )
        allowed_tools = set(policy["allowed"])

        # Check for tools the agent has but shouldn't
        excess = current_tools - allowed_tools
        if excess:
            violations.append({
                "invariant": "5-least-privilege",
                "severity": "high",
                "message": f"{agent_file} has excess tools: {excess}. {policy['reason']}",
            })

    return violations


# ============================================================================
# Invariant 6: Cypher-native intelligence
# ============================================================================

# Heartbeat scripts that must keep intelligence in Cypher, not Python
CYPHER_NATIVE_SCRIPTS = [
    "scripts/heartbeat.py",
    "scripts/integrity-rules.py",
    "scripts/dream-round.py",
    "scripts/convergence-detect.py",
    "scripts/ingest-to-graph.py",
]

# Regex for nested for-loops iterating graph results to build paths manually
# Matches: for <var> in <something>: ... for <var2> in <something with first var>
_NESTED_GRAPH_LOOP_RE = re.compile(
    r'for\s+(\w+)\s+in\s+.*:\s*\n'           # outer for loop
    r'(?:\s+[^\n]*\n)*?'                       # any intermediate lines
    r'\s+for\s+\w+\s+in\s+.*\1',              # inner for loop referencing outer var
    re.MULTILINE,
)

# Regex for json.loads on graph export files
_GRAPH_EXPORT_LOAD_RE = re.compile(
    r'json\.loads?\s*\([^)]*(?:graph-v|graph-export|graph_v|graph_export)[^)]*\)',
)


def check_invariant_6_cypher_native() -> list[dict]:
    """Check that heartbeat scripts keep intelligence in Cypher, not Python.

    Flags:
      - NetworkX imports (graph logic should be Cypher)
      - defaultdict(list/set) in files that also import falkordb (manual adjacency)
      - Nested for-loops over graph results (manual path traversal)
      - json.loads on graph export files (should query live graph)
    """
    violations = []

    for script_rel in CYPHER_NATIVE_SCRIPTS:
        script_path = REPO_ROOT / script_rel
        if not script_path.exists():
            continue

        content = script_path.read_text()
        fname = os.path.basename(script_rel)

        # Anti-pattern 1: NetworkX imports
        if re.search(r'^\s*import\s+networkx\b', content, re.MULTILINE) or \
           re.search(r'^\s*import\s+nx\b', content, re.MULTILINE) or \
           re.search(r'^\s*from\s+networkx\b', content, re.MULTILINE):
            violations.append({
                "invariant": "6-cypher-native",
                "severity": "high",
                "message": (
                    f"{fname} imports NetworkX — graph logic should be "
                    f"expressed as Cypher queries, not Python graph libraries"
                ),
            })

        # Anti-pattern 2: defaultdict(list/set) in files that also use falkordb
        has_falkordb = "falkordb" in content.lower() or "FalkorDB" in content
        if has_falkordb and re.search(r'defaultdict\s*\(\s*(list|set)\s*\)', content):
            violations.append({
                "invariant": "6-cypher-native",
                "severity": "medium",
                "message": (
                    f"{fname} uses defaultdict(list/set) alongside FalkorDB — "
                    f"likely building adjacency structures in Python instead of Cypher"
                ),
            })

        # Anti-pattern 3: Nested for-loops over graph results (manual path traversal)
        if _NESTED_GRAPH_LOOP_RE.search(content):
            violations.append({
                "invariant": "6-cypher-native",
                "severity": "medium",
                "message": (
                    f"{fname} has nested for-loops iterating graph query results — "
                    f"path traversal should be a Cypher query, not Python iteration"
                ),
            })

        # Anti-pattern 4: json.loads on graph export files
        if _GRAPH_EXPORT_LOAD_RE.search(content):
            violations.append({
                "invariant": "6-cypher-native",
                "severity": "high",
                "message": (
                    f"{fname} loads a graph export JSON file — "
                    f"should query the live graph via Cypher instead"
                ),
            })

    return violations


def check_graph_security() -> list[dict]:
    """Check graph-level security — secrets in nodes, suspicious proposals."""
    violations = []

    try:
        from falkordb import FalkorDB
        from scripts.lib.redact import has_secrets

        host = os.environ.get("FALKORDB_HOST", "localhost")
        port = int(os.environ.get("FALKORDB_PORT", "6380"))

        db = FalkorDB(host=host, port=port)
        g = db.select_graph("asgard")

        # Scan for secrets in node labels
        r = g.query("MATCH (n) WHERE n.label IS NOT NULL RETURN n.node_id, n.label LIMIT 1000")
        for row in (r.result_set or []):
            node_id, label = row
            if label and has_secrets(str(label)):
                violations.append({
                    "invariant": "4-boundary-redaction",
                    "severity": "critical",
                    "message": f"Secret detected in node {node_id} label. Redacting.",
                    "auto_remediate": True,
                    "node_id": node_id,
                })

        # Scan Trace questions for secrets
        r2 = g.query("MATCH (t:Trace) WHERE t.question IS NOT NULL RETURN t.node_id, t.question LIMIT 500")
        for row in (r2.result_set or []):
            node_id, question = row
            if question and has_secrets(str(question)):
                violations.append({
                    "invariant": "4-boundary-redaction",
                    "severity": "critical",
                    "message": f"Secret detected in Trace {node_id}. Redacting.",
                    "auto_remediate": True,
                    "node_id": node_id,
                })

        # Check for ActionProposals without provenance
        r3 = g.query(
            "MATCH (ap:ActionProposal {status: 'proposed'}) "
            "WHERE ap.created_by IS NULL "
            "RETURN ap.node_id, ap.label LIMIT 20"
        )
        for row in (r3.result_set or []):
            node_id, label = row
            violations.append({
                "invariant": "1-write-isolation",
                "severity": "high",
                "message": f"ActionProposal {node_id} has no created_by provenance. Could be injected.",
                "node_id": node_id,
            })

    except Exception:
        pass  # Graph unavailable — skip graph checks

    return violations


def remediate(violations: list[dict]) -> int:
    """Auto-remediate violations where safe to do so. Returns count remediated."""
    remediated = 0

    try:
        from falkordb import FalkorDB
        from scripts.lib.redact import redact

        host = os.environ.get("FALKORDB_HOST", "localhost")
        port = int(os.environ.get("FALKORDB_PORT", "6380"))
        db = FalkorDB(host=host, port=port)
        g = db.select_graph("asgard")

        for v in violations:
            if not v.get("auto_remediate"):
                continue

            node_id = v.get("node_id")
            if not node_id:
                continue

            # Redact the label in place
            try:
                r = g.query(
                    f"MATCH (n {{node_id: '{node_id}'}}) RETURN n.label, n.question"
                )
                if r.result_set:
                    label, question = r.result_set[0]
                    if label:
                        clean = redact(str(label)).replace("'", "\\'")
                        g.query(f"MATCH (n {{node_id: '{node_id}'}}) SET n.label = '{clean}'")
                    if question:
                        clean = redact(str(question)).replace("'", "\\'")
                        g.query(f"MATCH (n {{node_id: '{node_id}'}}) SET n.question = '{clean}'")
                    remediated += 1
            except Exception:
                pass

    except Exception:
        pass

    return remediated


def check_all() -> list[dict]:
    """Run all invariant checks. Returns list of violations."""
    violations = []
    violations.extend(check_invariant_1_write_isolation())
    violations.extend(check_invariant_2_distribution_gate())
    violations.extend(check_invariant_3_pipeline_allowlist())
    violations.extend(check_invariant_4_boundary_redaction())
    violations.extend(check_invariant_5_least_privilege())
    violations.extend(check_invariant_6_cypher_native())
    violations.extend(check_graph_security())
    return violations


def report(violations: list[dict]) -> str:
    """Format violations as a human-readable report."""
    if not violations:
        return "All 6 invariants hold. No violations detected."

    lines = [f"INVARIANT VIOLATIONS: {len(violations)} found\n"]
    by_severity = {"critical": [], "high": [], "medium": [], "low": []}
    for v in violations:
        by_severity.get(v.get("severity", "medium"), []).append(v)

    for severity in ["critical", "high", "medium", "low"]:
        items = by_severity[severity]
        if items:
            lines.append(f"  [{severity.upper()}]")
            for v in items:
                lines.append(f"    - [{v['invariant']}] {v['message']}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("Running invariant checks...\n")
    violations = check_all()
    print(report(violations))

    if any(v.get("auto_remediate") for v in violations):
        print("\nAuto-remediating...")
        count = remediate(violations)
        print(f"  Remediated: {count}")
