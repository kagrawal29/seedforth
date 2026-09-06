# Mycelium — Self-Describable Graph System

*Generated live from the graph.*

---

## Design Principles

### The graph is the source of truth

Everything the system knows, does, or enforces is represented as nodes and edges in Neo4j. Files in the repo are serialization formats for git persistence, not primary storage. If the graph and a file disagree, the graph wins — unless the file is a bootstrap that the graph has not yet been seeded from.

### Cypher-native, not code-native

Behavior is expressed as cypher, not as Python/TypeScript/etc. The only non-cypher files are: 2 small Python sidecars (ed25519 crypto, Ollama embedding) that cross boundaries cypher cannot, and ~15 bash shell runners that pipe cypher files to cypher-shell. Everything else is graph-native.

### Merkle as properties, not as entities

Earlier design stored Merkle trees as graph entities (:MerkleNode, :MerkleTree). That created a recursive inflation bug where each new tree included prior MerkleNodes in its hash input — 7 generations compounded into 546,450 nodes. Properties cannot contain themselves, so storing leaf_hash as a property on each node eliminates the recursion by construction.

### Self-describability is trust

A system that cannot fully explain itself cannot be fully trusted. Mycelium must be able to generate a complete human-readable manual from its own graph — concepts, protocols, invariants, commands, guides, principles — with zero hardcoded external documentation. mycelium docs reads :Concept + :Guide + :DesignPrinciple nodes plus the live Protocol/Invariant/TestCase/Command sets and emits a full markdown manual. This file (docs-seed.cypher) is the only place where conceptual explanations are authored, and even those live in the graph after seeding.

### Auto-heal via invariants

Anything that can be automatically repaired should be. Invariants with heal_protocols detect + fix their own unhealth without human intervention. Density drops, embeddings drift, orphans accumulate — the immune system compensates on its own cadence. Human attention reserved for structural decisions.


## Concepts (the vocabulary)

### Being (identity)

The singleton identity anchor for the whole graph. One node (node_id = being-mycelium) that holds the current root_hash, heartbeat counter, chain pointer (CURRENT_SPECIES), and liveness flags. Every query about \"where is the graph now?\" starts here.

```cypher
MATCH (b:Being) RETURN b.root_hash, b.heartbeat_count
```

### Species (chain)

A block in the chain. Commits to the state of the graph at the moment it was minted via its manifest_root (sha256 of sorted leaf_hashes of all domain nodes). Species form a parent chain via :DESCENDED_FROM edges. canonical=true marks the current head.

```cypher
MATCH (b:Being)-[:CURRENT_SPECIES]->(s:Species) RETURN s.node_id, s.manifest_root
```

### Witness (chain)

A cryptographic validator. Each Witness has an ed25519 public_key registered in the graph; the matching private key stays at ~/.mycelium/witness-<alias>.key outside the graph. Witnesses sign candidate species to promote them to canonical.

```cypher
MATCH (w:Witness) RETURN w.alias, w.public_key
```

### WitnessSignature (chain)

A signed attestation linking a Witness to a Species. Carries the ed25519 signature over (manifest_root || parent_dna || species_node_id). verify-signatures.sh walks these and stamps verified=true; canonize only counts verified signatures.

```cypher
MATCH (ws:WitnessSignature)-[:SIGNS]->(s:Species) RETURN ws.witness_alias, ws.algorithm, ws.verified
```

### Invariant (integrity)

A rule that must always be healthy. Each Invariant has a check_cypher property (run by graph/runner/run-invariants.sh) and can optionally carry a heal_protocol that the immune system fires when the invariant goes unhealthy. The immune loop re-runs the check after heal and logs the outcome.

```cypher
MATCH (i:Invariant) WHERE i.health = \"unhealthy\" RETURN i.node_id, i.check_cypher, i.heal_protocol
```

### TestCase (integrity)

An assertion that is verified on the graph. Each TestCase carries an assertion_cypher that returns a boolean (or a value compared to expected). run-tests.sh executes every enabled TestCase and sets last_result to pass|fail. Failing tests block validate-merge.

```cypher
MATCH (t:TestCase) WHERE t.last_result = \"fail\" RETURN t.node_id, t.label, t.actual, t.expected
```

### Protocol (behavior)

A named executable routine. Protocols either hold their cypher inline (for short ones like heartbeat) or reference a .cypher file via file_path + file_sha256. Graph/runner scripts look up Protocol nodes and execute them. Protocols are decomposed into :CypherAtom chains for finer granularity (Phase 15).

```cypher
MATCH (p:Protocol {enabled: true}) RETURN p.node_id, p.protocol_type, p.cadence
```

### CypherAtom (behavior)

An atomic unit of cypher, one statement or one clause. Atoms compose into protocols via :FEEDS (variable threading) and :FOLLOWS (sequential) edges. Each atom carries a semantic (natural-language description), fire_count (Hebbian weight), and embedding (semantic search). Scripts become walks through the atom graph.

```cypher
MATCH (p:Protocol)-[:FIRST_ATOM]->(first:CypherAtom) RETURN p.node_id, first.node_id, first.semantic
```

### Command (operator)

A user-facing CLI action exposed by the `mycelium` binary. Each Command has a name, usage, description, example, and runner. The CLI reads :Command nodes at runtime and dispatches to the registered runner — adding a new command is a single MERGE, no code edit.

```cypher
MATCH (c:Command) RETURN c.name, c.usage, c.description ORDER BY c.category, c.order
```

### Query (learning)

A cypher query keyed by sha256 of its text. Same cypher = same Query node, with fire_count incremented on every invocation. This is the Hebbian layer: paths that fire together literally ARE the same node, and their strength is fire_count. Query.semantic holds a natural-language description for future NL lookup.

```cypher
MATCH (q:Query) RETURN q.cypher_hash, q.fire_count, q.last_command ORDER BY q.fire_count DESC LIMIT 10
```

### QueryTrace (learning)

A per-invocation historical record of a Query firing. QueryTrace nodes link to their Query via :INSTANCE_OF and to the touched nodes via touched_ids. mycelium watching reads the last 10 seconds of QueryTraces to show live cognition.

```cypher
MATCH (qt:QueryTrace) WHERE qt.invoked_epoch_ms > timestamp() - 10000 RETURN qt.command, qt.cypher_summary
```

### SkipKey (integrity)

A property name excluded from the leaf_hash computation. Used to keep Merkle root stable against high-churn, derived, or liveness properties. Categories: merkle-output, liveness, phase1-state, lifecycle, derived-output, chain-verification, immune, execution-telemetry, hebbian, synapse.

```cypher
MATCH (sk:SkipKey) RETURN sk.category, sk.key, sk.reason
```

### Source (federation)

An external graph authorized to import nodes into mycelium. Each Source has a public_key, schema_version, and description. Imports from a Source land as :Imported nodes with compound node_ids of the form <source_alias>:<original-id>.

```cypher
MATCH (s:Source) RETURN s.alias, s.schema_version, s.public_key
```

### Imported (federation)

A secondary label on nodes that came from a Source. Imported nodes are read-only and isolated from core invariants by default. They carry provenance (the source alias) and imported_in_species (which candidate species the import landed in) for audit.

```cypher
MATCH (n:Imported {provenance: \"ember\"}) RETURN n.node_id, n.imported_in_species
```

### Adopted (federation)

A formerly-imported node promoted to a full citizen. Adoption removes :Imported, adds :Adopted, keeps provenance + adopted_from_provenance as audit trail. Adoption runs inside validate-merge, so if the adopted node would break any invariant, the adoption rolls back.

```cypher
MATCH (n:Adopted) RETURN n.node_id, n.adopted_from_provenance, n.adopted_by, n.adopted_at
```

### Research (lineage)

A note, paper, fragment, or unformed idea that could eventually become something. Researches have author, created_at, tags, and an optional :ORIGINATES edge to one or more :Hypothesis nodes that the research suggests. They are auditable — every reader can see where an idea came from.

```cypher
MATCH (r:Research {topic: \"Hebbian learning\"}) RETURN r.content, r.author, r.created_at
```

### Hypothesis (lineage)

An if-X-then-Y claim that is not yet verified. Carries a confidence score, evidence links (to :Research and :TestCase nodes), and a status (proposed | investigating | supported | refuted). A hypothesis becomes a :Skill or a :Feature when verified.

```cypher
MATCH (h:Hypothesis {status: \"investigating\"}) RETURN h.claim, h.confidence
```

### Skill (lineage)

A reusable capability — \"how to do X\". Skills are bundles of :CypherAtom + :ExternalCode + :IntegrationPoint that together achieve a goal. Skills can be composed into :Workflow nodes. A skill has an owner, a maturity level, and a test coverage score.

```cypher
MATCH (s:Skill)-[:POWERS]->(w:Workflow) RETURN s.name, w.name
```

### Workflow (lineage)

A sequence of operations achieving a user-level goal. Workflows :COMPOSE :CypherAtoms and/or :Skills, and each step is auditable via QueryTrace. Workflows can be :TRIGGERED_BY events (commit, webhook, cron) and have expected duration + success criteria.

```cypher
MATCH (w:Workflow {name: \"onboard-contributor\"})-[:COMPOSES]->(atom:CypherAtom) RETURN atom.node_id, atom.semantic
```

### Subagent (lineage)

An autonomous agent with its own system prompt, tool set, and identity. Subagents have a name, role, system_prompt, tools (list of :Command or :Skill node_ids), owner, and a :TRACE edge to every QueryTrace they originate. The graph tracks which subagent did what — full provenance per action.

```cypher
MATCH (sa:Subagent)-[:USES_SKILL]->(sk:Skill) RETURN sa.name, sk.name
```

### Schema (lineage)

A typed contract — the shape of a node label, the shape of an edge, the shape of an external API response. Schemas have a version, a set of required fields, optional fields, and an example. Validated at ingestion time by validate-merge.

```cypher
MATCH (sc:Schema {for_label: \"Species\"}) RETURN sc.version, sc.required_fields
```

### Feature (lineage)

A user-visible product capability. Features :IMPLEMENT :Workflow + :Skill, :SURFACE_IN :UIComponent, and have acceptance criteria (:TestCase list). Every feature carries its lineage from the :Research it came from, through :Hypothesis, to shipped code + UI. Feature flags can mark features as experimental/stable/deprecated.

```cypher
MATCH (f:Feature)-[:SURFACES_IN]->(ui:UIComponent) RETURN f.name, ui.label
```

### AuditTrail (lineage)

The chain of mutations on a node or subsystem. Every write goes through validate-merge which mints a candidate species — the species chain itself IS the audit trail at the system level. For per-node audit, each node can carry modified_by, modified_at, and a :LAST_MODIFIED_BY edge to a :Person or :Subagent.

```cypher
MATCH (n)-[:LAST_MODIFIED_BY]->(p:Person) WHERE n.modified_at > \"2026-04-01\" RETURN n.node_id, p.alias
```


## Operator Guides

### Installation + Quick Start (getting-started)

From zero to a live mycelium in ~10 minutes.

### Propose a Mutation (operator)

How to submit a change to the graph.

### Onboard a Witness (operator)

How to become a signer.

### Import an External Graph (federation)

How to flow another graph into mycelium.

### Merkle Integrity (design)

How the Merkle layer works.

### Immune System (design)

How the auto-heal loop works.

### Fire Together, Wire Together (design)

How the graph learns from its own operation.

### Using Mycelium Safely (operator)

Principles and guardrails for operating the graph without breaking it.

### Merge Protocol (end-to-end) (operator)

The complete flow from a mutation idea to a canonical chain advance.

### Daily Operations (operator)

Common tasks after the graph is running.

### Dev Mental Model — Code is a Runtime for the Graph (developer)

The one idea you need before writing anything that touches mycelium.

### Integrate a Workflow (developer)

Add a new external workflow to mycelium in 6 steps.

### Write a Protocol (developer)

The anatomy of a cypher protocol that other developers can trust.

### Write External Code (Python/Shell/Whatever) (developer)

When cypher cannot do it alone.

### Add a CLI Command (developer)

Make your workflow invokable via `mycelium <name>`.

### Best Practices (developer)

Learned-the-hard-way rules that keep the graph healthy.

### Troubleshooting (developer)

What to check when something is wrong.


## Live Capabilities

- **mycelium mint** — Mint a candidate species from the current graph state. No-op if no drift.
- **mycelium sign <candidate-id> <witness-alias>** — Sign a candidate species with your local ed25519 key.
- **mycelium canonize <candidate-id>** — Verify signatures + promote a signed candidate to canonical. Advances chain head.
- **mycelium witness-init <alias>** — Generate an ed25519 keypair and register as a Witness node.
- **mycelium import <source-alias> <bundle.cypher>** — Import an external graph bundle under a namespaced Source. Runs validate-merge internally.
- **mycelium adopt <node-id> <your-alias>** — Promote an imported node to a full citizen. Runs validate-merge scoped to the node.
- **mycelium register-source <alias> <public-key> [schema] [desc]** — Register an external Source with its public key.
- **mycelium docs** — Generate the full human-readable manual live from the graph. Concepts, guides, principles, capabilities, duties, UX rubric. Redirect to a file: mycelium docs > MYCELIUM.md
- **mycelium report [name]** — On-demand templatized dashboard reports. Run with no arg to list available reports. Categories: topology, chain, health, federation, cognition.
- **mycelium know-thyself** — Self-model: what I am, my capabilities, my protocols, my duties, my tests, my code. Queried live from the graph.
- **mycelium help** — List all commands registered in the graph.
- **mycelium health** — Detailed health report: identity, merkle, invariants (per-rule pass/fail), tests aggregate + failing list, deferrals, density, embedding coverage.
- **mycelium test [<node_id>|--all]** — List all active tests, run a single test by node_id, or run every test with --all.
- **mycelium watching** — Snapshot of atoms firing in the last 10 seconds — live cognition via QueryTraces.
- **mycelium top** — Unix top-style live feed of hottest atoms and queries by fire_count. Refreshes every 2s.
- **mycelium history [n]** — Recent CLI invocations, reconstructed from QueryTrace nodes. Default: last 20.
- **mycelium status** — Current chain head, invariant health, test status, pending candidates, Merkle root.
- **mycelium verify** — Run merkle-properties + invariants + tests. Exits non-zero if anything is unhealthy.
- **mycelium breathe** — Run the heartbeat protocol once. (Loop: graph/runner/heartbeat-loop.sh)
- **mycelium ask <prompt> [--top N] [--run]** — Natural-language semantic dispatch. Embed prompt via Ollama, vector-search for closest matches, optionally execute top hit.
- **mycelium search <text query>** — Semantic similarity search over node embeddings. Returns top 10.
- **mycelium embed** — Regenerate embeddings for any nodes whose leaf_hash changed. O(dirty nodes).
- **mycelium q <cypher>** — Ad-hoc cypher query with pretty-printed output. Alias: query.
- **mycelium show <node_id>** — Deep inspection of a node: labels, properties, incoming + outgoing edges.
- **mycelium explain <node_id>** — Everything show does, plus top 5 semantic neighbors via the vector index.
- **mycelium export** — Regenerate graph-state.cypher from current Neo4j state (skip-key aware).
- **mycelium swarm <prompt>** — Dispatch N parallel workers to run health + gap checks on the graph. Compounds to depth 3 by default: workers that find gaps spawn sub-swarms to investigate each gap type. Env: MYCELIUM_SWARM_MAX_DEPTH=3, MYCELIUM_SWARM_DEPTH=1 (auto-increment on recursion).
- **mycelium swarm-status [swarm_id]** — List recent swarms, or show detailed worker status for one swarm.
- **mycelium proof-of-merge <file.cypher>** — Dry-run a proposed cypher mutation against the current state. Applies inside a transaction that rolls back regardless of outcome. Answers: \"would this PR pass CI?\"

## Live Protocols

- `protocol-immune` — (no label)
- `protocol-liveness` — (no label)
- `protocol-wake` — (no label)
- `protocol-heartbeat` — Heartbeat — gives the graph its breath
- `protocol-boundary-traces` — (no label)
- `protocol-boundary-knowledge` — (no label)
- `protocol-boundary-layers` — (no label)
- `protocol-cypher-compound` — Digest: aggregate CodeCypher modules
- `protocol-boundary-code-cypher` — Boundary: ingest code Cypher literals
- `protocol-connect` — (no label)
- `protocol-dedup` — (no label)
- `protocol-decay-demand` — (no label)
- `protocol-atom-schema-init` — Initialize the CypherAtom schema + heartbeat PoC
- `protocol-decay-edges` — (no label)
- `protocol-decay-confidence` — (no label)
- `protocol-atomize-protocol` — Parse a .cypher file into CypherAtom nodes with FOLLOWS edges
- `protocol-decay-ttl` — (no label)
- `protocol-atom-run` — Execute a Protocol by walking its CypherAtom chain
- `protocol-resolve-contradictions` — (no label)
- `protocol-sync-workitems` — (no label)
- `protocol-skip-keys-init` — Initialize SkipKey config nodes for Merkle
- `protocol-converge` — (no label)
- `protocol-heal-triangles` — (no label)
- `protocol-heal-orphans` — (no label)
- `protocol-propose` — (no label)
- `protocol-route` — (no label)
- `protocol-learn` — (no label)
- `protocol-report` — (no label)
- `protocol-snapshot` — (no label)
- `protocol-merkle-properties` — Merkle-as-properties: compute leaf_hash per node + root_hash on Being
- `protocol-embed-index-init` — Create HNSW Vector Index for Node Embeddings
- `protocol-run-invariants` — Run Invariants
- `protocol-run-tests` — Run Tests
- `protocol-export-graph-state` — Export canonical graph state as deterministic MERGE cypher
- `protocol-embed-dirty` — Re-embed nodes whose leaf_hash drifted from embedding_for_leaf_hash
- `protocol-semantic-densify` — Semantic densification via embeddings
- `protocol-promote-refs-to-edges` — Promote foreign-key properties to edges
- `protocol-strengthen-edges` — Hebbian edge strengthening from recent QueryTraces
- `protocol-semantic-classify` — Zero-shot classification — every node gets a :SEEMS_LIKE edge to its closest :Concept
- `protocol-semantic-cluster` — Label-propagation community detection over INFERRED_SIMILAR edges
- `protocol-semantic-anomaly` — Surface nodes whose best neighbor cosine < 0.55 as :SemanticOutlier
- `protocol-crystal-replication` — Crystal Replication: spread successful patterns across the graph
- `protocol-dedup-convergence` — Dedup Convergence by region
- `protocol-detect-forks` — Detect Lineage Forks
- `protocol-dna-fingerprint` — DNA Fingerprint
- `protocol-genome-verify` — Genome Hash Verification
- `protocol-graph-native-auth` — Graph-Native Auth
- `protocol-resolve-forks` — Resolve Lineage Forks (heaviest-crystal wins)
- `protocol-self-iterate` — Heartbeat sample
- `protocol-self-registration` — Self-Registration
- `protocol-token-revocation` — Token Revocation
- `protocol-token-rotation` — Token Rotation
- `protocol-verify-lineage` — Verify Species Lineage

## Live Duties (Invariants)

- [healthy] **Distribution is additive**  
- [healthy] **Collective dream anchors everything**  
- [healthy] **Invariant 2: Distribution Gate**  Nothing reaches team repos without evaluation. Hooks are NEVER auto-distributed.
- [healthy] **Invariant 3: Pipeline Allowlist**  Only known scripts can execute. Graph-stored paths validated against allowlist.
- [healthy] **Invariant 4: Boundary Redaction**  All text entering the graph is scanned for secrets and redacted at every boundary.
- [healthy] **Invariant 5: Least Privilege**  Each agent gets only the tools its job requires. No Bash unless genuinely needed.
- [healthy] **Invariant 6: Cypher-Native Intelligence**  Intelligence lives in graph traversal. Python is I/O glue. No NetworkX, no manual adjacency.
- [healthy] **Invariant 7: Graph-Native System State**  All system knowledge, config, tests, and invariants live as graph nodes. If it is not in the graph, it does not exist to the system.
- [healthy] **Invariant 8: Real-Time Ingestion**  The graph reflects reality with zero delay. Every signal is ingested as it happens. Watermarks prevent duplication. The watermark lives in the graph.
- [healthy] **Cypher-Native Protocol**  The system does not read. It ingests. All cognition is Cypher. Python is I/O glue at the boundary. Every ingestion triggers the full protocol chain. Zero LLM cost.
- [healthy] **Invariant 13: Convergence Detection is Live**  At least one Convergence exists AND there are at least 2x more Intents than Convergences (healthy intent-to-convergence ratio).
- [healthy] **Invariant 21: Witnesses Have Distinct Keys**  No two Witnesses may share a public_key. Each witness is a distinct cryptographic identity.
- [healthy] **Invariant 24: Every node with leaf_hash has a current embedding**  A node is out-of-sync if its leaf_hash has drifted since its last embedding. Drift accumulates as the graph mutates. Immune system fires embed-dirty when this count is > 0.
- [healthy] **Invariant 17: Exactly One Genesis Species**  There must be exactly one Species with genesis=true. No genesis can have a parent. All other species descend from genesis through DESCENDED_FROM chain.
- [healthy] **Invariant 18: Genesis Species Has No Parent**  Genesis species must have null or literal-genesis parent_dna. Nothing points backwards from genesis.
- [healthy] **Invariant 23: Graph density >= threshold**  Edges per node must stay above the threshold. Below it, the graph becomes structurally weak — orphan nodes, un-traversable paths, weak semantic coverage. The immune system auto-fires semantic densification when this invariant goes unhealthy.
- [healthy] **Invariant 12: Auth is Graph-Native**  All auth resolves through Person.token_hash. Env tokens are bootstrap only.
- [healthy] **Invariant 14: Lineage is Always Traceable**  The current species must either be marked genesis OR have at least one ancestor reachable via DESCENDED_FROM. No orphan species.
- [healthy] **Invariant 16: Current Species has Manifest Root**  The current Species must carry a full 64-char sha256 manifest_root, committing to every verified crystal at mint time.
- [healthy] **Invariant 19: No Unresolved Forks**  Every fork in the species tree must have exactly one canonical child.
- [healthy] **Invariant 25: Every node with an embedding has a :SEEMS_LIKE classification**  Every non-Concept node with an embedding should have at least one :SEEMS_LIKE -> :Concept edge. Unclassified nodes are a densification gap.
- [healthy] **Invariant 15: Every Signed Species Has a Known Signer**  Every Species with signed=true must have a SIGNED_BY edge to a Person with matching public_key. No anonymous species.

## UX Rubric


---
*Manual generated by `mycelium docs`. Source: live Neo4j query over :Concept, :Guide, :Protocol, :Invariant, :Command, :DesignPrinciple, :UXRubric nodes. Nothing is hardcoded here.*
