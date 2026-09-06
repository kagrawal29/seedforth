// @node_id: protocol-sequence-observe
// @label: "Sequence Observe (Markov Transition Recorder)"
// ============================================================================
// Protocol: Sequence Observe (Markov Transition Recorder)
// ============================================================================
// Activation event creation and temporal transition wiring. Runs RIGHT AFTER
// prompt-ingest to record the firing event and wire :THEN edges that turn the
// graph into a predictive model.
//
// This protocol separates the activation creation from the transition-wiring
// to avoid WITH-chain fragility. Two independent cypher statements:
//   STATEMENT 1: Create the :Activation node for the incoming prompt
//   STATEMENT 2: Wire :THEN edges from prior activations (300-second window)
//
// Parameters:
//   $prompt_text_hash  string - the text_hash of the :Prompt to activate
//   $source            string - 'cli' | 'script' | 'subagent' | 'swarm'
//   $command           string - 'ask' | 'swarm' | 'q' | etc.
//
// Side effects:
//   1. MERGE :Activation node keyed by node_id (deterministic from text_hash + timestamp)
//      with fields: activated_at_ms, activated_at, actor, command, kind, file_type
//   2. MERGE :OF edge from Activation to the Prompt
//   3. Find all Activations in the previous 300 seconds (5 min window)
//   4. MERGE :THEN edges from each prior to this one, aggregating
//      {count, total_delta_ms, avg_delta_ms, last_at_ms} so the graph builds
//      transition probabilities P(b|a) = edge.count / sum(outgoing from a)
//   5. Idempotent — re-invocation with same prompt_text_hash does not duplicate
//      (node_id is deterministic; MERGE is used throughout)
//
// Runs in <100ms typical. Safe if no prior activations exist (OPTIONAL MATCH).
// Gracefully returns empty result if the :Prompt doesn't exist (no error).
// ============================================================================


// --- Statement 1: Create the :Activation node for this prompt firing -------
// Key the node deterministically by text_hash + current timestamp so multiple
// firings of the same prompt create distinct Activation nodes (one per firing),
// but re-invoking this statement with the same params creates the same node
// (idempotent). Wire it to the :Prompt via :OF edge.

MATCH (p:Prompt {text_hash: $prompt_text_hash})
WITH p, timestamp() AS now_ms
CREATE (a:Activation {
  node_id: 'activation-' + $prompt_text_hash + '-' + toString(now_ms),
  activated_at_ms: now_ms,
  activated_at: toString(datetime()),
  actor: $source,
  command: $command,
  kind: 'prompt',
  file_type: 'activation'
})
MERGE (a)-[:OF]->(p)
RETURN a.node_id AS activation_id, now_ms AS activated_at_ms;


// --- Statement 2: Wire :THEN edges from prior activations to the newest ----
// Find the most recently created :Activation (the one from Statement 1).
// Then match all prior :Activation nodes fired within 300 seconds (5 min).
// For each prior, MERGE a :THEN edge (idempotent), aggregating counts.
//
// Pattern:
//   prior_activation --[THEN: {count, total_delta_ms, avg_delta_ms, last_at_ms}]--> new_activation
//
// Properties:
//   count         - number of times this transition was observed
//   total_delta_ms - cumulative milliseconds between the two activations
//   avg_delta_ms  - running average of the inter-activation delay
//   last_at_ms    - timestamp of the most recent observation
//
// After sufficient observations, count / sum(outgoing .count from prior)
// approximates P(next_activation | current_activation) — the transition probability.

MATCH (a:Activation)
WITH a ORDER BY a.activated_at_ms DESC LIMIT 1
WITH a, a.activated_at_ms AS newest_activated_ms, timestamp() AS now_ms

OPTIONAL MATCH (prev:Activation)
WHERE prev.activated_at_ms >= newest_activated_ms - 300000
  AND prev.activated_at_ms < newest_activated_ms
  AND prev.node_id <> a.node_id
WITH a, prev, newest_activated_ms - prev.activated_at_ms AS delta_ms, now_ms
WHERE prev IS NOT NULL

MERGE (prev)-[t:THEN]->(a)
  ON CREATE SET t.count = 1,
                t.total_delta_ms = delta_ms,
                t.avg_delta_ms = toFloat(delta_ms),
                t.last_at_ms = now_ms
  ON MATCH SET t.count = t.count + 1,
               t.total_delta_ms = t.total_delta_ms + delta_ms,
               t.avg_delta_ms = (t.total_delta_ms + delta_ms) / (t.count + 1),
               t.last_at_ms = now_ms

WITH a, count(t) AS then_edges_created
RETURN then_edges_created, a.activated_at_ms AS observed_at_ms;
