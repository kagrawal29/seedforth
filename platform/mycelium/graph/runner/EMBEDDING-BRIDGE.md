# Embedding Bridge for Cypher Atoms

Cypher atoms can now natively call embeddings and semantic search during execution. This enables embedding-powered atoms to compound into semantic reasoning chains.

## How It Works

Three shell helpers form the bridge:

1. **embed-text.sh** - Takes arbitrary text, returns 768-dim embedding vector
2. **qdrant-search.sh** - Embeds text, queries Qdrant for nearest node_ids
3. **embed-node.sh** - Reads a node from Neo4j, embeds its properties, writes back

These can be called **from within cypher atoms** or from shell workflows.

## Usage Patterns

### Pattern 1: Embed Query Output (In-Atom)

A cypher atom can emit text that gets embedded mid-execution:

```cypher
MATCH (concept:Concept) 
RETURN concept.label + ': ' + concept.description AS text_to_embed, concept.node_id
```

Then from the shell runner:
```bash
# Capture the atom's output
output=$(./mycelium shell "...")

# Embed each line
while IFS= read -r line; do
  embedding=$(echo "$line" | bash graph/runner/embed-text.sh)
  # Do something with embedding
done <<< "$output"
```

### Pattern 2: Semantic Search Inside Atom Chain

A cypher atom can use semantic search results:

```cypher
WITH "healing protocol" AS query
CALL apoc.load.json("file:///tmp/search-results.json") YIELD value AS result
MATCH (n {node_id: result.node_id})
RETURN n, result.score AS relevance
```

Pre-populate the search results:
```bash
bash graph/runner/qdrant-search.sh "healing protocol" 10 > /tmp/search-results.json
atom-run.sh protocol-name
```

### Pattern 3: Embed Nodes Batch

Embed all nodes matching a label:

```bash
./mycelium shell "MATCH (n:Concept) RETURN n.node_id" \
  | tail -n +2 \
  | while read node_id; do
      bash graph/runner/embed-node.sh "$node_id"
    done
```

### Pattern 4: Atoms with `requires_embedding` Flag

An atom can declare that its output should be embedded:

```cypher
MATCH (p:Protocol) 
WHERE p.requires_embedding = true
RETURN p.node_id, p.description AS text
```

Then in atom-run.sh, check for this flag and auto-embed outputs.

## Extension to atom-run.sh

The current atom-run.sh can be extended to support embedding-aware atoms. Here's the modification strategy:

### Before concatenating atoms (around line 72):

Check if any atom has `requires_embedding = true`:

```bash
# Check if any atoms require embedding post-processing
EMBEDDING_ATOMS=$(cypher_exec <<CYPHER
MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'}) 
WHERE a.requires_embedding = true 
RETURN a.atom_order
CYPHER
)
if [ -n "$EMBEDDING_ATOMS" ]; then
  echo "[atom-run] embedding bridge active for protocol $PROTOCOL_ID"
  NEEDS_EMBED="yes"
else
  NEEDS_EMBED="no"
fi
```

### After executing atoms (around line 135):

If embeddings were needed, process the output:

```bash
if [ "$NEEDS_EMBED" = "yes" ]; then
  echo "[atom-run] post-processing embeddings..."
  grep -v "^$" /tmp/atom-run.out | while read -r line; do
    if [ -n "$line" ]; then
      embedding=$(bash graph/runner/embed-text.sh "$line" 2>/dev/null)
      if [ -n "$embedding" ]; then
        echo "embedded:$line -> ${embedding:0:20}..."
      fi
    fi
  done
fi
```

## Qdrant Collection Schema

The mycelium-embeddings collection should have this schema:

```json
{
  "name": "mycelium-embeddings",
  "vectors": {
    "size": 768,
    "distance": "Cosine"
  },
  "payload_schema": {
    "node_id": {"type": "keyword"},
    "label": {"type": "text"},
    "fractal_scale": {"type": "integer"},
    "node_type": {"type": "keyword"},
    "last_embedded": {"type": "integer"}
  }
}
```

Points are indexed by their embedding vector; search returns payloads with `node_id`, `label`, `fractal_scale`, etc.

## Implementation Checklist

- [x] embed-text.sh -- Ollama call, return CSV floats
- [x] qdrant-search.sh -- semantic search, return node_ids + scores
- [x] embed-node.sh -- read node from Neo4j, embed, write back
- [ ] Extend atom-run.sh to support requires_embedding flag
- [ ] Create Qdrant collection: mycelium-embeddings
- [ ] Register capabilities in graph (Capability nodes)
- [ ] Test: embed a concept, search for it, return related nodes

## Limitations

1. **Ollama must be running** at http://localhost:11434 (or $OLLAMA_URL)
2. **Qdrant must be accessible** at $QDRANT_URL (default: http://143.110.226.214:6333)
3. **Embedding latency** -- each embed call takes 100-500ms depending on text length
4. **Neo4j embedding storage** -- embedding property (768 floats = ~3KB) may impact query performance if applied to thousands of nodes
5. **Qdrant sync** -- embeddings in Neo4j and Qdrant must be kept in sync manually (no automatic replication)

## Next Steps

1. Test each script independently
2. Create Qdrant collection via API
3. Extend atom-run.sh with requires_embedding support
4. Create test atoms that use embeddings
5. Document usage patterns in skill or CLAUDE.md
