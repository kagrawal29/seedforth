# Cycle Telemetry — 2026-04-10-cycle-1854

**Time:** 2026-04-10T18:54:48 → 2026-04-10T19:10:34 (946.2s)
**Steps:** 6/11 OK
**Graph interactions:** 2

## Pipeline Steps

| Step | Status | Time | SDK Duration | Turns | Cost | Error |
|---|---|---|---|---|---|---|
| ingest | OK | 322.1s | 312.5s | 2 | $0.5995 |  |
| demand | OK | 347.9s | 338.8s | 21 | $0.7651 |  |
| intent | FAIL | 249.7s | 240.7s | 13 | $0.4067 |  |
| convergence | OK | 0.1s | — | — | — |  |
| sync-layers | OK | 0.3s | — | — | — |  |
| synthesis | FAIL | 8.2s | 0.4s | 1 | — |  |
| graph-sync | OK | 0.4s | — | — | — |  |
| dream | FAIL | 0.3s | — | — | — |  |
| integrity | OK | 0.1s | — | — | — |  |
| heimdall | FAIL | 8.2s | 0.4s | 1 | — |  |
| pre-dist-audit | FAIL | 8.3s | 0.4s | 1 | — |  |

## Graph Interactions

| Agent | Action | Target | Tokens | Results |
|---|---|---|---|---|
| orchestrator | cache_refresh | graph-context.md, graph-demand.md, heimdall-graph-context.md | 0 | 4 |
| orchestrator | cache_refresh | graph-context.md, graph-demand.md | 0 | 2 |