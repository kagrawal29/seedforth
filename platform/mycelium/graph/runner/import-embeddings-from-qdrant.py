#!/usr/bin/env python3
"""
import-embeddings-from-qdrant.py — Import embeddings from Qdrant back to Neo4j.

Reads all points from Qdrant "mycelium-embeddings" collection and writes
embeddings back to Neo4j node properties. Use this when reloading the graph
from a lean export (without embedding arrays).

Matches on node_id and reconstructs:
  - n.embedding (768-float vector)
  - n.embedding_for_leaf_hash (the leaf_hash this was embedded for)
  - n.embedding_model = "nomic-embed-text"

Idempotent — safe to run multiple times. Skips nodes that don't exist in Neo4j.
"""
import sys
import time
import hashlib
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "localtest12"

QDRANT_HOST = "143.110.226.214"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "mycelium-embeddings"

BATCH_SIZE = 500


def get_qdrant_embeddings(client):
    """Fetch all points from Qdrant collection.

    Returns list of dicts:
    {
        "point_id": <int>,
        "node_id": <str>,
        "embedding": [<float>, ...],
        "leaf_hash": <str or None>
    }
    """
    print(f"Fetching embeddings from Qdrant collection '{QDRANT_COLLECTION}'...")

    try:
        collection_info = client.get_collection(QDRANT_COLLECTION)
        total_points = collection_info.points_count
        print(f"  Total points: {total_points}")
    except Exception as e:
        print(f"✗ Failed to get collection info: {e}")
        return []

    # Scroll through all points
    points = []
    offset = 0
    limit = 1000

    while True:
        try:
            batch, next_offset = client.scroll(
                collection_name=QDRANT_COLLECTION,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )

            if not batch:
                break

            for point in batch:
                payload = point.payload or {}
                points.append({
                    "point_id": point.id,
                    "node_id": payload.get("node_id"),
                    "embedding": point.vector,
                    "leaf_hash": payload.get("leaf_hash"),
                })

            if next_offset is None:
                break

            offset = next_offset

        except Exception as e:
            print(f"✗ Scroll failed at offset {offset}: {e}")
            break

    print(f"✓ Fetched {len(points)} embeddings from Qdrant")
    return points


def write_to_neo4j(nodes):
    """Write embeddings back to Neo4j by node_id.

    Uses MERGE to match nodes that may have changed labels or structure.
    """
    if not nodes:
        print("No embeddings to import.")
        return 0

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    total = len(nodes)
    written = 0
    skipped = 0
    start = time.time()

    print(f"\nWriting {total} embeddings to Neo4j...")

    # Query to match nodes by node_id and write embedding
    write_query = """
    UNWIND $rows AS row
    MATCH (n) WHERE n.node_id = row.node_id
    SET n.embedding = row.embedding,
        n.embedding_for_leaf_hash = row.leaf_hash,
        n.embedding_model = "nomic-embed-text",
        n:GraphNode
    RETURN COUNT(n) AS matched
    """

    for batch_start in range(0, total, BATCH_SIZE):
        batch = nodes[batch_start:batch_start + BATCH_SIZE]

        # Filter out rows with missing node_id
        valid_rows = [r for r in batch if r["node_id"]]
        skipped += len(batch) - len(valid_rows)

        if not valid_rows:
            continue

        try:
            with driver.session() as session:
                result = session.run(write_query, rows=valid_rows)
                matched = result.single()["matched"]
                written += matched

        except Exception as e:
            print(f"✗ Batch write failed: {e}")
            continue

        elapsed = time.time() - start
        rate = written / elapsed if elapsed > 0 else 0
        print(f"  {written}/{total} written  ({rate:.1f} nodes/s)  skipped={skipped}")

    driver.close()

    total_elapsed = time.time() - start
    print(f"\n✓ Done. {written} embeddings imported in {total_elapsed:.1f}s "
          f"(skipped {skipped} with missing node_id)")

    return written


def main():
    print("=== Import Qdrant embeddings to Neo4j ===\n")

    # Connect to Qdrant
    try:
        qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT,
                               api_key=None, prefer_grpc=False)
        qdrant.get_collections()  # test connection
    except Exception as e:
        print(f"✗ Qdrant connection failed: {e}")
        sys.exit(1)

    # Check collection exists
    try:
        qdrant.get_collection(QDRANT_COLLECTION)
    except Exception as e:
        print(f"✗ Collection '{QDRANT_COLLECTION}' not found: {e}")
        sys.exit(1)

    # Fetch from Qdrant
    nodes = get_qdrant_embeddings(qdrant)

    # Write to Neo4j
    written = write_to_neo4j(nodes)

    # Verify
    print("\nVerifying...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        with driver.session() as session:
            result = session.run("MATCH (n) WHERE n.embedding IS NOT NULL RETURN COUNT(n) as count")
            count = result.single()["count"]
            print(f"✓ Neo4j now has {count} nodes with embeddings")
        driver.close()
    except Exception as e:
        print(f"⚠ Verification failed: {e}")


if __name__ == "__main__":
    main()
