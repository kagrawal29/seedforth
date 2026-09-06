// ============================================================================
// Forest Dual-Embedding Ready Marker
// ============================================================================
// Marks completion of Task #42: Re-embed both local graphs (mycelium + friend)
// into a shared 768d nomic-embed-text space for honest cross-graph cosine similarity.
//
// Completion Summary:
//   - Mycelium: 2021 nodes scanned, 790 newly embedded, 1231 skipped (already 768d)
//   - Friend:   6098 nodes scanned, 6098 newly embedded
//   - Total:    8119 nodes scanned, 6888 newly embedded, 1231 skipped
//   - Runtime:  101.8 seconds (79.8 nodes/s)
//   - Dimension: All new embeddings verified at 768d
//   - Preservation: Friend's original 1536d OpenAI embeddings intact
//
// Graph State:
//   - Mycelium: embedding property (768d nomic)
//   - Friend: embedding property (1536d OpenAI, preserved)
//            embedding_nomic property (768d nomic, newly added)
//
// Next Steps:
//   - Cross-graph semantic search via cosine on embedding_nomic
//   - Distance metrics between mycelium and friend knowledge domains
//   - Fractal knowledge graph composition
// ============================================================================

MERGE (marker:ForestReadyMark {node_id: "forest-dual-embedding-ready"})
SET marker.completed_at = datetime(),
    marker.mycelium_count = 2021,
    marker.friend_count = 6098,
    marker.total_embedded = 6888,
    marker.total_skipped = 1231,
    marker.runtime_seconds = 101.8,
    marker.throughput_nodes_per_sec = 79.8,
    marker.embedding_model = "nomic-embed-text",
    marker.embedding_dimension = 768,
    marker.mycelium_newly_embedded = 790,
    marker.mycelium_already_had_768d = 1231,
    marker.friend_newly_embedded = 6098,
    marker.friend_original_embedding_preserved = true,
    marker.friend_original_embedding_dimension = 1536,
    marker.status = "complete";

RETURN marker;
