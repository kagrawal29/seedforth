// @node_id: intent-vocab-seed
// @label: Intent Vocabulary Bootstrap
// @kind: bootstrap
// @description: Seeds IntentVocab nodes with action verbs, interrogatives, and identity responses

MERGE (vocab:IntentVocab {node_id: 'vocab-intent-core'})
SET vocab.label = 'Intent Vocabulary', vocab.version = '1.0', vocab.created_at = datetime(), vocab.description = 'Central vocabulary for natural language intent classification'
RETURN 'step 1 complete' AS status;

MATCH (vocab:IntentVocab {node_id: 'vocab-intent-core'})
UNWIND ['fix', 'heal', 'run', 'check', 'verify', 'clean', 'update', 'resolve', 'improve', 'repair', 'optimize', 'refresh', 'restart'] AS verb
MERGE (av:IntentVerb {word: verb})
SET av.label = 'Action verb: ' + verb, av.intent_class = 'action', av.target_cmd = 'agent', av.target_args = '--max-iter 3', av.embedding_pending = true, av.created_at = datetime()
MERGE (vocab)-[:HAS_VERB]->(av)
RETURN 'action verbs created' AS status;

MATCH (vocab:IntentVocab {node_id: 'vocab-intent-core'})
UNWIND ['what', 'how', 'why', 'when', 'where', 'who', 'is', 'are', 'do', 'does', 'can', 'could', 'tell', 'show', 'help'] AS query
MERGE (iv:IntentInterrogative {word: query})
SET iv.label = 'Interrogative: ' + query, iv.intent_class = 'interrogative', iv.target_cmd = 'ask', iv.target_args = '', iv.embedding_pending = true, iv.created_at = datetime()
MERGE (vocab)-[:HAS_INTERROGATIVE]->(iv)
RETURN 'interrogatives created' AS status;

MATCH (vocab:IntentVocab {node_id: 'vocab-intent-core'})
UNWIND [
  {pattern: 'who are you', response: 'I am Mycelium -- a living knowledge graph with 12,000+ nodes.'},
  {pattern: 'what are you', response: 'I am Mycelium -- a living knowledge graph with 12,000+ nodes.'},
  {pattern: 'introduce yourself', response: 'I am Mycelium -- a living knowledge graph with 12,000+ nodes.'},
  {pattern: 'what is mycelium', response: 'I am Mycelium -- a living knowledge graph with 12,000+ nodes.'}
] AS identity_entry
MERGE (idt:IdentityResponse {pattern: identity_entry.pattern})
SET idt.label = 'Identity: ' + identity_entry.pattern, idt.response = identity_entry.response, idt.intent_class = 'identity', idt.created_at = datetime()
MERGE (vocab)-[:HAS_IDENTITY]->(idt)
RETURN 'identity responses created' AS status;
