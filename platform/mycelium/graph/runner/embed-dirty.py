#!/usr/bin/env python3
"""
embed-dirty.py — Embed dirty nodes via Ollama nomic-embed-text + write back to Neo4j.

Dirty = leaf_hash IS NOT NULL AND (embedding IS NULL OR embedding_for_leaf_hash != leaf_hash).
Idempotent. Batched at 100 nodes per transaction.

--qdrant-mirror: Also upsert embeddings to Qdrant "mycelium-embeddings" collection.
"""
import sys
import time
import requests
import argparse
import hashlib
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "localtest12"
OLLAMA_URL = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"
BATCH_SIZE = 100

QDRANT_HOST = "143.110.226.214"
QDRANT_PORT = 6333
QDRANT_COLLECTION = "mycelium-embeddings"

DIRTY_QUERY = """
// Fractal embedding policy (2026-04-18):
// Only embed semantic heads. Derived nodes (CodeCypher atoms, TestCases,
// ConversationTraces, ...) resolve via a one-hop :EMBEDS_VIA traversal.
// This cut the dirty set from ~8600 to ~900 on the first pass.
// A node qualifies if is_semantic_head=true OR it has no :EMBEDS_VIA parent
// to borrow from.
MATCH (n)
WHERE n.node_id IS NOT NULL
  AND NOT n:QueryTrace
  AND n.leaf_hash IS NOT NULL
  AND (
    n.embedding IS NULL
    OR n.embedding_for_leaf_hash IS NULL
    OR n.embedding_for_leaf_hash <> n.leaf_hash
  )
  AND coalesce(n.is_semantic_head, false) = true
RETURN elementId(n) AS element_id,
       n.node_id AS node_id,
       labels(n)[0] AS node_label,
       n.label AS name,
       n.description AS description,
       n.leaf_hash AS leaf_hash
ORDER BY elementId(n)
"""

# IMPORTANT: match by elementId, not node_id. Some legacy nodes share a
# node_id across multiple labels (Protocol, ProtocolCycle, RhythmState),
# so matching by node_id would overwrite all of them with the same
# embedding_for_leaf_hash, leaving the non-last ones perpetually "dirty".
WRITE_QUERY = """
UNWIND $rows AS row
MATCH (n) WHERE elementId(n) = row.element_id
SET n.embedding = row.embedding,
    n.embedding_for_leaf_hash = row.leaf_hash,
    n.embedding_model = $model,
    n:GraphNode
"""


def element_id_to_point_id(element_id_str):
    """Convert Neo4j elementId string to a consistent uint64 for Qdrant."""
    hash_bytes = hashlib.sha256(element_id_str.encode()).digest()
    point_id = int.from_bytes(hash_bytes[:8], byteorder='big') & 0xFFFFFFFFFFFFFFFF
    return point_id


def serialize(node_label, name, description, node_id):
    parts = [
        node_label or "",
        name or "",
        description or "",
        node_id or "",
    ]
    return " ".join(p for p in parts if p)


def embed(text):
    resp = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": text}, timeout=60)
    resp.raise_for_status()
    return resp.json()["embedding"]


def main():
    parser = argparse.ArgumentParser(description="Embed dirty nodes and optionally mirror to Qdrant")
    parser.add_argument("--qdrant-mirror", action="store_true",
                       help="Also upsert embeddings to Qdrant 'mycelium-embeddings' collection")
    args = parser.parse_args()

    # Initialize Qdrant if mirroring
    qdrant = None
    if args.qdrant_mirror:
        try:
            qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT,
                                 api_key=None, prefer_grpc=False)
            qdrant.get_collections()  # test connection
            print(f"Qdrant mirror enabled: {QDRANT_HOST}:{QDRANT_PORT}\n")
        except Exception as e:
            print(f"Warning: Qdrant connection failed, mirroring disabled: {e}\n")
            qdrant = None

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    start = time.time()

    with driver.session() as session:
        result = session.run(DIRTY_QUERY)
        dirty = [dict(r) for r in result]

    total = len(dirty)
    if total == 0:
        print("All nodes up to date. Nothing to embed.")
        driver.close()
        return

    print(f"Dirty nodes: {total}. Embedding in batches of {BATCH_SIZE}...")
    embedded = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = dirty[batch_start: batch_start + BATCH_SIZE]
        rows = []
        qdrant_points = []

        for node in batch:
            text = serialize(
                node["node_label"],
                node["name"],
                node["description"],
                node["node_id"],
            )
            vec = embed(text)
            rows.append({"element_id": node["element_id"], "embedding": vec, "leaf_hash": node["leaf_hash"]})

            # Prepare for Qdrant if mirroring
            if qdrant:
                point_id = element_id_to_point_id(node["element_id"])
                point = PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "node_id": node["node_id"],
                        "label": node["node_label"],
                        "fractal_scale": node.get("fractal_scale"),
                        "leaf_hash": node["leaf_hash"],
                    }
                )
                qdrant_points.append(point)

        # Write to Neo4j
        with driver.session() as session:
            session.run(WRITE_QUERY, rows=rows, model=MODEL)

        # Write to Qdrant if mirroring
        if qdrant and qdrant_points:
            try:
                qdrant.upsert(
                    collection_name=QDRANT_COLLECTION,
                    points=qdrant_points
                )
            except Exception as e:
                print(f"  ⚠ Qdrant upsert failed: {e}")

        embedded += len(batch)
        elapsed = time.time() - start
        rate = embedded / elapsed if elapsed > 0 else 0
        print(f"  {embedded}/{total} embedded  ({rate:.1f} nodes/s)  "
              f"elapsed={elapsed:.0f}s")

    total_elapsed = time.time() - start
    avg = total_elapsed / total if total > 0 else 0
    print(f"\nDone. {embedded} nodes embedded in {total_elapsed:.1f}s "
          f"(avg {avg:.2f}s/node).")
    driver.close()


if __name__ == "__main__":
    main()
