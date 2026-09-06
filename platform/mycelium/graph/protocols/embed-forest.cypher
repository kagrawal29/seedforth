// @node_id: protocol-embed-forest
// @label: "Embed every unembedded node in the forest — fractal-coherent essence recipe"
// @kind: protocol
// @fsd_layer: features
//
// Purpose: surface the forest's semantic topology. One recipe applied to every
// node regardless of label or scope:
//
//   essence(n) = label + " | " + (description|rationale|summary|content_head|name|path)
//              + " | scope=" + project
//              + " | role=" + kind_or_role
//
// The structural position of the node rides through graph edges, not the text.
// This keeps the fractal honest: every node embeds itself the same way.
//
// Storage: Qdrant collection `mycelium-embeddings` with metadata
// {project, label, node_id}. Vector = 768d nomic-embed-text (local Ollama).
//
// This Cypher yields (node_id, essence_text) rows. The Python runner
// (scripts/embed-forest.py) iterates, embeds in batches of 64, writes to Qdrant,
// and sets n.embedded_at = datetime() on the Neo4j node so we can resume.
// ============================================================================

MATCH (n)
WHERE n.project IS NOT NULL
  AND n.embedded_at IS NULL
WITH n,
     labels(n)[0] AS lbl,
     coalesce(
       n.description,
       n.rationale,
       n.summary,
       n.narrative,
       n.label,
       n.name,
       n.path,
       n.content,
       ''
     ) AS body,
     coalesce(n.kind, n.role_in_forest, n.fsd_layer, '') AS role
WITH coalesce(
       n.node_id,
       labels(n)[0] + '-' + n.project + '-' + coalesce(n.sha, n.path, n.name, elementId(n))
     ) AS node_id,
     n.project AS scope,
     lbl,
     lbl + ' | ' +
     substring(body, 0, 400) + ' | scope=' + coalesce(n.project,'?') +
     CASE WHEN role <> '' THEN ' | role=' + role ELSE '' END AS essence
WHERE node_id IS NOT NULL
RETURN node_id, scope, lbl, essence
ORDER BY scope, lbl;
