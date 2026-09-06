#!/usr/bin/env python3
"""Embed every unembedded node in the local forest.

Usage:
    python3 scripts/embed-forest.py [--batch 64] [--limit N] [--scope X]

Pulls (node_id, scope, label, essence) rows from Neo4j via the embed-forest
protocol, embeds each batch through local Ollama (nomic-embed-text, 768d),
writes to Qdrant collection `mycelium-embeddings` with metadata filter
{project, label, node_id}, and marks the Neo4j node with `embedded_at`.

Idempotent: run repeatedly to resume. Skips already-embedded nodes.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Iterable

import requests
from neo4j import GraphDatabase

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://143.110.226.214:6333")
COLLECTION = os.environ.get("QDRANT_COLLECTION", "mycelium-embeddings")
NEO4J_BOLT = os.environ.get("NEO4J_BOLT", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")
# Resume by querying Qdrant for already-stored node_ids (no Neo4j writes needed
# against read-only targets like dev).
MARK_NEO4J = os.environ.get("MARK_NEO4J", "1") == "1"
MODEL = "nomic-embed-text"
VECTOR_DIM = 768

PROTOCOL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "graph", "protocols", "embed-forest.cypher"
)


def load_protocol_cypher() -> str:
    with open(PROTOCOL_PATH) as f:
        src = f.read()
    return "\n".join(line for line in src.splitlines() if not line.startswith("//"))


def ensure_collection() -> None:
    r = requests.get(f"{QDRANT_URL}/collections/{COLLECTION}")
    if r.status_code == 200:
        return
    body = {"vectors": {"size": VECTOR_DIM, "distance": "Cosine"}}
    r = requests.put(f"{QDRANT_URL}/collections/{COLLECTION}", json=body)
    r.raise_for_status()


def _embed_one(t: str) -> list[float]:
    r = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": MODEL, "prompt": t},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["embedding"]


def embed_batch(texts: list[str], workers: int = 8) -> list[list[float]]:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(_embed_one, texts))


def qdrant_upsert(points: list[dict]) -> None:
    r = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points?wait=true",
        json={"points": points},
        timeout=60,
    )
    r.raise_for_status()


def mark_embedded(session, node_ids: list[str]) -> None:
    session.run(
        "UNWIND $ids AS id MATCH (n {node_id: id}) SET n.embedded_at = datetime()",
        ids=node_ids,
    )


def rows_to_embed(session, scope: str | None, limit: int | None) -> Iterable[dict]:
    cypher = load_protocol_cypher()
    if scope:
        cypher = cypher.replace(
            "WHERE n.project IS NOT NULL",
            f"WHERE n.project = '{scope}'",
        )
    if not MARK_NEO4J:
        # Read-only dev target: can't write embedded_at. Drop that predicate.
        cypher = cypher.replace("AND n.embedded_at IS NULL", "")
    if limit:
        cypher = cypher.rstrip().rstrip(";") + f"\nLIMIT {limit};"
    result = session.run(cypher)
    for r in result:
        yield {
            "node_id": r["node_id"],
            "scope": r["scope"],
            "label": r["lbl"],
            "essence": r["essence"],
        }


def stable_point_id(node_id: str) -> int:
    # Qdrant wants uint64 or UUID. Use hash(node_id) truncated.
    import hashlib

    h = hashlib.sha256(node_id.encode()).digest()
    return int.from_bytes(h[:8], "big") & ((1 << 63) - 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--scope", type=str, default=None, help="restrict to project scope")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    ensure_collection()
    driver = GraphDatabase.driver(NEO4J_BOLT, auth=(NEO4J_USER, NEO4J_PASS))

    total = 0
    t0 = time.time()
    with driver.session() as session:
        rows = list(rows_to_embed(session, args.scope, args.limit))
        print(f"[embed-forest] {len(rows)} unembedded nodes")
        if args.dry_run:
            for r in rows[:5]:
                print(f"  {r['node_id']}  [{r['label']}@{r['scope']}]  {r['essence'][:120]}")
            return 0

        for i in range(0, len(rows), args.batch):
            chunk = rows[i : i + args.batch]
            texts = [r["essence"] for r in chunk]
            try:
                vecs = embed_batch(texts)
            except Exception as e:
                print(f"[embed-forest] batch {i} failed: {e}", file=sys.stderr)
                continue

            points = [
                {
                    "id": stable_point_id(r["node_id"]),
                    "vector": v,
                    "payload": {
                        "node_id": r["node_id"],
                        "project": r["scope"],
                        "label": r["label"],
                    },
                }
                for r, v in zip(chunk, vecs)
            ]
            qdrant_upsert(points)
            if MARK_NEO4J:
                mark_embedded(session, [r["node_id"] for r in chunk])
            total += len(chunk)
            if total % 500 == 0 or total == len(rows):
                dt = time.time() - t0
                print(
                    f"[embed-forest] {total}/{len(rows)} embedded "
                    f"({total/dt:.1f}/s, {dt:.0f}s elapsed)"
                )

    driver.close()
    print(f"[embed-forest] done: {total} nodes embedded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
