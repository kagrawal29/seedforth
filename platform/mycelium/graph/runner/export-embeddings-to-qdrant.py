#!/usr/bin/env python3
"""
export-embeddings-to-qdrant.py — Export Neo4j embeddings to Qdrant collection.

Reads all nodes with embeddings from Neo4j and upserts them into Qdrant
"mycelium-embeddings" collection. Each point has:
  - id: node_id (uint64 from Neo4j elementId)
  - vector: 768-float embedding
  - payload: {fractal_scale, label, leaf_hash}

Creates collection if it doesn't exist. Idempotent — safe to run multiple times.
"""
import sys
import time
import hashlib
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "localtest12"

QDRANT_HOST = "143.110.226.214"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "mycelium-embeddings"

VECTOR_SIZE = 768
BATCH_SIZE = 500


def element_id_to_point_id(element_id_str):
    """Convert Neo4j elementId string to a consistent uint64 for Qdrant.

    elementId format: "<partition>:<uuid>:<index>"
    Hash to uint64 to avoid collisions.
    """
    hash_bytes = hashlib.sha256(element_id_str.encode()).digest()
    # Take first 8 bytes and convert to unsigned 64-bit int
    point_id = int.from_bytes(hash_bytes[:8], byteorder='big') & 0xFFFFFFFFFFFFFFFF
    return point_id


def get_neo4j_embeddings():
    """Fetch all nodes with embeddings from Neo4j.

    Returns list of dicts:
    {
        "element_id": <int>,
        "node_id": <str>,
        "label": <str>,
        "fractal_scale": <int or None>,
        "leaf_hash": <str or None>,
        "embedding": [<float>, ...]
    }
    """
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    query = """
    MATCH (n)
    WHERE n.embedding IS NOT NULL
    RETURN elementId(n) AS element_id,
           n.node_id AS node_id,
           labels(n)[0] AS label,
           n.fractal_scale AS fractal_scale,
           n.leaf_hash AS leaf_hash,
           n.embedding AS embedding
    ORDER BY elementId(n)
    """

    with driver.session() as session:
        result = session.run(query)
        nodes = [dict(record) for record in result]

    driver.close()
    return nodes


def ensure_qdrant_collection(client):
    """Create collection if it doesn't exist."""
    try:
        client.get_collection(QDRANT_COLLECTION)
        print(f"Collection '{QDRANT_COLLECTION}' already exists.")
        return
    except:
        pass

    print(f"Creating collection '{QDRANT_COLLECTION}'...")
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
    )
    print(f"✓ Collection created")


def upsert_to_qdrant(client, nodes):
    """Upsert nodes to Qdrant in batches."""
    total = len(nodes)
    if total == 0:
        print("No embeddings to export.")
        return 0

    print(f"Upserting {total} embeddings to Qdrant...")
    upserted = 0
    start = time.time()

    for batch_start in range(0, total, BATCH_SIZE):
        batch = nodes[batch_start:batch_start + BATCH_SIZE]
        points = []

        for node in batch:
            # Use elementId (from Neo4j) as Qdrant point ID
            # Hash the string format to get a consistent uint64
            point_id = element_id_to_point_id(node["element_id"])

            point = PointStruct(
                id=point_id,
                vector=node["embedding"],
                payload={
                    "node_id": node["node_id"],
                    "label": node["label"],
                    "fractal_scale": node.get("fractal_scale"),
                    "leaf_hash": node.get("leaf_hash"),
                }
            )
            points.append(point)

        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=points
        )

        upserted += len(batch)
        elapsed = time.time() - start
        rate = upserted / elapsed if elapsed > 0 else 0
        print(f"  {upserted}/{total} upserted  ({rate:.1f} nodes/s)")

    total_elapsed = time.time() - start
    avg = total_elapsed / total if total > 0 else 0
    print(f"\n✓ Done. {upserted} embeddings exported in {total_elapsed:.1f}s "
          f"(avg {avg:.3f}s/node)")

    return upserted


def main():
    print("=== Export Neo4j embeddings to Qdrant ===\n")

    # Connect to Qdrant
    try:
        qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT,
                               api_key=None, prefer_grpc=False)
        qdrant.get_collections()  # test connection
    except Exception as e:
        print(f"✗ Qdrant connection failed: {e}")
        sys.exit(1)

    # Ensure collection exists
    ensure_qdrant_collection(qdrant)

    # Fetch embeddings from Neo4j
    print("\nFetching embeddings from Neo4j...")
    try:
        nodes = get_neo4j_embeddings()
        print(f"✓ Fetched {len(nodes)} nodes with embeddings")
    except Exception as e:
        print(f"✗ Neo4j fetch failed: {e}")
        sys.exit(1)

    # Upsert to Qdrant
    print()
    upsert_to_qdrant(qdrant, nodes)

    # Verify
    print("\nVerifying...")
    try:
        collection_info = qdrant.get_collection(QDRANT_COLLECTION)
        print(f"✓ Qdrant collection stats:")
        print(f"  - Points: {collection_info.points_count}")
        print(f"  - Vector size: {collection_info.config.params.vectors.size}")
    except Exception as e:
        print(f"⚠ Verification failed: {e}")


if __name__ == "__main__":
    main()
