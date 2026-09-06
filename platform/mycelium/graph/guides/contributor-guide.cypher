// @node_id: wi-cg-02-seed-sections
// @label: "Seed ContributorGuide Sections"
// @kind: graph-write
// @description: Seed 10 :GuideSection nodes for the maverick ContributorGuide (Track D wi-cg-02)
//
// Sections are derived from the current CONTRIBUTING.md and key teammate-facing patterns:
//   1. welcome — intro to contributing, graph-first mindset
//   2. install — local dev setup, tools prereqs
//   3. first-query — first Cypher command, zero setup
//   4. make-a-change — branching model, workflow steps
//   5. graph-native-discipline — MERGE over CREATE, TDD discipline
//   6. pr-workflow — PR process, review expectations, merge rules
//   7. testing — test first, invariants, protocols, automation
//   8. drift-and-healing — drift detection, healing protocols, invariants
//   9. release-cadence — versioning, tagging, deployment to prod/staging
//   10. upstream-sync-policy — syncing from kagrawal29/mycelium upstream
//
// Each section:
//   - MERGE on (guide_name, slug) — idempotent
//   - has stable node_id for reference elsewhere
//   - references relevant :Invariant/:Protocol/:WorkItem nodes (OPTIONAL MATCH guards)
//   - ordered numerically for export
// ============================================================================

// --- Parent node: ContributorGuide ---
MERGE (g:ContributorGuide {node_id: 'contributor-guide-maverick', name: 'maverick'})
SET
  g.description = 'Maverick team contribution guide: branching, graph-native discipline, testing, and release workflow',
  g.updated_ts = datetime()
RETURN g AS guide;

// --- Section 1: Welcome ---
MERGE (s1:GuideSection {guide_name: 'maverick', slug: 'welcome'})
SET
  s1.node_id = 'section-welcome',
  s1.title = 'Welcome to Contributing',
  s1.anchor = '#welcome',
  s1.order = 1,
  s1.body_md = 'Thanks for helping the graph grow. Maverick is opinionated: everything starts and ends in the graph.\n\nThis guide covers how to align your contributions with the team''s graph-first workflow. Follow this to keep code, documentation, and graph state in sync.\n\nBefore making changes, remember: **query first**. Check whether the graph already stores the data before creating something new. Use `maverick ask` to search the knowledge base.',
  s1.updated_ts = datetime()
WITH s1, g MERGE (g)-[:HAS_SECTION]->(s1);

// --- Section 2: Install & Setup ---
MERGE (s2:GuideSection {guide_name: 'maverick', slug: 'install'})
SET
  s2.node_id = 'section-install',
  s2.title = 'Local Development Setup',
  s2.anchor = '#install',
  s2.order = 2,
  s2.body_md = 'Install the maverick binary and set up your local development graph.\n\n## Quick Start\n\n```bash\ngh auth login\ngh release download -R Qubit-Capital/maverick -p install.sh && bash install.sh\nmaverick --version\n```\n\n## For Contributors (Local Graph)\n\nTo write code and experiment locally, set up the full Docker stack:\n\n```bash\ngit clone https://github.com/Qubit-Capital/maverick && cd maverick\nmaverick local bootstrap\nmaverick fork maverick-dev\n```\n\nAfter this, your local graph is a full snapshot of the shared dev graph. You can query and write to it safely.\n\n## Teardown\n\nWhen done (data is persisted in a Docker volume):\n\n```bash\nmaverick local teardown\n```\n\nOr remove all data:\n\n```bash\nmaverick local teardown --delete-data\n```',
  s2.updated_ts = datetime()
WITH s2, g MERGE (g)-[:HAS_SECTION]->(s2);

// --- Section 3: First Query ---
MERGE (s3:GuideSection {guide_name: 'maverick', slug: 'first-query'})
SET
  s3.node_id = 'section-first-query',
  s3.title = 'Run Your First Query',
  s3.anchor = '#first-query',
  s3.order = 3,
  s3.body_md = 'Query the shared dev graph without any local setup:\n\n```bash\nmaverick --target maverick-dev shell "MATCH (b:Being) RETURN count(b) AS beings"\n```\n\nExpect a result in under 60 seconds on first run (binary downloads + Neo4j connection).\n\n## Query with Ask\n\nSearch the graph semantically:\n\n```bash\nmaverick ask "how do I contribute"\nmaverick ask "what protocols exist for healing drifts"\n```\n\n`maverick ask` returns relevant :GuideSection and :Protocol nodes from the graph, zero token cost.',
  s3.updated_ts = datetime()
WITH s3, g MERGE (g)-[:HAS_SECTION]->(s3);

// --- Section 4: Make a Change ---
MERGE (s4:GuideSection {guide_name: 'maverick', slug: 'make-a-change'})
SET
  s4.node_id = 'section-make-a-change',
  s4.title = 'Make a Change: Branching & Workflow',
  s4.anchor = '#make-a-change',
  s4.order = 4,
  s4.body_md = 'Maverick enforces a two-tier branching model for code quality and coordinated development.\n\n## Branches\n\n| Branch | Rules | Purpose |\n|--------|-------|---------|\n| `main` | Protected. No direct pushes. PRs only from `dev` after owner + 1 reviewer. | Stable production code. Every commit is deployable. |\n| `dev` | Protected. No direct pushes. PRs only from feature branches after 1 reviewer. | Integration branch. Staging area before main. |\n| `dev/<user>/<short-desc>` | Unprotected. Push whenever. Rebase preferred. | Individual feature branches. |\n\n## Your Workflow\n\n```bash\n# 1. Start a feature branch off dev\ngit checkout -b dev/username/short-description\n# Examples: dev/alex/fix-heartbeat, dev/jordan/cypher-atom-refactor\n\n# 2. Make commits (small and frequent preferred)\ngit add <files>\ngit commit -m "clear message"\ngit push\n\n# 3. When ready, open a PR from dev/<user>/<desc> → dev\n# Get at least 1 review + approval, then reviewer merges\n\n# 4. When dev is ready for release, owner opens PR dev → main\n# Requires: owner approval + 1 reviewer + passing tests\n\n# 5. After main is updated, rebase your active branches\ngit fetch origin && git rebase origin/main\n```\n\n## No Direct Pushes\n\nDirect pushes to `main` or `dev` are forbidden. Enforce this locally:\n\n```bash\nbash scripts/install-git-hooks.sh\n```\n\nIf you push directly by mistake, the GitHub Actions workflow auto-reverts it and opens an issue.',
  s4.updated_ts = datetime()
WITH s4, g MERGE (g)-[:HAS_SECTION]->(s4);

// --- Section 5: Graph-Native Discipline ---
MERGE (s5:GuideSection {guide_name: 'maverick', slug: 'graph-native-discipline'})
SET
  s5.node_id = 'section-graph-native-discipline',
  s5.title = 'Graph-Native Discipline',
  s5.anchor = '#graph-native-discipline',
  s5.order = 5,
  s5.body_md = 'Maverick''s strength is in its graph. Follow these rules to keep it healthy.\n\n## Query First\n\nBefore writing a new node or edge, check the graph:\n\n```bash\nmaverick ask "does the graph already track X"\nmaverick --target maverick-dev shell "MATCH (n:Type {name: ''something''}) RETURN n"\n```\n\nIf it exists, reuse it. Deduplicate relentlessly.\n\n## MERGE Over CREATE\n\nAlways use `MERGE` with a stable `node_id` to deduplicate:\n\n```cypher\n// Good: MERGE ensures no duplicates\nMERGE (p:Protocol {node_id: ''my-protocol-v1''})\nSET p.name = ''My Protocol'', p.updated_ts = datetime()\n\n// Bad: CREATE always makes a new node\nCREATE (p:Protocol {name: ''My Protocol''})\nRETURN p\n```\n\n## TDD Enforced\n\nAny new automation, healing protocol, or hook must have tests:\n\n- Unit tests in `tests/` for Go / Python code\n- A `:TestCase` node in the graph paired with the Protocol\n- Integration tests that run on CI via the UX test harness\n\nNo test = no merge.\n\n## No Secrets in Repo\n\nUse environment variables (`.env` files ignored by git) or CI secrets vaults. Never commit credentials, API keys, or personal data.',
  s5.updated_ts = datetime()
WITH s5, g MERGE (g)-[:HAS_SECTION]->(s5);

// --- Section 6: PR Workflow ---
MERGE (s6:GuideSection {guide_name: 'maverick', slug: 'pr-workflow'})
SET
  s6.node_id = 'section-pr-workflow',
  s6.title = 'Pull Request Workflow',
  s6.anchor = '#pr-workflow',
  s6.order = 6,
  s6.body_md = 'Pull requests are the gate for all code and graph changes. Here''s what the process looks like.\n\n## Before Opening a PR\n\n1. Run tests locally: `python3 scripts/self-test.py` or your domain-specific test suite\n2. Test against your local graph if modifying Cypher: `maverick-dev apply <file> --target maverick-local`\n3. Verify no secrets were accidentally committed: `git diff origin/dev HEAD | rg "password|token|key"`\n\n## Opening a PR\n\n1. Use a clear title: \"fix(drift): heal protocol fires on every cycle\" or \"feat(cg): seed 10 guide sections\"\n2. Include a summary of changes and motivation\n3. List any follow-up work or environment changes needed\n4. Link relevant issues: \"Closes #42\" or \"Related to wi-cg-02\"\n\n## Review Expectations\n\n- **Minimum 1 approval** required on all PRs\n- Feature branches → dev: 1 reviewer, any teammate\n- dev → main: owner approval + 1 additional reviewer\n- Owner-authored main PRs: 1 reviewer (owner cannot self-approve)\n\n## Merge Rules\n\n- No force-pushes to `main` or `dev`\n- Fast-forward or squash-merge only (linear history preferred)\n- Reviewer merges (maintainer can merge owner''s PR once approved)\n- Wait for CI to turn green before merging\n\n## After Merge\n\n- Rebase your active feature branches on the new main: `git fetch origin && git rebase origin/main`\n- For dev-only changes, continue from dev on your next feature branch\n- Autodeploy monitors main + dev; changes propagate to maverick-dev within 2 minutes',
  s6.updated_ts = datetime()
WITH s6, g MERGE (g)-[:HAS_SECTION]->(s6);

// --- Section 7: Testing ---
MERGE (s7:GuideSection {guide_name: 'maverick', slug: 'testing'})
SET
  s7.node_id = 'section-testing',
  s7.title = 'Testing (TDD Discipline)',
  s7.anchor = '#testing',
  s7.order = 7,
  s7.body_md = 'Maverick enforces test-driven development at every layer: code, graph, protocols, and UX.\n\n## Code Tests\n\nFor Go and Python:\n\n```bash\n# Python\npython3 scripts/self-test.py\npython3 -m pytest tests/ -v\n\n# Go\ngo test ./...\ngo test -race ./...  # detect data races\n```\n\nAim for >80% coverage on critical paths.\n\n## Graph Tests: Invariants & Protocols\n\nEvery :Protocol node should have paired test cases:\n\n```cypher\nMERGE (t:TestCase {node_id: ''test-my-protocol''})\nSET t.protocol = ''my-protocol'', t.assertion = ''healing succeeds in 60s''\nWITH t MATCH (p:Protocol {name: ''my-protocol''})\nMERGE (t)-[:TESTS]->(p)\n```\n\nRun graph tests via:\n\n```bash\nmaverick test --target maverick-local\n```\n\n## UX Test Harness\n\nPer-persona tests in `test/ux/`:\n\n- `persona-reader.sh` — install + first query (5 min budget)\n- `persona-contributor.sh` — bootstrap + local fork + write + PR (10 min budget)\n- `persona-maintainer.sh` — ops commands on scratch environment\n\nThese run on every PR via GitHub Actions. Green required before merge.\n\n## CI Checks\n\n- Drift check: CONTRIBUTING.md must match :ContributorGuide export\n- Merge-gate: no CREATE without MERGE, no unguarded DETACH DELETE\n- Schema validation: new nodes/edges match declared invariants\n- Time budgets: Reader <5 min, Contributor <10 min\n\nAll checks run in parallel; first failure blocks merge.',
  s7.updated_ts = datetime()
WITH s7, g MERGE (g)-[:HAS_SECTION]->(s7);

// --- Section 8: Drift & Healing ---
MERGE (s8:GuideSection {guide_name: 'maverick', slug: 'drift-and-healing'})
SET
  s8.node_id = 'section-drift-and-healing',
  s8.title = 'Drift Detection & Healing Protocols',
  s8.anchor = '#drift-and-healing',
  s8.order = 8,
  s8.body_md = 'Maverick''s graph stays in sync with the repo via automated healing protocols.\n\n## What is Drift?\n\nDrift occurs when the running graph state (maverick-dev or maverick-prod) differs from what''s declared in `graph/` (the source of truth). Drift can happen if:\n\n- Someone writes directly to Neo4j (should be forbidden except via CI)\n- A protocol has a bug and creates unexpected nodes\n- Network partition during an autodeploy\n\n## Detection\n\nBefore applying the manifest, autodeploy compares graph state vs repo state. Any mismatch is logged as a `:DriftEvent`:\n\n```cypher\nMATCH (d:DriftEvent) WHERE d.ts > datetime() - duration(''P1D'')\nRETURN d.ts, d.source, d.drifted_nodes, d.corrected\nORDER BY d.ts DESC\n```\n\n## Healing\n\nThe `graph-manifest-reapply` protocol runs every 60 seconds on dev and prod:\n\n1. Snapshot current graph state\n2. Re-apply every `.cypher` file in `graph/manifest.yaml` (idempotent MERGE)\n3. If post-state differs from pre-state, write a `:DriftEvent`\n4. Return graph to declared state\n\nNo manual intervention needed. Healing is automatic.\n\n## Invariants\n\nHealing is backed by an invariant:\n\n```cypher\nMATCH (inv:Invariant {name: ''graph-state-matches-repo''})\nRETURN inv.description, inv.heal_protocol\n```\n\nThis invariant is part of `maverick health`, which all teammates can check:\n\n```bash\nmaverick health\n```\n\n## Visibility\n\nTeammates can always see drift:\n\n```bash\nmaverick --target maverick-dev shell \"MATCH (d:DriftEvent) RETURN count(d) AS drift_events_24h WHERE d.ts > datetime() - duration(''P1D'')\"\n```',
  s8.updated_ts = datetime()
WITH s8, g MERGE (g)-[:HAS_SECTION]->(s8);

// --- Section 9: Release Cadence ---
MERGE (s9:GuideSection {guide_name: 'maverick', slug: 'release-cadence'})
SET
  s9.node_id = 'section-release-cadence',
  s9.title = 'Release Cadence & Versioning',
  s9.anchor = '#release-cadence',
  s9.order = 9,
  s9.body_md = 'Maverick releases are coordinated, tested, and tracked in the graph.\n\n## Release Workflow\n\n1. **Candidate**: All features land on `main` via PR from `dev`\n2. **Tag**: Owner tags a release: `git tag v1.X.Y && git push --tags`\n3. **Build**: goreleaser automatically builds all 4 platform binaries (Darwin arm64/amd64, Linux amd64, Windows amd64)\n4. **Release**: GitHub Actions publishes the release with installer scripts\n5. **Manifest**: The `graph/manifest.yaml` at that tag becomes the source of truth for that release version\n6. **Deploy**: Teammates install via `gh release download -R Qubit-Capital/maverick -p install.sh`\n\n## Version Numbers\n\nMaverick follows semantic versioning:\n\n- `v1.0.0` — major, minor, patch\n- `v1.1.0-rc1` — release candidate (tagged but not published)\n- `v1.0.1` — patch release (bug fixes only)\n\n## Deploying to Prod\n\nOnce a release is published, prod deployment happens automatically:\n\n1. Release tag triggers a separate autodeploy against `maverick-prod`\n2. The manifest at that tag is applied (idempotent MERGE)\n3. `:DriftEvent` logging confirms the deploy\n4. Teammates can verify with `maverick --target maverick-prod health`\n\n## Graph Snapshots\n\nEach release pin should have a snapshot stored for recovery:\n\n```bash\nmaverick local snapshot from-tag v1.0.0\nmaverick local checkout v1.0.0\nmaverick --target maverick-local shell \"MATCH (b:Being) RETURN count(b)\"\n```',
  s9.updated_ts = datetime()
WITH s9, g MERGE (g)-[:HAS_SECTION]->(s9);

// --- Section 10: Upstream Sync Policy ---
MERGE (s10:GuideSection {guide_name: 'maverick', slug: 'upstream-sync-policy'})
SET
  s10.node_id = 'section-upstream-sync-policy',
  s10.title = 'Upstream Sync: Pulling from Mycelium',
  s10.anchor = '#upstream-sync-policy',
  s10.order = 10,
  s10.body_md = 'Maverick is a hard fork of `kagrawal29/mycelium` with its own identity. We sync upstream periodically without losing the fork divergence.\n\n## Why We Fork\n\nMycelium is the canonical upstream research project. Maverick is the team-distribution version with:\n- Renamed binaries: `mycelium` → `maverick`\n- Renamed targets: `mycelium-dev` → `maverick-dev`\n- Renamed services: `mycelium-smoke.service` → `maverick-smoke.service`\n- Team-specific docs and contributor guide\n\nThe fork ensures teammates see only "maverick" in their workflows while keeping the graph as a shared research artifact.\n\n## Syncing Upstream\n\nWhen mycelium gets a fix or new protocol we want to adopt:\n\n1. Owner runs: `bash scripts/translate-upstream.sh <branch-from-mycelium>`\n2. Script applies sed rules: `mycelium` → `maverick` in appropriate files\n3. Preserves mycelium-identity in docs and historical references\n4. Produces a branch ready to PR into maverick:dev\n5. Standard PR review + merge\n\nSync is manual, roughly ~15 min per sync. We don''t auto-sync; chosen merges only.\n\n## What Gets Synced\n\n- `graph/` — protocols, invariants, knowledge, schemas (always sync these)\n- `cmd/` — bug fixes to the CLI (sync as-needed)\n- Docs — if mycelium has new patterns, port them and re-customize\n\n## What Stays Separate\n\n- `CONTRIBUTING.md` — maverick''s guide is the authority; mycelium''s stays upstream\n- Binary name + version stamp\n- Services + systemd config (pulse-server deployment is maverick-specific)\n- Team-facing docs (AGENTS.md, installer scripts)\n\n## Downstream Identity\n\nTeammates should never see "mycelium" in:\n- `maverick --version` output\n- CLI help text\n- Service names (`systemctl list-units | grep maverick`)\n- README or installation instructions\n- Deployed artifacts\n\nIf you spot "mycelium" in teammate-facing surfaces, file an issue.',
  s10.updated_ts = datetime()
WITH s10, g MERGE (g)-[:HAS_SECTION]->(s10);

// --- Add optional REFERENCES edges (guards via OPTIONAL MATCH) ---
// These reference real invariants/protocols if they exist in the graph

// Section 5 (graph-native-discipline) references the merge-ethics invariant if it exists
MATCH (s5:GuideSection {guide_name: 'maverick', slug: 'graph-native-discipline'})
OPTIONAL MATCH (inv:Invariant {name: 'merge-ethics'})
WHERE inv IS NOT NULL
MERGE (s5)-[:REFERENCES {type: 'core-rule'}]->(inv);

// Section 8 (drift-and-healing) references the graph-state-matches-repo invariant if it exists
MATCH (s8:GuideSection {guide_name: 'maverick', slug: 'drift-and-healing'})
OPTIONAL MATCH (inv:Invariant {name: 'graph-state-matches-repo'})
WHERE inv IS NOT NULL
MERGE (s8)-[:REFERENCES {type: 'enforced-by'}]->(inv);

// Section 4 (make-a-change) references the forest-promise invariant if it exists (commit quality)
MATCH (s4:GuideSection {guide_name: 'maverick', slug: 'make-a-change'})
OPTIONAL MATCH (inv:Invariant {name: 'forest-promise'})
WHERE inv IS NOT NULL
MERGE (s4)-[:REFERENCES {type: 'governed-by'}]->(inv);

// --- Summary Report ---
WITH COUNT(*) AS section_count
MATCH (g:ContributorGuide {name: 'maverick'})-[:HAS_SECTION]->(s:GuideSection)
RETURN
  'wi-cg-02 complete: ContributorGuide seeded' AS status,
  COUNT(s) AS sections_created,
  g.updated_ts AS guide_updated
ORDER BY s.order;
