#!/usr/bin/env python3
"""
status.py — Show the current state of your living graph.

Output:
  You:               <wallet alias> (<pubkey prefix>)
  Local graph:       N nodes, M edges, dna XXXX
  Canonical:         species/XXXX  (you are at | ahead | behind)
  Local divergence:  +N nodes since canonical
  Breathing:         X.X Hz, last breath Yms ago
  Crystals:          P/T passing
  Witnesses:         N active, quorum X/X alive
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from graph import query


def load_wallet():
    p = Path.home() / ".asgard-wallet"
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def main():
    print("══ Mycelium status ══")

    # ── You ──
    wallet = load_wallet()
    if wallet:
        alias = wallet.get("alias", "?")
        pk = wallet.get("hash") or wallet.get("public_key", "")
        print(f"You:               {alias} ({pk[:16]}…)")
    else:
        print("You:               (no wallet — run mycelium init)")

    # ── Local graph ──
    try:
        nodes = query("MATCH (n) RETURN count(n)")[0][0]
        edges = query("MATCH ()-[r]->() RETURN count(r)")[0][0]
        being = query("MATCH (b:Being) RETURN b.dna_hash, b.current_species, b.last_heartbeat, b.heartbeat_count")
        if being:
            dna = being[0][0] or "?"
            current_species = being[0][1] or "?"
            last_hb = being[0][2] or 0
            hb_count = being[0][3] or 0
        else:
            dna = current_species = "?"
            last_hb = hb_count = 0
        print(f"Local graph:       {nodes:,} nodes, {edges:,} edges, dna {dna}")
    except Exception as e:
        print(f"Local graph:       (unreachable: {e})")
        return 1

    # ── Canonical ──
    try:
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("ct", REPO / "scripts" / "canonical-tip.py")
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        tip = mod.resolve_canonical()
        if tip:
            canonical_dna = tip["dna"]
            sigs = tip["sigs"]
            depth = tip["depth"]
            print(f"Canonical:         species/{canonical_dna}  ({sigs} sigs, depth {depth})")
            if current_species == canonical_dna:
                print(f"                   ✓ you are at the canonical tip")
            else:
                print(f"                   ⚠ your graph reflects {current_species}")
                print(f"                     run: mycelium pull")
        else:
            print(f"Canonical:         (none — mint your first species)")
    except Exception as e:
        print(f"Canonical:         (resolution failed: {e})")

    # ── Breathing ──
    import time
    now_ms = int(time.time() * 1000)
    if last_hb and last_hb > 0:
        age_ms = now_ms - last_hb
        if age_ms < 5000:
            print(f"Breathing:         alive, last heartbeat {age_ms} ms ago, count {hb_count:,}")
        elif age_ms < 60000:
            print(f"Breathing:         slow, last heartbeat {age_ms//1000}s ago, count {hb_count:,}")
        else:
            print(f"Breathing:         ⚠ stalled, last heartbeat {age_ms//1000}s ago")
            print(f"                   run: mycelium breathe")
    else:
        print(f"Breathing:         (not started — run breathe.py)")

    # ── Crystals ──
    try:
        p_total = query("MATCH (p:Protocol) WHERE p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL RETURN count(p)")[0][0]
        p_ok = query("MATCH (p:Protocol) WHERE (p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL) AND p.last_status = 'ok' RETURN count(p)")[0][0]
        t_total = query("MATCH (tc:TestCase) WHERE tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL RETURN count(tc)")[0][0]
        t_ok = query("MATCH (tc:TestCase) WHERE (tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL) AND tc.last_result = 'pass' RETURN count(tc)")[0][0]
        i_total = query("MATCH (inv:Invariant) WHERE inv.cypher_check IS NOT NULL RETURN count(inv)")[0][0]
        i_ok = query("MATCH (inv:Invariant) WHERE inv.cypher_check IS NOT NULL AND inv.last_healthy = true RETURN count(inv)")[0][0]
        total = p_total + t_total + i_total
        ok = p_ok + t_ok + i_ok
        pct = (100 * ok // total) if total else 0
        marker = "✓" if ok == total else "⚠"
        print(f"Crystals:          {marker} {ok}/{total} passing  ({pct}%)")
        if ok < total:
            print(f"                     protocols  {p_ok}/{p_total}")
            print(f"                     tests      {t_ok}/{t_total}")
            print(f"                     invariants {i_ok}/{i_total}")
    except Exception:
        print("Crystals:          (could not enumerate)")

    # ── Witnesses ──
    try:
        wit = query("MATCH (w:Witness) RETURN w.alias, w.public_key, w.active, w.last_heartbeat ORDER BY w.role")
        active_count = sum(1 for r in wit if r[2])
        quorum = query("MATCH (c:ConsensusConfig) RETURN c.quorum_required")
        q_req = quorum[0][0] if quorum else 1
        marker = "✓" if active_count >= q_req else "⚠"
        print(f"Witnesses:         {marker} {active_count} active, quorum {active_count}/{q_req}")
        for row in wit:
            alias, pk, active, _ = row
            mark = "  ●" if active else "  ○"
            print(f"                   {mark} {alias:<15} {pk[:16] if pk else '?'}…")
    except Exception:
        print("Witnesses:         (no consensus config)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
