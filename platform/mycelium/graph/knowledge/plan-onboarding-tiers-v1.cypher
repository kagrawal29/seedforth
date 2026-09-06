// @node_id: plan-onboarding-tiers-v1
// @label: Onboarding Tiers v1 — Read-Only + Editor, Safe Fork, Snapshot Rollback
// @kind: migration-plan
// @description: Teammate onboarding + safe local editing. Two tiers (readonly default, editor opt-in). Artifact-based fork, auto-snapshot ring buffer, conflict-aware sync, graph-native secret scrubber.

// ============================================================================
// PLAN NODE
// ============================================================================

MERGE (plan:MigrationPlan {node_id: 'plan-onboarding-tiers-v1'})
  SET plan.label            = 'Onboarding Tiers v1',
      plan.description      = 'Any teammate gets from git clone to productive in tier-appropriate time. Zero risk of losing local work. Clean PR-back flow to dev.',
      plan.status           = 'active',
      plan.created_at       = datetime(),
      plan.tiers            = ['readonly', 'editor'],
      plan.default_tier     = 'readonly',
      plan.ring_buffer_slots        = 3,
      plan.named_snapshot_keep_n    = 3,
      plan.artifact_refresh_trigger = 'post-autodeploy+manual',
      plan.project          = 'mycelium'
  RETURN plan.node_id AS result;

// ============================================================================
// WAVE NODES (execution groups)
// ============================================================================

MERGE (w1:Wave {node_id: 'wave-onboarding-1-readonly'}) SET w1.label='Wave 1 — Tier 1 (readonly) goes live', w1.order=1, w1.project='mycelium';
MERGE (w2:Wave {node_id: 'wave-onboarding-2-artifact'}) SET w2.label='Wave 2 — Fork artifact infra', w2.order=2, w2.project='mycelium';
MERGE (w3:Wave {node_id: 'wave-onboarding-3-fork-client'}) SET w3.label='Wave 3 — Fork client rewrite', w3.order=3, w3.project='mycelium';
MERGE (w4:Wave {node_id: 'wave-onboarding-4-editor'}) SET w4.label='Wave 4 — Tier editor (full stack + snapshots + conflict sync)', w4.order=4, w4.project='mycelium';
MERGE (w5:Wave {node_id: 'wave-onboarding-5-dogfood'}) SET w5.label='Wave 5 — Dogfood + knowledge seeding', w5.order=5, w5.project='mycelium';

MATCH (plan:MigrationPlan {node_id:'plan-onboarding-tiers-v1'})
MATCH (w:Wave) WHERE w.node_id STARTS WITH 'wave-onboarding-'
MERGE (plan)-[:CONTAINS]->(w);

MATCH (a:Wave {node_id:'wave-onboarding-1-readonly'}), (b:Wave {node_id:'wave-onboarding-2-artifact'}) MERGE (a)-[:FLOWS_TO]->(b);
MATCH (a:Wave {node_id:'wave-onboarding-2-artifact'}), (b:Wave {node_id:'wave-onboarding-3-fork-client'}) MERGE (a)-[:FLOWS_TO]->(b);
MATCH (a:Wave {node_id:'wave-onboarding-3-fork-client'}), (b:Wave {node_id:'wave-onboarding-4-editor'}) MERGE (a)-[:FLOWS_TO]->(b);
MATCH (a:Wave {node_id:'wave-onboarding-4-editor'}), (b:Wave {node_id:'wave-onboarding-5-dogfood'}) MERGE (a)-[:FLOWS_TO]->(b);

// ============================================================================
// WORK ITEMS (C1 – C13)
// ============================================================================

MERGE (wi:WorkItem {node_id:'wi-onboarding-c1-tiered-installer'})
  SET wi.label='C1 — Tiered installer (install-deps.sh --tier=readonly|editor)',
      wi.description='Restructure install-deps.sh with explicit --tier flag. Readonly tier installs CLI + config scaffold only. Editor tier adds Neo4j+APOC+Qdrant+Ollama+nomic-embed-text. Idempotent, resumable, self-tests on completion.',
      wi.status='new', wi.effort='M', wi.order=1, wi.tier='all', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c2-config-scaffold'})
  SET wi.label='C2 — Config scaffold + first-run self-test',
      wi.description='Generate ~/.mycelium/config.toml and secrets.env from examples on install. Run mycelium doctor + --target dev status as self-test. Never read these files into Claude sessions (honor no-read-env-files rule).',
      wi.status='new', wi.effort='S', wi.order=2, wi.tier='all', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c3-fork-artifact-builder'})
  SET wi.label='C3 — Fork artifact builder on pulse',
      wi.description='Systemd unit + post-autodeploy hook on pulse-server runs apoc.export.cypher.all to /var/mycelium/fork-artifacts/dev-latest.cypher (direct file write, no Bolt stream). Emits sha256 + timestamp + node-count sidecars. Manual trigger: mycelium refresh-fork-artifact.',
      wi.status='new', wi.effort='M', wi.order=3, wi.tier='editor', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c4-bolt-proxy-artifact-route'})
  SET wi.label='C4 — bolt-proxy static route for fork artifacts',
      wi.description='Extend deploy/bolt-proxy Go server: GET /forks/dev-latest.cypher|.sha256|.timestamp|.node-count with same Basic auth as Bolt. Rate-limit per client. No list endpoint (opaque URLs only).',
      wi.status='new', wi.effort='S', wi.order=4, wi.tier='editor', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c5-fork-client-rewrite'})
  SET wi.label='C5 — Rewrite mycelium fork dev — artifact-based, merge-mode default',
      wi.description='curl artifact + sha verify + age display + auto-snapshot local + replay with progress. Default merge-mode (preserves local work). --wipe flag for explicit reset. Target <2 min end-to-end.',
      wi.status='new', wi.effort='M', wi.order=5, wi.tier='editor', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c6-snapshot-subsystem'})
  SET wi.label='C6 — Snapshot subsystem (ring buffer + named snapshots + rollback)',
      wi.description='Auto ring buffer: 3 binary dumps in ~/.mycelium/snapshots/auto/ taken before every mutating op. Named snapshots via mycelium snapshot <name>. mycelium snapshots lists. mycelium rollback [--last|<name>] restores in <20s via neo4j-admin load. Named-snapshot auto-prune: keep N=3.',
      wi.status='new', wi.effort='L', wi.order=6, wi.tier='editor', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c7-write-stamping'})
  SET wi.label='C7 — Local-write stamping (last_edited_locally, edited_in_session)',
      wi.description='Every write through mycelium shell or protocol executor stamps last_edited_locally=datetime() and edited_in_session=<id> on touched nodes. Enables conflict detection on sync.',
      wi.status='new', wi.effort='S', wi.order=7, wi.tier='editor', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c8-conflict-aware-sync'})
  SET wi.label='C8 — Conflict-aware sync --from dev',
      wi.description='sync defaults to dry-run: shows conflict set (nodes with last_edited_locally > last_sync_from_dev). Resolution flags --mine / --theirs / --force explicit. Non-conflicts fast-forward silently.',
      wi.status='new', wi.effort='M', wi.order=8, wi.tier='editor', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c9-qdrant-ollama-default-on'})
  SET wi.label='C9 — Editor tier: Qdrant + Ollama default-on, toggleable',
      wi.description='Editor installer brings up local Qdrant + Ollama + pulls nomic-embed-text. CLI detects status on every start, surfaces clearly (green/yellow/red). User can disable via config.toml [embedding] local_stack = off — CLI then routes embedding calls to pulse Ollama/Qdrant automatically.',
      wi.status='new', wi.effort='M', wi.order=9, wi.tier='editor', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c10-quickstart-readme'})
  SET wi.label='C10 — Teammate quickstart README (two-tier flow)',
      wi.description='Single entry doc: tier picker, one-command install per tier, first-run self-test, troubleshoot top-5. Links to graph node plan-onboarding-tiers-v1 as source of truth.',
      wi.status='new', wi.effort='S', wi.order=10, wi.tier='all', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c11-contract-knowledge-nodes'})
  SET wi.label='C11 — Contract knowledge nodes',
      wi.description='Seed :Knowledge nodes describing the contracts: fork-artifact-v1, snapshot-subsystem-v1, sync-conflict-v1, tier-onboarding-v1, secret-scrubber-v1. These are the graph-level source of truth for the subsystems.',
      wi.status='new', wi.effort='S', wi.order=11, wi.tier='all', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c12-ingest-repo-redact'})
  SET wi.label='C12 — Patch ingest_repo.py to call redact.redact() before SET r.url',
      wi.description='Root cause fix for gho_ token leak found in :Repo.url on dev. scripts/ingest_repo.py:288 stores $url without redaction. Wrap with redact.redact(). Add unit test with a tokened URL asserting redaction.',
      wi.status='new', wi.effort='S', wi.order=12, wi.tier='all', wi.project='mycelium';

MERGE (wi:WorkItem {node_id:'wi-onboarding-c13-secret-scrubber-protocol'})
  SET wi.label='C13 — Graph-native secret-scrubber Protocol (heartbeat-driven)',
      wi.description='New graph/protocols/secret-scrubber.cypher Protocol: fires on heartbeat. Scans all node properties for secret regex hits (gho_, ghp_, ghs_, sk-ant-, lsv2_, AKIA, etc. — same set as scripts/lib/redact.py). Rewrites in place via apoc.text.regreplace. Emits :SecretLeak event with node_id + pattern_name (never value). Paired :Invariant inv-no-secret-properties rejects unhealthy state if any leak found. One-shot cleanup cypher strips the currently-leaked :Repo.url tokens at bootstrap.',
      wi.status='new', wi.effort='M', wi.order=13, wi.tier='all', wi.project='mycelium';

// ============================================================================
// WAVE ↔ WORKITEM CONTAINMENT
// ============================================================================

MATCH (w:Wave {node_id:'wave-onboarding-1-readonly'}), (wi:WorkItem) WHERE wi.node_id IN ['wi-onboarding-c1-tiered-installer','wi-onboarding-c2-config-scaffold','wi-onboarding-c10-quickstart-readme'] MERGE (w)-[:CONTAINS]->(wi);
MATCH (w:Wave {node_id:'wave-onboarding-2-artifact'}), (wi:WorkItem) WHERE wi.node_id IN ['wi-onboarding-c3-fork-artifact-builder','wi-onboarding-c4-bolt-proxy-artifact-route'] MERGE (w)-[:CONTAINS]->(wi);
MATCH (w:Wave {node_id:'wave-onboarding-3-fork-client'}), (wi:WorkItem) WHERE wi.node_id IN ['wi-onboarding-c5-fork-client-rewrite'] MERGE (w)-[:CONTAINS]->(wi);
MATCH (w:Wave {node_id:'wave-onboarding-4-editor'}), (wi:WorkItem) WHERE wi.node_id IN ['wi-onboarding-c6-snapshot-subsystem','wi-onboarding-c7-write-stamping','wi-onboarding-c8-conflict-aware-sync','wi-onboarding-c9-qdrant-ollama-default-on','wi-onboarding-c12-ingest-repo-redact','wi-onboarding-c13-secret-scrubber-protocol'] MERGE (w)-[:CONTAINS]->(wi);
MATCH (w:Wave {node_id:'wave-onboarding-5-dogfood'}), (wi:WorkItem) WHERE wi.node_id IN ['wi-onboarding-c11-contract-knowledge-nodes'] MERGE (w)-[:CONTAINS]->(wi);

// ============================================================================
// DEPENDS_ON (cross-wave dependencies)
// ============================================================================

MATCH (a:WorkItem {node_id:'wi-onboarding-c5-fork-client-rewrite'}),    (b:WorkItem {node_id:'wi-onboarding-c3-fork-artifact-builder'})    MERGE (a)-[:DEPENDS_ON]->(b);
MATCH (a:WorkItem {node_id:'wi-onboarding-c5-fork-client-rewrite'}),    (b:WorkItem {node_id:'wi-onboarding-c4-bolt-proxy-artifact-route'}) MERGE (a)-[:DEPENDS_ON]->(b);
MATCH (a:WorkItem {node_id:'wi-onboarding-c5-fork-client-rewrite'}),    (b:WorkItem {node_id:'wi-onboarding-c6-snapshot-subsystem'})        MERGE (a)-[:DEPENDS_ON]->(b);
MATCH (a:WorkItem {node_id:'wi-onboarding-c8-conflict-aware-sync'}),    (b:WorkItem {node_id:'wi-onboarding-c7-write-stamping'})           MERGE (a)-[:DEPENDS_ON]->(b);
MATCH (a:WorkItem {node_id:'wi-onboarding-c11-contract-knowledge-nodes'}), (b:WorkItem) WHERE b.node_id STARTS WITH 'wi-onboarding-c' AND b.node_id <> 'wi-onboarding-c11-contract-knowledge-nodes' MERGE (a)-[:DEPENDS_ON]->(b);

// ============================================================================
// INVARIANT — no secret patterns in node properties
// ============================================================================

MERGE (inv:Invariant {node_id:'inv-no-secret-properties'})
  SET inv.label='No secret patterns in node properties',
      inv.description='No persisted node property shall match known credential patterns (gho_, ghp_, ghs_, ghr_, sk-ant-, lsv2_, ls__, sk-proj-, AKIA*, tr_dev_, st.*, or bearer tokens). Violations surface as :SecretLeak events and mark being unhealthy until scrubbed.',
      inv.check_cypher='MATCH (n) UNWIND keys(n) AS k WITH n, k, toString(n[k]) AS v WHERE v =~ ".*(gho_|ghp_|ghs_|ghr_|sk-ant-|lsv2_pt_|ls__|sk-proj-|AKIA[0-9A-Z]{16}|tr_dev_).*" RETURN count(n) AS violations',
      inv.threshold=0,
      inv.status='active',
      inv.project='mycelium',
      inv.created_at=datetime();

MATCH (plan:MigrationPlan {node_id:'plan-onboarding-tiers-v1'}), (inv:Invariant {node_id:'inv-no-secret-properties'})
MERGE (plan)-[:ENFORCES]->(inv);

// ============================================================================
// ONE-SHOT CLEANUP — strip already-leaked tokens from :Repo.url on next bootstrap
// ============================================================================
// Safe to re-run. Only mutates URLs that still match the leak pattern.

MATCH (r:Repo)
WHERE r.url IS NOT NULL AND r.url =~ '.*x-access-token:gho_[A-Za-z0-9]{36,}@.*'
SET r.url = apoc.text.regreplace(r.url, 'x-access-token:gho_[A-Za-z0-9]{36,}@', ''),
    r.scrubbed_at = datetime(),
    r.scrubbed_reason = 'gho_ oauth token leaked at ingestion (see wi-onboarding-c12)'
RETURN count(r) AS scrubbed_repos;

// ============================================================================
// SUMMARY
// ============================================================================

MATCH (plan:MigrationPlan {node_id:'plan-onboarding-tiers-v1'})
OPTIONAL MATCH (plan)-[:CONTAINS]->(w:Wave)
OPTIONAL MATCH (w)-[:CONTAINS]->(wi:WorkItem)
RETURN plan.label AS plan,
       count(DISTINCT w) AS waves,
       count(DISTINCT wi) AS work_items,
       'onboarding tiers plan seeded' AS status;
