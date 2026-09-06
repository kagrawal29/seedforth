// @node_id: invariant-prod-admin-only
// @label: "Prod bootstrap runs only when admin-triggered"
// @scope: team
// ============================================================================
// Enforces decision-deploy-flow-v1 step 7: prod Neo4j must not be bootstrapped
// by the autodeploy webhook receiver. Any :BootstrapRun against target=prod
// that was fired by the webhook (not by an admin) is a violation.
//
// Depends on :BootstrapRun nodes (wi-sync-05 / #76). Until those land, this
// invariant cannot compute healthy=true definitively — its fallback is
// "alarm if webhook receiver has prod in MAVERICK_WEBHOOK_TARGETS".
// ============================================================================

MERGE (inv:Invariant {node_id: 'invariant-prod-admin-only'})
SET inv.label            = 'Prod bootstrap runs only when admin-triggered',
    inv.scope            = 'team',
    inv.severity         = 'critical',
    inv.category         = 'deploy-policy',
    inv.enforces_decision = 'decision-deploy-flow-v1',
    inv.heal_protocol_id  = 'protocol-enforce-prod-admin-only',
    inv.heal_protocol     = 'enforce-prod-admin-only',

    inv.check_cypher =
      "MATCH (br:BootstrapRun) WHERE br.target = 'prod' AND br.fired_by <> 'admin' " +
      "WITH collect(br) AS violations " +
      "RETURN " +
      "  size(violations) = 0 AS healthy, " +
      "  size(violations) AS violation_count, " +
      "  CASE WHEN size(violations) = 0 THEN 'Prod bootstraps all admin-triggered' " +
      "       ELSE 'Webhook-fired prod bootstrap detected — deploy-flow-v1 violated' END AS reason",

    inv.created_at       = datetime('2026-04-21T11:00:00Z');

MERGE (ap:ActionProposal {node_id: 'ap-invariant-prod-admin-only-setup'})
SET ap.title            = 'Operationalise invariant-prod-admin-only: disable prod webhook firing until admin-gate ships',
    ap.for_scope        = 'team',
    ap.status           = 'queued',
    ap.created_at       = datetime('2026-04-21T11:00:00Z'),
    ap.rationale        = 'Today MAVERICK_WEBHOOK_TARGETS includes prod. Until the admin-only promote path is built (see oq-maverick-promote-auth), the safest step is to drop prod from the webhook targets so no automated prod bootstrap can occur.',
    ap.action_steps = [
      'Edit /etc/systemd/system/maverick-autodeploy-webhook.service.d/ to set MAVERICK_WEBHOOK_TARGETS=dev only.',
      'systemctl daemon-reload && systemctl restart maverick-autodeploy-webhook.service.',
      'Disable mycelium-autodeploy-prod.timer (no polling path to prod either).',
      'Update deploy/maverick-autodeploy-webhook.service default in repo so fresh installs match.'
    ];

MERGE (inv)-[:SURFACED_AS]->(ap);

RETURN
  'invariant-prod-admin-only registered; ap-invariant-prod-admin-only-setup queued' AS status;
