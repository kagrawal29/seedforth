// ============================================================
// protocol-progress-score — graph-native progress scoring
// Reasoning lives IN the graph as CypherAtom chains.
// Reads :CommitSignal/:OutboxSignal/:ArtifactSignal (written by
// fleet-scanner.py, the thin I/O boundary) and produces weighted
// :ProgressEvent nodes. This is THOUGHT, resident in the graph.
// ============================================================

// --- Protocol node ---
MERGE (p:Protocol {node_id: 'protocol-progress-score'})
SET p.label = 'Progress Score - classify signals and produce weighted ProgressEvents',
    p.cadence = 'deep', p.enabled = true, p.project = 'system';

// --- Atom 0: classify commits (noise vs real) ---
MERGE (a0:CypherAtom {node_id: 'atom-progress-classify-commits'})
SET a0.semantic = 'Classify commit signals: noise (auto/sync/ci) scores 0, real work scores 1.0',
    a0.project = 'system',
    a0.cypher = '''
MATCH (s:CommitSignal) WHERE NOT exists(s.classified)
WITH s,
  CASE
    WHEN s.message =~ '(?i)^(auto|sync|ci|chore|wip|update|minor)[ :\\-]' THEN 0.0
    WHEN size(s.message) < 15 THEN 0.0
    WHEN s.message =~ '(?i)^(feat|fix|build|design|learn|memory|report|deploy|docs|refactor)[:\\-]' THEN 1.0
    ELSE 0.3
  END AS weight
SET s.is_real = weight > 0, s.weight = weight, s.classified = true
''';

// --- Atom 1: classify outbox signals ---
MERGE (a1:CypherAtom {node_id: 'atom-progress-classify-outbox'})
SET a1.semantic = 'Classify outbox signals: artifact attached 0.8, embed+numbers 0.7, text+numbers 0.5',
    a1.project = 'system',
    a1.cypher = '''
MATCH (s:OutboxSignal) WHERE NOT exists(s.classified)
WITH s,
  CASE
    WHEN s.has_file = true THEN 0.8
    WHEN s.has_embed = true AND s.has_numbers = true THEN 0.7
    WHEN s.length > 80 AND s.has_numbers = true THEN 0.5
    ELSE 0.0
  END AS weight
SET s.is_real = weight > 0, s.weight = weight, s.classified = true
''';

// --- Atom 2: classify artifact signals ---
MERGE (a2:CypherAtom {node_id: 'atom-progress-classify-artifacts'})
SET a2.semantic = 'Artifact signals score 0.4 (real but weak)',
    a2.project = 'system',
    a2.cypher = '''
MATCH (s:ArtifactSignal) WHERE NOT exists(s.classified)
SET s.is_real = true, s.weight = 0.4, s.classified = true
''';

// --- Atom 3: promote classified signals to ProgressEvents ---
MERGE (a3:CypherAtom {node_id: 'atom-progress-promote-events'})
SET a3.semantic = 'Promote weighted classified signals to ProgressEvent nodes',
    a3.project = 'system',
    a3.cypher = '''
MATCH (s) WHERE (s:CommitSignal OR s:OutboxSignal OR s:ArtifactSignal)
  AND s.classified = true AND s.weight > 0 AND NOT exists((s)-[:EVIDENCE]->())
CREATE (pe:ProgressEvent {
  node_id: 'pe-' + s.entity + '-' + s.node_id,
  entity: s.entity, marker: labels(s)[0], evidence: coalesce(s.message, s.text_preview, s.path),
  weight: s.weight, created_at: s.created_at, project: s.entity
})
MERGE (s)-[:EVIDENCE {decay_protected:true}]->(pe)
''';

// --- Atom 4: compute per-entity producing status ---
MERGE (a4:CypherAtom {node_id: 'atom-progress-compute-status'})
SET a4.semantic = 'Compute per-entity producing flag: weight >= 1.0 in last 7 days',
    a4.project = 'system',
    a4.cypher = '''
MATCH (pe:ProgressEvent)
WHERE pe.created_at > datetime() - duration({days:7})
WITH pe.entity AS entity, sum(pe.weight) AS total_weight
MERGE (f:FleetProgress {entity: entity, node_id: 'fp-' + entity})
SET f.producing = total_weight >= 1.0, f.total_weight = total_weight,
    f.updated_at = datetime(), f.project = entity
''';

// --- Chain: 0 -> 1 -> 2 -> 3 -> 4 ---
MATCH (a0:CypherAtom {node_id: 'atom-progress-classify-commits'})
MATCH (a1:CypherAtom {node_id: 'atom-progress-classify-outbox'})
MATCH (a2:CypherAtom {node_id: 'atom-progress-classify-artifacts'})
MATCH (a3:CypherAtom {node_id: 'atom-progress-promote-events'})
MATCH (a4:CypherAtom {node_id: 'atom-progress-compute-status'})
MERGE (a0)-[:FOLLOWS {decay_protected:true}]->(a1)
MERGE (a1)-[:FOLLOWS {decay_protected:true}]->(a2)
MERGE (a2)-[:FOLLOWS {decay_protected:true}]->(a3)
MERGE (a3)-[:FOLLOWS {decay_protected:true}]->(a4);

// --- Protocol points at first atom ---
MATCH (p:Protocol {node_id: 'protocol-progress-score'})
MATCH (a0:CypherAtom {node_id: 'atom-progress-classify-commits'})
MERGE (p)-[:FIRST_ATOM {decay_protected:true}]->(a0);
