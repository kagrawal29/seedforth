// @node_id: protocol-guide-atomize
// @label: "guide-atomize"
// ============================================================================
// Protocol: guide-atomize
// Atomize Guide descriptions into GuideStep nodes and wire to Commands/Protocols/Concepts
// ============================================================================
// Phases:
// 1. For each Guide with a non-empty description, split into sentences
// 2. Create GuideStep nodes for each sentence/chunk
// 3. Wire steps to the source Guide (HAS_STEP, STEP_OF)
// 4. Cross-reference steps to Commands, Protocols, and Concepts by text matching
// 5. Wire all GuideSteps to the root Ontology
// 6. Return metrics: guides_atomized, total_steps, references breakdown
// ============================================================================

// Phase 1-3: Identify guides, split descriptions, and create GuideStep nodes
MATCH (g:Guide)
WHERE g.description IS NOT NULL AND size(g.description) > 0
WITH g, split(g.description, '. ') AS sentences
WITH g,
     [i IN range(0, size(sentences) - 1) |
      trim(sentences[i]) + (CASE WHEN i < size(sentences) - 1 THEN '.' ELSE '' END)
     ] AS steps
WITH g,
     [step IN steps WHERE size(step) > 5] AS filtered_steps
WITH g, filtered_steps, size(filtered_steps) AS step_count
WHERE step_count > 0

UNWIND range(0, size(filtered_steps) - 1) AS idx
WITH g, filtered_steps, idx, filtered_steps[idx] AS step_text
MERGE (gs:GuideStep {
  node_id: g.node_id + '-step-' + (idx + 1),
  step_order: idx + 1,
  text: step_text,
  source_guide: g.node_id,
  file_type: 'guide-step',
  created_at: timestamp()
})

// Wire GuideStep to Guide (bidirectional)
MERGE (g)-[:HAS_STEP {order: idx + 1}]->(gs)
MERGE (gs)-[:STEP_OF]->(g);

// Phase 4a: Cross-reference GuideSteps to Commands
MATCH (gs:GuideStep), (c:Command)
WHERE gs.text CONTAINS c.name
   OR gs.text CONTAINS c.node_id
MERGE (gs)-[:REFERENCES {ref_type: 'command'}]->(c);

// Phase 4b: Cross-reference GuideSteps to Protocols
MATCH (gs:GuideStep), (p:Protocol)
WHERE gs.text CONTAINS p.node_id
   OR gs.text CONTAINS coalesce(p.label, '')
MERGE (gs)-[:REFERENCES {ref_type: 'protocol'}]->(p);

// Phase 4c: Cross-reference GuideSteps to Concepts
MATCH (gs:GuideStep), (con:Concept)
WHERE gs.text CONTAINS coalesce(con.name, '')
   OR gs.text CONTAINS coalesce(con.node_id, '')
MERGE (gs)-[:REFERENCES {ref_type: 'concept'}]->(con);

// Phase 5: Wire all GuideSteps to the root Ontology
MATCH (gs:GuideStep), (o:Ontology {node_id: 'ontology-mycelium'})
MERGE (gs)-[:GUIDESTEP_OF]->(o);

// Phase 6: Summary metrics (in one query)
MATCH (gs:GuideStep)
WITH count(DISTINCT gs.source_guide) AS guides_atomized,
     count(DISTINCT gs.node_id) AS total_steps
MATCH (gs2:GuideStep)-[r:REFERENCES]->(target)
WITH guides_atomized,
     total_steps,
     count(DISTINCT r) AS total_references,
     sum(CASE WHEN target:Command THEN 1 ELSE 0 END) AS refs_to_commands,
     sum(CASE WHEN target:Protocol THEN 1 ELSE 0 END) AS refs_to_protocols,
     sum(CASE WHEN target:Concept THEN 1 ELSE 0 END) AS refs_to_concepts
RETURN guides_atomized, total_steps, total_references, refs_to_commands, refs_to_protocols, refs_to_concepts;
