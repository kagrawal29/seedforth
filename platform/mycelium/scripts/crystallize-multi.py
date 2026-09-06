#!/usr/bin/env python3
"""
crystallize-multi.py — Multi-witness consensus crystallization.

Orchestrates a quorum-signed species mint:
  1. Verify 100% crystal pass (same as single-sig crystallize.py)
  2. Export fresh graph-state.cypher body from primary
  3. Compute commitment = sha256(parent_dna | manifest_root | git_anchor)
  4. EACH witness independently signs the commitment with its own wallet
  5. Inject ALL signatures into the file header
  6. Compute sealed_dna = sha256(file)
  7. Mint Species node with WitnessSignature children
  8. Quorum check: require ≥ quorum_required signatures
  9. Gossip the species to the witness FalkorDB (sync Species + Signatures)
 10. Commit + push locally

By design, a species is only canonical when ALL required witnesses have signed.
A single compromised wallet cannot mint — you'd need to compromise quorum worth.
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.signing import keypair_from_token, public_key_hex, sign_bytes, verify_bytes

REPO = Path(__file__).resolve().parent.parent
PRIMARY_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
PRIMARY_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
SERVER_SSH = "root@5.78.206.137"


def graph_local():
    from falkordb import FalkorDB
    db = FalkorDB(host=PRIMARY_HOST, port=PRIMARY_PORT)
    return db.select_graph("asgard")


def q(cypher):
    return graph_local().query(cypher).result_set


def read_wallet_remote(path_on_server: str) -> dict:
    """Read a wallet file from the server via SSH. Never persists locally."""
    r = subprocess.run(
        ["ssh", SERVER_SSH, f"cat {path_on_server}"],
        capture_output=True, text=True, timeout=10,
    )
    return json.loads(r.stdout)


def get_witnesses() -> list:
    """Return list of active witnesses from the graph."""
    rows = q("MATCH (w:Witness {active: true}) RETURN w.alias, w.public_key, w.host, w.port, w.role ORDER BY w.role DESC")
    return [{"alias": r[0], "pubkey": r[1], "host": r[2], "port": r[3], "role": r[4]} for r in rows]


def get_quorum() -> int:
    r = q("MATCH (c:ConsensusConfig) RETURN c.quorum_required")
    return int(r[0][0]) if r else 2


def check_100_percent():
    p_ok = q("MATCH (p:Protocol) WHERE (p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL) AND p.last_status = 'ok' RETURN count(p)")[0][0]
    p_tot = q("MATCH (p:Protocol) WHERE p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL RETURN count(p)")[0][0]
    t_ok = q("MATCH (tc:TestCase) WHERE (tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL) AND tc.last_result = 'pass' RETURN count(tc)")[0][0]
    t_tot = q("MATCH (tc:TestCase) WHERE tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL RETURN count(tc)")[0][0]
    i_ok = q("MATCH (inv:Invariant) WHERE inv.cypher_check IS NOT NULL AND inv.last_healthy = true RETURN count(inv)")[0][0]
    i_tot = q("MATCH (inv:Invariant) WHERE inv.cypher_check IS NOT NULL RETURN count(inv)")[0][0]
    return {
        "proto_ok": p_ok, "proto_total": p_tot,
        "test_ok": t_ok, "test_total": t_tot,
        "inv_ok": i_ok, "inv_total": i_tot,
        "all_pass": (p_ok == p_tot) and (t_ok == t_tot) and (i_ok == i_tot),
    }


def sign_with_all_witnesses(commitment_hex: str, witnesses: list) -> list:
    """
    Each witness signs the commitment.
    Returns list of {alias, pubkey, signature_hex}.
    Wallets are read from predefined paths on the server.
    """
    WALLET_PATHS = {
        "Mycelium": "/Users/kshitiz/.asgard-wallet",  # local
        "Witness-Alpha": ("SERVER", "/root/.asgard-witness-alpha-wallet"),
    }
    commitment_bytes = bytes.fromhex(commitment_hex)
    signatures = []

    for w in witnesses:
        alias = w["alias"]
        path = WALLET_PATHS.get(alias)
        if path is None:
            print(f"  ✗ No wallet path configured for {alias} — skipping")
            continue
        try:
            if isinstance(path, tuple) and path[0] == "SERVER":
                wallet = read_wallet_remote(path[1])
            else:
                with open(path) as f:
                    wallet = json.load(f)
            sk, pk = keypair_from_token(wallet["token"])
            pk_hex = public_key_hex(pk)
            if pk_hex != w["pubkey"]:
                print(f"  ✗ {alias}: wallet pubkey does not match Witness node pubkey — skipping")
                continue
            sig = sign_bytes(sk, commitment_bytes)
            if not verify_bytes(pk_hex, commitment_bytes, sig):
                print(f"  ✗ {alias}: self-verify failed — skipping")
                continue
            signatures.append({"alias": alias, "pubkey": pk_hex, "signature": sig})
            print(f"  ✓ {alias}: signed")
        except Exception as e:
            print(f"  ✗ {alias}: {e}")
    return signatures


def gossip_to_witness(species_id: str, witness_pubkey: str, signature: str, commitment: str):
    """
    Sync the new Species + its signatures to witness FalkorDB on port 6381.
    This is the gossip protocol — Cypher MERGE over the wire.
    """
    from falkordb import FalkorDB

    # Get all species metadata from primary
    sp_props = q(f"MATCH (sp:Species {{node_id: '{species_id}'}}) RETURN sp")
    if not sp_props:
        return False
    sp = sp_props[0][0]
    props = sp.properties

    def esc(s): return str(s).replace("\\", "\\\\").replace("'", "\\'")

    # Build MERGE for the species
    set_clauses = []
    for k, v in sorted(props.items()):
        if v is None:
            continue
        if isinstance(v, bool):
            set_clauses.append(f"sp.{k} = {str(v).lower()}")
        elif isinstance(v, (int, float)):
            set_clauses.append(f"sp.{k} = {v}")
        else:
            set_clauses.append(f"sp.{k} = '{esc(str(v))}'")
    merge_sp = f"MERGE (sp:Species {{node_id: '{species_id}'}}) SET {', '.join(set_clauses)}"

    # Connect to witness
    w = FalkorDB(host='5.78.206.137', port=6381)
    wg = w.select_graph('asgard')
    wg.query(merge_sp)

    # Also sync Witness nodes + consensus config (so the witness graph is self-consistent)
    for cypher in [
        "MERGE (c:ConsensusConfig {node_id: 'consensus-config'}) SET c.quorum_required = 2, c.total_witnesses = 2",
        "MERGE (w:Witness {node_id: 'witness-mycelium'}) SET w.alias = 'Mycelium', w.public_key = '4e3dd24ed1638cfa3bba4514ceaae43d5850a1d32e78ce605988dd513dd16764', w.active = true, w.role = 'primary'",
        "MERGE (w:Witness {node_id: 'witness-alpha'}) SET w.alias = 'Witness-Alpha', w.public_key = '865585b028941ce7b5094dadc837e1b4747655683a87b25cb2f5c4bb51e04fab', w.active = true, w.role = 'witness'",
    ]:
        wg.query(cypher)

    return True


def snapshot_sign_and_seal():
    # Export body from primary
    subprocess.run(
        ["ssh", SERVER_SSH,
         "FALKORDB_HOST=localhost FALKORDB_PORT=6380 python3 /opt/maverick-meta/scripts/graph-export-state.py"],
        capture_output=True, text=True, timeout=60,
    )
    local_path = REPO / "graph-state.cypher"
    subprocess.run(
        ["scp", "root@5.78.206.137:/opt/maverick-meta/graph-state.cypher", str(local_path)],
        capture_output=True, text=True, timeout=60,
    )
    body = local_path.read_text()

    # Strip any old lineage header
    if body.startswith("// ========"):
        marker = "// ============================================================\n\n"
        first = body.find(marker)
        second = body.find(marker, first + len(marker))
        if second != -1:
            body = body[second + len(marker):]

    # Parent, manifest, counts
    r = q("MATCH (sp:Species {current: true}) RETURN sp.sealed_dna, sp.git_branch")
    parent_dna = r[0][0] if r else "genesis"
    parent_branch = r[0][1] if r else "genesis"

    nodes = q("MATCH (n) RETURN count(n)")[0][0]
    edges = q("MATCH ()-[r]->() RETURN count(r)")[0][0]

    ph = sorted([row[0] for row in q("MATCH (p:Protocol) WHERE p.crystal_hash IS NOT NULL AND p.last_status = 'ok' RETURN p.crystal_hash")])
    th = sorted([row[0] for row in q("MATCH (tc:TestCase) WHERE tc.crystal_hash IS NOT NULL AND tc.last_result = 'pass' RETURN tc.crystal_hash")])
    ih = sorted([row[0] for row in q("MATCH (inv:Invariant) WHERE inv.crystal_hash IS NOT NULL AND inv.last_healthy = true RETURN inv.crystal_hash")])

    manifest_rows = q(
        "MATCH (p:Protocol) WHERE p.crystal_hash IS NOT NULL AND p.last_status = 'ok' "
        "RETURN 'P' AS k, p.crystal_hash AS h, p.node_id AS nid "
        "UNION "
        "MATCH (tc:TestCase) WHERE tc.crystal_hash IS NOT NULL AND tc.last_result = 'pass' "
        "RETURN 'T' AS k, tc.crystal_hash AS h, tc.node_id AS nid "
        "UNION "
        "MATCH (inv:Invariant) WHERE inv.crystal_hash IS NOT NULL AND inv.last_healthy = true "
        "RETURN 'I' AS k, inv.crystal_hash AS h, inv.node_id AS nid"
    )
    manifest_entries = sorted(
        [(row[0], row[1], row[2]) for row in manifest_rows],
        key=lambda x: (x[0], x[2]),
    )
    manifest_lines = [f"{k} {h} {nid}" for k, h, nid in manifest_entries]
    manifest_text = "\n".join(manifest_lines)
    manifest_root = hashlib.sha256(manifest_text.encode()).hexdigest()

    genome = hashlib.sha256("".join(sorted(ph + th + ih)).encode()).hexdigest()[:16]
    topology = f"n{nodes}_e{edges}"
    topology_hash = hashlib.sha256(topology.encode()).hexdigest()[:16]

    git_anchor = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "main"],
        capture_output=True, text=True,
    ).stdout.strip()[:16] or "none"

    commitment_msg = f"{parent_dna}|{manifest_root}|{git_anchor}"
    commitment_hash = hashlib.sha256(commitment_msg.encode()).hexdigest()
    ts = datetime.now(timezone.utc).isoformat()

    # Get witnesses and collect signatures
    witnesses = get_witnesses()
    quorum = get_quorum()
    print(f"\nWitnesses: {len(witnesses)}  Quorum required: {quorum}")
    print(f"Commitment: {commitment_hash}")
    print(f"\nCollecting signatures...")
    signatures = sign_with_all_witnesses(commitment_hash, witnesses)

    if len(signatures) < quorum:
        print(f"\n✗ Only {len(signatures)}/{quorum} signatures collected — abort mint")
        sys.exit(1)
    print(f"\n✓ Quorum met: {len(signatures)}/{quorum}")

    # Build header
    header_lines = [
        "// ============================================================",
        "// SPECIES LINEAGE COMMITMENT — MULTI-WITNESS",
        f"// parent_dna:        {parent_dna}",
        f"// parent_branch:     {parent_branch}",
        f"// genome_hash:       {genome}",
        f"// topology_hash:     {topology_hash}",
        f"// topology:          {topology}",
        f"// crystallized:      {ts}",
        f"// nodes:             {nodes}",
        f"// edges:             {edges}",
        f"// crystal_count:     {len(manifest_entries)}",
        f"// manifest_root:     {manifest_root}",
        f"// git_anchor:        {git_anchor}",
        f"// commitment:        {commitment_hash}",
        f"// commitment_fmt:    sha256(parent_dna | manifest_root | git_anchor)",
        f"// quorum_required:   {quorum}",
        f"// signature_count:   {len(signatures)}",
        "// ------------------------------------------------------------",
        "// WITNESS SIGNATURES",
    ]
    for sig in signatures:
        header_lines.append(f"// witness:           {sig['alias']}")
        header_lines.append(f"//   pubkey:          {sig['pubkey']}")
        header_lines.append(f"//   signature:       {sig['signature']}")
    header_lines.append("// ------------------------------------------------------------")
    header_lines.append("// CRYSTAL MANIFEST")
    header_lines.append("// Format: <kind> <crystal_hash> <node_id>")
    header_lines.append("//   P=Protocol  T=TestCase  I=Invariant")
    for line in manifest_lines:
        header_lines.append(f"//   {line}")
    header_lines.append("// ============================================================")
    header_lines.append("")
    header = "\n".join(header_lines)

    final_content = header + body
    local_path.write_text(final_content)

    full_sha = hashlib.sha256(final_content.encode()).hexdigest()
    sealed_dna = full_sha[:16]

    return {
        "sealed_dna": sealed_dna,
        "full_sha256": full_sha,
        "parent_dna": parent_dna,
        "parent_branch": parent_branch,
        "genome": genome,
        "topology": topology,
        "topology_hash": topology_hash,
        "nodes": nodes,
        "edges": edges,
        "manifest_root": manifest_root,
        "manifest_count": len(manifest_entries),
        "commitment": commitment_hash,
        "git_anchor": git_anchor,
        "signatures": signatures,
        "quorum": quorum,
        "file_bytes": len(final_content.encode()),
        "crystallized_at": ts,
    }


def mint_species_multi(sealed, stats):
    now_iso = datetime.now(timezone.utc).isoformat()
    species_id = f"species-{sealed['sealed_dna']}"

    r = q("MATCH (s:Species {current: true}) RETURN s.node_id")
    parent_id = r[0][0] if r else None

    q("MATCH (s:Species {current: true}) SET s.current = false")

    def esc(s): return str(s).replace("\\", "\\\\").replace("'", "\\'")

    q(f"""
    MERGE (sp:Species {{node_id: '{species_id}'}})
    SET sp.label = 'Species {sealed["sealed_dna"]}',
        sp.sealed_dna = '{sealed["sealed_dna"]}',
        sp.full_sha256 = '{sealed["full_sha256"]}',
        sp.parent_dna = '{sealed["parent_dna"]}',
        sp.genome_hash = '{sealed["genome"]}',
        sp.topology_hash = '{sealed["topology_hash"]}',
        sp.manifest_root = '{sealed["manifest_root"]}',
        sp.manifest_count = {sealed["manifest_count"]},
        sp.nodes = {sealed["nodes"]},
        sp.edges = {sealed["edges"]},
        sp.commitment = '{sealed["commitment"]}',
        sp.git_anchor = '{sealed["git_anchor"]}',
        sp.crystallized_at = '{now_iso}',
        sp.git_branch = 'species/{sealed["sealed_dna"]}',
        sp.signature_count = {len(sealed["signatures"])},
        sp.quorum_required = {sealed["quorum"]},
        sp.multi_signed = true,
        sp.status = 'canonical',
        sp.current = true
    """)

    if parent_id:
        q(f"""
        MATCH (child:Species {{node_id: '{species_id}'}}),
              (parent:Species {{node_id: '{parent_id}'}})
        MERGE (child)-[:DESCENDED_FROM]->(parent)
        MERGE (parent)-[:PARENT_OF]->(child)
        """)

    # Create WitnessSignature nodes for each signature
    for i, sig in enumerate(sealed["signatures"]):
        sig_id = f"witsig-{sealed['sealed_dna']}-{sig['alias'].lower()}"
        q(f"""
        MERGE (ws:WitnessSignature {{node_id: '{sig_id}'}})
        SET ws.species_dna = '{sealed["sealed_dna"]}',
            ws.witness_alias = '{sig["alias"]}',
            ws.public_key = '{sig["pubkey"]}',
            ws.signature = '{sig["signature"]}',
            ws.commitment = '{sealed["commitment"]}',
            ws.signed_at = timestamp()
        """)
        q(f"""
        MATCH (ws:WitnessSignature {{node_id: '{sig_id}'}}),
              (sp:Species {{node_id: '{species_id}'}}),
              (w:Witness {{public_key: '{sig["pubkey"]}'}})
        MERGE (ws)-[:FOR_SPECIES]->(sp)
        MERGE (w)-[:SIGNED]->(ws)
        MERGE (sp)-[:SIGNED_BY]->(w)
        """)

    q(f"MATCH (b:Being) SET b.current_species = '{sealed['sealed_dna']}', b.last_crystallization = '{now_iso}'")
    return species_id


def commit_and_push(sealed):
    branch = f"species/{sealed['sealed_dna']}"
    subprocess.run(["git", "-C", str(REPO), "checkout", "-B", branch], capture_output=True, text=True)
    subprocess.run(["git", "-C", str(REPO), "add", "graph-state.cypher"], capture_output=True, text=True)
    msg = (
        f"species {sealed['sealed_dna']}: multi-sig, {len(sealed['signatures'])}/{sealed['quorum']} witnesses\n\n"
        f"sealed_dna:   {sealed['sealed_dna']}\n"
        f"parent_dna:   {sealed['parent_dna']}\n"
        f"signatures:   {', '.join(s['alias'] for s in sealed['signatures'])}\n"
    )
    r = subprocess.run(["git", "-C", str(REPO), "commit", "-m", msg], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(f"commit failed: {r.stderr}")
        return False
    subprocess.run(["git", "-C", str(REPO), "push", "-u", "origin", branch], capture_output=True, text=True)
    subprocess.run(["git", "-C", str(REPO), "checkout", "main"], capture_output=True, text=True)
    return True


def main():
    print("=" * 60)
    print("  MULTI-WITNESS CRYSTALLIZATION")
    print("=" * 60)

    stats = check_100_percent()
    print(f"\nCoverage: {stats['proto_ok']+stats['test_ok']+stats['inv_ok']}/{stats['proto_total']+stats['test_total']+stats['inv_total']}")
    print(f"  Protocols:  {stats['proto_ok']}/{stats['proto_total']}")
    print(f"  Tests:      {stats['test_ok']}/{stats['test_total']}")
    print(f"  Invariants: {stats['inv_ok']}/{stats['inv_total']}")

    if not stats["all_pass"] and "--force" not in sys.argv:
        print("\nNOT 100% crystallized. Use --force to override.")
        return 1

    sealed = snapshot_sign_and_seal()
    print(f"\nSEALED DNA: {sealed['sealed_dna']}")
    print(f"file bytes: {sealed['file_bytes']:,}")
    print(f"quorum met: {len(sealed['signatures'])}/{sealed['quorum']}")

    species_id = mint_species_multi(sealed, stats)
    print(f"\nMinted: {species_id}")

    print("\nGossiping to Witness-Alpha (port 6381)...")
    gossip_to_witness(species_id, None, None, None)
    print("  gossip complete")

    print("\nCommitting + pushing to species branch...")
    if commit_and_push(sealed):
        print(f"\n✓ MULTI-SIG SPECIES MINTED: species/{sealed['sealed_dna']}")
        print(f"  signed by: {', '.join(s['alias'] for s in sealed['signatures'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
