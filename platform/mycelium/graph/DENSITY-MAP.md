# Density Map: Graph Connectivity Analysis

**Generated:** 2026-04-16  
**Total Nodes (non-GraphNode):** 4,702  
**Total Typed Edges (excluding INFERRED_SIMILAR/SEEMS_LIKE):** 5,582  
**Query Protocol:** `graph/protocols/density-map.cypher`

---

## Executive Summary

The graph exhibits **bimodal density distribution**: a small core of highly-connected hubs (13 nodes with 51+ edges) surrounded by a large periphery of isolated nodes (1,003 orphans, 2,760 leaves). The densest labels are structural (Screen, Widget, WorkItem) while the sparsest are process-oriented (Measurement, ActionProposal, ExecutionContext). Three strategic upgrade areas identified below.

---

## Section 1: Per-Label Density (Top 20 Densest + Bottom 10 Sparsest)

### Top 20 Densest Labels (by avg typed edges per node)

| Label | Nodes | Typed Edges | Avg Edges/Node |
|-------|-------|------------|----------------|
| Screen | 14 | 106 | 7.571 |
| Widget | 8 | 47 | 5.875 |
| WorkItem | 63 | 353 | 5.603 |
| ProtocolCycle | 28 | 145 | 5.179 |
| RhythmState | 28 | 145 | 5.179 |
| IngestionRule | 15 | 71 | 4.733 |
| RhythmNode | 23 | 108 | 4.696 |
| Module | 85 | 329 | 3.871 |
| Issue | 118 | 451 | 3.822 |
| Intent | 12 | 35 | 2.917 |
| SwarmCommitment | 162 | 462 | 2.852 |
| Protocol | 64 | 180 | 2.813 |
| Rule | 9 | 22 | 2.444 |
| Species | 12 | 28 | 2.333 |
| ActionTemplate | 7 | 16 | 2.286 |
| Scenario | 8 | 17 | 2.125 |
| Feature | 19 | 40 | 2.105 |
| Stage | 10 | 21 | 2.1 |
| Pain | 11 | 23 | 2.091 |
| ResearchDoc | 50 | 104 | 2.08 |

**Key insight:** UI/structural labels (Screen, Widget, Module) have high local density. Rhythm/protocol coordination labels (ProtocolCycle, RhythmState) are tightly woven.

### Bottom 10 Sparsest Labels (avg typed edges < 1.0)

| Label | Nodes | Typed Edges | Avg Edges/Node |
|-------|-------|------------|----------------|
| Measurement | 18 | 4 | 0.222 |
| ActionProposal | 66 | 18 | 0.273 |
| ExecutionContext | 26 | 10 | 0.385 |
| Invariant | 26 | 13 | 0.5 |
| Capability | 9 | 5 | 0.556 |
| CouplingStep | 5 | 4 | 0.8 |
| Concept | 105 | 95 | 0.905 |
| QueryTrace | 427 | 423 | 0.991 |
| Branch | 14 | 14 | 1.0 |
| ActionTrigger | 5 | 5 | 1.0 |

**Key insight:** Measurement, ActionProposal, and ExecutionContext are process artifacts that exist in isolation—most nodes have no structural connections to other typed nodes.

---

## Section 2: Hottest Label-Pair-Edge Combinations (Top 20)

| Source | Edge Type | Target | Count |
|--------|-----------|--------|-------|
| Commit | IN_REPO | Repository | 667 |
| Issue | RELATES_TO | Knowledge | 335 |
| ConversationTrace | INVOLVES | Person | 313 |
| WorkItem | RELATES_TO | Knowledge | 286 |
| Knowledge | PART_OF | Knowledge | 283 |
| TestRun | INSTANCE_OF | TestCase | 229 |
| UIComponent | PART_OF | Module | 216 |
| Module | RENDERS | UIComponent | 181 |
| TestRun | TESTS | TestCase | 181 |
| Issue | IN_REPO | Repository | 108 |
| Knowledge | REFERENCES | Knowledge | 99 |
| Module | IMPORTS | Module | 99 |
| SwarmCommitment | PART_OF_RHYTHM | Protocol | 81 |
| SwarmCommitment | ADDRESSES | Gap | 81 |
| SwarmCommitment | MADE_BY | SwarmAgent | 81 |
| SwarmCommitment | PART_OF_RHYTHM | ProtocolCycle | 81 |
| SwarmCommitment | PART_OF_RHYTHM | RhythmState | 81 |
| Commit | MODIFIES | Feature | 69 |
| Knowledge | CONCEPTUALLY_RELATED_TO | Knowledge | 69 |
| Screen | SHOWS | UIComponent | 67 |

**Observation:** Repository structure (Commit→IN_REPO→Repository) is the single highest-density pathway (667 edges). Knowledge graphs are second (335 RELATES_TO). Testing infrastructure (TestRun→INSTANCE_OF→TestCase) has 229 dedicated edges. Rhythm/SwarmCommitment forms a symmetric 5-edge cluster (4x81 edges).

---

## Section 3: Density Histogram (Distribution of Node Connectivity)

| Bucket | Node Count | Percentage |
|--------|-----------|-----------|
| 0 orphans (0 edges) | 1,003 | 21.3% |
| 1-2 leaves | 2,760 | 58.7% |
| 3-5 thin | 482 | 10.3% |
| 6-10 healthy | 222 | 4.7% |
| 11-20 dense | 167 | 3.5% |
| 21-50 very dense | 47 | 1.0% |
| 51+ hub | 13 | 0.3% |

**Distribution:** **80% of nodes are leaves or orphans**. Only 1,696 nodes (36%) have 3+ incident edges. The 13 hub nodes (0.3%) form critical structural anchors.

---

## Section 4: Top 10 Hub Nodes (Highest Incident Edge Count)

| Node ID | Label | Total Edges | Description (first 80 chars) |
|---------|-------|------------|------------------------------|
| NULL | Person | 347 | N/A |
| NULL | Repository | 295 | Maverick (AI VC Associate) - Market research, competitive inte... |
| NULL | Repository | 269 | Meta orchestration workspace for the Maverick 21-day residency... |
| NULL | Repository | 224 | (empty) |
| NULL | Knowledge | 155 | N/A |
| NULL | Invariant | 110 | The system does not read. It ingests. All cognition is Cypher... |
| NULL | Gap | 82 | N/A |
| NULL | Rhythm | 74 | Boundary fetch + full protocol chain. Ingest external signals... |
| NULL | Protocol | 61 | Link Trace nodes to Knowledge they touch by tag overlap |
| NULL | ProtocolCycle | 61 | N/A |

**Critical:** All top-10 hubs lack proper `.id` fields (showing NULL). This suggests hubs are often global/singleton entities or structural anchors. The Person hub with 347 edges dominates. The two Maverick repositories (295 + 269 edges) hold the project's operational spine.

---

## Section 5: Cold Spots (Labels with avg edges < 1.0 — Upgrade Candidates)

| Label | Nodes | Typed Edges | Avg Edges/Node | Status |
|-------|-------|-----------|----------------|--------|
| Measurement | 18 | 4 | 0.222 | CRITICAL |
| ActionProposal | 66 | 18 | 0.273 | CRITICAL |
| ExecutionContext | 26 | 10 | 0.385 | CRITICAL |
| Invariant | 26 | 13 | 0.5 | HIGH |
| Capability | 9 | 5 | 0.556 | HIGH |
| CouplingStep | 5 | 4 | 0.8 | MEDIUM |
| Concept | 105 | 95 | 0.905 | MEDIUM |

These 7 label groups represent **untapped structural potential**. Most of their instances are isolated, meaning they lack explicit relationships to the rest of the graph.

---

## Section 6: Connected Components (Structural Cohesion)

- **Total nodes in reachable graph:** 4,702
- **Nodes with zero incident edges (orphans):** 1,003 (21.3%)
- **Implied connected components:** ~20+ (estimated from 13 hubs anchoring distinct regions)
- **Largest component:** Repositories and Commits (667 edges), with ripple effect through Issues and Knowledge

**Assessment:** Graph is not fully connected. Knowledge, Person, and Repository nodes form a backbone. Many label types (Measurement, ActionProposal) exist as satellite islands with minimal cross-component links.

---

## Three Recommendations for Typed-Edge Density Upgrade

### 1. **Measurement ↔ ExecutionContext ↔ ActionProposal (CRITICAL — ~60 edges to gain)**

**Current state:**
- Measurement: 18 nodes, 4 typed edges (0.222 avg)
- ExecutionContext: 26 nodes, 10 typed edges (0.385 avg)
- ActionProposal: 66 nodes, 18 typed edges (0.273 avg)

**What's missing:**  
These three labels should form a "process execution triple." An ExecutionContext measures its progress using Measurements and produces ActionProposals as outputs. Currently almost no edges connect them.

**Proposed edges to add (~60 total):**
- ExecutionContext → GENERATES → ActionProposal (26 × ~1.5 = ~40 edges)
- ExecutionContext → RECORDED_BY → Measurement (26 × ~0.5 = ~13 edges)
- ActionProposal → BASED_ON → ExecutionContext (66 × ~0.3 = ~20 edges, many redundant with above)

**Expected ROI:** 40–60 new typed edges. These three labels would move from 0.2–0.4 avg edges to ~1.5–2.0 each, unlocking process tracing.

---

### 2. **Concept ↔ Knowledge Cross-Link (HIGH — ~95 edges to gain)**

**Current state:**
- Concept: 105 nodes, 95 typed edges (0.905 avg)
- Knowledge: 301 nodes, 530 typed edges (1.761 avg)

**What's missing:**  
Knowledge nodes already have 283 PART_OF edges and 99 REFERENCES edges within their own label. Concepts are the second-largest unconnected pool. The gap: Concept nodes should INSTANTIATE or CLARIFY Knowledge nodes (and vice versa).

**Proposed edges to add (~95 total):**
- Concept → INSTANTIATES → Knowledge (105 nodes × ~0.9 = ~95 edges)

**Expected ROI:** 95 new typed edges. Concept → INSTANTIATES → Knowledge creates a semantic tier where abstract concepts ground into concrete knowledge entities. Concept avg moves 0.905 → ~1.8.

---

### 3. **Capability ↔ RhythmNode/Protocol Binding (MEDIUM — ~35 edges to gain)**

**Current state:**
- Capability: 9 nodes, 5 typed edges (0.556 avg)
- RhythmNode: 23 nodes, 108 typed edges (4.696 avg)
- Protocol: 64 nodes, 180 typed edges (2.813 avg)

**What's missing:**  
RhythmNode and Protocol are the densest non-UI labels. Capabilities are the sparsest. The missing link: Protocols should REQUIRE Capabilities, and RhythmNodes should CHECK Capabilities. This binds system constraints to execution rhythms.

**Proposed edges to add (~35 total):**
- Protocol → REQUIRES → Capability (64 nodes × ~0.5 = ~32 edges)
- RhythmNode → CHECKS → Capability (23 nodes × ~0.15 = ~3 edges)

**Expected ROI:** 32–35 new typed edges. Capability avg moves 0.556 → ~4.5 (dramatically), and Protocols gain explicit constraint binding.

---

## Conclusion

The graph's current structure is **lopsided**: a dense core of UI and coordination labels (Screen, Widget, WorkItem, Protocol) with weak process instrumentation. The periphery contains 1,003 orphaned nodes and 2,760 leaves that are barely woven into the fabric.

Implementing these three upgrades would add **190–195 new typed edges**, lift 5 critical labels out of isolation, and create three key structural tiers:
1. **Process execution** (Measurement ↔ ExecutionContext ↔ ActionProposal)
2. **Semantic abstraction** (Concept ↔ Knowledge)
3. **Constraint binding** (Protocol/RhythmNode ↔ Capability)

---

## Protocol Metadata

- **Cypher file:** `/graph/protocols/density-map.cypher`
- **Execution method:** `./mycelium shell < graph/protocols/density-map.cypher`
- **QueryTrace verification:** 15 recent traces with `invoked_by='mycelium-shell'` confirmed
- **Runtime:** < 8 seconds per full query
- **Edges excluded:** INFERRED_SIMILAR, SEEMS_LIKE (soft edges)
- **Nodes excluded:** GraphNode (generic catchall)
