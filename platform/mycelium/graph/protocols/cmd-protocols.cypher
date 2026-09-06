// @node_id: protocol-cmd-protocols
// @label: Protocols Command — telemetry view across all Protocols
// @kind: command
// @description: Lists every Protocol with its run_count, error_count, last_run_status, last_run_ms. Added by proprioception Phase 2.

// Atom 1: Summary header — how many protocols have ever run vs never run
MATCH (p:Protocol)
WITH count(p) AS total,
     count(CASE WHEN p.run_count IS NOT NULL AND p.run_count > 0 THEN 1 END) AS run_at_least_once,
     count(CASE WHEN p.error_count IS NOT NULL AND p.error_count > 0 THEN 1 END) AS has_errors,
     count(CASE WHEN p.last_run_status = 'running' THEN 1 END) AS currently_running,
     count(CASE WHEN p.last_run_status = 'ok' THEN 1 END) AS last_ok
RETURN 'summary|total:' + toString(total)
       + ' ever_ran:' + toString(run_at_least_once)
       + ' with_errors:' + toString(has_errors)
       + ' last_ok:' + toString(last_ok)
       + ' stuck_running:' + toString(currently_running) AS result;

// Atom 2: Per-protocol telemetry, sorted by most-recently-run first.
// Only shows Protocols that have actual telemetry (run_count > 0) so the
// output stays readable.
MATCH (p:Protocol)
WHERE p.run_count IS NOT NULL AND p.run_count > 0
WITH p
ORDER BY coalesce(p.last_run_started_ms, 0) DESC
LIMIT 25
RETURN 'protocol|'
       + coalesce(p.node_id, '?') + '|'
       + 'runs:' + toString(p.run_count) + ' '
       + 'errs:' + toString(coalesce(p.error_count, 0)) + ' '
       + 'status:' + coalesce(p.last_run_status, '-') + ' '
       + 'last_ms:' + toString(coalesce(p.last_run_ms, 0))
       + CASE WHEN p.last_run_error IS NOT NULL AND p.last_run_error <> ''
              THEN ' err=' + substring(p.last_run_error, 0, 60)
              ELSE '' END AS result;

// Atom 3: Failure hotlist — protocols whose error rate is >= 20% over >= 5 runs
MATCH (p:Protocol)
WHERE p.run_count IS NOT NULL AND p.run_count >= 5
  AND toFloat(coalesce(p.error_count, 0)) / toFloat(p.run_count) >= 0.2
WITH p, toFloat(coalesce(p.error_count, 0)) / toFloat(p.run_count) AS err_rate
ORDER BY err_rate DESC
LIMIT 10
RETURN 'failing|' + coalesce(p.node_id, '?')
       + '|err_rate:' + toString(round(err_rate * 100) / 100)
       + ' (' + toString(coalesce(p.error_count, 0)) + '/' + toString(p.run_count) + ')' AS result;
