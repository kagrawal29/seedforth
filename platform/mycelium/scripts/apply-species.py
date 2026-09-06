#!/usr/bin/env python3
"""
apply-species.py — Pull a species, verify, restore into local FalkorDB.

Usage:
    python3 scripts/apply-species.py canonical          # apply current canonical
    python3 scripts/apply-species.py <sealed_dna>       # apply specific species
    python3 scripts/apply-species.py <sealed_dna> --merge  # don't wipe, just MERGE on top

Steps:
    1. Resolve the species DNA (from arg or canonical-tip)
    2. Find the species file (local git checkout, or fetch from remote)
    3. Run verify-species-local.sh on it
    4. If --restore (default): wipe local FalkorDB, replay the body
       If --merge: replay the body on top of current state
    5. Update Being.current_species
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from graph import query, graph as get_graph

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"


def resolve_dna(arg: str) -> str:
    """Resolve 'canonical' or a literal DNA to a sealed_dna string."""
    if arg == "canonical":
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("ct", REPO / "scripts" / "canonical-tip.py")
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        tip = mod.resolve_canonical()
        if not tip:
            print("ERROR: no canonical tip found", file=sys.stderr)
            sys.exit(1)
        return tip["dna"]
    return arg


def fetch_species_file(dna: str) -> Path:
    """Get the species file. Try local checkout first, then fetch from remote."""
    branch = f"species/{dna}"
    out = Path(f"/tmp/species-{dna}.cypher")

    # Try local git first
    r = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{branch}:graph-state.cypher"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        out.write_text(r.stdout)
        return out

    # Try fetching the branch from remote
    print(f"  fetching species/{dna} from remote...")
    subprocess.run(
        ["git", "-C", str(REPO), "fetch", "origin", f"species/{dna}:species/{dna}"],
        capture_output=True, text=True,
    )
    r = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{branch}:graph-state.cypher"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        out.write_text(r.stdout)
        return out

    print(f"ERROR: cannot find species/{dna} locally or on remote", file=sys.stderr)
    sys.exit(1)


def verify(file_path: Path) -> bool:
    """Run verify-species-local.sh, return True if all checks pass."""
    r = subprocess.run(
        ["bash", str(REPO / "scripts" / "verify-species-local.sh"), file_path.stem.replace("species-", "")],
        capture_output=True, text=True,
    )
    # The script handles its own output. We check exit code only.
    return r.returncode == 0


def extract_body(content: str) -> str:
    """Strip the lineage commitment header. Body is what comes after the second close marker."""
    marker = "// ============================================================\n"
    # Find the close-marker that ends the species header
    # The header has a structure like:
    #   // ====
    #   // SPECIES LINEAGE COMMITMENT
    #   ...
    #   // ====
    first = content.find(marker)
    if first == -1:
        return content
    # Walk forward to the next close marker
    second = content.find(marker, first + len(marker))
    if second == -1:
        return content
    # The body starts after the second marker line
    after = second + len(marker)
    # Skip blank line
    if content[after:after+1] == "\n":
        after += 1
    return content[after:]


def restore(file_path: Path, mode: str = "restore"):
    """
    Apply the species body to the local FalkorDB.

    mode='restore' → wipe and replay
    mode='merge'   → MERGE on top of current state
    """
    content = file_path.read_text()
    body = extract_body(content)

    g = get_graph()

    if mode == "restore":
        print(f"  wiping local graph...")
        try:
            from falkordb import FalkorDB
            FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT).select_graph(GRAPH_NAME).delete()
        except Exception:
            pass
        g = get_graph()

    print(f"  replaying body ({len(body):,} bytes)...")
    executed = errors = 0
    for line in body.split("\n"):
        s = line.strip()
        if not s or s.startswith("//"):
            continue
        if s.endswith(";"):
            s = s[:-1]
        try:
            g.query(s)
            executed += 1
        except Exception:
            errors += 1

    print(f"  executed: {executed} statements, {errors} errors")
    return executed, errors


def update_being(dna: str):
    """Mark the local Being as expressing the new species."""
    try:
        query(f"""
        MERGE (b:Being {{node_id: 'being-mycelium'}})
        SET b.current_species = '{dna}',
            b.last_apply = timestamp()
        """)
    except Exception as e:
        print(f"  warn: could not update Being: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: apply-species.py <canonical|dna> [--merge]")
        sys.exit(1)

    arg = sys.argv[1]
    mode = "merge" if "--merge" in sys.argv else "restore"
    skip_verify = "--skip-verify" in sys.argv

    print(f"══ apply-species ══")
    dna = resolve_dna(arg)
    print(f"target: species/{dna}")

    print(f"\n[fetch] locating species file...")
    file_path = fetch_species_file(dna)
    print(f"  found: {file_path} ({file_path.stat().st_size:,} bytes)")

    if not skip_verify:
        print(f"\n[verify] running 6 cryptographic checks...")
        # Use the verify-species-local.sh script
        r = subprocess.run(
            ["bash", str(REPO / "scripts" / "verify-species-local.sh"), dna],
            capture_output=False, text=True,
        )
        if r.returncode != 0:
            print(f"\n✗ VERIFICATION FAILED. Refusing to apply.")
            print(f"  Your local graph is unchanged.")
            sys.exit(1)
    else:
        print("\n[verify] skipped (--skip-verify)")

    print(f"\n[apply] mode: {mode}")
    executed, errors = restore(file_path, mode)

    print(f"\n[update] marking Being.current_species = {dna}")
    update_being(dna)

    # Summary
    n = query("MATCH (n) RETURN count(n)")[0][0]
    e = query("MATCH ()-[r]->() RETURN count(r)")[0][0]
    print(f"\n🜂 SPECIES APPLIED")
    print(f"  current:  species/{dna}")
    print(f"  graph:    {n} nodes, {e} edges")
    return 0


if __name__ == "__main__":
    sys.exit(main())
