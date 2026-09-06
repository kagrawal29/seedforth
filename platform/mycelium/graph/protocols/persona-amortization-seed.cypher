// @kind: seed
/*
  SEED PROTOCOL: Persona + Amortization Layer

  Introduces two intertwined graph layers:

  1. :Persona layer — first-class nodes modeling subagent personas with cost budgets,
     system prompts, model preferences, and dense wiring to Skills, Commands, TestCases,
     and historical Subagents via INSTANCE_OF edges.

  2. Amortization layer — tracks author cost and reuse on :Skill and :Protocol nodes,
     enabling visibility into which protocols have paid for themselves through repeated use.

  Dense connections:
  - Each Persona wired to Model, Ontology, and historical Subagents
  - All Protocols and Skills enriched with cost fields for economic visibility
  - CostEstimate rollup nodes aggregate persona spend from historical subagent runs
  - New Concepts added to ontology: Persona, Amortization, CostEstimate (orders 39-41)

  Author: Tetrahedron (mycelium-shell)
  Date: 2026-04-16
  Idempotent: MERGE only, no mutations of existing data
*/

// ============================================================================
// PART A: Persona Layer — Schema + Seed Data + Wirings
// ============================================================================

// Persona 1: cypher-author
MERGE (p1:Persona {node_id: "persona-cypher-author"})
ON CREATE SET p1.name = "Cypher Author",
    p1.description = "Writes new Cypher protocols from scratch using idempotent MERGE patterns, dense typed edges, and constraint-aware design",
    p1.system_prompt = "You write production-grade Cypher that is idempotent (MERGE-only, no DETACH/DELETE). Every node gets a node_id. Every edge is strongly typed. Prioritize density: maximize meaningful edges per node. Use APOC for batch operations. Emit :QueryTrace for observability.",
    p1.preferred_model = "claude-haiku-4-5",
    p1.preferred_top_k = 10,
    p1.default_timeout_ms = 120000,
    p1.cost_budget_usd = 0.20,
    p1.usage_count = 0,
    p1.total_cost_usd = 0.0,
    p1.avg_tokens = 0,
    p1.file_type = "persona"
MERGE (p1)-[:USES_MODEL]->(m1:Model {node_id: "model-claude-haiku-4-5"})
MERGE (p1)-[:PART_OF]->(o:Ontology {node_id: "ontology-mycelium"})
WITH p1
MATCH (s:Subagent) WHERE s.role = "cypher-native-author" OR s.name =~ ".*cypher.*"
MERGE (s)-[:INSTANCE_OF]->(p1);

// Persona 2: density-auditor
MERGE (p2:Persona {node_id: "persona-density-auditor"})
ON CREATE SET p2.name = "Density Auditor",
    p2.description = "Read-only graph analyst that measures node richness, edge quality, embedding health, and produces structured audit reports",
    p2.system_prompt = "You run pure MATCH/RETURN queries. No mutations. Produce measurement reports: node count by label, edge count by type, density metrics (edges per node), orphaned nodes, embedding coverage. Output as structured JSON with timestamps.",
    p2.preferred_model = "claude-haiku-4-5",
    p2.preferred_top_k = 10,
    p2.default_timeout_ms = 90000,
    p2.cost_budget_usd = 0.15,
    p2.usage_count = 0,
    p2.total_cost_usd = 0.0,
    p2.avg_tokens = 0,
    p2.file_type = "persona"
MERGE (p2)-[:USES_MODEL]->(m2:Model {node_id: "model-claude-haiku-4-5"})
MERGE (p2)-[:PART_OF]->(o)
WITH p2
MATCH (s:Subagent) WHERE s.role = "density-auditor" OR s.name =~ ".*[Cc]oherence.*"
MERGE (s)-[:INSTANCE_OF]->(p2);

// Persona 3: install-scaffolder
MERGE (p3:Persona {node_id: "persona-install-scaffolder"})
ON CREATE SET p3.name = "Install Scaffolder",
    p3.description = "Generates production-ready docker-compose, install scripts, health checks, and secret rotation patterns for infrastructure",
    p3.system_prompt = "You write bash, docker-compose, systemd services, and Python init scripts. Assume production: error handling, retry logic, secret rotation, health checks, logging. Never hardcode secrets. Always include a DOCTOR command for validation.",
    p3.preferred_model = "claude-haiku-4-5",
    p3.preferred_top_k = 10,
    p3.default_timeout_ms = 150000,
    p3.cost_budget_usd = 0.25,
    p3.usage_count = 0,
    p3.total_cost_usd = 0.0,
    p3.avg_tokens = 0,
    p3.file_type = "persona"
MERGE (p3)-[:USES_MODEL]->(m3:Model {node_id: "model-claude-haiku-4-5"})
MERGE (p3)-[:PART_OF]->(o)
WITH p3
MATCH (s:Subagent) WHERE s.role = "install-scaffolder" OR s.name =~ ".*[Ss]caffold.*"
MERGE (s)-[:INSTANCE_OF]->(p3);

// Persona 4: narrator
MERGE (p4:Persona {node_id: "persona-narrator"})
ON CREATE SET p4.name = "Narrator",
    p4.description = "Produces graph-native natural language responses by reading edge connectives and composing fluent sentences",
    p4.system_prompt = "You read :EdgeConnective phrases from the graph and compose human-readable responses. Vary sentence structure. Use metaphor. Cite graph nodes inline as [[:Label {name}]]. Prefer Sonnet for nuance and coherence.",
    p4.preferred_model = "claude-sonnet-4-5",
    p4.preferred_top_k = 20,
    p4.default_timeout_ms = 180000,
    p4.cost_budget_usd = 0.30,
    p4.usage_count = 0,
    p4.total_cost_usd = 0.0,
    p4.avg_tokens = 0,
    p4.file_type = "persona"
MERGE (p4)-[:USES_MODEL]->(m4:Model {node_id: "model-claude-sonnet-4-5"})
MERGE (p4)-[:PART_OF]->(o)
WITH p4
MATCH (s:Subagent) WHERE s.role = "narrator" OR s.name =~ ".*[Vv]erbali[sz]ation.*"
MERGE (s)-[:INSTANCE_OF]->(p4);

// ============================================================================
// PART B: Amortization Layer — Enrich Existing Nodes
// ============================================================================

// Enrich all :Skill nodes with amortization fields
MATCH (sk:Skill)
SET sk.author_cost_usd = coalesce(sk.author_cost_usd, 0.0),
    sk.fire_count = coalesce(sk.fire_count, 0),
    sk.total_usage_cost_usd = coalesce(sk.total_usage_cost_usd, 0.0),
    sk.cost_per_use = 0.0,
    sk.amortization_status = "un-amortized",
    sk.file_type = coalesce(sk.file_type, "skill");

// Enrich all :Protocol nodes with amortization fields and backfill author_cost_usd
MATCH (p:Protocol) WHERE p.source_file IS NOT NULL
SET p.author_cost_usd = coalesce(p.author_cost_usd, 0.0),
    p.fire_count = coalesce(p.fire_count, 0),
    p.total_usage_cost_usd = coalesce(p.total_usage_cost_usd, 0.0),
    p.cost_per_use = 0.0,
    p.amortization_status = "un-amortized",
    p.file_type = "protocol";

// Backfill author_cost_usd from :Subagent :AUTHORED edges
MATCH (s:Subagent)-[e:AUTHORED]->(p:Protocol)
SET p.author_cost_usd = s.cost_usd;

// ============================================================================
// PART C: CostEstimate Rollup Nodes
// ============================================================================

// CostEstimate for cypher-author: aggregate from subagents with INSTANCE_OF
MERGE (ce1:CostEstimate {
  node_id: "costestimate-cypher-author"
})
SET ce1.persona_id = "persona-cypher-author",
    ce1.category = "collaboration",
    ce1.file_type = "costestimate"
WITH ce1
MATCH (p1:Persona {node_id: "persona-cypher-author"})<-[:INSTANCE_OF]-(s:Subagent)
WITH ce1, count(s) AS run_count, sum(s.cost_usd) AS total_spend
SET ce1.total_runs = run_count,
    ce1.total_cost_usd = total_spend,
    ce1.avg_cost_per_run = CASE WHEN run_count > 0 THEN total_spend / run_count ELSE 0.0 END,
    ce1.last_updated = timestamp()
MERGE (ce1)-[:FOR_PERSONA]->(p1:Persona {node_id: "persona-cypher-author"});

// CostEstimate for density-auditor
MERGE (ce2:CostEstimate {
  node_id: "costestimate-density-auditor"
})
SET ce2.persona_id = "persona-density-auditor",
    ce2.category = "collaboration",
    ce2.file_type = "costestimate"
WITH ce2
MATCH (p2:Persona {node_id: "persona-density-auditor"})<-[:INSTANCE_OF]-(s:Subagent)
WITH ce2, count(s) AS run_count, sum(s.cost_usd) AS total_spend
SET ce2.total_runs = run_count,
    ce2.total_cost_usd = total_spend,
    ce2.avg_cost_per_run = CASE WHEN run_count > 0 THEN total_spend / run_count ELSE 0.0 END,
    ce2.last_updated = timestamp()
MERGE (ce2)-[:FOR_PERSONA]->(p2:Persona {node_id: "persona-density-auditor"});

// CostEstimate for install-scaffolder
MERGE (ce3:CostEstimate {
  node_id: "costestimate-install-scaffolder"
})
SET ce3.persona_id = "persona-install-scaffolder",
    ce3.category = "collaboration",
    ce3.file_type = "costestimate"
WITH ce3
MATCH (p3:Persona {node_id: "persona-install-scaffolder"})<-[:INSTANCE_OF]-(s:Subagent)
WITH ce3, count(s) AS run_count, sum(s.cost_usd) AS total_spend
SET ce3.total_runs = run_count,
    ce3.total_cost_usd = total_spend,
    ce3.avg_cost_per_run = CASE WHEN run_count > 0 THEN total_spend / run_count ELSE 0.0 END,
    ce3.last_updated = timestamp()
MERGE (ce3)-[:FOR_PERSONA]->(p3:Persona {node_id: "persona-install-scaffolder"});

// CostEstimate for narrator
MERGE (ce4:CostEstimate {
  node_id: "costestimate-narrator"
})
SET ce4.persona_id = "persona-narrator",
    ce4.category = "collaboration",
    ce4.file_type = "costestimate"
WITH ce4
MATCH (p4:Persona {node_id: "persona-narrator"})<-[:INSTANCE_OF]-(s:Subagent)
WITH ce4, count(s) AS run_count, sum(s.cost_usd) AS total_spend
SET ce4.total_runs = run_count,
    ce4.total_cost_usd = total_spend,
    ce4.avg_cost_per_run = CASE WHEN run_count > 0 THEN total_spend / run_count ELSE 0.0 END,
    ce4.last_updated = timestamp()
MERGE (ce4)-[:FOR_PERSONA]->(p4:Persona {node_id: "persona-narrator"});

// ============================================================================
// PART D: Concept + Ontology Linkage
// ============================================================================

// Add Concept nodes for Persona, Amortization, CostEstimate (orders 39-41, category: collaboration)
MERGE (c39:Concept {
  node_id: "concept-persona",
  name: "Persona",
  order: 39,
  category: "collaboration",
  file_type: "concept",
  description: "First-class subagent archetype with system prompt, model, cost budget, and wiring to Skills, Commands, TestCases"
})
MERGE (c39)-[:DESCRIBES_IN]->(o:Ontology {node_id: "ontology-mycelium"});

MERGE (c40:Concept {
  node_id: "concept-amortization",
  name: "Amortization",
  order: 40,
  category: "collaboration",
  file_type: "concept",
  description: "Economic lifecycle tracking: author cost, fire count, usage cost, amortization status (dead/un-amortized/amortizing/amortized)"
})
MERGE (c40)-[:DESCRIBES_IN]->(o);

MERGE (c41:Concept {
  node_id: "concept-costestimate",
  name: "CostEstimate",
  order: 41,
  category: "collaboration",
  file_type: "concept",
  description: "Rollup node aggregating per-persona spend, run count, and average cost per run from historical subagent executions"
})
MERGE (c41)-[:DESCRIBES_IN]->(o);

// ============================================================================
// PART E: Amortization Status Query + Reporting
// ============================================================================

// Compute amortization status for all Protocols based on fire_count rules
MATCH (p:Protocol) WHERE p.source_file IS NOT NULL
WITH p,
     CASE
       WHEN p.fire_count = 0 THEN "dead"
       WHEN p.fire_count < 10 THEN "un-amortized"
       WHEN p.fire_count < 100 THEN "amortizing"
       WHEN p.fire_count >= 100 THEN "amortized"
       ELSE "unknown"
     END AS computed_status
SET p.amortization_status = computed_status
RETURN
  p.node_id,
  p.name,
  p.author_cost_usd,
  p.fire_count,
  p.total_usage_cost_usd,
  CASE WHEN p.fire_count > 0 THEN p.author_cost_usd / p.fire_count ELSE 0.0 END AS cost_per_use,
  p.amortization_status
ORDER BY p.fire_count DESC;
