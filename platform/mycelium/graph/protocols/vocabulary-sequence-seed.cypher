// @kind: seed
// ============================================================================
// Protocol: Vocabulary + Sequence Seed
// ============================================================================
// Three layers in one dense seed:
//
//   LAYER 1 — Vocabulary
//     :Word        one per distinct lemma. Carries embedding (via embed-dirty).
//                  Frequency, first_seen, last_seen. Stopwords flagged.
//     :Prompt      one per distinct prompt text (hashed). Carries embedding,
//                  fire_count, source, command, raw_text, entered_at.
//                  Lives in the shared node_embeddings vector index so prompt
//                  retrieval is free — every new prompt finds its semantic
//                  neighbors across prompts, concepts, atoms, guides.
//     :CONTAINS    Prompt -> Word with {position, count}
//     :RESOLVED_TO Prompt -> (Concept|Protocol|Guide|…) with {cosine, rank}
//     :APPEARS_IN  Word -> Concept|Guide|Description source (inverted index)
//     :CO_OCCURS   Word -> Word with {count}  (word-pair within one text field)
//
//   LAYER 2 — Activation & Sequence
//     :Activation  an event: "node X was fired at time T by actor A". Lightweight.
//                  OF -> the actual node that fired.
//     :OF          Activation -> node it activated
//     :THEN        (Prompt|Concept|Protocol|Activation) -> (same) with
//                  {count, total_delta_ms, avg_delta_ms, last_at}
//                  Temporal transition edge. Sum counts across window W;
//                  P(b|a) = edge.count / sum(outgoing .count from a).
//                  This is the Markov transition layer. No LLM — pure
//                  counting over observed firings.
//
//   LAYER 3 — Language N-grams
//     :BIGRAM      Word -> Word with {count, last_at}  (word-pair within
//                  same prompt, ordered by position). After N prompts,
//                  this IS an n-gram language model of the operator's
//                  actual vocabulary. Future prompts can be predicted
//                  from bigram chains, autocompleted, or used as
//                  similarity boost for prompt cosine search.
//
// Everything uses the shared node_embeddings index. :Word and :Prompt
// are both embedded, both retrievable, both densifiable via
// semantic-densify / semantic-cluster / semantic-anomaly — the existing
// protocols work on them automatically because they key on n.embedding,
// not on label.
//
// This protocol seeds schema + indexes + stopwords + the first backfill
// from existing text-bearing nodes + retroactive :Prompt nodes from
// historical :QueryTrace cypher_summary values. Idempotent (MERGE only).
// ============================================================================


// --- Part 1: Indexes ------------------------------------------------------

CREATE INDEX word_lemma IF NOT EXISTS
  FOR (w:Word) ON (w.lemma);

CREATE INDEX prompt_text_hash IF NOT EXISTS
  FOR (p:Prompt) ON (p.text_hash);

CREATE INDEX activation_at IF NOT EXISTS
  FOR (a:Activation) ON (a.activated_at_ms);


// --- Part 2: Stopwords ----------------------------------------------------
// A standard English stopword set. Stored as :Word nodes with is_stopword=true
// so they are excluded from prompt-ingest token processing but still live in
// the graph if the user wants to inspect them.

UNWIND split('a about above after again against all am an and any are as at be because been before being below between both but by can cannot could did do does doing down during each few for from further had has have having he her here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not now of off on once only or other ought our ours out over own same she should so some such than that the their theirs them themselves then there these they this those through to too under until up very was we were what when where which while who whom why with would you your yours', ' ') AS sw
MERGE (w:Word {node_id: 'word-' + sw})
ON CREATE SET w.lemma = sw,
              w.surface_forms = [sw],
              w.is_stopword = true,
              w.frequency = 0,
              w.first_seen = toString(datetime()),
              w.pos = 'stopword',
              w.file_type = 'word';


// --- Part 3: Concept rows so docs layer covers the new labels -------------

MERGE (c:Concept {node_id: 'concept-word'})
SET c.name = 'Word',
    c.order = 34,
    c.category = 'language',
    c.description = 'A lemma (canonical word form) as a first-class graph citizen. Carries embedding, surface forms, frequency, and edges to everywhere it appears. Words are the compositional unit of prompt parsing: a prompt becomes its set of :Word nodes, and intent resolution is the intersection of their neighborhoods. Every word lives in the shared vector index so similar words (synonyms) cluster emergently.',
    c.example = 'MATCH (w:Word {lemma: "merkle"})-[:APPEARS_IN]->(target) RETURN target.node_id, labels(target)[0] AS kind',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-prompt'})
SET c.name = 'Prompt',
    c.order = 35,
    c.category = 'language',
    c.description = 'A natural-language query entering the system. Stored as a first-class node with its own embedding so it lives in the shared vector index alongside concepts, atoms, and guides. Repeat prompts hash to the same node and accumulate fire_count - the graph remembers what it was asked. Prompt-to-prompt cosine similarity is free, enabling cross-user prompt clustering and emergent FAQ discovery.',
    c.example = 'MATCH (p:Prompt)-[:RESOLVED_TO]->(c:Concept) RETURN p.raw_text, c.node_id, p.fire_count ORDER BY p.fire_count DESC LIMIT 10',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-activation'})
SET c.name = 'Activation',
    c.order = 36,
    c.category = 'sequence',
    c.description = 'An event: node X fired at time T by actor A. Lightweight node that sits between the thing that fired and the temporal transition graph. Activations are chained by :THEN edges whose counts become transition probabilities. The activation layer turns the graph from a passive lookup table into a predictive sequence model.',
    c.example = 'MATCH (a1:Activation)-[:THEN]->(a2:Activation) WHERE a2.activated_at_ms - a1.activated_at_ms < 60000 RETURN a1, a2',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-then-edge'})
SET c.name = 'THEN edge',
    c.order = 37,
    c.category = 'sequence',
    c.description = 'The Markov transition edge. Between any two nodes that fire within a time window, :THEN aggregates {count, total_delta_ms, avg_delta_ms, last_at}. After enough observations, count / sum(outgoing .count) gives P(b|a). The graph learns what usually follows what. Enables predictive prefetch, anomaly detection, emergent workflow discovery, and narrative explanation without any LLM.',
    c.example = 'MATCH (a)-[t:THEN]->(b) WITH a, sum(t.count) AS total, t, b WHERE a.node_id = "concept-merkle" RETURN b.node_id, toFloat(t.count)/total AS probability ORDER BY probability DESC LIMIT 5',
    c.file_type = 'concept';

MERGE (c:Concept {node_id: 'concept-bigram'})
SET c.name = 'Bigram edge',
    c.order = 38,
    c.category = 'language',
    c.description = 'Word-to-word transition edge within one prompt, ordered by token position. After N prompts the bigram graph IS an n-gram language model of the operator\\s actual vocabulary. Future prompts can be predicted, autocompleted, or distance-scored against this model as a similarity signal that complements cosine.',
    c.example = 'MATCH (w1:Word {lemma: "merkle"})-[b:BIGRAM]->(w2:Word) RETURN w2.lemma, b.count ORDER BY b.count DESC LIMIT 5',
    c.file_type = 'concept';

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (c:Concept) WHERE c.category IN ['language', 'sequence']
MERGE (c)-[:DESCRIBES_IN]->(o);


// --- Part 4: Retroactive :Prompt nodes from historical QueryTrace ---------
// Every existing :QueryTrace with a command of 'ask' or 'swarm' had a prompt
// in its cypher_summary. Promote those strings to first-class :Prompt nodes
// so the graph retroactively remembers what it has been asked. Embeddings
// get filled in by the next embed-dirty run.

MATCH (qt:QueryTrace)
WHERE qt.command IN ['ask', 'swarm']
  AND qt.cypher_summary IS NOT NULL
  AND qt.cypher_summary <> ''
WITH qt, replace(replace(qt.cypher_summary, 'cli:ask ', ''), 'cli:swarm ', '') AS prompt_text
WHERE size(prompt_text) > 2
WITH qt, prompt_text,
     'prompt-' + substring(
       replace(replace(replace(toLower(prompt_text), ' ', '-'), '"', ''), "'", ''),
       0, 60
     ) AS prompt_node_id
MERGE (p:Prompt {node_id: prompt_node_id})
ON CREATE SET p.raw_text = prompt_text,
              p.text_hash = toString(apoc.util.md5([prompt_text])),
              p.source = 'cli',
              p.command = qt.command,
              p.first_seen = toString(datetime()),
              p.last_seen = toString(datetime()),
              p.fire_count = 1,
              p.file_type = 'prompt'
ON MATCH SET p.fire_count = coalesce(p.fire_count, 0) + 1,
             p.last_seen = toString(datetime())
MERGE (p)<-[:EMITTED_PROMPT]-(qt);


// --- Part 5: Ontology linkage ---------------------------------------------

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (w:Word) MERGE (w)-[:WORD_OF]->(o);

MATCH (o:Ontology {node_id: 'ontology-mycelium'})
MATCH (p:Prompt) MERGE (p)-[:PROMPT_OF]->(o);


// --- Summary -------------------------------------------------------------

MATCH (w:Word) WITH count(w) AS total_words, sum(CASE WHEN w.is_stopword THEN 1 ELSE 0 END) AS stopwords
MATCH (p:Prompt) WITH total_words, stopwords, count(p) AS prompts
RETURN total_words, stopwords, prompts,
       'vocabulary + sequence layer seeded' AS status;
