// @node_id: protocol-reregister-forest-heartbeat
// @label: "Reregister Forest Heartbeat — idempotent re-arm of the 30s Being sync job"
// ============================================================================
// Context:
//   The forest-heartbeat APOC periodic job is registered ad-hoc (not via a
//   SchedulerJob node) and is lost on every Neo4j restart or APOC job
//   expiry. This file re-registers it idempotently.
//
// What it does:
//   1. Cancels any existing forest-heartbeat job (safe no-op if absent).
//   2. Re-registers a 30s repeat that stamps last_heartbeat_at on every
//      :Being node across all 6 forest scopes.
//
// To apply (one-shot, read-only session is NOT enough — must be write session):
//   cypher-shell -a bolt://127.0.0.1:7688 -u neo4j -p "$ADMIN_PASS" \
//     --file graph/protocols/reregister-forest-heartbeat.cypher
//
// Or drop into the bootstrap sequence after scheduler-arm.cypher runs so
// that the forest-heartbeat survives reboots alongside mycelium-heartbeat.
//
// NOTE: this file does NOT register a SchedulerJob node (that would wire it
// into scheduler-arm.cypher and make it permanent across restarts). If you
// want it to survive restarts without manual re-fire, also run the companion
// seed below (Phase 2) and re-run scheduler-arm.cypher.
// ============================================================================

// --- Phase 1: Cancel any stale registration ---------------------------------
CALL apoc.periodic.cancel('forest-heartbeat') YIELD name AS _cancelled;

// --- Phase 2 (optional — uncomment to make permanent via scheduler-arm): ---
// MERGE (j:SchedulerJob {job_name: 'forest-heartbeat'})
//   SET j.target_protocol_id  = 'protocol-forest-heartbeat-core',
//       j.interval_seconds    = 30,
//       j.enabled             = true,
//       j.description         = 'Stamp last_heartbeat_at on all Being nodes across all forest scopes',
//       j.node_id             = 'scheduler-job-forest-heartbeat';

// --- Phase 3: Re-register the 30s forest heartbeat -------------------------
// Updates last_heartbeat_at (ISO 8601 string) and last_heartbeat (epoch ms)
// on every :Being node in the forest, regardless of project scope.
// apoc.cypher.runMany is used (not apoc.cypher.run) because the APOC
// periodic executor runs with reduced token-write permissions; runMany
// permits multi-statement writes in that context.
CALL apoc.periodic.repeat(
  'forest-heartbeat',
  'MATCH (b:Being)
   SET b.last_heartbeat_at = toString(datetime()),
       b.last_heartbeat    = timestamp(),
       b.alive             = true
   RETURN count(b) AS beings_pulsed',
  30
) YIELD name
RETURN name AS registered_job, 30 AS interval_seconds, 'all :Being nodes' AS scope;
