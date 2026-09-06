// @node_id: protocol-route-input
// @label: Route Natural Language Input
// @kind: protocol
// @description: Classify raw user input intent (action_verb/interrogative/identity/literal_cmd) and return target cmd_name with args. Routes based on vocab in graph, not regex.

// Atom 1: Extract first word from input
WITH split($input, ' ') AS words
WITH words[0] AS first_word, $input AS full_input
RETURN first_word, full_input;

// Atom 2: Check for identity responses first (most specific, whole-phrase matching)
WITH $first_word AS first_word, $full_input AS full_input
OPTIONAL MATCH (vocab:IntentVocab)-[:HAS_IDENTITY]->(idt:IdentityResponse)
WHERE any(p IN [idt.pattern] WHERE full_input CONTAINS p)
RETURN CASE
  WHEN idt IS NOT NULL THEN 'identity:' + idt.response
  ELSE 'continue'
END AS route_result;

// Atom 3: Check if first word is an action verb
WITH CASE WHEN route_result = 'continue' THEN 'check_action' ELSE route_result END AS next_step,
     first_word, full_input
OPTIONAL MATCH (av:IntentVerb {word: first_word})
WHERE av.intent_class = 'action'
RETURN CASE
  WHEN next_step STARTS WITH 'identity' THEN next_step
  WHEN av IS NOT NULL THEN 'action:' + av.target_cmd + '|' + av.target_args
  ELSE 'continue'
END AS route_result;

// Atom 4: Check if first word is an interrogative
WITH CASE WHEN route_result = 'continue' THEN 'check_interrogative' ELSE route_result END AS next_step,
     first_word, full_input
OPTIONAL MATCH (iv:IntentInterrogative {word: first_word})
WHERE iv.intent_class = 'interrogative'
RETURN CASE
  WHEN next_step STARTS WITH 'identity' OR next_step STARTS WITH 'action' THEN next_step
  WHEN iv IS NOT NULL THEN 'interrogative:' + iv.target_cmd
  ELSE 'literal_cmd'
END AS route_result;

// Atom 5: Determine final routing and return target command
WITH route_result, first_word, full_input
RETURN CASE
  WHEN route_result STARTS WITH 'identity:' THEN
    // Identity response: special return format
    {cmd_name: 'identity', response: substring(route_result, 10), input: full_input}
  WHEN route_result STARTS WITH 'action:' THEN
    // Action verb: extract cmd and args
    {cmd_name: split(substring(route_result, 8), '|')[0],
     args: split(substring(route_result, 8), '|')[1],
     input: full_input}
  WHEN route_result STARTS WITH 'interrogative:' THEN
    // Interrogative: route to ask
    {cmd_name: split(substring(route_result, 15), '|')[0],
     args: '',
     input: full_input}
  ELSE
    // Literal command: use first word as cmd_name, rest as args
    {cmd_name: first_word, args: substring(full_input, length(first_word) + 1), input: full_input}
END AS route_decision;
