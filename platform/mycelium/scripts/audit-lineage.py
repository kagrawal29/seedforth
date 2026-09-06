#!/usr/bin/env python3
"""
audit-lineage.py — Walk the full species lineage and verify every link.

Independent stranger audit: starts from the canonical tip and walks
DESCENDED_FROM edges back to genesis, verifying each species's signature
chain along the way.

Usage:
  python3 scripts/audit-lineage.py            # audit from canonical to genesis
  python3 scripts/audit-lineage.py <dna>      # audit from a specific species
  python3 scripts/audit-lineage.py --quick    # just walk the chain, no replay
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from graph import query
from lib.signing import verify_bytes


def get_species_file(dna: str) -> bytes:
    """Read the graph-state.cypher from a species/* git branch as raw bytes."""
    branch = f"species/{dna}"
    r = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{branch}:graph-state.cypher"],
        capture_output=True,  # binary mode
    )
    if r.returncode != 0:
        subprocess.run(
            ["git", "-C", str(REPO), "fetch", "origin", f"{branch}:{branch}"],
            capture_output=True, text=True,
        )
        r = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{branch}:graph-state.cypher"],
            capture_output=True,
        )
    return r.stdout if r.returncode == 0 else b""


def parse_header(content: str) -> dict:
    """Extract header fields from a species file."""
    fields = {}
    witnesses = []
    current = {}
    manifest_lines = []
    manifest_re = re.compile(r'^//   ([PTI]) ([0-9a-f]{16}) (\S+)$')

    for line in content.split("\n"):
        if not line.startswith("//") and line.strip() != "":
            break
        if manifest_re.match(line):
            manifest_lines.append(line.replace("//   ", "", 1))
            continue
        if line.startswith("// witness:"):
            if current:
                witnesses.append(current)
            current = {"alias": line.split(":", 1)[1].strip()}
            continue
        if line.startswith("//   pubkey:"):
            current["pubkey"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("//   signature:"):
            current["signature"] = line.split(":", 1)[1].strip()
            continue
        if line.startswith("// ") and ":" in line:
            stripped = line[3:]
            if len(stripped) > 2 and stripped[0] in "PTI" and stripped[1] == " ":
                continue
            k, v = stripped.split(":", 1)
            if k.strip() not in fields:
                fields[k.strip()] = v.strip()
    if current and "alias" in current:
        witnesses.append(current)

    fields["_witnesses"] = witnesses
    fields["_manifest_lines"] = manifest_lines
    return fields


def verify_species(dna: str, content: bytes) -> dict:
    """Run all 5 cryptographic checks on a species file."""
    result = {"dna": dna, "checks": {}}

    # 1. file hash matches branch (hash the raw bytes!)
    computed = hashlib.sha256(content).hexdigest()[:16]
    result["checks"]["file_hash"] = (computed == dna)
    result["computed_dna"] = computed

    # 2. parse header (decode to text for parsing)
    text = content.decode("utf-8", errors="replace")
    fields = parse_header(text)
    result["fields"] = fields
    result["parent_dna"] = fields.get("parent_dna")
    result["genesis"] = (fields.get("parent_dna") in (None, "genesis", "null") and not result["parent_dna"])

    # 3. manifest_root
    manifest_text = "\n".join(fields["_manifest_lines"])
    if manifest_text:
        recomputed_root = hashlib.sha256(manifest_text.encode()).hexdigest()
        result["checks"]["manifest_root"] = (recomputed_root == fields.get("manifest_root"))
    else:
        result["checks"]["manifest_root"] = None  # no manifest in pre-v2 species

    # 4. commitment
    commit_claim = fields.get("commitment")
    if commit_claim:
        commitment_msg = f"{fields.get('parent_dna')}|{fields.get('manifest_root')}|{fields.get('git_anchor')}"
        recomputed = hashlib.sha256(commitment_msg.encode()).hexdigest()
        result["checks"]["commitment"] = (recomputed == commit_claim)
    else:
        result["checks"]["commitment"] = None

    # 5. signatures
    sigs_valid = []
    if commit_claim:
        for w in fields["_witnesses"]:
            ok = verify_bytes(w["pubkey"], bytes.fromhex(commit_claim), w["signature"])
            sigs_valid.append((w["alias"], ok))
        # Old single-sig species also have a signature field
        if fields.get("signer_pubkey") and fields.get("signature"):
            ok = verify_bytes(
                fields["signer_pubkey"],
                bytes.fromhex(commit_claim),
                fields["signature"],
            )
            sigs_valid.append((fields.get("signer_alias", "?"), ok))
    result["signatures"] = sigs_valid
    result["checks"]["signatures"] = all(ok for _, ok in sigs_valid) if sigs_valid else None

    return result


def main():
    print("══ Mycelium audit ══")

    # Resolve start point
    start_dna = None
    quick = "--quick" in sys.argv
    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            continue
        start_dna = arg

    if not start_dna:
        # Resolve canonical
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("ct", REPO / "scripts" / "canonical-tip.py")
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        tip = mod.resolve_canonical()
        if not tip:
            print("ERROR: no canonical tip", file=sys.stderr)
            sys.exit(1)
        start_dna = tip["dna"]

    print(f"Walking lineage from species/{start_dna}\n")

    # Walk the chain
    chain = []
    current_dna = start_dna
    visited = set()

    while current_dna and current_dna not in visited:
        visited.add(current_dna)
        content = get_species_file(current_dna)
        if not content:
            chain.append({"dna": current_dna, "missing": True})
            break

        verdict = verify_species(current_dna, content)
        # content is now bytes — keep that reference for hashing

        chain.append(verdict)

        if verdict["genesis"] or not verdict["parent_dna"] or verdict["parent_dna"] == "genesis":
            break
        current_dna = verdict["parent_dna"]

    # Print the chain
    print(f"Chain length: {len(chain)} species\n")
    all_pass = True
    for i, link in enumerate(chain):
        dna = link["dna"]
        if link.get("missing"):
            print(f"  [{i}] species/{dna}  ✗ FILE MISSING")
            all_pass = False
            continue

        chk = link["checks"]
        sigs = link["signatures"]
        sig_summary = ""
        if sigs:
            sig_summary = ", ".join(f"{name}:{'✓' if ok else '✗'}" for name, ok in sigs)
        marks = []
        if chk["file_hash"] is False:
            marks.append("HASH✗")
            all_pass = False
        if chk["manifest_root"] is False:
            marks.append("MANIFEST✗")
            all_pass = False
        if chk["commitment"] is False:
            marks.append("COMMITMENT✗")
            all_pass = False
        if chk["signatures"] is False:
            marks.append("SIG✗")
            all_pass = False
        marker = "✓" if not marks else "✗ " + " ".join(marks)
        print(f"  [{i}] species/{dna}  {marker}")
        if sig_summary:
            print(f"        signatures: {sig_summary}")
        if link["parent_dna"]:
            print(f"        parent:     {link['parent_dna']}")

    print()
    if all_pass:
        print("🜂 LINEAGE VERIFIED — all signatures and parent commitments hold.")
    else:
        print("✗ LINEAGE INVALID — at least one species fails verification.")
        sys.exit(1)


if __name__ == "__main__":
    main()
