#!/usr/bin/env python3
"""
Seed the system's own structure into the graph.

Everything that IS the system lives as graph nodes:
- Invariant nodes (the rules)
- AgentPolicy nodes (least privilege)
- AllowedScript nodes (pipeline allowlist)
- TestCase nodes (self-testing)

This script is idempotent (uses MERGE). Run it whenever
the system's structure changes.

Invariant 7: Graph-Native System State —
if it's not in the graph, it doesn't exist to the system.
"""

import os
import sys

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def esc(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:500]


def main():
    from falkordb import FalkorDB
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    g = db.select_graph("asgard")

    # ================================================================
    # INVARIANT NODES
    # ================================================================

    invariants = [
        (1, "Write Isolation", "Only system processes write to the graph. MCP queries are read-only. Admin writes require separate token."),
        (2, "Distribution Gate", "Nothing reaches team repos without evaluation. Hooks are NEVER auto-distributed."),
        (3, "Pipeline Allowlist", "Only known scripts can execute. Graph-stored paths validated against allowlist."),
        (4, "Boundary Redaction", "All text entering the graph is scanned for secrets and redacted at every boundary."),
        (5, "Least Privilege", "Each agent gets only the tools its job requires. No Bash unless genuinely needed."),
        (6, "Cypher-Native Intelligence", "Intelligence lives in graph traversal. Python is I/O glue. No NetworkX, no manual adjacency."),
        (7, "Graph-Native System State", "All system knowledge, config, tests, and invariants live as graph nodes. If it is not in the graph, it does not exist to the system."),
    ]

    for num, label, description in invariants:
        nid = f"invariant-{num}"
        g.query(
            f"MERGE (inv:Invariant {{node_id: '{esc(nid)}'}}) "
            f"SET inv.label = 'Invariant {num}: {esc(label)}', "
            f"inv.number = {num}, "
            f"inv.description = '{esc(description)}', "
            f"inv.status = 'enforced', "
            f"inv.file_type = 'invariant'"
        )

    print(f"  Invariants: {len(invariants)} nodes")

    # ================================================================
    # AGENT TOOL POLICY NODES
    # ================================================================

    policies = [
        ("ingest-agent", ["Bash", "Read", "Write", "Glob", "Grep"], "Needs Bash for curl/gh API calls"),
        ("synthesis-agent", ["Read", "Write", "Edit", "Glob", "Grep"], "NO Bash — prompt injection risk"),
        ("evaluation-agent", ["Read", "Glob", "Grep"], "Read-only — should not modify what it evaluates"),
        ("pre-dist-audit-agent", ["Read", "Glob", "Grep"], "Read-only — should not modify what it audits"),
        ("feedback-agent", ["Read", "Write", "Edit", "Glob", "Grep"], "No Bash needed"),
        ("skill-feedback-agent", ["Read", "Write", "Edit", "Glob", "Grep"], "No Bash needed"),
        ("demand-engine", ["Read", "Write", "Glob", "Grep"], "NO Bash — processes untrusted content"),
        ("intent-engine", ["Read", "Write", "Glob", "Grep"], "NO Bash — processes untrusted content"),
        ("artifact-graphify", ["Read", "Write", "Glob", "Grep"], "NO Bash — processes external content"),
        ("context-gen", ["Read", "Write", "Glob", "Grep"], "NO Bash — reads graph, writes context"),
        ("distribute", ["Bash", "Read", "Glob", "Grep"], "Needs Bash for git push"),
    ]

    for agent, tools, reason in policies:
        nid = f"policy-{agent}"
        tools_str = ", ".join(tools)
        g.query(
            f"MERGE (p:AgentPolicy {{node_id: '{esc(nid)}'}}) "
            f"SET p.label = '{esc(agent)} tool policy', "
            f"p.agent = '{esc(agent)}', "
            f"p.allowed_tools = '{esc(tools_str)}', "
            f"p.reason = '{esc(reason)}', "
            f"p.file_type = 'agent-policy'"
        )
        g.query(
            f"MATCH (p:AgentPolicy {{node_id: '{esc(nid)}'}}), "
            f"(inv:Invariant {{node_id: 'invariant-5'}}) "
            f"MERGE (p)-[:ENFORCES]->(inv)"
        )

    print(f"  AgentPolicies: {len(policies)} nodes")

    # ================================================================
    # PIPELINE ALLOWLIST NODES
    # ================================================================

    allowed_scripts = [
        "scripts/ingest-to-graph.py", "scripts/graph-sync.py", "scripts/sync-layers.py",
        "scripts/convergence-detect.py", "scripts/dream-round.py", "scripts/integrity-rules.py",
        "scripts/graph-export.py", "scripts/build-community-map.py",
        "agents/ingest-agent.py", "agents/artifact-graphify.py",
        "agents/demand-engine.py", "agents/intent-engine.py",
        "agents/context-gen.py", "agents/synthesis-agent.py",
        "agents/evaluation-agent.py", "agents/pre-dist-audit-agent.py",
        "agents/distribute.py", "agents/feedback-agent.py",
        "agents/skill-feedback-agent.py",
    ]

    for script in allowed_scripts:
        nid = f"allowed-script-{script.replace('/', '-').replace('.py', '')}"
        g.query(
            f"MERGE (s:AllowedScript {{node_id: '{esc(nid)}'}}) "
            f"SET s.label = '{esc(script)}', "
            f"s.script_path = '{esc(script)}', "
            f"s.file_type = 'allowed-script'"
        )
        g.query(
            f"MATCH (s:AllowedScript {{node_id: '{esc(nid)}'}}), "
            f"(inv:Invariant {{node_id: 'invariant-3'}}) "
            f"MERGE (s)-[:ENFORCES]->(inv)"
        )

    print(f"  AllowedScripts: {len(allowed_scripts)} nodes")

    # ================================================================
    # TEST CASE NODES — the system tests itself through Cypher
    # ================================================================

    tests = [
        {
            "id": "test-redaction-catches-github-pat",
            "label": "Secret redaction catches GitHub PAT in node labels",
            "mechanism": "invariant-4",
            "setup": "CREATE (n:_TestNode {node_id: '_test-secret-1', label: 'token ghp_abcdefghijklmnopqrstuvwxyz1234567890', file_type: '_test'})",
            "assertion": "MATCH (n {node_id: '_test-secret-1'}) WHERE n.label CONTAINS 'ghp_' RETURN count(n)",
            "expected": "0",
            "teardown": "MATCH (n) WHERE n.node_id STARTS WITH '_test-' DETACH DELETE n",
        },
        {
            "id": "test-proposal-requires-provenance",
            "label": "ActionProposals without created_by are not executed by L7",
            "mechanism": "invariant-1",
            "setup": "CREATE (ap:ActionProposal {node_id: '_test-orphan-proposal', status: 'proposed', label: 'test orphan', file_type: 'action-proposal'})",
            "assertion": "MATCH (d:Dream)-[:PROPOSED]->(ap:ActionProposal {node_id: '_test-orphan-proposal'}) RETURN count(d)",
            "expected": "0",
            "teardown": "MATCH (n {node_id: '_test-orphan-proposal'}) DETACH DELETE n",
        },
        {
            "id": "test-coupling-event-decay",
            "label": "CouplingEvents older than 7 days are pruned by integrity",
            "mechanism": "integrity-rule-6",
            "setup": "CREATE (e:CouplingEvent {node_id: '_test-old-ce', timestamp: '2020-01-01T00:00:00', file_type: 'coupling'})",
            "assertion": "MATCH (e:CouplingEvent {node_id: '_test-old-ce'}) RETURN count(e)",
            "expected": "0",
            "teardown": "MATCH (n {node_id: '_test-old-ce'}) DETACH DELETE n",
        },
        {
            "id": "test-workitem-unblocked-detection",
            "label": "Dream round detects unblocked WorkItems with no dependencies",
            "mechanism": "dream-workplan",
            "setup": "CREATE (w:WorkItem {node_id: '_test-wi-ready', label: 'Test ready', status: 'open', effort: 'small', file_type: 'workitem'})",
            "assertion": "MATCH (w:WorkItem {node_id: '_test-wi-ready', status: 'open'}) OPTIONAL MATCH (w)-[:DEPENDS_ON]->(dep:WorkItem) WHERE dep.status <> 'done' WITH w, count(dep) AS blocking WHERE blocking = 0 RETURN count(w)",
            "expected": "1",
            "teardown": "MATCH (n {node_id: '_test-wi-ready'}) DETACH DELETE n",
        },
        {
            "id": "test-workitem-blocked-not-surfaced",
            "label": "WorkItems with open dependencies stay blocked",
            "mechanism": "dream-workplan",
            "setup": "CREATE (w:WorkItem {node_id: '_test-wi-blocked', label: 'Blocked', status: 'open', file_type: 'workitem'}) CREATE (d:WorkItem {node_id: '_test-wi-blocker', label: 'Blocker', status: 'open', file_type: 'workitem'})",
            "assertion": "MATCH (w:WorkItem {node_id: '_test-wi-blocked'})-[:DEPENDS_ON]->(dep:WorkItem {node_id: '_test-wi-blocker'}) WHERE dep.status <> 'done' RETURN count(w)",
            "expected": "1",
            "teardown": "MATCH (n) WHERE n.node_id IN ['_test-wi-blocked', '_test-wi-blocker'] DETACH DELETE n",
        },
        {
            "id": "test-invariant-nodes-exist",
            "label": "All 7 invariant nodes exist in the graph",
            "mechanism": "invariant-7",
            "setup": "",
            "assertion": "MATCH (inv:Invariant) RETURN count(inv)",
            "expected": "7",
            "teardown": "",
        },
        {
            "id": "test-agent-policies-exist",
            "label": "All agent policy nodes exist in the graph",
            "mechanism": "invariant-7",
            "setup": "",
            "assertion": "MATCH (p:AgentPolicy) RETURN count(p)",
            "expected": "11",
            "teardown": "",
        },
        {
            "id": "test-test-cases-exist",
            "label": "TestCase nodes exist — the system can test itself",
            "mechanism": "invariant-7",
            "setup": "",
            "assertion": "MATCH (tc:TestCase) RETURN count(tc)",
            "expected": "8",
            "teardown": "",
        },
    ]

    for t in tests:
        nid = t["id"]
        g.query(
            f"MERGE (tc:TestCase {{node_id: '{esc(nid)}'}}) "
            f"SET tc.label = '{esc(t['label'])}', "
            f"tc.mechanism = '{esc(t['mechanism'])}', "
            f"tc.setup_cypher = '{esc(t['setup'])}', "
            f"tc.assertion_cypher = '{esc(t['assertion'])}', "
            f"tc.expected = '{esc(t['expected'])}', "
            f"tc.teardown_cypher = '{esc(t['teardown'])}', "
            f"tc.file_type = 'test-case'"
        )
        # Link to invariant if applicable
        if t["mechanism"].startswith("invariant-"):
            g.query(
                f"MATCH (tc:TestCase {{node_id: '{esc(nid)}'}}), "
                f"(inv:Invariant {{node_id: '{esc(t['mechanism'])}'}}) "
                f"MERGE (tc)-[:TESTS]->(inv)"
            )

    print(f"  TestCases: {len(tests)} nodes")

    # ================================================================
    # SUMMARY
    # ================================================================

    r = g.query("MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC")
    print("\nGraph topology:")
    for row in r.result_set:
        print(f"  {row[0]}: {row[1]}")

    total = g.query("MATCH (n) RETURN count(n)").result_set[0][0]
    edges = g.query("MATCH ()-[r]->() RETURN count(r)").result_set[0][0]
    print(f"\nTotal: {total} nodes, {edges} edges")
    print("The system IS the graph.")


if __name__ == "__main__":
    main()
