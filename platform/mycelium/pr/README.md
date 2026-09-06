# `pr/` — Proposed cypher mutations

Drop a `.cypher` file here to propose a mutation to the graph. The file
goes through:

1. **Local validation** before push:
   ```bash
   graph/runner/validate-merge.sh pr/my-change.cypher
   ```
   This runs the same checks CI will run. Exit 0 = safe to push.

2. **CI validation on PR open** via `.github/workflows/graph-validate.yml`:
   - spins a clean Neo4j seeded from the base branch's `graph-state.cypher`
   - applies your `.cypher` inside a transaction
   - runs every enabled Invariant + TestCase
   - recomputes Merkle
   - mints a candidate Species if everything passes
   - posts the result + candidate DNA back to your PR as a comment

3. **Local witness sign-off** (once the candidate is minted in CI):
   ```bash
   graph/runner/witness-sign.sh <candidate-id> <your-alias>
   graph/runner/verify-signatures.sh <candidate-id>
   graph/runner/species-canonize.sh <candidate-id>
   ```
   (Phase 2.5 uses your local ed25519 key at `~/.mycelium/witness-<alias>.key`.
   See `graph/runner/witness-init.sh` for bootstrapping a fresh witness.)

## Format

Each `.cypher` file is one atomic mutation. Use `MERGE` / `SET` / `MATCH`
statements. Avoid `CREATE` except for relationships — `MERGE` is idempotent
and re-running the PR against a re-seeded graph gives the same result.

Example:
```cypher
MERGE (p:Principle {node_id: 'principle-my-new-idea'})
SET p.label = 'Short name',
    p.description = 'What it means and when it applies.',
    p.file_type = 'principle',
    p.added_by = 'my-alias';
```

## What CI will reject

- Any enabled Invariant's check becomes unhealthy
- Any enabled TestCase returns an unexpected value
- Syntax errors in your cypher
- Broken relationships (e.g., referencing a non-existent node by id)

CI fails loudly with the named rule and the actual vs expected values.
Fix locally, re-push, CI re-runs.

## What CI will NOT gate

- Performance (a slow mutation will commit if it passes the checks)
- Semantic intent (you can add a node that satisfies every invariant
  but is nonsense domain-wise)
- Node pruning without replacement (if you delete a node that nothing
  depends on, the gate accepts it)

For those, rely on human review on the PR itself.

## File naming

No strict convention. Suggested: `<date>-<short-description>.cypher`, e.g.
`2026-04-16-add-witness-quorum-rule.cypher`. CI validates all `.cypher`
files added or modified under `pr/` in the PR diff.
