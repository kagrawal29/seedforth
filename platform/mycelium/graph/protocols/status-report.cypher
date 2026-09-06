// @node_id: protocol-status-report
// @label: "Status Report"
// ============================================================================
// Protocol: Status Report
// ============================================================================
// Comprehensive, cypher-native read-only status report that queries every
// stat the graph knows about itself and returns a single structured result.
//
// Output: one comprehensive result map containing all sections:
//   1. IDENTITY       - being_node_id, root_hash, species_id, heartbeat_count, last_heartbeat
//   2. SCALE          - total_nodes, total_edges, avg_edges_per_node, labels, rel_types, embedded_nodes, embedding_coverage_pct
//   3. LAYERS         - per-label counts (Protocols, Atoms, Commands, etc.) with health/status breakdowns
//   4. INTEGRITY      - merkle_healthy, orphan_nodes_count, untraced_protocols
//   5. LEARNING       - top 5 fired atoms, protocols, words, commands
//   6. GAPS           - pending questions by severity, top 3 blocking questions
//   7. ACTIVITY       - time-windowed query traces and prompts (last hour, last 24h)
//
// Constraints: read-only, runs in under 5 seconds on ~5k-node graph, handles missing data gracefully.
// ============================================================================

MATCH (b:Being {node_id: 'being-mycelium'})

// Gather global metrics
WITH b,
     timestamp() AS now_ms,
     3600000 AS one_hour_ms,
     86400000 AS one_day_ms

// SCALE section: graph size
OPTIONAL MATCH (n)
WITH b, now_ms, one_hour_ms, one_day_ms, count(n) AS total_nodes

OPTIONAL MATCH (r)-[]-()
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, count(r) AS total_edges

OPTIONAL MATCH (n WHERE n.embedding IS NOT NULL)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, count(n) AS embedded_nodes

CALL db.labels() YIELD label
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, count(label) AS total_labels

CALL db.relationshipTypes() YIELD relationshipType
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, count(relationshipType) AS total_rel_types

// LAYERS section: node type counts
MATCH (p:Protocol)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, count(p) AS protocol_count

OPTIONAL MATCH (a:CypherAtom)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, count(a) AS atom_count

OPTIONAL MATCH (c:Command)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, count(c) AS command_count

OPTIONAL MATCH (co:Concept)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, count(co) AS concept_count

OPTIONAL MATCH (g:Guide)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, count(g) AS guide_count

OPTIONAL MATCH (dp:DesignPrinciple)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, count(dp) AS principle_count

OPTIONAL MATCH (i:Invariant)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, count(i) AS invariant_count

OPTIONAL MATCH (tc:TestCase)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, count(tc) AS test_count

OPTIONAL MATCH (m:Metaphor)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, count(m) AS metaphor_count

OPTIONAL MATCH (ss:Subsystem)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, count(ss) AS subsystem_count

OPTIONAL MATCH (q:Question)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, count(q) AS question_count

OPTIONAL MATCH (pr:Prompt)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, count(pr) AS prompt_count

OPTIONAL MATCH (w:Word)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, count(w) AS word_count

OPTIONAL MATCH (sa:Subagent)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, count(sa) AS subagent_count

// Invariant health and test pass/fail
OPTIONAL MATCH (inv:Invariant WHERE inv.check_cypher IS NOT NULL)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count,
     count(CASE WHEN inv.health = 'healthy' THEN 1 END) AS inv_healthy,
     count(CASE WHEN inv.health = 'unhealthy' THEN 1 END) AS inv_unhealthy,
     count(CASE WHEN inv.health = 'error' THEN 1 END) AS inv_error

OPTIONAL MATCH (test:TestCase WHERE test.last_result IS NOT NULL)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error,
     count(CASE WHEN test.last_result = 'pass' THEN 1 END) AS test_passed,
     count(CASE WHEN test.last_result = 'fail' THEN 1 END) AS test_failed

// Question status
OPTIONAL MATCH (qu:Question WHERE qu.status IS NOT NULL)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed,
     count(CASE WHEN qu.status = 'pending' THEN 1 END) AS q_pending,
     count(CASE WHEN qu.status = 'answered' THEN 1 END) AS q_answered

// INTEGRITY: orphan nodes
OPTIONAL MATCH (orphan) WHERE NOT (orphan)--()
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered,
     count(orphan) AS orphan_count

// Untraced protocols
OPTIONAL MATCH (proto:Protocol WHERE proto.last_fired_at IS NOT NULL)
OPTIONAL MATCH (proto)<-[:FROM]-(qt:QueryTrace)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count,
     count(CASE WHEN qt IS NULL THEN 1 END) AS untraced_proto_count

// LEARNING: top performers (collect in nested queries)
OPTIONAL MATCH (atom:CypherAtom WHERE atom.fire_count IS NOT NULL)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count,
     atom, atom.fire_count AS afc ORDER BY afc DESC LIMIT 5
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count,
     collect({name: coalesce(atom.name, 'unnamed'), fire_count: afc}) AS top_atoms

OPTIONAL MATCH (prot:Protocol WHERE prot.fire_count IS NOT NULL)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms,
     prot, prot.fire_count AS pfc ORDER BY pfc DESC LIMIT 5
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms,
     collect({name: coalesce(prot.name, 'unnamed'), fire_count: pfc}) AS top_protocols

OPTIONAL MATCH (word:Word WHERE word.frequency IS NOT NULL)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols,
     word, word.frequency AS wf ORDER BY wf DESC LIMIT 5
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols,
     collect({text: coalesce(word.text, 'unknown'), frequency: wf}) AS top_words

OPTIONAL MATCH (cmd:Command)<-[:EXECUTED_BY]-(qtrace:QueryTrace)
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words,
     cmd, count(qtrace) AS trc ORDER BY trc DESC LIMIT 5
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words,
     collect({name: coalesce(cmd.name, 'unnamed'), trace_count: trc}) AS top_commands

// GAPS: question severity
OPTIONAL MATCH (qb:Question WHERE qb.status = 'pending' AND qb.severity = 'block')
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands,
     count(qb) AS q_block_count

OPTIONAL MATCH (qw:Question WHERE qw.status = 'pending' AND qw.severity = 'warn')
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands, q_block_count,
     count(qw) AS q_warn_count

OPTIONAL MATCH (qi:Question WHERE qi.status = 'pending' AND qi.severity = 'info')
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands, q_block_count, q_warn_count,
     count(qi) AS q_info_count

// Top blocking questions
OPTIONAL MATCH (qtop:Question WHERE qtop.status = 'pending' AND qtop.severity = 'block')
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands, q_block_count, q_warn_count, q_info_count,
     qtop ORDER BY qtop.raised_at DESC LIMIT 3
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands, q_block_count, q_warn_count, q_info_count,
     collect({text: coalesce(qtop.text, 'no text'), raised_by: coalesce(qtop.raised_by, 'unknown')}) AS blocking_questions

// ACTIVITY: time-windowed
OPTIONAL MATCH (qt1h:QueryTrace WHERE qt1h.invoked_epoch_ms IS NOT NULL AND qt1h.invoked_epoch_ms > (now_ms - one_hour_ms))
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands, q_block_count, q_warn_count, q_info_count, blocking_questions,
     count(qt1h) AS traces_1h

OPTIONAL MATCH (qt24h:QueryTrace WHERE qt24h.invoked_epoch_ms IS NOT NULL AND qt24h.invoked_epoch_ms > (now_ms - one_day_ms))
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands, q_block_count, q_warn_count, q_info_count, blocking_questions, traces_1h,
     count(qt24h) AS traces_24h

OPTIONAL MATCH (p1h:Prompt WHERE p1h.created_at_ms IS NOT NULL AND p1h.created_at_ms > (now_ms - one_hour_ms))
WITH b, now_ms, one_hour_ms, one_day_ms, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count, inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands, q_block_count, q_warn_count, q_info_count, blocking_questions, traces_1h, traces_24h,
     count(p1h) AS prompts_1h

// Calculate derived values
WITH b, total_nodes, total_edges, embedded_nodes, total_labels, total_rel_types, protocol_count, atom_count, command_count, concept_count, guide_count, principle_count, invariant_count, test_count, metaphor_count, subsystem_count, question_count, prompt_count, word_count, subagent_count,
     inv_healthy, inv_unhealthy, inv_error, test_passed, test_failed, q_pending, q_answered, orphan_count, untraced_proto_count, top_atoms, top_protocols, top_words, top_commands,
     q_block_count, q_warn_count, q_info_count, blocking_questions, traces_1h, traces_24h, prompts_1h,
     CASE WHEN total_nodes > 0 THEN round(toFloat(total_edges) / total_nodes, 2) ELSE 0 END AS avg_edges,
     CASE WHEN total_nodes > 0 THEN round(100.0 * embedded_nodes / total_nodes, 1) ELSE 0 END AS emb_coverage,
     b.leaf_hash IS NOT NULL AND b.root_hash IS NOT NULL AS merkle_ok

// Final result
RETURN {
  IDENTITY: {
    being_node_id: b.node_id,
    current_root_hash: coalesce(b.root_hash, 'null'),
    current_species_id: coalesce(b.species_id, 'null'),
    heartbeat_count: coalesce(b.heartbeat_count, 0),
    last_heartbeat: coalesce(b.last_heartbeat_at, 'never')
  },
  SCALE: {
    total_nodes: total_nodes,
    total_edges: total_edges,
    avg_edges_per_node: avg_edges,
    total_node_labels: total_labels,
    total_edge_types: total_rel_types,
    embedded_nodes: embedded_nodes,
    embedding_coverage_pct: emb_coverage
  },
  LAYERS: {
    protocol_count: protocol_count,
    atom_count: atom_count,
    command_count: command_count,
    concept_count: concept_count,
    guide_count: guide_count,
    principle_count: principle_count,
    invariant_count: invariant_count,
    invariants_healthy: inv_healthy,
    invariants_unhealthy: inv_unhealthy,
    invariants_error: inv_error,
    test_count: test_count,
    tests_passed: test_passed,
    tests_failed: test_failed,
    metaphor_count: metaphor_count,
    subsystem_count: subsystem_count,
    question_count: question_count,
    questions_pending: q_pending,
    questions_answered: q_answered,
    prompt_count: prompt_count,
    word_count: word_count,
    subagent_count: subagent_count
  },
  INTEGRITY: {
    merkle_healthy: merkle_ok,
    orphan_nodes_count: orphan_count,
    untraced_protocols: untraced_proto_count
  },
  LEARNING: {
    top_5_fired_atoms: top_atoms,
    top_5_fired_protocols: top_protocols,
    top_5_words_by_frequency: top_words,
    top_5_commands_by_trace_count: top_commands
  },
  GAPS: {
    pending_questions_by_severity: {
      block: q_block_count,
      warn: q_warn_count,
      info: q_info_count
    },
    top_3_blocking_questions: blocking_questions
  },
  ACTIVITY: {
    query_traces_last_hour: traces_1h,
    query_traces_last_24h: traces_24h,
    new_prompts_last_hour: prompts_1h,
    new_traces_last_24h: traces_24h
  }
} AS status_report;
