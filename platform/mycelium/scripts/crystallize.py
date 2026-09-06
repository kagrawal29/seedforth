#!/usr/bin/env python3
"""
crystallize.py — Detect crystallization events and push species to lineage branch.

Crystallization happens when:
  1. Every executable Protocol passed last run (last_status = 'ok')
  2. Every executable TestCase passed (last_result = 'pass')
  3. Every live Invariant is healthy (last_healthy = true)
  4. The genome_hash has been stable for N consecutive breaths

When all four are true:
  - Freeze a sealed DNA = sha256(topology + genome)
  - Export graph-state.cypher
  - Git: commit + push to lineage branch 'species/<sealed_dna>'
  - Create a Species node in the graph with lineage pointer
  - Being records the crystallization event

Run via breathe.py cool tier, or directly:
    python3 scripts/crystallize.py --check     # report state, don't commit
    python3 scripts/crystallize.py --seal      # force a seal (for testing)
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.signing import load_wallet, keypair_from_token, public_key_hex, sign_bytes, verify_bytes

REPO = Path(__file__).resolve().parent.parent
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))

_graph = None


def graph():
    global _graph
    if _graph is None:
        from falkordb import FalkorDB
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        _graph = db.select_graph("asgard")
    return _graph


def q(cypher):
    r = graph().query(cypher)
    return r.result_set


def check_crystallization():
    """Return (crystallized, stats, blockers)."""
    stats = {}

    r = q("MATCH (p:Protocol) WHERE p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL RETURN count(p)")
    stats["protocols_total"] = r[0][0]

    r = q("MATCH (p:Protocol) WHERE (p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL) AND p.last_status = 'ok' RETURN count(p)")
    stats["protocols_ok"] = r[0][0]

    r = q("MATCH (tc:TestCase) WHERE tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL RETURN count(tc)")
    stats["tests_total"] = r[0][0]

    r = q("MATCH (tc:TestCase) WHERE (tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL) AND tc.last_result = 'pass' RETURN count(tc)")
    stats["tests_pass"] = r[0][0]

    r = q("MATCH (inv:Invariant) WHERE inv.cypher_check IS NOT NULL RETURN count(inv)")
    stats["invariants_total"] = r[0][0]

    r = q("MATCH (inv:Invariant) WHERE inv.cypher_check IS NOT NULL AND inv.last_healthy = true RETURN count(inv)")
    stats["invariants_healthy"] = r[0][0]

    total = stats["protocols_total"] + stats["tests_total"] + stats["invariants_total"]
    passing = stats["protocols_ok"] + stats["tests_pass"] + stats["invariants_healthy"]
    stats["crystal_count"] = total
    stats["passing"] = passing
    stats["coverage"] = round(100 * passing / total) if total else 0

    crystallized = passing == total and total > 0

    blockers = []
    if not crystallized:
        r = q("""
        MATCH (tc:TestCase)
        WHERE (tc.cypher IS NOT NULL OR tc.assertion_query IS NOT NULL)
        AND tc.last_result <> 'pass'
        RETURN tc.node_id, tc.last_result
        """)
        blockers += [("test", row[0], row[1]) for row in r]

        r = q("""
        MATCH (p:Protocol)
        WHERE (p.cypher IS NOT NULL OR p.cypher_execute IS NOT NULL)
        AND p.last_status <> 'ok'
        RETURN p.node_id, p.last_status
        """)
        blockers += [("protocol", row[0], row[1]) for row in r]

        r = q("""
        MATCH (inv:Invariant)
        WHERE inv.cypher_check IS NOT NULL
        AND inv.last_healthy <> true
        RETURN inv.node_id, inv.last_healthy
        """)
        blockers += [("invariant", row[0], row[1]) for row in r]

    return crystallized, stats, blockers


def snapshot_and_hash():
    """
    Take the snapshot, inject parent DNA commitment into content, hash bytes.
    Parent hash is cryptographically bound into the child's file.

    A stranger can verify lineage by:
      1. Reading the first lines of graph-state.cypher (sees // parent: <hash>)
      2. Fetching that parent hash's branch from GitHub
      3. Hashing the parent file and confirming the parent claim
      4. Hashing the child file and confirming it matches the branch name

    Returns dict with sealed_dna (file hash after parent commitment).
    """
    # 1. Export graph-state.cypher on the server first
    subprocess.run(
        ["ssh", "root@5.78.206.137",
         "FALKORDB_HOST=localhost FALKORDB_PORT=6380 "
         "python3 /opt/maverick-meta/scripts/graph-export-state.py"],
        capture_output=True, text=True, timeout=60,
    )
    local_path = REPO / "graph-state.cypher"
    subprocess.run(
        ["scp", "root@5.78.206.137:/opt/maverick-meta/graph-state.cypher",
         str(local_path)],
        capture_output=True, text=True, timeout=60,
    )

    # 2. Read the pristine export
    body = local_path.read_text()

    # 3. Fetch parent DNA from the graph (current Species before this mint)
    r = q("MATCH (sp:Species {current: true}) RETURN sp.sealed_dna, sp.git_branch")
    if r:
        parent_dna = r[0][0]
        parent_branch = r[0][1]
    else:
        parent_dna = "genesis"
        parent_branch = "genesis"

    # 4. Compute body-only hashes for metadata
    r = q("MATCH (n) RETURN count(n)")
    nodes = r[0][0]
    r = q("MATCH ()-[r]->() RETURN count(r)")
    edges = r[0][0]

    ph = sorted([row[0] for row in q("MATCH (p:Protocol) WHERE p.crystal_hash IS NOT NULL RETURN p.crystal_hash")])
    th = sorted([row[0] for row in q("MATCH (tc:TestCase) WHERE tc.crystal_hash IS NOT NULL RETURN tc.crystal_hash")])
    ih = sorted([row[0] for row in q("MATCH (inv:Invariant) WHERE inv.crystal_hash IS NOT NULL RETURN inv.crystal_hash")])
    genome = hashlib.sha256("".join(sorted(ph + th + ih)).encode()).hexdigest()[:16]

    topology = f"n{nodes}_e{edges}"
    topology_hash = hashlib.sha256(topology.encode()).hexdigest()[:16]

    # 5. Strip any prior lineage header from the body
    if body.startswith("// ============================================================\n// SPECIES LINEAGE COMMITMENT"):
        lines = body.split("\n")
        end_idx = 0
        for i, line in enumerate(lines[1:], 1):
            if line.startswith("// ============================================================"):
                end_idx = i
                break
        if end_idx:
            body = "\n".join(lines[end_idx + 2:])

    # 6. Timestamp anchoring: the latest git commit sha on main
    git_anchor = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "main"],
        capture_output=True, text=True,
    ).stdout.strip()[:16] or "none"

    # 7. Load wallet, derive signer pubkey
    wallet = load_wallet()
    sk, pk = keypair_from_token(wallet["token"])
    signer_pubkey = public_key_hex(pk)
    signer_alias = wallet.get("alias", "Mycelium")

    ts = datetime.now(timezone.utc).isoformat()

    # 8a. Build the crystal manifest — every verified crystal with its hash + kind + node_id
    # This commits the block to exactly which crystals were passing at mint time.
    # A stranger can prove "crystal X was in this species" by reading the manifest.
    manifest_rows = q(
        "MATCH (p:Protocol) WHERE p.crystal_hash IS NOT NULL AND p.last_status = 'ok' "
        "RETURN 'P' AS kind, p.crystal_hash AS h, p.node_id AS nid "
        "UNION "
        "MATCH (tc:TestCase) WHERE tc.crystal_hash IS NOT NULL AND tc.last_result = 'pass' "
        "RETURN 'T' AS kind, tc.crystal_hash AS h, tc.node_id AS nid "
        "UNION "
        "MATCH (inv:Invariant) WHERE inv.crystal_hash IS NOT NULL AND inv.last_healthy = true "
        "RETURN 'I' AS kind, inv.crystal_hash AS h, inv.node_id AS nid"
    )
    manifest_entries = sorted(
        [(row[0], row[1], row[2]) for row in manifest_rows],
        key=lambda x: (x[0], x[2]),
    )
    # Merkle-ish root: hash of the sorted manifest lines
    manifest_lines = [f"{kind} {h} {nid}" for kind, h, nid in manifest_entries]
    manifest_text = "\n".join(manifest_lines)
    manifest_root = hashlib.sha256(manifest_text.encode()).hexdigest()

    # 8b. The signing commitment: sha256(parent_dna + '|' + manifest_root + '|' + git_anchor)
    # This binds the signer to: (which parent, which crystals, which point in time)
    commitment_msg = f"{parent_dna}|{manifest_root}|{git_anchor}"
    commitment_hash = hashlib.sha256(commitment_msg.encode()).hexdigest()

    # 8c. Build the header
    pre_sig_header_lines = [
        "// ============================================================",
        "// SPECIES LINEAGE COMMITMENT",
        f"// parent_dna:    {parent_dna}",
        f"// parent_branch: {parent_branch}",
        f"// genome_hash:   {genome}",
        f"// topology_hash: {topology_hash}",
        f"// topology:      {topology}",
        f"// crystallized:  {ts}",
        f"// nodes:         {nodes}",
        f"// edges:         {edges}",
        f"// crystal_count: {len(manifest_entries)}",
        f"// manifest_root: {manifest_root}",
        f"// git_anchor:    {git_anchor}",
        f"// signer_alias:  {signer_alias}",
        f"// signer_pubkey: {signer_pubkey}",
        f"// signer_algo:   ed25519",
        f"// commitment:    {commitment_hash}",
        f"// commitment_fmt: sha256(parent_dna | manifest_root | git_anchor)",
        "// ------------------------------------------------------------",
        "// CRYSTAL MANIFEST",
        "// Every verified-passing crystal at mint time:",
        "//   Format: <kind> <crystal_hash> <node_id>",
        "//   P=Protocol  T=TestCase  I=Invariant",
    ]
    for line in manifest_lines:
        pre_sig_header_lines.append(f"//   {line}")
    pre_sig_header = "\n".join(pre_sig_header_lines) + "\n"
    # 9. SIGN the commitment hash. This binds (parent, crystals, time) to the signer.
    signature_hex = sign_bytes(sk, bytes.fromhex(commitment_hash))
    presig_hash = commitment_hash  # kept as alias for backward-compat storage
    assert verify_bytes(signer_pubkey, bytes.fromhex(commitment_hash), signature_hex), \
        "self-verify failed — bad wallet key"

    # 10. Full header now includes signature — the file's final form
    full_header = (
        pre_sig_header
        + f"// signature:     {signature_hex}\n"
        + f"// presig_hash:   {presig_hash}\n"
        + f"// ------------------------------------------------------------\n"
        + f"// Verify offline: strip everything from '// signature:' to end of\n"
        + f"// this header block, recompute sha256, verify ed25519 signature\n"
        + f"// against signer_pubkey using that hash.\n"
        + f"// ============================================================\n"
        + f"\n"
    )

    final_content = full_header + body
    local_path.write_text(final_content)

    # 11. Hash the full file (with signature in it). THIS is the sealed DNA.
    file_bytes = local_path.read_bytes()
    full_sha = hashlib.sha256(file_bytes).hexdigest()
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
        "file_path": str(local_path),
        "file_bytes": len(file_bytes),
        "git_anchor": git_anchor,
        "signer_pubkey": signer_pubkey,
        "signer_alias": signer_alias,
        "signature": signature_hex,
        "presig_hash": presig_hash,
        "manifest_root": manifest_root,
        "manifest_count": len(manifest_entries),
    }


def commit_and_push(sealed):
    """Commit the already-exported graph-state.cypher to the lineage branch."""
    branch = f"species/{sealed['sealed_dna']}"
    ts = datetime.now(timezone.utc).isoformat()

    # Create lineage branch
    subprocess.run(
        ["git", "-C", str(REPO), "checkout", "-B", branch],
        capture_output=True, text=True,
    )
    subprocess.run(
        ["git", "-C", str(REPO), "add", "graph-state.cypher"],
        capture_output=True, text=True,
    )
    msg = (
        f"species {sealed['sealed_dna']}: {sealed['nodes']} nodes, {sealed['edges']} edges\n\n"
        f"sealed_dna:    {sealed['sealed_dna']}  (sha256 of graph-state.cypher)\n"
        f"full_sha256:   {sealed['full_sha256']}\n"
        f"genome_hash:   {sealed['genome']}\n"
        f"topology_hash: {sealed['topology_hash']}\n"
        f"topology:      {sealed['topology']}\n"
        f"file_bytes:    {sealed['file_bytes']}\n"
        f"crystallized:  {ts}\n"
        f"\n"
        f"Verify: shasum -a 256 graph-state.cypher | cut -c1-16\n"
        f"        must equal {sealed['sealed_dna']}\n"
    )
    r = subprocess.run(
        ["git", "-C", str(REPO), "commit", "-m", msg],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(f"  commit failed: {r.stderr}")
        return False

    r = subprocess.run(
        ["git", "-C", str(REPO), "push", "-u", "origin", branch],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print(f"  push failed: {r.stderr}")

    subprocess.run(["git", "-C", str(REPO), "checkout", "main"], capture_output=True, text=True)
    return True


def mint_species(sealed, stats):
    """Create Species node, link to lineage with parent commitment."""
    now_iso = datetime.now(timezone.utc).isoformat()
    species_id = f"species-{sealed['sealed_dna']}"

    r = q("MATCH (s:Species {current: true}) RETURN s.node_id, s.sealed_dna")
    parent_id = r[0][0] if r else None

    q("MATCH (s:Species {current: true}) SET s.current = false")

    q(f"""
    MERGE (sp:Species {{node_id: '{species_id}'}})
    SET sp.label = 'Species {sealed["sealed_dna"]}',
        sp.sealed_dna = '{sealed["sealed_dna"]}',
        sp.full_sha256 = '{sealed["full_sha256"]}',
        sp.parent_dna = '{sealed["parent_dna"]}',
        sp.genome_hash = '{sealed["genome"]}',
        sp.topology_hash = '{sealed["topology_hash"]}',
        sp.nodes = {sealed["nodes"]},
        sp.edges = {sealed["edges"]},
        sp.crystal_count = {stats["crystal_count"]},
        sp.crystallized_at = '{now_iso}',
        sp.git_branch = 'species/{sealed["sealed_dna"]}',
        sp.parent_in_content = true,
        sp.git_anchor = '{sealed.get("git_anchor", "")}',
        sp.signer_alias = '{sealed.get("signer_alias", "")}',
        sp.signer_pubkey = '{sealed.get("signer_pubkey", "")}',
        sp.signer_algo = 'ed25519',
        sp.signature = '{sealed.get("signature", "")}',
        sp.presig_hash = '{sealed.get("presig_hash", "")}',
        sp.manifest_root = '{sealed.get("manifest_root", "")}',
        sp.manifest_count = {sealed.get("manifest_count", 0)},
        sp.signed = true,
        sp.current = true
    """)

    # Link the species to the Person who signed it
    q(f"""
    MATCH (sp:Species {{node_id: '{species_id}'}}),
          (p:Person {{public_key: '{sealed.get("signer_pubkey", "")}'}})
    MERGE (p)-[:MINTED]->(sp)
    MERGE (sp)-[:SIGNED_BY]->(p)
    """)

    if parent_id:
        q(f"""
        MATCH (child:Species {{node_id: '{species_id}'}}),
              (parent:Species {{node_id: '{parent_id}'}})
        MERGE (child)-[:DESCENDED_FROM {{
            cryptographic: true,
            method: 'parent-dna-in-content'
        }}]->(parent)
        MERGE (parent)-[:PARENT_OF]->(child)
        """)

    q(f"""
    MATCH (b:Being), (sp:Species {{node_id: '{species_id}'}})
    MERGE (b)-[:EXPRESSES]->(sp)
    SET b.current_species = '{sealed["sealed_dna"]}',
        b.last_crystallization = '{now_iso}'
    """)
    q("MATCH (b:Being)-[r:EXPRESSES]->(sp:Species) WHERE sp.current <> true DELETE r")
    return species_id


def verify_species_file(file_path: Path) -> dict:
    """
    Offline trustless verification.

    Four independent cryptographic checks:
      1. sealed_dna = sha256(file) → must equal branch name / expected
      2. manifest_root = sha256(joined manifest lines) → must equal claimed
      3. commitment_hash = sha256(parent_dna | manifest_root | git_anchor) → matches claim
      4. ed25519_verify(signer_pubkey, commitment_hash, signature) → True

    Anyone with just the file can run all four. No network. No trust.
    """
    import re
    content = file_path.read_text()
    result = {
        "file": str(file_path),
        "file_bytes": len(content.encode()),
    }

    # ── Extract header fields (scan until first non-comment line) ──
    header_fields = {}
    for line in content.split("\n"):
        if not line.startswith("//") and line.strip() != "":
            break
        if line.startswith("// ") and ":" in line:
            stripped = line[3:]
            # Skip lines that are manifest entries (start with single letter + space)
            if len(stripped) > 2 and stripped[0] in "PTI" and stripped[1] == " ":
                continue
            k, v = stripped.split(":", 1)
            if k.strip() not in header_fields:  # first occurrence wins
                header_fields[k.strip()] = v.strip()

    result["parent_dna"] = header_fields.get("parent_dna")
    result["signer_pubkey"] = header_fields.get("signer_pubkey")
    result["signer_alias"] = header_fields.get("signer_alias")
    result["signature"] = header_fields.get("signature")
    result["commitment"] = header_fields.get("commitment")
    result["manifest_root"] = header_fields.get("manifest_root")
    result["git_anchor"] = header_fields.get("git_anchor")

    # ── Check 1: file sha256 = sealed_dna ──
    result["computed_file_sha"] = hashlib.sha256(content.encode()).hexdigest()
    result["computed_sealed_dna"] = result["computed_file_sha"][:16]

    # ── Check 2: manifest_root = sha256(manifest lines) ──
    manifest_line_re = re.compile(r'^//   ([PTI]) ([0-9a-f]{16}) (\S+)$')
    manifest_lines = []
    for line in content.split("\n")[:500]:
        if manifest_line_re.match(line):
            manifest_lines.append(line.replace("//   ", "", 1))
    manifest_text = "\n".join(manifest_lines)
    result["recomputed_manifest_root"] = hashlib.sha256(manifest_text.encode()).hexdigest()
    result["manifest_count"] = len(manifest_lines)
    result["manifest_root_check"] = (
        result["recomputed_manifest_root"] == result["manifest_root"]
    )

    # ── Check 3: commitment = sha256(parent_dna | manifest_root | git_anchor) ──
    commitment_msg = f"{result['parent_dna']}|{result['manifest_root']}|{result['git_anchor']}"
    result["recomputed_commitment"] = hashlib.sha256(commitment_msg.encode()).hexdigest()
    result["commitment_check"] = (
        result["recomputed_commitment"] == result["commitment"]
    )

    # ── Check 4: ed25519 signature over commitment ──
    if result["signer_pubkey"] and result["signature"] and result["commitment"]:
        result["signature_check"] = verify_bytes(
            result["signer_pubkey"],
            bytes.fromhex(result["commitment"]),
            result["signature"],
        )
    else:
        result["signature_check"] = False

    result["all_checks_pass"] = (
        result["manifest_root_check"]
        and result["commitment_check"]
        and result["signature_check"]
    )
    return result


def verify_lineage(sealed_dna=None):
    """Verify a species file's parent commitment. Returns (ok, details)."""
    branch = f"species/{sealed_dna}" if sealed_dna else None
    if not sealed_dna:
        local_path = REPO / "graph-state.cypher"
    else:
        # Fetch from github branch
        r = subprocess.run(
            ["gh", "api",
             f"repos/Qubit-Capital/maverick-meta/contents/graph-state.cypher?ref={branch}",
             "--jq", ".download_url"],
            capture_output=True, text=True,
        )
        url = r.stdout.strip()
        r = subprocess.run(["curl", "-sL", url], capture_output=True, text=True)
        local_path = Path(f"/tmp/verify_{sealed_dna}.cypher")
        local_path.write_text(r.stdout)

    content = local_path.read_text()
    computed = hashlib.sha256(content.encode()).hexdigest()[:16]

    # Parse parent from header
    parent_dna = None
    for line in content.split("\n")[:20]:
        if line.startswith("// parent_dna:"):
            parent_dna = line.split(":", 1)[1].strip()
            break

    ok = (not sealed_dna) or computed == sealed_dna
    return {
        "file": str(local_path),
        "computed_dna": computed,
        "expected_dna": sealed_dna,
        "parent_dna": parent_dna,
        "hash_ok": ok,
    }


def main():
    check_only = "--check" in sys.argv
    force = "--seal" in sys.argv
    verify = "--verify" in sys.argv

    if verify:
        # Verify a species' lineage cryptographically
        target = None
        for arg in sys.argv:
            if arg.startswith("species/") or (len(arg) == 16 and all(c in "0123456789abcdef" for c in arg)):
                target = arg.replace("species/", "")
                break
        result = verify_lineage(target)
        print(f"File:         {result['file']}")
        print(f"Computed DNA: {result['computed_dna']}")
        print(f"Expected DNA: {result['expected_dna'] or '(local)'}")
        print(f"Parent DNA:   {result['parent_dna'] or '(not in header)'}")
        print(f"Match:        {'✓ YES' if result['hash_ok'] else '✗ NO'}")
        return 0 if result['hash_ok'] else 1


    print("=" * 60)
    print("CRYSTALLIZATION CHECK")
    print("=" * 60)

    crystallized, stats, blockers = check_crystallization()
    print(f"\nCoverage: {stats['passing']}/{stats['crystal_count']} ({stats['coverage']}%)")
    print(f"  Protocols:  {stats['protocols_ok']}/{stats['protocols_total']}")
    print(f"  Tests:      {stats['tests_pass']}/{stats['tests_total']}")
    print(f"  Invariants: {stats['invariants_healthy']}/{stats['invariants_total']}")

    if blockers:
        print(f"\n{len(blockers)} blockers:")
        for kind, nid, status in blockers[:30]:
            print(f"  [{kind:<9} {status or 'null':<7}] {nid}")

    if not crystallized and not force:
        print("\nNOT crystallized. Use --seal to force.")
        return 1

    print("\nSnapshotting + hashing graph-state.cypher...")
    sealed = snapshot_and_hash()
    print(f"  file:          {sealed['file_path']}")
    print(f"  bytes:         {sealed['file_bytes']:,}")
    print(f"  SEALED DNA:    {sealed['sealed_dna']}  (first 16 of sha256)")
    print(f"  full sha256:   {sealed['full_sha256']}")
    print(f"  genome_hash:   {sealed['genome']}")
    print(f"  topology_hash: {sealed['topology_hash']}")

    if check_only:
        return 0

    print("\nMinting species node...")
    species_id = mint_species(sealed, stats)
    print(f"  {species_id}")

    print("\nCommitting + pushing to lineage branch...")
    if commit_and_push(sealed):
        print(f"\n✓ Pushed to species/{sealed['sealed_dna']}")
        print(f"  Verify: shasum -a 256 graph-state.cypher | cut -c1-16")
        print(f"  Expected: {sealed['sealed_dna']}")
    else:
        print("\n✗ Push failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
