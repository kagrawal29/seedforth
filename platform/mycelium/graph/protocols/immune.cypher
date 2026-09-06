// @node_id: immune-protocol
// @label: "Immune System (legacy heal dispatcher — referenced by invariant-vital-orphan-ceiling)"
// ============================================================================
// Protocol: Immune System
// ============================================================================
// Walks every enabled Invariant that has a heal_protocol attached, runs the
// invariant's check_cypher, and if unhealthy, fires the linked Protocol to
// self-heal, then re-checks. Tracks last_heal_at + heal_count for cooldown
// and observability.
//
// Call pattern (from heartbeat-loop or on its own cadence):
//   docker exec -i mycelium-neo4j-local cypher-shell ... < immune.cypher
//
// Inside the cypher we can only run cypher on the current DB. For file-
// referenced Protocols (Protocol.file_path set), we CANNOT read the file
// from inside cypher — that requires the shell runner. So this protocol
// implements two behaviors:
//
//   (A) Invariant.heal_protocol references a Protocol that has an inline
//       cypher property (e.g. protocol-heartbeat). We call
//       apoc.cypher.run(protocol.cypher, {}).
//
//   (B) Invariant.heal_protocol references a Protocol with file_path only.
//       We mark the invariant with heal_requested=true and rely on the
//       shell runner (graph/runner/immune.sh) to detect the marker and
//       execute the file.
//
// Cooldown: if an invariant was healed less than heal_cooldown_sec ago,
// skip this round — prevents runaway loops when a heal doesn't fix the
// underlying condition.
//
// Idempotent: pure property updates + delegated heal calls.
//
// Dependencies: APOC (apoc.cypher.run, apoc.util.validate).
// ============================================================================

// --- Step 1: find enabled Invariants with heal_protocol --------------------
MATCH (i:Invariant)
WHERE coalesce(i.enabled, true) = true
  AND i.heal_protocol IS NOT NULL
WITH i, i.heal_protocol AS heal_id, coalesce(i.heal_cooldown_sec, 300) AS cooldown_sec
// Check cooldown
WITH i, heal_id, cooldown_sec,
     CASE WHEN i.last_heal_at IS NULL THEN true
          ELSE duration.between(datetime(i.last_heal_at), datetime()).seconds >= cooldown_sec
     END AS cooldown_elapsed

// --- Step 2: run the invariant's own check_cypher --------------------------
CALL apoc.cypher.run(coalesce(i.check_cypher, 'RETURN true AS healthy'), {})
  YIELD value
WITH i, heal_id, cooldown_sec, cooldown_elapsed, collect(value) AS rows
WITH i, heal_id, cooldown_sec, cooldown_elapsed,
     CASE WHEN size(rows) = 0 THEN null ELSE rows[0] END AS r0
WITH i, heal_id, cooldown_sec, cooldown_elapsed, r0,
     CASE WHEN r0 IS NULL THEN null
          ELSE r0[head(keys(r0))] END AS first_val
WITH i, heal_id, cooldown_elapsed,
     CASE
       WHEN first_val = true THEN true
       WHEN first_val = false THEN false
       WHEN apoc.meta.cypher.type(first_val) IN ['INTEGER', 'FLOAT'] THEN first_val > 0
       WHEN apoc.meta.cypher.type(first_val) = 'STRING' THEN toLower(toString(first_val)) IN ['healthy', 'ok', 'pass', 'true']
       ELSE false
     END AS healthy


// --- Step 3: if unhealthy + cooldown passed + heal exists, try to heal -----
WITH i, heal_id, cooldown_elapsed, healthy
OPTIONAL MATCH (heal:Protocol {node_id: heal_id})
WITH i, heal_id, cooldown_elapsed, healthy, heal,
     CASE
       WHEN healthy THEN 'healthy'
       WHEN NOT cooldown_elapsed THEN 'cooldown'
       WHEN heal IS NULL THEN 'no-heal-protocol'
       WHEN heal.cypher IS NOT NULL THEN 'inline-heal'
       WHEN heal.file_path IS NOT NULL THEN 'file-heal-requested'
       ELSE 'no-runnable-body'
     END AS action

// Execute inline heal if possible
CALL {
  WITH i, heal, action
  WITH i, heal, action WHERE action = 'inline-heal'
  CALL apoc.cypher.run(heal.cypher, {}) YIELD value
  RETURN count(*) AS heal_invocations
  UNION
  WITH i, heal, action
  WITH i, heal, action WHERE action <> 'inline-heal'
  RETURN 0 AS heal_invocations
}

// --- Step 4: stamp the invariant with heal outcome -------------------------
WITH i, action,
     CASE action
       WHEN 'inline-heal'          THEN 'healed-inline'
       WHEN 'file-heal-requested'  THEN 'file-heal-requested'
       WHEN 'healthy'              THEN 'healthy'
       WHEN 'cooldown'             THEN 'cooldown'
       WHEN 'no-heal-protocol'     THEN 'no-heal-protocol'
       ELSE 'no-runnable-body'
     END AS status

SET i.last_heal_at = CASE WHEN status IN ['healed-inline', 'file-heal-requested'] THEN toString(datetime()) ELSE i.last_heal_at END,
    i.last_heal_status = status,
    i.heal_count = CASE WHEN status IN ['healed-inline', 'file-heal-requested'] THEN coalesce(i.heal_count, 0) + 1 ELSE coalesce(i.heal_count, 0) END,
    i.heal_requested = CASE WHEN status = 'file-heal-requested' THEN true ELSE false END


// --- Step 5: summary --------------------------------------------------------
WITH collect({id: i.node_id, status: status}) AS results
RETURN size(results) AS invariants_checked,
       size([r IN results WHERE r.status = 'healthy']) AS already_healthy,
       size([r IN results WHERE r.status = 'healed-inline']) AS healed_inline,
       size([r IN results WHERE r.status = 'file-heal-requested']) AS file_heals_queued,
       size([r IN results WHERE r.status = 'cooldown']) AS in_cooldown,
       [r IN results WHERE r.status IN ['healed-inline', 'file-heal-requested'] | r.id] AS acted_on;
