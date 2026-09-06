# Contributing to Mycelium

Thanks for helping the graph grow. Mycelium is opinionated: everything starts and ends in the graph. Follow this guide to keep contributions aligned.

## 0. Branching Model (Two-Tier Protocol)

This project enforces a **two-tier branching model** to maintain code quality and coordinated development. All team members (including the owner) follow the same protocol.

### Branches and Rules

| Branch | Rules | Purpose |
|--------|-------|---------|
| `main` | Protected. No direct pushes. Accept PRs only from `dev` after owner + 1 reviewer approval. | Stable production code. Every commit is deployable. |
| `dev` | Protected. No direct pushes. Accept PRs only from feature branches after at least 1 reviewer. | Integration branch. Staging area before main. |
| `dev/<user>/<short-desc>` | Unprotected. Work here. Push whenever. Rebase preferred. | Individual feature branches. Owner: `dev/kshitiz/*`. |

### Branch Protection (No-Pro Workaround)

GitHub's branch protection requires a paid plan. While on the free tier, we enforce the same rules via three layers:

1. **GitHub Actions workflow** — runs on every push to `main`. Detects direct pushes (non-merge-commits), auto-reverts them, and opens an issue explaining the rule violation.
2. **Client-side pre-push hook** — blocks direct pushes locally before they reach GitHub. Install via `bash scripts/install-git-hooks.sh`.
3. **Social contract** — documented in this file. Direct pushes are treated as policy violations, not accidents.

**If a direct push happens:**
- The Action auto-reverts it on a new branch (`auto-revert-<sha>`)
- An issue is opened with the violation and the revert branch
- You must reopen the change as a proper PR

**To bypass in emergencies:** `git push --no-verify` — but only after coordinating in Slack. This is traceable in Actions logs.

### Your Workflow

**First time setup:** install the pre-push hook to prevent accidental direct pushes:
```bash
bash scripts/install-git-hooks.sh
```

Then follow this workflow:

```
1. Start feature work:
   git checkout -b dev/<username>/<short-description>
   # Examples: dev/kshitiz/graph-migration, dev/alex/fix-heartbeat

2. Make commits (frequent small commits are preferred):
   git add <files>
   git commit -m "clear, concise message"
   git push

3. When ready (after tests pass locally):
   - Open a PR from dev/<username>/<short-desc> → dev
   - Get at least 1 review + approval
   - Reviewer merges the PR (maintainers: no need to wait for you to merge)

4. When dev is ready for release:
   - Owner opens a PR from dev → main
   - Requires: owner approval + 1 additional reviewer + passing tests
   - Smoke test locally or on staging before merge
   - Reviewer merges

5. After main is updated:
   - Rebase your active feature branches on the new main:
     git fetch origin && git rebase origin/main
   - Or just pull from dev on your next feature branch
```

### Rules (Enforced by GitHub)

- **Direct pushes to `main` are forbidden** — all changes via PR
- **Direct pushes to `dev` are forbidden** — all changes via PR
- **Force-pushes to `main` and `dev` are forbidden** — only fast-forward or squash-merge
- **All PRs require at least 1 review** — you can't merge your own PR
- **`main` requires owner approval** — ensures coordinated releases
- **Linear history** — rebase before pushing to keep history clean

### Anti-Patterns (Don't Do These)

- Don't revert someone else's PR without discussing first
- Don't force-push to any branch
- Don't commit directly to main or dev
- Don't merge your own PRs to main or dev
- Don't skip tests before opening a PR

## 1. Ground Rules

- **Query first**: before changing files, check whether the graph already stores the data (`scripts/graph.py --ask "…"`, `MATCH` queries, etc.).
- **MERGE over CREATE**: deduplicate nodes/edges to maintain a canonical knowledge base.
- **TDD enforced**: any automation, hook, or protocol must be backed by a `TestCase` node plus unit/integration tests where appropriate.
- **No secrets in repo**: use environment variables (`.env` files ignored by git) or vaults.

## 0.5 Graph Data Flow and Local Development

Code flows: `feature → dev → main` (reviewed, tested, merged)
Graph state flows: `dev Neo4j → prod Neo4j` (species chain, witness signatures)
Local graph mirrors: `dev` (synced via `mycelium sync`, additive, safe)

**Your local workflow:**
1. During setup, your local Neo4j is seeded from dev (via `mycelium sync`)
2. As you work, run `mycelium sync` (no args) to stay current with dev — this defaults to `dev` and safely skips your local edits
3. Nodes you modify locally are marked with `_local_edited_at` (automatic on any write)
4. Sync operations preserve your edits; use `mycelium sync --force` to override (destructive)
5. When you commit code changes, they flow through dev → main via PRs
6. When code is deployed, it may create new graph state; those changes flow through dev → prod separately

Local edits (via `mycelium shell`, local scripts, manual graph work) are **preserved** and never overwritten by sync. Run `mycelium drift` to see locally-edited vs dev-synced nodes.

## 2. Workflow

1. Fork or branch off `main` (preferred naming: `feature/<slug>` or `docs/<slug>`).
2. Run or update relevant tests:
   - `python3 scripts/self-test.py`
   - Any domain-specific suites (see `tests/`).
3. Make changes (code, Cypher, docs).
4. Export/update graph snapshots only when intentionally versioning state (`scripts/graph-export-state.py`).
5. Open a Pull Request with:
   - Summary of changes
   - Tests run
   - Any required follow-up (e.g., seed scripts, environment tweaks)

## 3. Coding Standards

- Python: follow `ruff` defaults / PEP8; prefer typing hints.
- Cypher: use `MERGE` for nodes with `node_id`, `SET` for properties, `MATCH` before `MERGE` for relations.
- Shell scripts: `bash` with `set -euo pipefail`.
- Documentation: Markdown, 80–100 character soft wrap preferred.

## 4. Graph Hygiene Checklist

- [ ] New nodes include `node_id`, `label`, `tags`, and timestamps where relevant.
- [ ] Confidence / status flags reflect reality (`confidence`, `_decay_flagged`, etc.).
- [ ] Knowledge is linked (at minimum `RELATES_TO`, `CONCEPTUALIZED_BY`, or `ENABLES`).
- [ ] If you touch ontology, update `CLAUDE.md`, `README.md`, or `docs/` so humans stay in sync.

## 5. Communication

- Use GitHub Issues or Discussions for feature proposals.
- Emergency fixes: coordinate in the Mycelium Slack/Signal channel, then document via `knowledge/` entries or Cypher nodes.

## 6. Licensing

Submitting code means you agree to the [MIT License](LICENSE) and confirm you have the right to contribute the code/data.

Welcome aboard. Be gentle with the organism, but keep it evolving.
