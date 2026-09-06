// @kind: seed
// ============================================================================
// Protocol: Commands Wire
// ============================================================================
// Densely wires Command nodes into the rest of the graph via four passes:
//
// 1. TYPED PROTOCOL LINKAGE  — MERGE :INVOKES edges from each Command to the
//    :Protocol it runs. Runner strings are parsed at Cypher time:
//      - "bash graph/runner/<script>.sh"  → protocol-<script> (stem without .sh)
//      - "docker exec ... < graph/protocols/<file>.cypher"  → protocol-<stem>
//      - "mycelium__builtin_*"  → no edge; sets command.builtin = true
//    INVOKES carries `runner_raw` (the original runner string) so the edge is
//    self-documenting and parseable by downstream protocols.
//
// 2. ALIAS EDGES  — MERGE bidirectional :ALIAS_OF edges between Command pairs
//    that share the same runner string (and neither is a builtin). Both
//    directions are created so traversal works either way.
//
// 3. MULTI-ANGLE EXPLANATION FIELDS  — SET three new properties on every
//    Command node for use by compose-reply depending on which SwarmRole
//    invoked the command:
//      angle_brief      — 120-char slice of description (quick lookup)
//      angle_teaching   — newbie-friendly sentence built from description + example
//      angle_technical  — operator-level sentence combining description + usage + example
//
// 4. CATEGORY → CONCEPT BRIDGE  — MERGE one :Concept node per distinct
//    category value (node_id: "concept-cmd-category-<category>") and create
//    :IN_CATEGORY edges from Command to that Concept, enabling "what health
//    commands do I have" style queries.
//
// Idempotent: all writes use MERGE or SET (SET overwrites are safe — these
// fields are deterministically derived from existing Command properties and
// will produce the same values on re-run). No CREATE.
//
// Dependencies: Command nodes must already exist (seeded by command-register.cypher).
// Protocol nodes must already exist for INVOKES edges to resolve.
// ============================================================================


// ============================================================================
// PASS 1 — Typed protocol linkage
// ============================================================================
// Sub-pass 1a: bash-runner commands → INVOKES the corresponding Protocol.
// Pattern: "bash graph/runner/<stem>.sh"
// Protocol node_id convention: protocol-<stem>
// e.g. runner "bash graph/runner/adopt-node.sh"  →  protocol "protocol-adopt-node"
// ============================================================================

MATCH (c:Command)
WHERE c.runner STARTS WITH "bash graph/runner/"
WITH c,
     replace(
       split(c.runner, "graph/runner/")[1],
       ".sh", ""
     ) AS proto_stem
WITH c, "protocol-" + proto_stem AS proto_id
MATCH (p:Protocol {node_id: proto_id})
MERGE (c)-[r:INVOKES]->(p)
ON CREATE SET
  r.runner_raw    = c.runner,
  r.resolved_at   = toString(datetime()),
  r.resolved_by   = "commands-wire.cypher"
ON MATCH SET
  r.runner_raw    = c.runner;


// ============================================================================
// Sub-pass 1b: docker-exec runner (breathe / cmd-heartbeat)
// Pattern: "docker exec -i mycelium-neo4j-local cypher-shell ... < graph/protocols/<stem>.cypher"
// Protocol node_id: protocol-<stem>
// ============================================================================

MATCH (c:Command)
WHERE c.runner STARTS WITH "docker exec"
  AND c.runner CONTAINS "graph/protocols/"
WITH c,
     replace(
       split(c.runner, "graph/protocols/")[1],
       ".cypher", ""
     ) AS proto_stem
WITH c, "protocol-" + proto_stem AS proto_id
MATCH (p:Protocol {node_id: proto_id})
MERGE (c)-[r:INVOKES]->(p)
ON CREATE SET
  r.runner_raw    = c.runner,
  r.resolved_at   = toString(datetime()),
  r.resolved_by   = "commands-wire.cypher"
ON MATCH SET
  r.runner_raw    = c.runner;


// ============================================================================
// Sub-pass 1c: builtin commands → no INVOKES edge; mark as builtin
// Pattern: "mycelium__builtin_*"
// ============================================================================

MATCH (c:Command)
WHERE c.runner STARTS WITH "mycelium__builtin"
SET c.builtin = true;


// ============================================================================
// PASS 2 — Alias edges
// ============================================================================
// Find pairs of non-builtin Commands that share the exact same runner string.
// MERGE :ALIAS_OF in BOTH directions so traversal works from either node.
// Self-loops are excluded (same node_id check).
// ============================================================================

MATCH (a:Command), (b:Command)
WHERE a.builtin IS NULL
  AND b.builtin IS NULL
  AND a.runner = b.runner
  AND a.node_id < b.node_id
MERGE (a)-[r1:ALIAS_OF]->(b)
ON CREATE SET
  r1.reason       = "shared_runner",
  r1.created_by   = "commands-wire.cypher",
  r1.created_at   = toString(datetime())
MERGE (b)-[r2:ALIAS_OF]->(a)
ON CREATE SET
  r2.reason       = "shared_runner",
  r2.created_by   = "commands-wire.cypher",
  r2.created_at   = toString(datetime());


// ============================================================================
// PASS 3 — Multi-angle explanation fields
// ============================================================================
// SET three derived properties on every Command node.
//
//   angle_brief      120-char slice of description — used for quick surface
//   angle_teaching   Newbie sentence: context + example invocation
//   angle_technical  Operator detail: full description + usage + example
//
// Uses toLower() + substring() — pure Cypher, no APOC needed.
// Double-quoted strings avoid apostrophe escaping issues.
// ============================================================================

MATCH (c:Command)
SET
  c.angle_brief      = substring(c.description, 0, 120),

  c.angle_teaching   = "If you are new, "
                       + toLower(substring(c.description, 0, 1))
                       + substring(c.description, 1)
                       + ". Try it with: "
                       + c.example,

  c.angle_technical  = c.description
                       + " Usage: "
                       + c.usage
                       + ". Example: "
                       + c.example
                       + ".";


// ============================================================================
// PASS 4 — Category → Concept bridge
// ============================================================================
// For each distinct category value found on Command nodes, MERGE a :Concept
// node with a stable node_id and human-readable label.  Then MERGE
// :IN_CATEGORY edges from every Command to its category Concept.
//
// Concept node_id format: "concept-cmd-category-<category>"
// This is query-friendly: MATCH (cat:Concept) WHERE cat.node_id STARTS WITH
// "concept-cmd-category-" RETURN cat.label finds all command categories.
// ============================================================================

MATCH (c:Command)
WITH DISTINCT c.category AS cat
WHERE cat IS NOT NULL
MERGE (concept:Concept {node_id: "concept-cmd-category-" + cat})
ON CREATE SET
  concept.label       = cat + " commands",
  concept.description = "Commands in the " + cat + " category.",
  concept.created_by  = "commands-wire.cypher",
  concept.created_at  = toString(datetime()),
  concept.file_type   = "concept";


MATCH (c:Command)
WHERE c.category IS NOT NULL
MATCH (concept:Concept {node_id: "concept-cmd-category-" + c.category})
MERGE (c)-[r:IN_CATEGORY]->(concept)
ON CREATE SET
  r.created_by = "commands-wire.cypher",
  r.created_at = toString(datetime());


// ============================================================================
// Verification summary
// ============================================================================

MATCH (c:Command)
RETURN
  count(c)               AS total_commands,
  count(c.angle_brief)   AS with_brief,
  count(c.angle_teaching) AS with_teaching,
  count(c.angle_technical) AS with_technical,
  count(CASE WHEN c.builtin = true THEN 1 END) AS builtin_commands;
