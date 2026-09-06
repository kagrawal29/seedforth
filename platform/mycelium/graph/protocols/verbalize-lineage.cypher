// @node_id: protocol-verbalize-lineage
// @label: "Verbalize Lineage"
// ============================================================================
// Protocol: Verbalize Lineage
// ============================================================================
// Purpose:
//   Given any node_id ($target), walk the lineage chain
//   (Research -> Hypothesis -> Skill -> Workflow -> Feature)
//   and emit a single natural-language sentence narrating how that node
//   came to exist.
//
// Parameters:
//   $target  — node_id of the starting point (any node in the lineage chain)
//
// Output columns:
//   sentence     — the composed narrative string
//   node_names   — ordered list of display names visited (ancestor first)
//   node_ids     — ordered list of node_ids visited (ancestor first)
//
// Algorithm:
//   1. Load EdgeConnective phrases from the graph (runtime, not hardcoded).
//   2. From $target, find the connected lineage component (all nodes reachable
//      bidirectionally within the lineage edge whitelist).
//   3. Within that component, identify roots: nodes with no incoming lineage
//      edges (these are the oldest ancestors — Research, Feature, etc.).
//   4. From each root, walk outward (bidirectional, up to 6 hops) to find all
//      simple paths that pass through $target.
//   5. Score each candidate path by how well its nodes follow the canonical
//      lineage label order (Research=0, Hypothesis=1, Skill=2, Workflow=3,
//      Feature=4). Higher monotone-increase score = cleaner narrative.
//   6. Orient the winning path so it reads ancestor-first (lowest label
//      priority first, e.g. Research before Feature).
//   7. For each step detect traversal direction (startNode vs position in path).
//      Forward  -> use ec.phrase.
//      Backward -> use ec.inverse_phrase (falls back to "connects to" if unset).
//   8. Stitch: first node name, then for each subsequent step "phrase dst",
//      joined with commas.
//   9. If no lineage path exists, return a graceful no-lineage message.
//
// Edge whitelist (lineage vocabulary only — keeps traversal focused):
//   ORIGINATES, LEADS_TO, POWERS, IMPLEMENTS_VIA, TESTS_HYPOTHESIS, SURFACES_IN
//
// Connectives are read from :EdgeConnective nodes at runtime (not hardcoded).
// To set a backward phrase for any edge type, add inverse_phrase to its node:
//   MATCH (ec:EdgeConnective {edge_type: 'IMPLEMENTS_VIA'})
//   SET ec.inverse_phrase = 'which implements'
//
// Idempotent: pure READ query — no mutations. Safe to run anytime.
// ============================================================================

// 1. Load EdgeConnective vocabulary for the lineage edge set ------------------
MATCH (ec:EdgeConnective)
WHERE ec.edge_type IN [
  'ORIGINATES', 'LEADS_TO', 'POWERS',
  'IMPLEMENTS_VIA', 'TESTS_HYPOTHESIS', 'SURFACES_IN'
]
WITH collect({
  edge_type:      ec.edge_type,
  phrase:         coalesce(ec.phrase,         ec.edge_type),
  inverse_phrase: coalesce(ec.inverse_phrase, 'connects to')
}) AS connective_map

// 2. Locate the target node ---------------------------------------------------
MATCH (target)
WHERE target.node_id = $target

// 3. Find connected lineage component from target ----------------------------
// Collect all nodes reachable bidirectionally via lineage edges, including target
OPTIONAL MATCH (target)-[:ORIGINATES|LEADS_TO|POWERS|IMPLEMENTS_VIA|TESTS_HYPOTHESIS|SURFACES_IN*0..6]-(connected)
WITH target, connective_map,
     collect(DISTINCT connected) AS component_raw

// 4. Identify roots in the component (no incoming lineage edges) --------------
WITH target, connective_map, component_raw
UNWIND component_raw AS cn
WITH target, connective_map, component_raw, cn
WHERE NOT exists(
  (cn)<-[:ORIGINATES|LEADS_TO|POWERS|IMPLEMENTS_VIA|TESTS_HYPOTHESIS|SURFACES_IN]-()
)
WITH target, connective_map, collect(DISTINCT cn) AS roots, component_raw

// Guard: if no roots found (disconnected or isolated node), use target itself
WITH target, connective_map,
     CASE WHEN size(roots) = 0 THEN [target] ELSE roots END AS roots,
     component_raw

// 5. From each root, find simple paths (bidirectional) through target ---------
UNWIND roots AS root
OPTIONAL MATCH p_through = (root)
  -[:ORIGINATES|LEADS_TO|POWERS|IMPLEMENTS_VIA|TESTS_HYPOTHESIS|SURFACES_IN*1..6]-
  (end_n)
WHERE target IN nodes(p_through)
  AND all(n IN nodes(p_through) WHERE single(x IN nodes(p_through) WHERE x = n))

WITH target, connective_map, collect(p_through) AS candidate_paths

// 6. Score each path by canonical label-order monotonicity --------------------
// Label priority: Research=0, Hypothesis=1, Skill=2, Workflow=3, Feature=4, other=5
// Score = count of consecutive steps where priority is non-decreasing
// Also record whether the path needs reversing (if last node has lower priority
// than first, reverse for ancestor-first narrative).
WITH target, connective_map,
     [p IN candidate_paths WHERE p IS NOT NULL |
       {
         path: p,
         score: reduce(
           s = 0, i IN range(0, length(p)-1) |
           s + CASE WHEN
             (CASE WHEN nodes(p)[i]:Research   THEN 0
                   WHEN nodes(p)[i]:Hypothesis THEN 1
                   WHEN nodes(p)[i]:Skill      THEN 2
                   WHEN nodes(p)[i]:Workflow   THEN 3
                   WHEN nodes(p)[i]:Feature    THEN 4
                   ELSE 5 END)
             <=
             (CASE WHEN nodes(p)[i+1]:Research   THEN 0
                   WHEN nodes(p)[i+1]:Hypothesis THEN 1
                   WHEN nodes(p)[i+1]:Skill      THEN 2
                   WHEN nodes(p)[i+1]:Workflow   THEN 3
                   WHEN nodes(p)[i+1]:Feature    THEN 4
                   ELSE 5 END)
             THEN 1 ELSE 0 END
         ),
         hops: length(p)
       }
     ] AS scored_paths

// 7. Select best path (highest score, then longest hops) ---------------------
WITH target, connective_map, scored_paths,
     CASE size(scored_paths)
       WHEN 0 THEN null
       ELSE reduce(best = scored_paths[0], c IN scored_paths |
              CASE
                WHEN c.score > best.score                        THEN c
                WHEN c.score = best.score AND c.hops > best.hops THEN c
                ELSE best
              END).path
     END AS best_path

// 8. Extract and orient nodes/rels from the winning path ---------------------
WITH target, connective_map, best_path,
     CASE WHEN best_path IS NULL THEN [] ELSE nodes(best_path)         END AS raw_nodes,
     CASE WHEN best_path IS NULL THEN [] ELSE relationships(best_path) END AS raw_rels

// Orient ancestor-first: compare label priority of first vs last node.
// If first node has higher priority (= more downstream), reverse both arrays.
WITH target, connective_map, raw_nodes, raw_rels,
     CASE
       WHEN size(raw_nodes) = 0 THEN false
       WHEN
         (CASE WHEN raw_nodes[0]:Research   THEN 0
               WHEN raw_nodes[0]:Hypothesis THEN 1
               WHEN raw_nodes[0]:Skill      THEN 2
               WHEN raw_nodes[0]:Workflow   THEN 3
               WHEN raw_nodes[0]:Feature    THEN 4
               ELSE 5 END)
         >
         (CASE WHEN raw_nodes[size(raw_nodes)-1]:Research   THEN 0
               WHEN raw_nodes[size(raw_nodes)-1]:Hypothesis THEN 1
               WHEN raw_nodes[size(raw_nodes)-1]:Skill      THEN 2
               WHEN raw_nodes[size(raw_nodes)-1]:Workflow   THEN 3
               WHEN raw_nodes[size(raw_nodes)-1]:Feature    THEN 4
               ELSE 5 END)
         THEN true
       ELSE false
     END AS should_reverse

WITH target, connective_map,
     CASE WHEN should_reverse THEN reverse(raw_nodes) ELSE raw_nodes END AS ord_nodes,
     CASE WHEN should_reverse THEN reverse(raw_rels)  ELSE raw_rels  END AS ord_rels

// 9. Build per-step data with direction flags and display names ---------------
// Display name priority: name -> topic (Research) -> claim (Hypothesis) ->
//                        label -> node_id
// is_forward = true when startNode(rel) matches the src position in path.
WITH target, connective_map, ord_nodes, ord_rels,
     [i IN range(0, size(ord_rels)-1) |
       {
         src_id:     ord_nodes[i].node_id,
         dst_id:     ord_nodes[i+1].node_id,
         src_name:   left(coalesce(
                       ord_nodes[i].name,
                       ord_nodes[i].topic,
                       ord_nodes[i].claim,
                       ord_nodes[i].label,
                       ord_nodes[i].node_id
                     ), 80),
         dst_name:   left(coalesce(
                       ord_nodes[i+1].name,
                       ord_nodes[i+1].topic,
                       ord_nodes[i+1].claim,
                       ord_nodes[i+1].label,
                       ord_nodes[i+1].node_id
                     ), 80),
         edge_type:  type(ord_rels[i]),
         is_forward: startNode(ord_rels[i]).node_id = ord_nodes[i].node_id
       }
     ] AS steps

// 10. Resolve connective phrase per step (lookup from EdgeConnective map) ------
WITH target, steps, connective_map,
     [step IN steps |
       {
         src_id:   step.src_id,
         dst_id:   step.dst_id,
         src_name: step.src_name,
         dst_name: step.dst_name,
         phrase:   coalesce(
                     head([c IN connective_map
                           WHERE c.edge_type = step.edge_type
                             AND step.is_forward
                           | c.phrase]),
                     head([c IN connective_map
                           WHERE c.edge_type = step.edge_type
                             AND NOT step.is_forward
                           | c.inverse_phrase]),
                     '(via ' + step.edge_type + ')'
                   )
       }
     ] AS resolved

// 11. Build sentence and metadata lists ---------------------------------------
// Sentence pattern:
//   "<src0> <phrase0> <dst0>, <phrase1> <dst1>, ..."
// Only the first fragment includes the root node name; subsequent fragments
// only append "phrase dst" so node names are not repeated.
WITH target, resolved,
     CASE
       WHEN size(resolved) = 0 THEN []
       ELSE
         [resolved[0].src_name + ' ' + resolved[0].phrase + ' ' + resolved[0].dst_name]
         + [step IN resolved[1..] | step.phrase + ' ' + step.dst_name]
     END AS fragments,
     CASE
       WHEN size(resolved) = 0 THEN [left(coalesce(target.name, target.topic, target.claim, target.node_id), 80)]
       ELSE [step IN resolved | step.src_name] + [resolved[size(resolved)-1].dst_name]
     END AS names_list,
     CASE
       WHEN size(resolved) = 0 THEN [target.node_id]
       ELSE [step IN resolved | step.src_id] + [resolved[size(resolved)-1].dst_id]
     END AS ids_list

// 12. Compose final sentence --------------------------------------------------
WITH target, fragments, names_list, ids_list,
     CASE
       WHEN size(fragments) = 0
         THEN 'No lineage traceable from ' +
              left(coalesce(target.name, target.topic, target.claim,
                            target.label, target.node_id), 80) + '.'
       ELSE reduce(s = fragments[0], frag IN fragments[1..] | s + ', ' + frag) + '.'
     END AS sentence

// 13. Return ------------------------------------------------------------------
RETURN
  sentence    AS sentence,
  names_list  AS node_names,
  ids_list    AS node_ids
