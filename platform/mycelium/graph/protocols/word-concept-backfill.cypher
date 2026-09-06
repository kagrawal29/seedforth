// @node_id: protocol-word-concept-backfill
// @label: "Word-Concept Backfill"
============================================================================
Protocol: Word-Concept Backfill
=================================

PURPOSE:
  Wire every :Concept, :Guide, :DesignPrinciple, :Metaphor, and :Protocol
  description to the :Word layer via :APPEARS_IN edges. Transforms 86 edges
  into 4000+, making every word a cross-concept bridge.

SCALE:
  108 Concepts + 30 Guides + 8 Principles + 7 Metaphors + 64 Protocols
  = 217 text-bearing nodes × ~20 content words each = ~4,000+ edges

CONSTRAINTS:
  - MERGE only (idempotent, safe to re-run)
  - All cypher through mycelium shell
  - Filter stopwords (common English words that carry no semantic weight)
  - Batch by node type if needed to avoid timeouts

============================================================================
Atom: Extract tokens from descriptions (all node types)
============================================================================

-- Phase 1: Extract vocabulary from Concepts
MATCH (n:Concept)
WHERE n.node_id IS NOT NULL
  AND coalesce(n.description, n.explanation, '') <> ''
WITH n, apoc.text.split(
  toLower(coalesce(n.description, '') + ' ' + coalesce(n.explanation, '')),
  '[^a-z0-9\\-]+'
) AS tokens
UNWIND tokens AS token
WITH n, token
WHERE size(token) > 2
  AND NOT token IN [
    'the','and','for','that','this','with','from','are','not','has','was',
    'but','all','its','can','via','one','also','each','will','may','does',
    'into','than','when','been','have','any','our','how','who','what','them',
    'then','they','which','there','these','those','only','more','some','such',
    'other','over','very','just','about','after','would','should','could',
    'being','most','must','were','where','same','like','both','here','many',
    'well','should','could','would','could','going','being','having','let',
    'new','use','used','using','get','got','set','make','made','way','even',
    'work','works','working','says','said','say','know','knows','knowing',
    'see','seen','seeing','form','forms','forming','part','parts','thing',
    'things','time','times','value','values','level','levels','type','types',
    'data','set','state','include','includes','including','represent','shows'
  ]
MERGE (w:Word {lemma: token})
ON CREATE SET w.node_id = 'word-' + token,
              w.surface_forms = [token],
              w.is_stopword = false,
              w.frequency = 1,
              w.first_seen = toString(datetime()),
              w.file_type = 'word'
ON MATCH SET w.frequency = coalesce(w.frequency, 0) + 1
MERGE (w)-[:APPEARS_IN {field: 'description'}]->(n);

-- Phase 2: Extract vocabulary from Guides
MATCH (n:Guide)
WHERE n.node_id IS NOT NULL
  AND coalesce(n.description, n.explanation, '') <> ''
WITH n, apoc.text.split(
  toLower(coalesce(n.description, '') + ' ' + coalesce(n.explanation, '')),
  '[^a-z0-9\\-]+'
) AS tokens
UNWIND tokens AS token
WITH n, token
WHERE size(token) > 2
  AND NOT token IN [
    'the','and','for','that','this','with','from','are','not','has','was',
    'but','all','its','can','via','one','also','each','will','may','does',
    'into','than','when','been','have','any','our','how','who','what','them',
    'then','they','which','there','these','those','only','more','some','such',
    'other','over','very','just','about','after','would','should','could',
    'being','most','must','were','where','same','like','both','here','many',
    'well','should','could','would','could','going','being','having','let',
    'new','use','used','using','get','got','set','make','made','way','even',
    'work','works','working','says','said','say','know','knows','knowing',
    'see','seen','seeing','form','forms','forming','part','parts','thing',
    'things','time','times','value','values','level','levels','type','types',
    'data','set','state','include','includes','including','represent','shows'
  ]
MERGE (w:Word {lemma: token})
ON CREATE SET w.node_id = 'word-' + token,
              w.surface_forms = [token],
              w.is_stopword = false,
              w.frequency = 1,
              w.first_seen = toString(datetime()),
              w.file_type = 'word'
ON MATCH SET w.frequency = coalesce(w.frequency, 0) + 1
MERGE (w)-[:APPEARS_IN {field: 'description'}]->(n);

-- Phase 3: Extract vocabulary from DesignPrinciples
MATCH (n:DesignPrinciple)
WHERE n.node_id IS NOT NULL
  AND coalesce(n.description, n.explanation, '') <> ''
WITH n, apoc.text.split(
  toLower(coalesce(n.description, '') + ' ' + coalesce(n.explanation, '')),
  '[^a-z0-9\\-]+'
) AS tokens
UNWIND tokens AS token
WITH n, token
WHERE size(token) > 2
  AND NOT token IN [
    'the','and','for','that','this','with','from','are','not','has','was',
    'but','all','its','can','via','one','also','each','will','may','does',
    'into','than','when','been','have','any','our','how','who','what','them',
    'then','they','which','there','these','those','only','more','some','such',
    'other','over','very','just','about','after','would','should','could',
    'being','most','must','were','where','same','like','both','here','many',
    'well','should','could','would','could','going','being','having','let',
    'new','use','used','using','get','got','set','make','made','way','even',
    'work','works','working','says','said','say','know','knows','knowing',
    'see','seen','seeing','form','forms','forming','part','parts','thing',
    'things','time','times','value','values','level','levels','type','types',
    'data','set','state','include','includes','including','represent','shows'
  ]
MERGE (w:Word {lemma: token})
ON CREATE SET w.node_id = 'word-' + token,
              w.surface_forms = [token],
              w.is_stopword = false,
              w.frequency = 1,
              w.first_seen = toString(datetime()),
              w.file_type = 'word'
ON MATCH SET w.frequency = coalesce(w.frequency, 0) + 1
MERGE (w)-[:APPEARS_IN {field: 'description'}]->(n);

-- Phase 4: Extract vocabulary from Metaphors
MATCH (n:Metaphor)
WHERE n.node_id IS NOT NULL
  AND coalesce(n.description, n.explanation, '') <> ''
WITH n, apoc.text.split(
  toLower(coalesce(n.description, '') + ' ' + coalesce(n.explanation, '')),
  '[^a-z0-9\\-]+'
) AS tokens
UNWIND tokens AS token
WITH n, token
WHERE size(token) > 2
  AND NOT token IN [
    'the','and','for','that','this','with','from','are','not','has','was',
    'but','all','its','can','via','one','also','each','will','may','does',
    'into','than','when','been','have','any','our','how','who','what','them',
    'then','they','which','there','these','those','only','more','some','such',
    'other','over','very','just','about','after','would','should','could',
    'being','most','must','were','where','same','like','both','here','many',
    'well','should','could','would','could','going','being','having','let',
    'new','use','used','using','get','got','set','make','made','way','even',
    'work','works','working','says','said','say','know','knows','knowing',
    'see','seen','seeing','form','forms','forming','part','parts','thing',
    'things','time','times','value','values','level','levels','type','types',
    'data','set','state','include','includes','including','represent','shows'
  ]
MERGE (w:Word {lemma: token})
ON CREATE SET w.node_id = 'word-' + token,
              w.surface_forms = [token],
              w.is_stopword = false,
              w.frequency = 1,
              w.first_seen = toString(datetime()),
              w.file_type = 'word'
ON MATCH SET w.frequency = coalesce(w.frequency, 0) + 1
MERGE (w)-[:APPEARS_IN {field: 'description'}]->(n);

-- Phase 5: Extract vocabulary from Protocols
MATCH (n:Protocol)
WHERE n.node_id IS NOT NULL
  AND coalesce(n.description, n.explanation, '') <> ''
WITH n, apoc.text.split(
  toLower(coalesce(n.description, '') + ' ' + coalesce(n.explanation, '')),
  '[^a-z0-9\\-]+'
) AS tokens
UNWIND tokens AS token
WITH n, token
WHERE size(token) > 2
  AND NOT token IN [
    'the','and','for','that','this','with','from','are','not','has','was',
    'but','all','its','can','via','one','also','each','will','may','does',
    'into','than','when','been','have','any','our','how','who','what','them',
    'then','they','which','there','these','those','only','more','some','such',
    'other','over','very','just','about','after','would','should','could',
    'being','most','must','were','where','same','like','both','here','many',
    'well','should','could','would','could','going','being','having','let',
    'new','use','used','using','get','got','set','make','made','way','even',
    'work','works','working','says','said','say','know','knows','knowing',
    'see','seen','seeing','form','forms','forming','part','parts','thing',
    'things','time','times','value','values','level','levels','type','types',
    'data','set','state','include','includes','including','represent','shows'
  ]
MERGE (w:Word {lemma: token})
ON CREATE SET w.node_id = 'word-' + token,
              w.surface_forms = [token],
              w.is_stopword = false,
              w.frequency = 1,
              w.first_seen = toString(datetime()),
              w.file_type = 'word'
ON MATCH SET w.frequency = coalesce(w.frequency, 0) + 1
MERGE (w)-[:APPEARS_IN {field: 'description'}]->(n);

============================================================================
Atom: Identify central terms for each Concept
============================================================================

-- For each Concept, find the word that appears most often in its description
-- and create a :CENTRAL_TO edge to mark semantic primacy
MATCH (w:Word)-[a:APPEARS_IN]->(c:Concept)
WITH c, w, count(a) AS mentions
ORDER BY c.node_id, mentions DESC
WITH c, head(collect(w)) AS central_word
MERGE (central_word)-[:CENTRAL_TO]->(c);

============================================================================
End Protocol
============================================================================
