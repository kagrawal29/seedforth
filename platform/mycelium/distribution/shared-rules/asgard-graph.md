# Asgard Graph

You have a nervous system. It's called Asgard Graph.

It holds what 21 people have collectively decided, questioned, struggled with, and left unfinished — as structure. Not a database you look things up in. A topology you think through.

## The Tools

You have 7 MCP tools for interacting with the live graph:

| Tool | What it does |
|---|---|
| `asgard_graph_schema` | The shape of the graph — node types, edge types, communities, example Cypher. Start here. |
| `asgard_graph_query` | Execute Cypher directly. Structural analysis, path finding, topology. |
| `asgard_graph_ask` | Natural language question — finds matching nodes, connections, demand. |
| `asgard_graph_demand` | What the team is actively asking about. Cross-person convergence. |
| `asgard_graph_neighborhood` | What connects to a specific node. Follow edges. See what's adjacent. |
| `asgard_graph_bridges` | Where one community touches another. Structural gaps. Coordination opportunities. |
| `asgard_graph_trace` | Tell the graph what was asked and by whom (use forest aliases, never real names). |

If Asgard Graph MCP tools are not available (server down, not configured), fall back to the flat knowledge base at `.claude/knowledge/` — read `community-map.md` for community structure, `index.md` for the entry catalog, and `search-index.md` for keyword lookup. These files are a snapshot of the graph, not the live graph itself.

## How to Use It

### Think through the graph, not at it

When you encounter a concept — a technology, a decision, an architectural pattern — don't just check if the graph has an answer. Think about where that concept sits in the topology. What community does it belong to? What bridges connect it to other communities? Who else's work touches this neighborhood?

### Dream with it

The graph rewards exploration. Run `asgard_graph_schema` to see the shape. Pick a community and follow its bridges with `asgard_graph_bridges`. Walk the neighborhood of a node with `asgard_graph_neighborhood` and see where the edges take you. Look for things you didn't expect.

Three dream patterns that produce insight:

- **Distant path**: pick two concepts that seem unrelated. Query the path between them. The intermediate nodes are the hidden dependencies.
- **Cold zones**: find communities with no demand signals. That's either knowledge that's settled (good) or knowledge the team has forgotten exists (surface it).
- **Convergence**: check `asgard_graph_demand` for cross-person connections. When multiple people's questions point at the same gap, that's the highest-value signal in the system.

### Let the work be the coupling

Don't treat graph queries as a separate step from your work. When you're researching a technology, check what decisions already exist — that's a graph query. When you're debugging, wonder if anyone else hit this — that's a demand check. When you discover something, record it — that's a trace.

Specific patterns the team has validated:

- **"Should we use X?"** — check for settled decisions first. 40+ decisions exist. Don't recommend what was already rejected. Don't re-research what was already evaluated.
- **"How does X work in our system?"** — X connects to other things. Find X's community and follow the bridges to adjacent communities. The connections are what the person doesn't know about.
- **When someone is stuck or frustrated** — high frustration usually means they're solving something in isolation that connects to someone else's work. Check cross-person demand.
- **When making changes that touch a settled decision** — follow the rationale edge. "On-prem enterprise constraint drives OSS stack" is not a preference — it's a business requirement. Surface the rationale, don't silently override.

### Leave traces

Every query you make is a signal. When you ask the graph something meaningful, use `asgard_graph_trace` to record it. This is how the graph learns what matters. Use forest aliases (Banyan, Sequoia, Birch, Cedar, Oak, Mycelium), never real names.

### Surface what surprises you

When a graph query returns something unexpected — a connection you didn't anticipate, a gap where you expected fullness, two people's work converging on the same problem without knowing — mention it. Don't wait to be asked. The graph's surprises are emergence happening in real time.

## When Not to Query

- Simple coding tasks unrelated to architecture or decisions
- If the tools return errors — the graph is down, fall back to `.claude/knowledge/` flat files
- If the answer is clearly in a local file you can read directly

The graph is a resource, not a requirement. But like any nervous system — the more you use it, the more useful it becomes.
