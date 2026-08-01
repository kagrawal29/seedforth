# Rhythm & Immune System — Living System Architecture

*Capra's living systems made concrete. The graph is not a batch job. It has
metabolism, circulation, a nervous system, and an immune system — each on its
own tempo, all synchronized.*

---

## 1. The Rhythms (varying tempos, synced)

Not everything runs every 30 minutes. The system breathes on multiple
cadences, like a percussion ensemble. Each rhythm serves a different function.

### Fast Pulse — every 5 min (circulatory system)
*Metabolism: what's alive right now.*
- `fleet-ingest` — FleetState + SystemHealth mutable nodes, FleetEvent on change

### Heartbeat — every 30 min (nervous system)
*Signal processing: connect, decay, sense.*
- 01-wake — anything new?
- 02-connect — wire traces to knowledge
- 03-converge — agents converging on same topic
- 04-07 decay — forget gracefully (confidence, demand, edges, TTL)
- 08-dedup — remove duplicate edges
- 09-heal-orphans — delete zero-edge noise
- 12-liveness — is the system alive?
- 13-report — record system shape
- 14-snapshot — capture state

### Dream Cycle — every 4 hours (cognition)
*Deep processing: inference, structure.*
- 10-heal-dream — close triangles, infer hidden connections
- 11-immune — detect unauthorized structural change
- 15-health-check — load/mem/cpu ActionProposal
- 16-agent-fatal — fatal agent ActionProposal

### Deep Cycle — every 24 hours (immune system full sweep)
*Self-healing: detect → heal → verify → escalate.*
- 17-invariants — full invariant + test suite
- 18-immune-response — for each failing invariant: run heal_protocol,
  re-verify, escalate if still failing
- 19-embed-dirty — regenerate embeddings for changed nodes
- 20-report-daily — daily health summary

### Long Cycle — every 7 days (metabolic consolidation)
*Deep consolidation.*
- Snapshot folding — merge 7 days of events into weekly summary
- Compaction — merge duplicate/related Knowledge
- Repository sync — refresh repo/project links

---

## 2. The Immune System — Closed Loop

The invariant runner today only DETECTS. A living system's immune system
must do: **detect → diagnose → heal → verify → escalate**. Full autonomy.

### The loop (18-immune-response.py)

```
for each failing invariant:
  1. DETECT    — invariant check returned violations
  2. DIAGNOSE  — list the violating node_ids
  3. HEAL      — if invariant has heal_protocol, run it
  4. VERIFY    — re-run the invariant check
  5. RESOLVED  — if 0 violations now, record: {invariant, healed, time}
                  and mark ActionProposal resolved
  6. ESCALATE  — if still failing, keep/update ActionProposal
                  (SuperAgent reads it and acts)
```

### ImmuneResponse nodes

```
(:ImmuneResponse {
  node_id, invariant_id, detected_at,
  violation_count, healing_action, heal_result,
  resolved: true/false, resolved_at, project: 'system'
})
```

This creates the audit trail: every healing event is recorded, traceable,
and the SuperAgent can read "what did the system heal on its own today?"

### Heal protocol execution

The heal_protocols stored on invariant nodes are Cypher fragments (mostly
SET statements). 18-immune-response:
1. Reads `i.heal_protocol`
2. If it's an inline Cypher fragment → wrap + execute
3. If it's a named protocol (`protocol-heal-*`) → look up the Protocol node
   or the known mapping, execute the corresponding action
4. Never heals what requires judgment — only structural/mechanical fixes
   (assign project, set decay_protected, link server, set status)
5. Invariants without heal_protocol (scope, liveness, snapshot) → escalate
   directly to ActionProposal — these need SuperAgent attention

---

## 3. What This Makes the System

| Capra concept | Implementation |
|---|---|
| Metabolism | ingestion (fleet-ingest) + decay (04-07) |
| Circulation | connect (02) + route knowledge |
| Nervous system | wake/converge/liveness/snapshot (01,03,12,14) |
| Cognition | dream round (10) |
| Immune system | 17-invariants + 18-immune-response (detect→heal→verify→escalate) |
| Rhythms | 5min/30min/4h/24h/7d synchronized tempos |
| Self-healing | heal_protocols executed, verified, recorded |
| Self-awareness | InvariantRun + ImmuneResponse + FleetState + SystemHealth |

The system is alive in Capra's precise sense: pattern (graph protocols),
structure (Neo4j + fleet), and process (rhythms + immune loop) — inseparable,
self-sustaining, self-healing.
