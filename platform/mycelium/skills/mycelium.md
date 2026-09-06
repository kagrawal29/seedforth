---
name: mycelium
description: Query the team's living knowledge graph to find prior decisions, patterns, solutions to similar problems, architectural insights, open gaps, and cross-project couplings. Invoke whenever the user asks questions that might already have an answer in the team's collective memory, or before building something that might already exist.
triggers:
  - user asks "has anyone done X", "is there already", "what did we decide", "who worked on"
  - user is about to implement something where a pattern or prior decision might exist
  - user mentions architecture decisions, invariants, protocols, naming conventions, or design patterns
  - before designing a new integration, data flow, or architectural component
  - user is debugging something that looks like a known problem
---

## What Mycelium Is

Mycelium is the team's living knowledge graph built on Neo4j. It holds 9,377+ nodes spanning decisions, protocols (108), test cases (280), invariants (53), architectural patterns, work items, conversation traces, and code couplings. The graph runs at `bolt://5.78.206.137:7699` (production, read-only, team-canonical) and `bolt://5.78.206.137:7698` (development, forkable). Unlike a database that you query, Mycelium IS the team's collective operating system — it encodes how decisions are made, what's been tried, what works, and what's blocked. Autonomous score: 100.

## How to Invoke It

You have the **Bash tool**. The `mycelium` CLI is installed globally on every teammate's machine by `setup-team.sh` (Slice E-A, merged). It resolves from any directory.

When appropriate, run mycelium commands through Bash and cite the results. No MCP server, no special tools — just the `mycelium` CLI via Bash:

```bash
mycelium --target prod ask "how do we handle rate limiting"
```

Then parse the output and surface it to the user with proper citation.

## Target Selection

The CLI accepts `--target <prod|dev|local>`:

- **`prod`** — canonical team-trusted graph. Read-only. **Default for all read queries.**
- **`dev`** — experimental branch, still forkable. Use when the user is exploring speculative patterns or the prod graph lacks context on a very recent topic.
- **`local`** — teammate's own writable copy. Only use if the user explicitly asks about their local state.

**Default: always use `--target prod` unless told otherwise.**

## When to Use Mycelium

### Scenario 1: User asks for a pattern or prior solution

**What to do:** Run `mycelium --target prod ask "how do we usually handle <pattern>"` via Bash.

Example: User asks "How do we rate-limit API calls?" → Search returns the RateLimitingProtocol node with its implementation, test cases, and known gotchas.

### Scenario 2: User is about to name or design something

**What to do:** Run `mycelium --target prod ask "naming convention for <thing>"` before inventing a new convention.

Example: User wants to name a new work item type → Search returns existing naming patterns plus examples.

### Scenario 3: User hits a familiar-looking bug or blocker

**What to do:** Run `mycelium --target prod ask "similar error: <symptom>"`.

Example: User sees "timeout during graph traversal" → Search returns the known issue, the fix (batch size reduction), and who implemented it.

### Scenario 4: User is designing a new protocol or architecture component

**What to do:** Run `mycelium --target prod ask "existing protocols that do <capability>"`.

Example: User wants to add healing logic → Search returns existing healing protocols with their amortization scores and test coverage.

### Scenario 5: User is curious about the team's topology around a concept

**What to do:** Run a neighborhood Cypher query through `mycelium shell`:

```bash
mycelium --target prod shell "MATCH (n {node_id:'being-pulse'})-[*1..2]-(m) RETURN DISTINCT m.node_id, labels(m) LIMIT 50"
```

Example: User asks "What do we know about Acme Corp?" → Returns the Company node neighborhood (nearby projects, decisions, signals, team demand).

## CLI Reference

### mycelium --target <target> ask "<question>"

Natural language semantic search. Returns ranked matching nodes as plain text (node_ids, labels, snippets, scores).

**Purpose:** Answer questions about patterns, decisions, and prior solutions by meaning, not keyword.

**Example:**
```bash
mycelium --target prod ask "how do we handle authentication in agents"
```

### mycelium --target <target> shell "<cypher>"

Execute a Cypher query against the graph. Returns a plain-text table.

**Purpose:** Precise structural navigation when you know the graph shape (labels, relationships, properties). Use for neighborhoods, counts, filtered lookups.

**Example:**
```bash
mycelium --target prod shell "MATCH (p:Protocol) WHERE p.capability = 'rate-limiting' RETURN p.node_id, p.label LIMIT 10"
```

### mycelium --target <target> status

Graph health snapshot. Prints node count, edge count, autonomous_score, healthy/failing invariants, heartbeat state.

**Purpose:** Verify the graph is healthy before relying on its answers, or when the user asks "is mycelium up?"

**Example:**
```bash
mycelium --target prod status
```

### Neighborhood exploration (via shell)

There's no dedicated subcommand — express it as Cypher:

```bash
mycelium --target prod shell "MATCH (n {node_id:'<id>'})-[*1..2]-(m) RETURN DISTINCT m.node_id, labels(m) LIMIT 50"
```

Adjust the hop count (`*1..2` or `*1..3`) depending on how far out the user wants to explore. Keep the `LIMIT 50` cap.

## Output Parsing

Both `ask` and `shell` return **plain text**, not JSON. There is no schema guarantee today. Parse loosely:

- `ask` returns something like:
  ```
  [score 0.87] node_id=proto-rate-limiting-v2  label=Protocol
    snippet: rate limit at ingress, not per-handler...
  ```
- `shell` returns a Cypher table (header row + data rows + summary line).

When the format surprises you, surface the raw text to the user with the node_ids you identified. Don't fabricate structure that isn't there.

## Query Discipline

- **Always cite node_ids.** When surfacing a result, include the node_id so the team can trace it back. Never surface mycelium output as fact without attribution.

- **Prefer `ask` for semantic questions.** Use it for "what pattern does this look like", "have we solved this before", "what's the convention". It's semantic search, not keyword matching.

- **Use `shell` for structural navigation.** When you know the exact graph structure, write Cypher. When searching by meaning, use `ask`.

- **Cap Cypher at `LIMIT 50`.** The graph is live and shared. Large queries block other users. The prod target enforces read-only — mutations will be rejected.

- **Never try to write against prod.** The prod target is read-only by design. If the user asks to mutate something, route them to `local` or `dev` on their own machine.

## How to Cite Mycelium Results

When surfacing a mycelium answer to the user, format it like this:

**📍 According to graph (node: `node_id_here`): [1-line summary of what the node says].**

This makes it clear:
1. The answer comes from the team's collective knowledge, not from you
2. The team can click through and verify or drill deeper
3. The statement is traceable and debatable

Example: "📍 According to graph (node: `proto-rate-limiting-v2`): rate limit at the ingress layer, not per-handler, to avoid distributed decision-making overhead."

## Forest Aliases

When discussing team members or creating traces, always use forest aliases. Never use real names.

- Banyan — senior architect
- Sequoia — full-stack lead
- Birch — infrastructure / DevOps
- Cedar — product / strategy
- Oak — security / compliance
- Mycelium — integration / meta-intelligence

## When NOT to Use Mycelium

- **Pure syntax or library questions.** "How do I use the `asyncio` module?" is outside mycelium's scope. Use docs or web search.
- **Public-domain algorithms.** "How do I sort a list?" is not team knowledge. Use your training or docs.
- **Anything unrelated to the team's work.** Don't clutter every response with mycelium calls.
- **When the graph is slow or down.** If a query times out, move on. The graph is live and shared — don't retry aggressive queries.

---

## Examples

### Example 1: Leveraging Prior Decisions

**Scenario:** Teammate is building a new LinkedIn integration and asks "should we use Unipile or our own OAuth flow?"

**Action:**
```bash
mycelium --target prod ask "Unipile vs custom OAuth for LinkedIn"
```

**Result (plain text):** Graph returns a ranked list. Top hit: node `decision-unipile-adoption`, label `Decision`, snippet mentioning rate-limit handling, 2FA, cost tradeoffs. 5 linked TestCases, status "amortized" (47 fires).

**Your response:** "📍 According to graph (node: `decision-unipile-adoption`): the team decided to use Unipile for multi-account management because it handles rate limits, 2FA, and account recovery at scale. 5 test cases cover this, all passing. Sequoia and Banyan owned the call."

---

### Example 2: Finding Naming Conventions

**Scenario:** Teammate wants to add a new invariant check and asks "what should we call it?"

**Action:**
```bash
mycelium --target prod ask "invariant naming convention"
```

**Result:** Top hit: node `convention-invariant-naming`, label `Convention`. Snippet describes PascalCase + capability verb. Links to 53 existing invariants as examples.

**Your response:** "📍 According to graph (node: `convention-invariant-naming`): invariants use PascalCase with a capability verb. Examples: `HealthCheckEnabled`, `CircuitBreakerTriggered`. This reads like a state assertion and matches the 53 existing invariants."

---

### Example 3: Exploring a Company or Concept

**Scenario:** Teammate asks "what do we know about Acme Corp?" before a sales call.

**Action:** Two steps — first semantic search for the entry point, then a neighborhood walk.

```bash
mycelium --target prod ask "Acme Corp"
# assume the top hit is node_id=company-acme-corp
mycelium --target prod shell "MATCH (n {node_id:'company-acme-corp'})-[*1..2]-(m) RETURN DISTINCT m.node_id, labels(m) LIMIT 50"
```

**Result:** The `ask` returns the Company node with funding history and market segment. The `shell` query returns the neighborhood: 4 Opportunity nodes (prior deals + pipeline), 2 Decision nodes (why we passed Q2 2025, why we're re-engaging), 3 SignalSource nodes (recent mentions), 3 team members (Sequoia, Cedar, Birch) who demanded context in the last 2 weeks.

**Your response:** "📍 According to graph (node: `company-acme-corp`): Acme Corp is in B2B data enrichment. We passed on them in Q2 2025 (node: `decision-acme-q2-pass`) because their features overlapped with our pipeline product. Recent signals (Sequoia, Cedar, Birch asked within 2 weeks) suggest their new AI module changes the picture. Here's the current neighborhood: [list nodes]."

---

## How Claude Code Activates This Skill

This skill is registered in Claude Code's skill system. When you start a Claude Code session:

1. Claude Code reads this skill's frontmatter and sees the triggers
2. If your question matches a trigger, the skill loads automatically
3. The skill's body becomes context — you know to reach for the `mycelium` CLI via Bash
4. You don't need to manually invoke the skill

Just ask a question that matches the triggers, and the skill is active for your session.

---

## Architecture

- The `mycelium` CLI is installed globally by `setup-team.sh` (Slice E-A, merged).
- It resolves from any directory on any teammate's machine.
- It connects to the Neo4j graph over Bolt with read-only credentials for `prod`.
- `dev` and `local` targets allow forking and local mutations — only use when explicitly asked.
- No MCP layer. The Bash tool is enough.
