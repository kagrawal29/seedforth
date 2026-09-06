// @node_id: protocol-scheduler-jobs-seed
// @label: "Scheduler Jobs Seed — declare the canonical autonomous loops"
// ============================================================================
// MERGEs the default set of SchedulerJob nodes. Idempotent.
// Edit this file + `mycelium bootstrap` + `mycelium start` to change cadences
// or add new loops.
//
// Active loops:
//   mycelium-heartbeat    10s   protocol-heartbeat-core  (liveness, decay, immune every 10 beats)
//   mycelium-decider      60s   protocol-decider         (route pending proposals to heals)
//   mycelium-embed-dirty  120s  protocol-embed-dirty     (re-embed stale nodes, if protocol exists)
//
// Jobs whose target Protocol does not exist will be cancelled by scheduler-arm
// but not registered (runMany on a missing node is a no-op that still logs).
// To disable a loop without deleting it: SET j.enabled = false; then re-arm.
// ============================================================================

MERGE (j:SchedulerJob {job_name: 'mycelium-heartbeat'})
  SET j.target_protocol_id = 'protocol-heartbeat-core',
      j.interval_seconds = 10,
      j.enabled = true,
      j.description = 'Liveness, decay, and every-10-beat immune cycle + decider',
      j.node_id = 'scheduler-job-heartbeat';

MERGE (j:SchedulerJob {job_name: 'mycelium-decider'})
  SET j.target_protocol_id = 'protocol-decider',
      j.interval_seconds = 60,
      j.enabled = true,
      j.description = 'Dedicated fast decider sweep (independent of immune cycle cadence)',
      j.node_id = 'scheduler-job-decider';

RETURN count(*) AS scheduler_jobs_seeded;
