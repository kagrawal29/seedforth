// @node_id: contribution-rules-v1
// @label: "Contribution Rule Set v1 — rules for shipping local→dev novelty"
// @kind: knowledge
//
// Graph-native contribution pipeline: every :MergeRule node declares what
// counts as "novel" (detect_cypher + novelty_mode) and how to ship it
// (ship_dir + ship_filename + ship_body templates). The generic driver at
// scripts/contribute.py reads all rules in priority order and fires them.
//
// Placeholder conventions:
//   Inside detect_cypher / fetch_cypher (stored as string properties):
//     <item>      — substituted by the driver at runtime with the current
//                   item's value (the column named by rule.item_key).
//                   Driver does simple string replace before executing.
//   Inside ship_filename / ship_body (Python .format_map templates):
//     {slug}      — lowercased-kebab of the item
//     {item}      — raw item value
//     {nid}, {label}, {observed_count}, ... — any column from fetch_cypher
//     {{ }}       — literal brace in output (for Cypher map syntax)
// ============================================================================

// Parent set — all rules link back here
MERGE (ruleset:ContributionRuleSet {node_id: 'contribution-rules-v1'})
SET ruleset.project = 'mycelium',
    ruleset.version = '1.0',
    ruleset.declared_at = datetime(),
    ruleset.description = 'Starter rule set — 8 dimensions of novelty the driver detects and emits';

// ----------------------------------------------------------------------------
// Rule 1: novel label schema (medium priority)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-novel-label-schema'})
SET r.project = 'mycelium',
    r.priority = 'medium',
    r.kind = 'label-schema',
    r.detect_cypher = 'CALL db.labels() YIELD label RETURN label',
    r.novelty_mode = 'in-local-not-in-dev',
    r.item_key = 'label',
    r.fetch_cypher = 'MATCH (n:`<item>`) WITH n LIMIT 500 RETURN count(n) AS observed_count, apoc.coll.toSet([k IN reduce(acc=[], ks IN collect(keys(n)) | acc + ks) | k]) AS properties',
    r.ship_dir = 'graph/knowledge',
    r.ship_filename = '{slug}-schema-v1.cypher',
    r.ship_body = '// @node_id: schema-{slug}-v1\n// @label: "{item} schema v1 (auto-extracted)"\n// @kind: knowledge\n\nMERGE (s:SchemaDeclaration {{node_id: \'schema-{slug}-v1\'}})\nSET s.project = \'mycelium\',\n    s.for_label = \'{item}\',\n    s.observed_count = {observed_count},\n    s.properties = {properties_cypher_list},\n    s.declared_at = datetime(),\n    s.source = \'rule-novel-label-schema\';\n\nMERGE (inv:Invariant {{node_id: \'invariant-{slug}-scoped\'}})\nSET inv.project = \'mycelium\',\n    inv.label = \'Every :{item} has project scope\',\n    inv.severity = \'critical\',\n    inv.check_cypher = \'MATCH (n:{item}) WHERE n.project IS NULL RETURN count(n) AS violations\',\n    inv.heal_protocol = \'protocol-backfill-{slug}-project-scope\';\n',
    r.rationale = 'New label = new capability. Schema declaration + scoped invariant lets dev enforce the Forest Promise on friends new shape.',
    r.scope_default = 'maverick-dev-friend',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Rule 2: novel label fixtures (medium priority)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-novel-label-fixtures'})
SET r.project = 'mycelium',
    r.priority = 'medium',
    r.kind = 'fixtures',
    r.detect_cypher = 'CALL db.labels() YIELD label RETURN label',
    r.novelty_mode = 'in-local-not-in-dev',
    r.item_key = 'label',
    r.fetch_cypher = 'MATCH (n:`<item>`) WITH n ORDER BY rand() LIMIT 3 RETURN collect(properties(n)) AS sample_rows',
    r.ship_dir = 'graph/fixtures',
    r.ship_filename = '{slug}-examples.cypher',
    r.ship_body = '// @node_id: fixtures-{slug}-examples\n// @label: "{item} sample fixtures"\n// @kind: fixtures\n\n{fixture_merges}',
    r.rationale = 'Teammates benefit from 3 real exemplars. Prune aggressively — not the full corpus.',
    r.scope_default = 'maverick-dev-friend',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Rule 3: novel relationship type (high priority)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-novel-relationship-type'})
SET r.project = 'mycelium',
    r.priority = 'high',
    r.kind = 'rel-type',
    r.detect_cypher = 'CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType',
    r.novelty_mode = 'in-local-not-in-dev',
    r.item_key = 'relationshipType',
    r.fetch_cypher = 'MATCH (a)-[r:`<item>`]->(b) WITH labels(a)[0] AS src, labels(b)[0] AS tgt, count(*) AS c ORDER BY c DESC LIMIT 5 RETURN collect({src: src, tgt: tgt, count: c}) AS typical_shapes, sum(c) AS total_count',
    r.ship_dir = 'graph/knowledge',
    r.ship_filename = 'reltype-{slug}-v1.cypher',
    r.ship_body = '// @node_id: reltype-{slug}-v1\n// @label: "{item} relationship type declaration"\n// @kind: knowledge\n\nMERGE (rt:RelationshipTypeDeclaration {{node_id: \'reltype-{slug}-v1\'}})\nSET rt.project = \'mycelium\',\n    rt.rel_type = \'{item}\',\n    rt.typical_shapes = {typical_shapes_repr},\n    rt.total_count = {total_count},\n    rt.declared_at = datetime();\n',
    r.rationale = 'Novel relationship types describe new ways shared node labels connect. Pure semantic glue.',
    r.scope_default = 'mycelium',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Rule 4: novel Protocol instance (HIGHEST priority — executable behavior)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-novel-protocol-instance'})
SET r.project = 'mycelium',
    r.priority = 'highest',
    r.kind = 'protocol-instance',
    r.detect_cypher = 'MATCH (p:Protocol) WHERE p.node_id IS NOT NULL RETURN p.node_id AS node_id',
    r.novelty_mode = 'in-local-not-in-dev',
    r.item_key = 'node_id',
    r.fetch_cypher = 'MATCH (p:Protocol {node_id: \'<item>\'}) RETURN p.cypher AS body, p.label AS label',
    r.ship_dir = 'graph/protocols',
    r.ship_filename = '{slug}.cypher',
    r.ship_body = '{body_or_synthesized}',
    r.rationale = 'Friends novel :Protocol instances are the executable spec-to-code engine. Highest-value contribution.',
    r.scope_default = 'maverick-dev-friend',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Rule 5: novel Invariant instance (HIGHEST priority)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-novel-invariant-instance'})
SET r.project = 'mycelium',
    r.priority = 'highest',
    r.kind = 'invariant-instance',
    r.detect_cypher = 'MATCH (i:Invariant) WHERE i.node_id IS NOT NULL RETURN i.node_id AS node_id',
    r.novelty_mode = 'in-local-not-in-dev',
    r.item_key = 'node_id',
    r.fetch_cypher = 'MATCH (i:Invariant {node_id: \'<item>\'}) RETURN i.label AS label, i.severity AS severity, i.check_cypher AS check_cypher, i.heal_protocol AS heal_protocol',
    r.ship_dir = 'graph/knowledge',
    r.ship_filename = 'invariant-{slug}.cypher',
    r.ship_body = '// @node_id: invariant-{slug}\n// @label: "Invariant: {label_escaped}"\n// @kind: knowledge\n\nMERGE (inv:Invariant {{node_id: \'{item}\'}})\nSET inv.project = \'maverick-dev-friend\',\n    inv.label = \'{label_escaped}\',\n    inv.severity = \'{severity_or_medium}\',\n    inv.check_cypher = \'{check_cypher_escaped}\',\n    inv.heal_protocol = \'{heal_protocol_or_none}\',\n    inv.declared_at = datetime();\n',
    r.rationale = 'Novel :Invariant instances encode what friends subsystem claims must stay true. Critical.',
    r.scope_default = 'maverick-dev-friend',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Rule 6: novel TestCase instance (high priority)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-novel-testcase-instance'})
SET r.project = 'mycelium',
    r.priority = 'high',
    r.kind = 'testcase-instance',
    r.detect_cypher = 'MATCH (tc:TestCase) WHERE tc.node_id IS NOT NULL RETURN tc.node_id AS node_id',
    r.novelty_mode = 'in-local-not-in-dev',
    r.item_key = 'node_id',
    r.fetch_cypher = 'MATCH (tc:TestCase {node_id: \'<item>\'}) RETURN tc.label AS label, tc.claim AS claim, tc.verify_cypher AS verify_cypher',
    r.ship_dir = 'graph/knowledge',
    r.ship_filename = 'test-{slug}.cypher',
    r.ship_body = '// @node_id: test-{slug}\n// @label: "{label_escaped}"\n// @kind: knowledge\n\nMERGE (tc:TestCase {{node_id: \'{item}\'}})\nSET tc.project = \'maverick-dev-friend\',\n    tc.label = \'{label_escaped}\',\n    tc.claim = \'{claim_escaped}\',\n    tc.verify_cypher = \'{verify_cypher_escaped}\',\n    tc.declared_at = datetime();\n',
    r.rationale = 'Novel :TestCase instances encode what friend claims is verifiable about their subsystem.',
    r.scope_default = 'maverick-dev-friend',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Rule 7: novel Decision instance (high priority)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-novel-decision-instance'})
SET r.project = 'mycelium',
    r.priority = 'high',
    r.kind = 'decision-instance',
    r.detect_cypher = 'MATCH (d:Decision) WHERE d.node_id IS NOT NULL RETURN d.node_id AS node_id',
    r.novelty_mode = 'in-local-not-in-dev',
    r.item_key = 'node_id',
    r.fetch_cypher = 'MATCH (d:Decision {node_id: \'<item>\'}) RETURN d.label AS label, d.rationale AS rationale, d.status AS status',
    r.ship_dir = 'graph/knowledge',
    r.ship_filename = 'decision-{slug}.cypher',
    r.ship_body = '// @node_id: decision-{slug}\n// @label: "Decision: {label_escaped}"\n// @kind: knowledge\n\nMERGE (d:Decision {{node_id: \'{item}\'}})\nSET d.project = \'maverick-dev-friend\',\n    d.label = \'{label_escaped}\',\n    d.rationale = \'{rationale_escaped}\',\n    d.status = \'{status_or_active}\',\n    d.declared_at = datetime();\n',
    r.rationale = 'Novel :Decision instances record team commitments friend has made. Ships as prior art for dev.',
    r.scope_default = 'maverick-dev-friend',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Rule 8: property-drift report (medium, report-only)
// ----------------------------------------------------------------------------
MERGE (r:MergeRule {node_id: 'rule-property-drift-report'})
SET r.project = 'mycelium',
    r.priority = 'medium',
    r.kind = 'property-drift',
    r.detect_cypher = 'CALL db.labels() YIELD label RETURN label',
    r.novelty_mode = 'property-drift',
    r.item_key = 'label',
    r.fetch_cypher = 'MATCH (n:`<item>`) WITH n LIMIT 500 RETURN apoc.coll.toSet([k IN reduce(acc=[], ks IN collect(keys(n)) | acc + ks) | k]) AS properties',
    r.ship_dir = 'manifest-only',
    r.ship_filename = '',
    r.ship_body = '',
    r.rationale = 'For labels present on both graphs, surface property-key sets that differ. Report-only — reviewer decides what to do.',
    r.scope_default = 'mycelium',
    r.fire_count = 0,
    r.declared_at = datetime();

// ----------------------------------------------------------------------------
// Link all rules to the ruleset
// ----------------------------------------------------------------------------
MATCH (ruleset:ContributionRuleSet {node_id: 'contribution-rules-v1'}),
      (r:MergeRule)
WHERE r.node_id STARTS WITH 'rule-'
MERGE (ruleset)-[:CONTAINS_RULE]->(r);
