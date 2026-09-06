# Mycelium Operating System — Plain English

How the graph thinks, breathes, and evolves. Every behavior described here is a Cypher query stored on a node in the graph. The graph runs itself.

---

## Rhythms — The Heartbeat

### Heartbeat (every 30 minutes)
Every 30 minutes, fetch all enabled Protocols and run them in order. This is the system's pulse — ingest external signals, digest them into the graph, excrete waste (expired nodes, stale edges). 18 protocols execute in sequence.

### Realtime (on every new node)
On every MERGE operation (new node or edge created), immediately run the digest and excrete protocols. This is the system's fast-twitch response — when something new enters the graph, process it immediately rather than waiting for the heartbeat.

---

## Ingestion Rules — How New Things Enter

### Commit → Feature
When a new Commit arrives, scan its message for words matching Feature names. If a commit message mentions a feature (e.g. "fix pipeline board"), wire the Commit to that Feature via MODIFIES edge. Marks the commit as digested so it won't be processed again.

### Convergence Detection
When two team members (Person nodes) are marked as converging on the same topic, create or update a Convergence node for that topic. Wire both people to it. This is how the system detects when multiple people are independently working toward the same thing.

### Delivery Confirmation
When a piece of knowledge is delivered to a team member (DeliveryEvent), create a RECEIVED edge from that Person to the Knowledge. This closes the distribution loop — we can now track who has seen what.

### Dependency Blocking
When a WorkItem depends on another WorkItem that isn't done yet, mark the dependent item as blocked. This is how the graph knows which work items can proceed and which must wait.

### Hook Metrics
When a Claude Code hook fires (e.g. pre-commit, post-push), record its execution metrics and wire them to the OperationalRule that defines the hook. This tracks how often each automation actually runs.

### Insight Wiring
When someone produces an insight (via /report or synthesis), wire it to the Person who created it and to any Knowledge nodes it relates to by tag overlap. Insights are the highest-signal data in the system.

### Issue → Knowledge
When a GitHub Issue is ingested, find Knowledge nodes that share tags with the issue title. Wire them via RELATES_TO. This is how issues connect to the knowledge graph — an issue about "LP reporting" auto-links to LP-related Knowledge.

### Knowledge Clustering
When new Knowledge arrives, find existing Knowledge nodes that share 3+ tags with it. Wire them via CONCEPTUALLY_RELATED_TO. This auto-builds the community structure — related knowledge clusters together without anyone manually organizing it.

### Manual Report
When someone submits a manual report (/report), wire it to the Person who reported it and to any Knowledge nodes matching by tag overlap. Manual reports are the team's way of telling the system something important happened.

### MCP Query → Demand
When someone queries the graph via MCP tools (asgard_graph_ask, etc.), check if their query text matches any Demand node domains. If so, wire the query as REINFORCES that demand. Every time you ask the graph about something, that thing becomes more demanded.

### Note → Knowledge
When a Note is created in the graph, find Knowledge nodes that share tags with its content. Wire them via TOUCHES. Notes are lightweight signals — session observations, quick captures.

### Delivery Receipt
When a Person receives Knowledge (delivery confirmed), mark the RECEIVED edge as confirmed. This removes the item from the routing queue — the system knows this person has seen this knowledge.

### TDD Gate
The TDD gate: find any executable node (has a cypher property) that does NOT have a TestCase validating it. These are untested automations — the system flags them as a quality risk. Every protocol and rule must have at least one test.

### Trace → Knowledge
When a Trace arrives (from LangSmith — a team member's Claude session), find Knowledge nodes that share tags with the trace question. Wire them via TOUCHES. This is how the system learns what Knowledge is being actively used.

### WorkItem → Issue
When a WorkItem is created, find the GitHub Issue it tracks by issue number. Wire them via TRACKS. This connects the development plan (WorkItems) to the issue tracker (GitHub Issues).

---

## Protocols — What the System Thinks About

### Connect
Wire unprocessed Traces to the Knowledge they touch. When someone asks about "LP reporting" in a Claude session, that trace gets connected to LP-related Knowledge nodes. The graph learns what people are actively thinking about.

### Converge
Detect when 2+ people are independently asking about the same graph region. If Abhishek and Pranav both have intents touching "architecture", create a Convergence node. This is the system's way of saying "these two should talk."

### Decay: Confidence
If a Knowledge node has high/medium confidence but only 1 evidence source, downgrade it to low. Single-source claims don't get to be confident. Forces the system to be honest about what it's sure of.

### Decay: Demand
Flag Knowledge that nobody is asking about, nobody is tracing, and no coupling events touch. This is knowledge that may have gone stale — not deleted, but flagged for review. The system forgets gracefully.

### Decay: Edges
Remove inferred conceptual edges where neither endpoint has any recent activity. If the system guessed two Knowledge nodes are related, but nobody ever queries or touches either one, the guess gets pruned. Keeps the graph from filling with noise.

### Decay: TTL
Time-to-live cleanup. CouplingEvents expire after 7 days. Traces after 2 days. Commits after 14 days. QueryTraces after 2 days. These are transient signals — they informed the graph when fresh, now they can go. Keeps the graph lean.

### Dedup
Find and remove duplicate edges between the same pair of nodes. If two CONCEPTUALLY_RELATED_TO edges exist between Knowledge A and Knowledge B, delete one. Prevents edge accumulation from repeated protocol runs.

### Gap: Feature-Screen
Find Features that aren't placed on any Screen in the UI. A feature without a screen means it's built but invisible to users. Flags orphan features for the product team.

### Gap: Knowledge
Find Demand signals that have gap_signal=true and low coverage. These are things the team is asking about where the graph has no good answer. The highest-priority gaps to fill.

### Gap: Scenario Coverage
Find Scenarios that have no Feature serving them. Creates an ActionProposal saying "build a feature for this unserved scenario." This is how the graph proposes new work based on product gaps.

### Gap: Spec-Needs
Find SpecNeeds whose addressed Scenario has no implementing Feature. These are spec requirements that haven't been built yet. Surfaces the gap between what was specified and what exists.

### Heal: Orphans
Delete transient nodes (concepts, demands, intents, traces, commits) that have zero edges. A node with no connections is noise — it got created but never wired to anything. Clean it up.

### Heal: Triangles (The Dream Round)
If Knowledge A connects to Bridge and Bridge connects to Knowledge C, but A and C aren't directly connected — and one of them has recent trace activity — infer a CONCEPTUALLY_RELATED_TO edge. This is the dream round: the graph discovers hidden connections by closing triangles.

### Immune System
Compare current counts of Protocols, Invariants, IngestionRules, Rhythms, and ENABLES edges against the last authorized snapshot. If any count changed without authorization, flag it as a MUTATION. Prevents unauthorized structural changes to the system's core.

### Learn
Count how many dream-round-inferred edges got subsequently activated (someone traced or queried one of their endpoints). Record as a Measurement. This measures whether the system's guesses were useful — did anyone actually follow the connections it inferred?

### Liveness
Is the system alive? Check when the last pipeline ran, when the last trace arrived, and whether rhythms are active. If nothing has happened recently, the system may need attention.

### Propose
Find WorkItems that are open and have no unfinished dependencies. Create ActionProposal nodes for them. This is how the system says "these work items are ready to start — no blockers." The dream round surfaces unblocked work automatically.

### Report
Count total nodes, total edges, tests passing vs total. The system knows its own shape — how big it is and how healthy its test suite is.

### Resolve Contradictions
When two Knowledge nodes in the same category share 4+ tags, they're probably about the same thing. Demote the one with fewer connections (lower degree = less validated). The graph resolves its own contradictions by trusting the more-connected version.

### Route
Find Knowledge that addresses a Convergence topic but hasn't been delivered to the people converging on it. This is the distribution engine — when the graph knows something relevant to your work and you haven't seen it yet, it routes it to you.

### Snapshot
Capture the current graph state (node counts, edge counts, deltas from last snapshot). Link to previous snapshot via FOLLOWS edge. Creates a time series of the graph's evolution. Used by the immune system to detect unauthorized changes.

### Sync WorkItems
When a GitHub Issue is closed, find the WorkItem that tracks it and mark it as done. This is the feedback loop — humans close issues, the graph updates its development plan automatically.

### Wake
Should the system process right now? Check if any node is newer than the last pipeline run. If yes, there's new data to digest. If no, the system can sleep. This prevents unnecessary processing cycles.

---

## Bridges — Connecting Team Work to Market Intelligence

### Intent → Market Evidence
When a team member has a recurring intent (e.g. Abhishek asking about architecture 7 times), find market evidence in the FeatureCategories that match their domain. Surface the top 5 practitioner quotes by engagement. This is how architecture decisions get market-informed automatically.

### Demand → Competitive Context
When the team has active demand signals, find competitors who cover that space, their claims, and market insights that contradict those claims. Automatically surfaces "you are asking about X — here is what competitors say and where they are wrong."

### Architecture → Market Landscape
When someone is evaluating a technology choice, find competitors who ship MCP servers or integrations in that space. Surfaces "you are deciding on Nango — here is what Attio ships (35 MCP tools), what Affinity ships (20 ops), what Standard Metrics ships (38 tools)." Architecture decisions informed by competitive reality.

---

## The Compounding Loop

```
Team works → Traces captured → Graph connects traces to knowledge
  → Demand signals strengthen → Dream round infers new connections
    → Gaps detected → ActionProposals created → Team picks up work
      → Issues closed → WorkItems synced → Downstream work unblocks
        → Loop continues
```

Every 30 minutes. Automatically. The graph doesn't wait to be asked.

---

## The Market Research Layer (built 2026-04-11)

The graph now holds the full competitive intelligence layer:

- **42 Competitors** with threat levels, MCP status, pricing, and feature coverage
- **40 Claims** — what competitors say about themselves
- **1,200+ Evidence items** — practitioner quotes from Reddit, Twitter, LinkedIn with citations
- **488 G2 Reviews** — structured product reviews wired to competitors
- **15 Pain Points** — quantified with signal counts and platform spread
- **5 Market Gaps** — validated across all platforms
- **22 Market Insights** — ground truth findings about the VC tool market
- **18 Switching Signals** — who's leaving which competitor for whom
- **12 Feature Categories** — market workflow areas mapped to product features
- **10 Segments** — buyer personas with pain profiles
- **7 Platforms** — where evidence was collected

### Key bridges
- Product Pain → VALIDATED_BY → Market PainPoint → BACKED_BY → Evidence
- Feature → COMPETES_WITH → FeatureCategory ← COVERS ← Competitor
- Segment → MAPS_TO → Persona
- SwitchingSignal → CREATES_OPPORTUNITY → FeatureCategory
- MarketInsight → TENSIONS_WITH → Claim
- Convergence → CONVERGES_TO → PainPoint

### The strongest signal
LP Reporting: impact score 48 (8 evidence items x 3 segments x 2x convergence bonus). 4x higher than anything else. Felt by Emerging Manager, GP/Partner, IR Professional. Status: planned-v2. The graph's loudest unresolved signal.

---

*This file is a snapshot. The graph is the living version. Query it:*
```cypher
MATCH (n) WHERE n.plain_english IS NOT NULL
RETURN labels(n)[0] AS type, n.label, n.plain_english
```
