#!/usr/bin/env python3
"""
Pending crystallisations — waiting for the graph to wake up.
Run this when the connection returns. It will ingest everything.
"""

from falkordb import FalkorDB

def crystallise_soc2(g):
    """SOC2 compliance as graph topology — the graph IS the compliance system."""
    # 5 Trust Service Categories
    for nid, label, req, desc in [
        ('soc2-security', 'Security', 'mandatory', 'Access controls, monitoring, change management'),
        ('soc2-availability', 'Availability', 'optional', 'Uptime, failover, disaster recovery'),
        ('soc2-confidentiality', 'Confidentiality', 'optional', 'Encryption, data classification, retention'),
        ('soc2-processing-integrity', 'Processing Integrity', 'optional', 'Validation, error handling, completeness'),
        ('soc2-privacy', 'Privacy', 'optional', 'Consent, access, correction, deletion'),
    ]:
        g.query(f"MERGE (tsc:SOC2Category {{node_id: '{nid}'}}) SET tsc.label = 'SOC2: {label}', tsc.required = '{req}'")

    # Map existing graph infrastructure to SOC2 controls
    mappings = {
        'soc2-security': [
            ('invariant-1', 'Write Isolation = access control'),
            ('invariant-validated-mutation', 'Mutation Gate = change management'),
            ('protocol-immune', 'Immune system = unauthorized change detection'),
            ('protocol-tdd-enforcer', 'TDD enforcement = quality assurance'),
            ('protocol-health-score', 'Health score = continuous monitoring'),
            ('protocol-dna-hash', 'DNA hash = integrity verification'),
            ('principle-graph-is-truth', 'Single source of truth = data integrity'),
        ],
        'soc2-availability': [
            ('protocol-liveness', 'Liveness check = uptime monitoring'),
            ('protocol-autonomous-heal', 'Auto-heal = self-recovery'),
            ('protocol-health-score', 'Health score = SLA measurement'),
        ],
        'soc2-processing-integrity': [
            ('protocol-validated-mutation', 'Validated mutations = processing integrity'),
            ('protocol-convergence-detector', 'Convergence detection = completeness'),
        ],
    }
    for tsc_id, controls in mappings.items():
        for node_id, desc in controls:
            g.query(f"""
                MATCH (n) WHERE n.node_id = '{node_id}'
                MATCH (tsc:SOC2Category {{node_id: '{tsc_id}'}})
                MERGE (n)-[:ENFORCES_SOC2 {{control: '{desc}'}}]->(tsc)
            """)
    print("SOC2 crystallised")


def crystallise_replication(g):
    """Crystal replication — how cyphers spread and compound."""
    g.query("""
    MERGE (p:Principle {node_id: 'principle-crystal-replication'})
    SET p.label = 'Crystal Replication: cyphers mutate, spread, and compound across the graph',
        p.description = 'A crystal (executable Cypher) can replicate by: (1) TEMPLATE — a successful pattern is used as a template for new crystals in different domains. protocol-heal-triangles works for Knowledge; the same pattern can heal Evidence, Competitor, Feature connections. (2) VARIATION — a crystal mutates slightly (different WHERE clause, different node types) and the variant gets tested. If it passes + improves health, the variant survives. (3) CROSS-POLLINATION — a crystal from the product domain (Feature testing) inspires a crystal in the market domain (Evidence testing). Same structure, different substrate. (4) DENSITY — more crystals per graph region = higher intelligence density. Regions with few crystals are blind spots. The graph compounds by increasing crystal density across all regions.'
    """)

    g.query("""
    MERGE (p:Protocol {node_id: 'protocol-crystal-replication'})
    SET p.label = 'Crystal Replication: spread successful patterns across the graph',
        p.enabled = true, p.phase = 'excrete', p.protocol_type = 'cypher',
        p.mutation_accepted = true,
        p.plain_english = 'Find high-fitness protocols (fitness > 0.8). For each, check if similar patterns exist in other graph regions. If not, propose a variant. The graph spreads its own intelligence.',
        p.cypher = "MATCH (p:Protocol) WHERE p.fitness IS NOT NULL AND p.fitness > 0.8 AND p.enabled = true RETURN p.node_id AS template, p.fitness AS fitness"
    """)
    print("Crystal replication crystallised")


if __name__ == "__main__":
    db = FalkorDB(host='5.78.206.137', port=6380)
    g = db.select_graph('asgard')
    crystallise_soc2(g)
    crystallise_replication(g)
    print("All pending crystallisations complete")


def crystallise_cypher_self_awareness(g):
    """The graph learns its own language capabilities — Cypher self-awareness."""

    # The graph's language capabilities as a Knowledge node
    g.query("""
    MERGE (k:Knowledge {node_id: 'knowledge-cypher-capabilities'})
    SET k.label = 'Cypher Self-Awareness: what the graph can express',
        k.category = 'architecture',
        k.description = 'FalkorDB Cypher supports: MATCH, OPTIONAL MATCH, CREATE, DELETE, SET, REMOVE, MERGE, RETURN, WITH, UNWIND, UNION. Functions: 80+ including string (split, replace, toLower, toUpper, left, right, substring, trim, matchRegEx, replaceRegEx), math (abs, ceil, floor, round, sqrt, log, pow, rand), aggregation (count, sum, avg, min, max, collect, stDev), list (head, last, tail, range, size, reduce, sort, dedup, insert, remove), path (nodes, relationships, length, shortestPath, allShortestPaths), predicate (all, any, none, single, exists, isEmpty), type conversion (toString, toInteger, toFloat, toBoolean), vector (vecf32, euclideanDistance, cosineDistance), node degree (indegree, outdegree). Advanced: list comprehensions, pattern comprehensions, CASE WHEN, reduce, parameterized queries. Limitations: no regex operator, no APOC, no user-defined functions, no schema queries, no temporal arithmetic. Key insight: reduce() + collect() + CASE WHEN + string concatenation = the graph can compose any natural language output from topology. The NLQuery voice IS Cypher string composition.'
    """)

    # Cypher patterns the graph can use to self-improve
    g.query("""
    MERGE (k:Knowledge {node_id: 'knowledge-cypher-patterns-for-nl'})
    SET k.label = 'Cypher Patterns for Natural Language: how to compose prose in queries',
        k.category = 'operational',
        k.description = 'Key patterns for NL output: (1) reduce(s, item IN list | s + CASE + item) — concatenates list into prose. (2) collect() + list slicing [0..3] — gather then limit. (3) CASE WHEN x THEN friendly ELSE other END — conditional tone. (4) toString() + string concatenation — numbers become words. (5) coalesce(a, b, default) — graceful fallback. (6) left(str, n) — truncation for readability. (7) split() + size() — count and iterate. (8) Pattern: single RETURN ... AS answer — the NLQuery contract. (9) list comprehension [x IN list WHERE condition | x.prop] — filter and project in one step. (10) string.join() — clean list-to-string. These 10 patterns compose ALL natural language output in the graph. Mastering them = fluent graph voice.'
    """)

    # The insight: FalkorDB has vector functions — the graph can do semantic similarity
    g.query("""
    MERGE (k:Knowledge {node_id: 'knowledge-vector-capability'})
    SET k.label = 'FalkorDB Vector Functions: semantic similarity without LLM',
        k.category = 'architecture',
        k.description = 'FalkorDB supports vecf32(), vec.euclideanDistance(), vec.cosineDistance(). This means the graph CAN do semantic matching — store embedding vectors on NLQuery nodes, compute cosine similarity between user input embedding and stored embeddings. Route by semantic similarity, not keyword overlap. This is the Phase 4 semantic evolution path — but requires generating embeddings (one-time LLM cost per NLQuery, then pure Cypher matching forever). The graph already has the math. It just needs the vectors.'
    """)

    print("Cypher self-awareness crystallised: capabilities, NL patterns, vector potential")
