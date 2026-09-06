# Archive Log — v1-pre-migration Runners

**Date archived:** 2026-04-17  
**WorkItem:** wi-wave3-c-runner-prune  
**Reason:** These shell/Python runners predate cypher-native migration. Functionality superseded by in-graph heartbeat, immune cycle, and protocol-based operations via APOC periodic jobs.

## Archived Files

| File | Lines | Reason | Last Commit | Status |
|------|-------|--------|-------------|--------|
| immune.sh | 108 | Immune cycle now runs natively inside Neo4j via protocol-immune-cycle | 2026-04-16 | Superseded by protocol-immune-cycle + APOC |
| run-invariants.sh | 94 | Test invariants now via cmd-test protocol (calls protocol-run-invariants) | 2026-04-16 | Superseded by protocol-run-invariants |
| run-tests.sh | 82 | Test cases now via cmd-test protocol | 2026-04-16 | Superseded by protocol-run-tests |
| witness-sign.sh | 72 | Signing/witness logic migrated to species-sign protocol | 2026-04-16 | Superseded by protocol species-sign |
| verify-signatures.sh | 127 | Signature verification now in protocol-species-sign | 2026-04-16 | Superseded by protocol-species-sign |
| validate-merge.sh | 103 | Merge validation now in protocol-validate-merge | 2026-04-16 | Superseded by protocol-validate-merge |
| species-canonize.sh | 42 | Species canonization now in protocol-species-canonize | 2026-04-16 | Superseded by protocol-species-canonize |
| species-sign.sh | 53 | Species signing now in protocol-species-sign | 2026-04-16 | Superseded by protocol-species-sign |
| adopt-node.sh | 59 | Node adoption now in protocol-adopt-node | 2026-04-16 | Superseded by protocol-adopt-node |
| agent-bootstrap.sh | 42 | Bootstrap now via protocol-bootstrap | 2026-04-16 | Superseded by protocol-bootstrap |
| import-external.sh | 133 | External import now in protocol-import-external | 2026-04-16 | Superseded by protocol-import-external |
| semantic-query.sh | 64 | Semantic queries now via qdrant-search.sh helper + protocols | 2026-04-16 | Superseded by qdrant-search.sh + protocols |
| test-swarm-autonomy.sh | 205 | Swarm benchmarking now in protocol-swarm-benchmark | 2026-04-16 | Superseded by protocol-swarm-benchmark |

**Total archived:** 13 files, 1184 lines

## Protocols Documenting Deprecated Scripts

The following protocols contain references to archived shell scripts. These are **documentation references only** (e.g., "see immune.sh for the shell version") and do **not require updates** — the protocols remain active and functional via native APOC execution:

- protocol-immune-cycle: references immune.sh in comments
- protocol-run-invariants: references run-invariants.sh in comments
- protocol-run-tests: references run-tests.sh in comments
- protocol-validate-merge: references validate-merge.sh in comments
- protocol-species-canonize: references species-canonize.sh in comments
- protocol-species-sign: references species-sign.sh in comments
- protocol-adopt-node: references adopt-node.sh in comments
- protocol-import-external: references import-external.sh in comments
- protocol-swarm-benchmark: references test-swarm-autonomy.sh in comments

## Why These Were Archived

The cypher-native architecture (v1, 2026-04-17) moved all runtime logic inside Neo4j using APOC periodic jobs and inline cypher execution. Shell runners are no longer invoked. Protocol files are the editable source; the graph is the executable source via bootstrapped `.cypher` property on Protocol nodes.

## Recovery Path

If a shell script needs to be recovered:
```bash
git show <commit>:graph/runner/<script> > graph/runner/<script>
```

Example:
```bash
git show 2026-04-16:graph/runner/immune.sh > graph/runner/immune.sh
```

## Next Steps

- Monitor `mycelium health` to ensure no regressions
- Update protocol documentation to note that shell versions are archived
- Protocol references to archived scripts are safe — they're comments, not live calls
