#!/usr/bin/env python3
"""
canonical-tip.py — Resolve THE canonical species deterministically.

Pure Cypher protocol. Same answer on every instance. No coordination.

Tie-break order:
  1. Most witness signatures
  2. Deepest lineage from genesis
  3. Most recent crystallized_at
  4. Lex-smallest sealed_dna (final deterministic tiebreak)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import query

CANONICAL_TIP_CYPHER = """
MATCH (sp:Species)
WHERE (sp.signature_count IS NOT NULL AND sp.signature_count >= coalesce(sp.quorum_required, 1))
   OR sp.status = 'canonical'
   OR (sp.signed = true)
   OR sp.genesis = true
OPTIONAL MATCH path = (sp)-[:DESCENDED_FROM*0..]->(g:Species {genesis: true})
WITH sp, length(path) AS depth
RETURN sp.sealed_dna AS dna,
       sp.git_branch AS branch,
       coalesce(sp.signature_count, 0) AS sigs,
       depth,
       coalesce(sp.crystallized_at, '') AS ts
ORDER BY sigs DESC, depth DESC, ts DESC, dna ASC
LIMIT 1
"""


def resolve_canonical():
    """Return (dna, branch, sigs, depth) of the canonical tip, or None if no species."""
    r = query(CANONICAL_TIP_CYPHER)
    if not r:
        return None
    return {
        "dna": r[0][0],
        "branch": r[0][1],
        "sigs": r[0][2],
        "depth": r[0][3],
        "ts": r[0][4],
    }


def update_pointer(tip):
    """Update the CanonicalPointer node so other consumers can read the cached value."""
    if not tip:
        return
    query(f"""
    MERGE (p:CanonicalPointer {{node_id: 'canonical-tip'}})
    SET p.species_dna = '{tip["dna"]}',
        p.species_branch = '{tip["branch"]}',
        p.signature_count = {tip["sigs"]},
        p.lineage_depth = {tip["depth"]},
        p.last_updated = timestamp()
    """)


def main():
    tip = resolve_canonical()
    if not tip:
        print("(no species found)", file=sys.stderr)
        sys.exit(1)

    if "--quiet" in sys.argv:
        print(tip["dna"])
        return

    if "--update-pointer" in sys.argv:
        update_pointer(tip)

    print(f"canonical: {tip['dna']}")
    print(f"  branch:    {tip['branch']}")
    print(f"  signatures:{tip['sigs']}")
    print(f"  depth:     {tip['depth']}")
    print(f"  ts:        {tip['ts']}")


if __name__ == "__main__":
    main()
