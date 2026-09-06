// @node_id: protocol-persona-atomize
// @label: "Persona Atomize"
// ============================================================================
// PROTOCOL: persona-atomize
// Atomize every :Persona node's system_prompt into :PromptClause nodes
// Wire each clause to :DesignPrinciple, :Skill, :Command, or :Concept
// ============================================================================
//
// Purpose: Convert text-blob system_prompts into first-class graph nodes.
// Each clause becomes queryable, measurable, and connectable to the graph's
// own ontology. Embeds fractal principle: a persona's clause has same
// structure as a CypherAtom — atomic instruction wired to its context.
//
// Schema (:PromptClause):
//   - node_id: persona.node_id + '-clause-' + N
//   - clause_order: N (position in prompt)
//   - text: clause text (trimmed)
//   - source_persona: persona.node_id
//   - source_guide: NULL (unless from :Guide)
//   - clause_type: 'instruction' | 'constraint' | 'preference' | 'identity'
//   - file_type: 'prompt-clause'
//   - created_at: current timestamp
//
// Clause type heuristics:
//   - Contains "must", "always", "never", "do not" → 'constraint'
//   - Contains "prefer", "default", "usually" → 'preference'
//   - Contains "you are", "your role", "you write" → 'identity'
//   - Everything else → 'instruction'
//
// Wire to personas:
//   (persona)-[:HAS_CLAUSE {order: N}]->(clause)
//   (clause)-[:CLAUSE_OF]->(persona)
//
// Wire to ontology (if keywords match):
//   (clause)-[:EMBODIES]->(principle)   [if mentions DesignPrinciple name]
//   (clause)-[:INVOKES_SKILL]->(skill)  [if mentions Skill name]
//   (clause)-[:REFERENCES]->(command)   [if mentions Command name]
//   (clause)-[:ABOUT]->(concept)        [if mentions Concept name]
//
// ============================================================================

// STEP 1: Split :Persona system_prompts into clauses and create :PromptClause nodes
// ============================================================================

MATCH (p:Persona)
WHERE p.system_prompt IS NOT NULL AND size(p.system_prompt) > 0

WITH p,
  split(replace(replace(replace(replace(
    p.system_prompt,
    '. ', '|SPLIT|'),
    '? ', '|SPLIT|'),
    ': ', '|SPLIT|'),
    '\n', '|SPLIT|'),
  '|SPLIT|') AS raw_clauses

UNWIND raw_clauses AS raw
WITH p, trim(raw) AS clause_text
WHERE size(clause_text) > 10

// Create a hash to ensure idempotency
WITH p, clause_text,
  apoc.util.md5([p.node_id, clause_text]) AS clause_hash

// Determine clause_type based on heuristics
WITH p, clause_text, clause_hash,
  CASE
    WHEN clause_text =~ '(?i).*(must|always|never|do not|cannot|should not).*'
      THEN 'constraint'
    WHEN clause_text =~ '(?i).*(prefer|default|usually|tend to).*'
      THEN 'preference'
    WHEN clause_text =~ '(?i).*(you are|your role|you write|you run|you read).*'
      THEN 'identity'
    ELSE 'instruction'
  END AS detected_type

// MERGE :PromptClause nodes
MERGE (clause:PromptClause {
  node_id: p.node_id + '-clause-' + clause_hash
})
SET
  clause.text = clause_text,
  clause.source_persona = p.node_id,
  clause.source_guide = NULL,
  clause.clause_type = detected_type,
  clause.file_type = 'prompt-clause',
  clause.created_at = timestamp()

// Wire persona to clause
MERGE (p)-[:HAS_CLAUSE]->(clause)
MERGE (clause)-[:CLAUSE_OF]->(p)

WITH p, count(clause) AS clause_count
RETURN p.name AS persona_name, clause_count
ORDER BY persona_name;

// ============================================================================
// STEP 2: Split :Guide {node_id: 'guide-agent-contract'} contract_text
// ============================================================================

MATCH (g:Guide {node_id: 'guide-agent-contract'})
WHERE g.contract_text IS NOT NULL AND size(g.contract_text) > 0

WITH g,
  split(
    replace(
      replace(
        replace(
          replace(
            replace(
              replace(
                replace(g.contract_text, ' ONE: ', '|SPLIT|'),
              ' TWO: ', '|SPLIT|'),
            ' THREE: ', '|SPLIT|'),
          ' FOUR: ', '|SPLIT|'),
        ' FIVE: ', '|SPLIT|'),
      ' SIX: ', '|SPLIT|'),
    ' SEVEN: ', '|SPLIT|'),
  '|SPLIT|') AS rule_chunks

UNWIND rule_chunks AS raw_clause
WITH g, trim(raw_clause) AS clause_text
WHERE size(clause_text) > 10

WITH g, clause_text,
  apoc.util.md5(['guide-agent-contract', clause_text]) AS clause_hash

// Determine clause_type for guide clauses
WITH g, clause_text, clause_hash,
  CASE
    WHEN clause_text =~ '(?i).*(must|always|never|do not|cannot|should not|strictly).*'
      THEN 'constraint'
    WHEN clause_text =~ '(?i).*(prefer|default|usually).*'
      THEN 'preference'
    ELSE 'instruction'
  END AS detected_type

// MERGE guide clause nodes
MERGE (clause:PromptClause {
  node_id: 'guide-agent-contract-clause-' + clause_hash
})
SET
  clause.text = clause_text,
  clause.source_persona = NULL,
  clause.source_guide = 'guide-agent-contract',
  clause.clause_type = detected_type,
  clause.file_type = 'prompt-clause',
  clause.created_at = timestamp()

// Wire guide to clause
MERGE (g)-[:HAS_CLAUSE]->(clause)
MERGE (clause)-[:CLAUSE_OF]->(g)

RETURN count(clause) AS guide_clauses_created;

// ============================================================================
// STEP 3: Wire :PromptClause nodes to :DesignPrinciple nodes
// ============================================================================

MATCH (clause:PromptClause), (principle:DesignPrinciple)
WHERE NOT exists((clause)-[:EMBODIES]->(principle))
  AND (
    clause.text =~ '(?i).*(idempotent|merkle|self-describe|cypher-native|fractal|auto-heal|graph.*source).*'
    OR clause.text =~ '(?i).*(MERGE|production-grade|density).*'
  )

MERGE (clause)-[:EMBODIES {created_at: timestamp()}]->(principle)

WITH clause, count(DISTINCT principle) AS principles_count
WHERE principles_count > 0
RETURN count(DISTINCT clause) AS clauses_with_principles, principles_count;

// ============================================================================
// STEP 4: Wire :PromptClause nodes to :Skill nodes
// ============================================================================

MATCH (clause:PromptClause), (skill:Skill)
WHERE NOT exists((clause)-[:INVOKES_SKILL]->(skill))
  AND (
    clause.text =~ '(?i).*(strengthening|reply|compose).*'
    OR skill.name IN ['Compose Natural-Language Reply', 'Hebbian Edge Strengthening']
  )

MERGE (clause)-[:INVOKES_SKILL {created_at: timestamp()}]->(skill)

RETURN count(DISTINCT clause) AS clauses_with_skills;

// ============================================================================
// STEP 5: Wire :PromptClause nodes to :Command nodes
// ============================================================================

MATCH (clause:PromptClause), (cmd:Command)
WHERE NOT exists((clause)-[:REFERENCES]->(cmd))
  AND clause.text =~ ('(?i).*\\b' + cmd.name + '\\b.*')

MERGE (clause)-[:REFERENCES {created_at: timestamp()}]->(cmd)

RETURN count(DISTINCT clause) AS clauses_with_commands;

// ============================================================================
// STEP 6: Wire all :PromptClause nodes to :Ontology
// ============================================================================

MATCH (clause:PromptClause), (o:Ontology {node_id: 'ontology-mycelium'})
WHERE NOT exists((clause)-[:CLAUSE_OF_ONTOLOGY]->(o))

MERGE (clause)-[:CLAUSE_OF_ONTOLOGY {created_at: timestamp()}]->(o)

RETURN count(clause) AS clauses_wired_to_ontology;

// ============================================================================
// STEP 7: Summary Statistics
// ============================================================================

MATCH (pc:PromptClause)
RETURN
  count(pc) AS total_clauses,
  size([c IN collect(pc.clause_type) WHERE c = 'instruction']) AS instruction_count,
  size([c IN collect(pc.clause_type) WHERE c = 'constraint']) AS constraint_count,
  size([c IN collect(pc.clause_type) WHERE c = 'preference']) AS preference_count,
  size([c IN collect(pc.clause_type) WHERE c = 'identity']) AS identity_count;

// ============================================================================
// STEP 8: Cross-reference counts
// ============================================================================

MATCH (pc:PromptClause)
RETURN
  size([p IN collect(pc) WHERE (p)-[:EMBODIES]->()]) AS clauses_with_principles,
  size([p IN collect(pc) WHERE (p)-[:INVOKES_SKILL]->()]) AS clauses_with_skills,
  size([p IN collect(pc) WHERE (p)-[:REFERENCES]->()]) AS clauses_with_commands,
  size([p IN collect(pc) WHERE (p)-[:ABOUT]->()]) AS clauses_with_concepts;

// ============================================================================
// STEP 9: Sample clauses with their cross-references
// ============================================================================

MATCH (pc:PromptClause)
WITH pc LIMIT 3
OPTIONAL MATCH (pc)-[:EMBODIES]->(principle:DesignPrinciple)
OPTIONAL MATCH (pc)-[:INVOKES_SKILL]->(skill:Skill)
OPTIONAL MATCH (pc)-[:REFERENCES]->(cmd:Command)
OPTIONAL MATCH (pc)-[:ABOUT]->(concept:Concept)
RETURN
  pc.node_id,
  pc.text,
  pc.clause_type,
  collect(DISTINCT principle.name) AS principles,
  collect(DISTINCT skill.name) AS skills,
  collect(DISTINCT cmd.name) AS commands,
  collect(DISTINCT concept.node_id) AS concepts;
