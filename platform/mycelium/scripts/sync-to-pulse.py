#!/usr/bin/env python3
"""
Sync graph to pulse server — Redis DUMP/RESTORE.

Exact binary copy. No node-by-node Cypher. No inflation.
Preserves all structure, all properties, all edges.

Usage: python3 scripts/sync-to-pulse.py
"""

import os
import sys

PULSE_HOST = os.environ.get("PULSE_HOST", "5.78.206.137")
PULSE_PORT = int(os.environ.get("PULSE_PORT", "6380"))
LOCAL_HOST = os.environ.get("FALKORDB_HOST", "localhost")
LOCAL_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def main():
    import redis

    src = redis.Redis(host=LOCAL_HOST, port=LOCAL_PORT)
    dst = redis.Redis(host=PULSE_HOST, port=PULSE_PORT)

    keys = src.keys("*")
    print(f"[sync-to-pulse] Keys to copy: {[k.decode() for k in keys]}")

    for key in keys:
        name = key.decode()
        try:
            ttl = src.pttl(key)
            if ttl < 0:
                ttl = 0
            dump = src.dump(key)
            if dump:
                dst.delete(key)
                dst.restore(key, ttl, dump, replace=True)
                print(f"  Copied: {name} ({len(dump)} bytes)")
        except Exception as e:
            print(f"  Failed: {name}: {e}")

    # Verify
    from falkordb import FalkorDB
    db = FalkorDB(host=PULSE_HOST, port=PULSE_PORT)
    g = db.select_graph("asgard")
    r = g.query("MATCH (n) RETURN count(n)")
    e = g.query("MATCH ()-[r]->() RETURN count(r)")
    print(f"[sync-to-pulse] Pulse server: {r.result_set[0][0]} nodes, {e.result_set[0][0]} edges")


if __name__ == "__main__":
    main()
