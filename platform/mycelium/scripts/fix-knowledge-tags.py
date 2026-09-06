#!/usr/bin/env python3
"""
Fix Knowledge.tags — the neurotransmitter.

102/103 Knowledge nodes have null/empty tags. The entire digestion pipeline
(connect protocol, 15 IngestionRules, contradiction resolver) depends on
tag-based matching. This script generates tags from each node's label,
category, and community context, then SETs them.

Python is I/O glue. The tag generation logic is simple keyword extraction.
"""

import os
import sys
from falkordb import FalkorDB

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


# Tag mappings: node_id -> comma-separated tags
# Generated from label analysis, grouped by community
TAGS = {
    # Community -1: Meta/design
    "graph-native-system-design": "graph, cypher, system design, falkordb, knowledge graph, graph-native, topology",
    "patterns-spec-reading-guides": "spec-to-ship, specs, reading-guide, documentation, code-review, technical-writing, playbook",

    # Community 0: Agent harness, memory layer, workflow orchestration
    "agent_harness_decisions": "agent, harness, vercel, trigger.dev, orchestration, AI SDK",
    "agent_harness_crewai_rejected": "crewai, autogen, agent framework, rejected, multi-agent",
    "cross_channel_continuity_work_unit_members": "cross-channel, continuity, slack, email, work-unit, members",
    "memory_layer_falkordb": "falkordb, graph database, memory, redis, knowledge graph",
    "memory_layer_graphiti": "graphiti, knowledge graph, self-hosted, memory layer",
    "cost_optimization_patterns": "cost optimization, tokens, multi-agent, pipeline, splitting",
    "agent_harness_langgraph_rejected": "langgraph, rejected, python, agent framework, abstraction",
    "memory_layer_decisions": "memory layer, architecture, falkordb, pgvector, decisions",
    "memory_layer_rationale_falkordb": "falkordb, neo4j, memory, performance, rationale",
    "cost_optimization_rationale": "cost optimization, tokens, context, sub-task, rationale",
    "trigger_dev_vs_temporal_rationale_managed_workers": "trigger.dev, temporal, workers, managed, rationale",
    "trigger_dev_vs_temporal_rationale_v3_shutdown": "trigger.dev, migration, shutdown, rationale",
    "agent_harness_rationale": "typescript, streaming, agent, lightweight, rationale",
    "cross_channel_continuity_rationale": "cross-channel, work-unit, members, rationale, workflow",
    "memory_layer_rationale_zep_rejected": "memory, rejected, async, deadlocks, reliability",
    "memory_layer_rls": "row-level security, fund_id, tenant isolation, multi-tenant, security",
    "trigger_dev_vs_temporal_temporal": "temporal, workflow, orchestration, rejected",
    "trigger_dev_vs_temporal_trigger_dev_v4": "trigger.dev, workflow, orchestration, serverless",
    "trigger_dev_vs_temporal_decision": "trigger.dev, temporal, architecture decision, workflow",
    "agent_harness_vercel_ai_sdk": "vercel, AI SDK, agent, orchestration, streaming",
    "cross_channel_continuity_members_table": "continuity, members, table, schema, database",
    "cross_channel_continuity_contexts_table": "continuity, contexts, table, schema, database",
    "memory_layer_pgvector": "pgvector, semantic search, embeddings, vector, postgresql",

    # Community 1: Product architecture, fund config, FSD
    "configurable_per_fund_pattern": "configurable, per-fund, multi-tenant, architecture, fund configuration",
    "cycle_log_cycle_log": "cycle log, ingest, synthesize, distribute, ledger, pipeline",
    "fsd_audit_deal_research_repo": "deal research, repository, service provider, wiring, audit",
    "fsd_audit_critical_issues": "FSD, architecture audit, critical issues, frontend",
    "fsd_audit_layer_inversion": "FSD, layer inversion, shared, widgets, imports, audit",
    "fixture_first_development": "fixture, development, testing, frontend, backend",
    "production_readiness_fixture_backend": "fixture, backend, database, API calls, production",
    "fsd_audit_god_components": "god components, LOC, refactoring, code quality, audit",
    "configurable_per_fund_jsonb": "JSONB, fund configuration, extensible, postgresql, schema",
    "phase1_decisions_mcp_server": "MCP server, MVP, tools, read-only, sprint",
    "research_to_product_positioning_bridge": "positioning, market research, product, bridge, competitive",
    "phase1_decisions_pass_decision": "pass decision, decline, fund learning, deal flow, pipeline",
    "phase1_decisions_settled": "phase 1, architecture decisions, settled, foundation",
    "production_readiness_gap": "production readiness, gap analysis, deployment, infrastructure",
    "fixture_first_rationale": "fixture, frontend velocity, backend, decoupled, rationale",
    "configurable_per_fund_rationale": "configurable, multi-tenant, fund, flexibility, rationale",
    "research_to_product_pipeline": "research, product, pipeline, market research, competitive intelligence",
    "fixture_first_service_provider": "service provider, react context, dependency injection, fixture swap",

    # Community 2: Security, infra, tech stack
    "security_scanning_coraza": "coraza, OWASP, WAF, security, web application firewall",
    "tech_stack_coolify": "docker, coolify, deployment, infrastructure, self-hosted",
    "tech_stack_drizzle": "drizzle, ORM, database, schema, typescript",
    "tech_stack_completed": "tech stack, services, settled, infrastructure, architecture",
    "security_scanning_infisical": "infisical, secrets, management, self-hosted, security",
    "tech_stack_keycloak": "keycloak, authentication, self-hosted, security, OAuth",
    "tech_stack_nango": "nango, OAuth, integrations, connectors, self-hosted",
    "security_scanning_owasp_zap": "OWASP ZAP, DAST, security scanning, deferred",
    "tech_stack_postgrest": "PostgREST, CRUD, API, REST, auto-generated",
    "security_scanning_rationale_oss": "OSS, self-hosted, on-prem, enterprise, rationale",
    "tech_stack_rationale_onprem": "on-premises, enterprise, deployment, OSS, rationale",
    "tech_stack_rationale_postgrest": "PostgREST, tRPC, REST, universal, rationale",
    "security_scanning_stack": "security stack, secrets, scanning, semgrep, trivy",
    "security_scanning_semgrep": "semgrep, SAST, static analysis, security scanning",
    "security_scanning_trivy": "trivy, CVE scanning, dependencies, security, container",

    # Community 3: Hooks, telemetry, context, research tools
    "auto_sync_hooks": "auto-sync, hooks, git push, git pull, invisible",
    "hooks_data_capture": "hooks, data capture, PostToolUse, claude code, telemetry",
    "concept_heimdall_gate": "heimdall, evaluation gate, quality, distribution, guard",
    "langsmith_tracing_setup": "langsmith, tracing, claude code, setup, monitoring",
    "auto_sync_rationale": "auto-sync, push friction, visibility, rationale",
    "hooks_data_capture_rationale": "hooks, data collection, analysis, decoupled, rationale",
    "rules_loaded_rationale": "telemetry, hook, distribution, verification, rationale",
    "research_tools_catalog": "research tools, xpoz, twitter, youtube, linkedin, searxng",
    "rules_loaded_telemetry": "rules-loaded, telemetry, hook, SessionStart, verification",
    "concept_smart_context_hook": "smart context, hook, injection, claude code, context",
    "meta_system_effectiveness": "effectiveness, tracking, system, metrics, evaluation",
    "research_tools_twitterapi": "twitter, API, keyword search, social media, research",
    "research_tools_xpoz": "xpoz, social media, research, MCP, practitioner",

    # Community 4: Knowledge base, workflows
    "workflow_active_email_redesign": "email, redesign, workflow, active, frontend",
    "antipattern_keyword_search_noise": "keyword search, noise, social media, antipattern, signal",
    "meta_lint_report": "knowledge base, lint, report, quality, validation",
    "workflow_parallel_workstream": "parallel, workstream, research, concurrent",
    "concept_practitioner_accounts": "practitioner, accounts, data collection, social media",
    "pattern_rapid_api_pivot": "API pivot, failure, rapid, fallback, resilience",
    "search_index": "search index, knowledge base, lookup, keywords",
    "concept_parallel_workstream_split": "workstream, split, skills, parallel, delegation",
    "knowledge_index": "knowledge base, index, team, catalog",

    # Community 5: Market research, competitive intelligence
    "knowledge-brand-competitor-mapping": "brand name, competitor, mapping, market research, G2",
    "pattern_competitor_research_dataset": "competitor, research, dataset, brands, market research",
    "meta_evaluation_log": "evaluation, log, distribution, quality, tracking",
    "concept_issue_ledger": "github issues, research, ledger, tracking",
    "pattern_issue_driven_research": "issue-driven, research, tracking, methodology",
    "knowledge-market-research-data-schema": "market research, data schema, tagged, ingestion, evidence",
    "concept_or_and_group_logic": "OR logic, AND logic, group, filter, rule builder",
    "pattern_rule_builder_group_logic": "rule builder, group logic, within-group, across-groups, filter",
    "knowledge-workflow-fc-mapping": "workflow, feature category, mapping, market research",

    # Community 6: Architecture validation, research methodology
    "workflow_architecture_validation": "architecture validation, multi-agent, research, decisions",
    "pattern_expert_panel_validation": "expert panel, validation, tech decisions, review",
    "concept_multi_agent_research": "multi-agent, parallel research, architecture, validation",
    "pattern_research_driven_arch": "research-driven, architecture, decisions, methodology",
    "concept_social_media_verification": "social media, verification, practitioner, credibility",

    # Community 7: Claude Code, quality gates, design system
    "concept_quality_gates": "quality gates, automated, CI, testing, enforcement",
    "pattern_claude_code_agent_builder": "claude code, agent, builder, primary, development",
    "pattern_design_system_enforcement": "design system, enforcement, drift, consistency, frontend",
    "concept_esLint_enforcement": "eslint, design tokens, enforcement, linting, frontend",

    # Community 8: Memory alternatives (rejected)
    "concept_graphiti_oss": "graphiti, OSS, self-hosted, knowledge graph, alternative",
    "concept_zep_cloud": "cloud, managed service, memory, alternative",
    "antipattern_zep_cloud_reliability": "cloud, reliability, production, deadlocks, antipattern",

    # Community null: Operational mappings
    "knowledge-domain-fc-mapping": "intent domain, feature category, mapping, demand, routing",
    "pattern-remote-graph-write": "remote graph, write, script, inline, pattern",
}


def esc(s):
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:500]


def main():
    graph = get_graph()

    # Verify current state
    r = graph.query("MATCH (k:Knowledge) WHERE k.tags IS NOT NULL AND k.tags <> '' RETURN count(k)")
    before = r.result_set[0][0]
    print(f"Knowledge nodes with tags BEFORE: {before}/103")

    updated = 0
    skipped = 0
    errors = 0

    for node_id, tags in TAGS.items():
        try:
            graph.query(
                f"MATCH (k:Knowledge {{node_id: '{esc(node_id)}'}}) "
                f"SET k.tags = '{esc(tags)}' "
                f"RETURN k.node_id"
            )
            updated += 1
        except Exception as e:
            print(f"  ERROR {node_id}: {e}")
            errors += 1

    # Verify after
    r = graph.query("MATCH (k:Knowledge) WHERE k.tags IS NOT NULL AND k.tags <> '' RETURN count(k)")
    after = r.result_set[0][0]
    print(f"Knowledge nodes with tags AFTER: {after}/103")
    print(f"Updated: {updated}, Skipped: {skipped}, Errors: {errors}")

    # Now test the connect protocol — using UNWIND instead of ANY()
    # FalkorDB quirk: ANY() with CONTAINS on large strings fails silently.
    # UNWIND + explicit filter works.
    print("\n--- Testing connect protocol (UNWIND approach) ---")
    r = graph.query("MATCH (t:Trace) WHERE t._digested IS NULL RETURN count(t)")
    undigested = r.result_set[0][0]
    print(f"Undigested traces: {undigested}")

    # Preview matches
    r = graph.query(
        "MATCH (t:Trace) WHERE t._digested IS NULL AND t.question IS NOT NULL "
        "MATCH (k:Knowledge) WHERE k.tags IS NOT NULL "
        "WITH t, k, split(k.tags, ', ') AS tags "
        "UNWIND tags AS tag "
        "WITH t, k, tag WHERE toLower(t.question) CONTAINS tag AND size(tag) > 4 "
        "RETURN substring(t.label, 0, 60) AS trace, k.label AS knowledge, collect(tag) AS matched_tags "
        "LIMIT 30"
    )
    print(f"Connect matches found: {len(r.result_set)}")
    for row in r.result_set:
        print(f"  {row[0]} -> {row[1]} via {row[2]}")

    # Actually wire them
    print("\n--- Wiring traces to Knowledge ---")
    r = graph.query(
        "MATCH (t:Trace) WHERE t._digested IS NULL AND t.question IS NOT NULL "
        "MATCH (k:Knowledge) WHERE k.tags IS NOT NULL "
        "WITH t, k, split(k.tags, ', ') AS tags "
        "UNWIND tags AS tag "
        "WITH t, k, tag WHERE toLower(t.question) CONTAINS tag AND size(tag) > 4 "
        "WITH DISTINCT t, k "
        "MERGE (t)-[:TOUCHES]->(k) "
        "WITH DISTINCT t SET t._digested = true "
        "RETURN count(t) AS connected"
    )
    connected = r.result_set[0][0] if r.result_set else 0
    print(f"Traces connected: {connected}")

    # Check remaining undigested
    r = graph.query("MATCH (t:Trace) WHERE t._digested IS NULL RETURN count(t)")
    remaining = r.result_set[0][0]
    print(f"Remaining undigested: {remaining}")

    # Run IngestionRule for undigested Issues
    print("\n--- Testing Issue ingestion rule (UNWIND) ---")
    r = graph.query(
        "MATCH (i:Issue) WHERE i._digested IS NULL AND i.label IS NOT NULL "
        "MATCH (k:Knowledge) WHERE k.tags IS NOT NULL "
        "WITH i, k, split(k.tags, ', ') AS tags "
        "UNWIND tags AS tag "
        "WITH i, k, tag WHERE toLower(i.label) CONTAINS tag AND size(tag) > 4 "
        "WITH DISTINCT i, k "
        "MERGE (i)-[:RELATES_TO]->(k) "
        "WITH DISTINCT i SET i._digested = true "
        "RETURN count(i) AS linked"
    )
    linked_issues = r.result_set[0][0] if r.result_set else 0
    print(f"Issues linked to Knowledge: {linked_issues}")

    # Run Knowledge-to-Knowledge wiring
    print("\n--- Testing Knowledge-to-Knowledge wiring (UNWIND) ---")
    r = graph.query(
        "MATCH (a:Knowledge), (b:Knowledge) "
        "WHERE a.node_id < b.node_id AND a.tags IS NOT NULL AND b.tags IS NOT NULL "
        "WITH a, b, split(a.tags, ', ') AS a_tags "
        "UNWIND a_tags AS tag "
        "WITH a, b, tag WHERE b.tags CONTAINS tag AND size(tag) > 4 "
        "WITH a, b, count(tag) AS shared_tags "
        "WHERE shared_tags >= 3 "
        "MERGE (a)-[:CONCEPTUALLY_RELATED_TO]->(b) "
        "RETURN count(*) AS linked"
    )
    k2k = r.result_set[0][0] if r.result_set else 0
    print(f"Knowledge-to-Knowledge links created: {k2k}")

    # Summary
    print("\n=== DIGESTION FIX SUMMARY ===")
    print(f"Tags populated: {before} -> {after} Knowledge nodes")
    print(f"Traces wired to Knowledge: {connected}")
    print(f"Issues wired to Knowledge: {linked_issues}")
    print(f"Knowledge-to-Knowledge links: {k2k}")
    print(f"Remaining undigested traces: {remaining}")


if __name__ == "__main__":
    main()
