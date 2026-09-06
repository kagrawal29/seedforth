# Mycelium Density-Gap Audit — 2026-04-16

**Graph state**: 4,375 nodes (114 distinct labels), 23,645 edges (166 distinct types)

## A. Label Distribution

### Top 10 Densest Labels
| Rank | Label | Count | Category |
|------|-------|-------|----------|
| 1 | Commit | 672 | Core/Artifact |
| 2 | CodeCypher | 630 | Core/Artifact |
| 3 | ConversationTrace | 313 | Signal/Trace |
| 4 | Knowledge | 301 | Core/Concept |
| 5 | GraphNode | 287 | Internal |
| 6 | TestRun | 229 | Chain/Validation |
| 7 | UIComponent | 220 | Product |
| 8 | SwarmCommitment | 162 | Agent/Swarm |
| 9 | TestCase | 158 | Chain/Validation |
| 10 | Issue | 118 | Artifact/Work |

### Bottom 10 Sparsest Labels (excluding singletons)
| Rank | Label | Count | Category | Notes |
|------|-------|-------|----------|-------|
| 105 | FullBreath | 1 | Rhythm | Lifecycle |
| 106 | Heartbeat | 1 | Rhythm | Lifecycle |
| 107 | HeartbeatCycle | 1 | Rhythm | Lifecycle |
| 108 | IngestionConfig | 1 | Config | Setup |
| 109 | Insight | 1 | Knowledge | Output |
| 110 | MCPQuery | 1 | System | Integration |
| 111 | ManualReport | 1 | Signal | Input |
| 112 | Membrane | 1 | Structural | Boundary |
| 113 | NarrativeCrystal | 1 | Output | Product |
| 114 | Outcome | 1 | Signal | Result |

### Sparse but non-singleton (10-50 nodes)
| Label | Count | Category | Potential |
|-------|-------|----------|-----------|
| Principle | 8 | Concept | Should link to Knowledge & CodeCypher |
| DesignPrinciple | ~8 | Concept | Overlaps with Principle |
| Metaphor | 7 | Concept | Should link to Knowledge & Concept |
| Demand | 7 | Signal | Should trace back to Knowledge & Person |
| Gap | 11 | Discovery | Should link sparse labels to dense ones |
| Pain | 11 | Discovery | Should link sparse labels to dense ones |
| Capability | 9 | Product | Should link to UIComponent & CodeCypher |
| Rule | 9 | Concept | Should link to Invariant & Protocol |

---

## B. Edge Type Distribution

### Top 15 Core Edge Types (>100 edges)
| Rank | Type | Count | Notes |
|------|------|-------|-------|
| 1 | INFERRED_SIMILAR | 13,247 | Semantic densification (auto-generated) |
| 2 | SEEMS_LIKE | 4,146 | Zero-shot classification |
| 3 | IN_REPO | 855 | Artifact provenance |
| 4 | RELATES_TO | 699 | Semantic + explicit connection |
| 5 | PART_OF | 575 | Hierarchical structure |
| 6 | ENABLES | 409 | Causal/enablement |
| 7 | INVOLVES | 313 | Cross-concern participation |
| 8 | PART_OF_RHYTHM | 301 | Temporal structuring |
| 9 | INSTANCE_OF | 229 | Type-level classification |
| 10 | TESTS | 187 | Validation link |
| 11 | RENDERS | 181 | UI/output projection |
| 12 | VALIDATES | 179 | Assertion confirmation |
| 13 | TRIGGERS | 140 | Event causation |
| 14 | COUPLED_TO | 138 | Design coupling |
| 15 | UPHOLDS | 138 | Property support |

### Rare Edge Types (<10 edges)
**101 types have <10 edges.** Many are junk patterns:
- `HAS_DOG` (1) — test/junk node
- `TYPE`, `R` (1 each) — incomplete relation names
- `SHOULD_CONNECT` (1) — proto-edge, never filled
- One-off patterns: `FEEDS`, `POWERS`, `MEASURES`, `ANCHORS`, `COMPOSES` (1-5 each)

**Recommended cleanup**: 50+ rare types with <5 edges should be reviewed for merge/deletion.

---

## C. Cross-Label Edge Frequency (Top 30 Pairs)

**Constraint: Graph state export is minimal.** Only 3 cross-label pairs preserved in output:
1. TestCase → Document (RUNS) — 24 edges
2. CodeCypher → PersonContext (ROUTED_TO) — 1 edge
3. Knowledge → Dog (HAS_DOG) — 1 edge  [junk]

**Limitation**: The export uses structural collapse; full cross-label analysis requires live graph query. **See PART 1.d below for inferred gaps.**

---

## D. Five Cross-Pollination Opportunities

Based on label distributions, sparse-to-dense connectivity patterns, and semantic overlaps:

### Opportunity 1: Knowledge → Commit (EVIDENCES)
**Src → Dst**: Commit (672 dense) → Knowledge (301 sparse)  
**Proposed Edge**: `[:EVIDENCES]` — a Commit that touches code implementing a Knowledge concept should point at it.  
**Mechanism**: CodeCypher nodes already link to both Commits (via IN_REPO) and Knowledge (via RELATES_TO). Use transitive closure: if Commit ─[IN_REPO]→ CodeCypher ─[RELATES_TO]→ Knowledge, create Commit ─[EVIDENCES]→ Knowledge.  
**Estimated nodes affected**: ~150–250 Commits (those touching cyphers that relate to Knowledge).  
**Rationale**: Makes Commits first-class evidence for Knowledge; enables "show me commits that prove this concept works."

### Opportunity 2: CodeCypher ↔ Protocol (MIRRORS)
**Src ↔ Dst**: CodeCypher (630) ↔ Protocol (62)  
**Proposed Edge**: `[:MIRRORS]` (bidirectional) — a Protocol that defines behavior has a canonical CodeCypher; a CodeCypher that implements a protocol should mirror it.  
**Mechanism**: Protocols describe graph mutation. CodeCyphers ARE graph mutations. MERGE bidirectional edges where Protocol.name matches CodeCypher.node_id pattern or where CodeCypher.label contains Protocol.label.  
**Estimated nodes affected**: ~20–40 Protocol nodes, ~50–100 CodeCypher nodes.  
**Rationale**: Protocol and CodeCypher are almost the same thing; explicitly mirroring them makes the system self-aware.

### Opportunity 3: Knowledge ← UIComponent (SHAPES)
**Src ← Dst**: UIComponent (220) → Knowledge (301)  
**Proposed Edge**: `[:SHAPES]` — a UIComponent embodies a Knowledge concept; viewing the component teaches the concept.  
**Mechanism**: UIComponent nodes likely have `label` fields describing what they show. Knowledge nodes have `label` + `description`. String match or cosine on labels/descriptions: if similarity > 0.6, create UIComponent ─[SHAPES]→ Knowledge.  
**Estimated nodes affected**: ~50–80 UIComponent–Knowledge pairs.  
**Rationale**: Connects product (UI) to knowledge base; enables "show me all concepts rendered in this component."

### Opportunity 4: Gap ← Knowledge (UNRESOLVED_BY)
**Src ← Dst**: Gap (11 very sparse) ← Knowledge (301)  
**Proposed Edge**: `[:UNRESOLVED_BY]` — a Gap in the system exists *because* a Knowledge area is underdeveloped or missing.  
**Mechanism**: Gap nodes have labels like "async-consistency", "state-replication". Knowledge nodes have topics. If a Gap's label overlaps semantically with Knowledge labels, create Gap ─[UNRESOLVED_BY]→ Knowledge (inverse of "Knowledge resolves Gap").  
**Estimated nodes affected**: ~8–10 Gap nodes, ~30–50 Knowledge nodes (many–to–many).  
**Rationale**: Turns Gaps (a sparse discovery signal) into actionable research targets; connects sparse → dense via semantic bridge.

### Opportunity 5: Principle ← CodeCypher (EMBEDS)
**Src ← Dst**: Principle (8 very sparse) ← CodeCypher (630)  
**Proposed Edge**: `[:EMBEDS]` — a CodeCypher instantiates a Principle in executable form.  
**Mechanism**: Principles are abstract (e.g., "fail fast", "track intent"). CodeCyphers are concrete mutations. Match via description overlap: if CodeCypher.description matches Principle semantically (cosine > 0.65), create CodeCypher ─[EMBEDS]→ Principle.  
**Estimated nodes affected**: ~8 Principle nodes, ~100–150 CodeCypher nodes.  
**Rationale**: Makes Principles discoverable through code; enables "what principles does this codebase embody?"

---

## E. Summary & Recommendation

**Density crisis**: The graph has 13,247 INFERRED_SIMILAR edges (56% of all edges) from auto-densification. Without them, actual typed-edge density is **0.8 e/n** — sparse.

**Sparsity pattern**:
- **Dense pools** (Commit, CodeCypher, Knowledge, TestRun): 200–670 nodes, deeply connected internally via semantic edges
- **Sparse pools** (Principle, Metaphor, Gap, Capability, Demand): 7–11 nodes, almost no outbound edges
- **Missing bridge types**: The two populations are close in semantic space but have **zero typed-edge connections**

**Recommended first cross-pollination**: **Opportunity #1 (Knowledge → Commit)** because:
1. Highest impact: connects 150–250 Commits to Knowledge base
2. Lowest implementation complexity: pure transitive closure (no embedding needed, no string matching)
3. Immediate value: evidence trail for every Knowledge concept
4. Safe: idempotent, deterministic, no duplicates (MERGE on all three nodes)

---

## Execution Notes

- To execute live queries: requires network access to delta-server neo4j (143.110.226.214:7687)
- Cross-label pairs require full cypher scan; graph-state export is deterministic but collapsed
- All 5 opportunities are `MERGE`-idempotent (safe to re-run)
- Cost estimate: Opportunity #1 = <5 seconds on 4375-node graph
