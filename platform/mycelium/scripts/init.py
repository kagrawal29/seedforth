#!/usr/bin/env python3
"""
init.py — Onboard a new team member into the living graph.

One command, six steps:
  1. Locate or install FalkorDB binary
  2. Start local FalkorDB instance
  3. Generate Ed25519 wallet (or load existing)
  4. Pull canonical species + verify
  5. Restore into local FalkorDB
  6. Register self as Witness in the graph

After init: you have a verified, signed, breathing copy of the team's graph.
"""

import getpass
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def step(n, total, msg):
    print(f"[{n}/{total}] {msg}")


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def have_falkordb():
    """Check if a local FalkorDB instance is reachable on localhost:6380."""
    try:
        from falkordb import FalkorDB
        db = FalkorDB(host="localhost", port=6380)
        db.list_graphs()
        return True
    except Exception:
        return False


def setup_local_falkordb():
    """If localhost:6380 isn't running, try to start one with the binary on the server."""
    if have_falkordb():
        return True

    # Check if /opt/falkordb exists locally
    falkordb_dir = Path("/opt/falkordb")
    if not falkordb_dir.exists():
        print("  ⚠ /opt/falkordb not found on this machine.")
        print("    To install: copy /opt/falkordb/{redis-server,falkordb.so} from server.")
        print("    Or: docker run -p 6380:6379 falkordb/falkordb:latest")
        return False

    # Try to start it
    data_dir = Path("/var/lib/falkordb/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    subprocess.Popen([
        str(falkordb_dir / "redis-server"),
        "--loadmodule", str(falkordb_dir / "falkordb.so"),
        "--dir", str(data_dir),
        "--port", "6380",
        "--daemonize", "yes",
        "--save", "60 1",
    ])
    time.sleep(2)
    return have_falkordb()


def generate_wallet(alias: str = None):
    """Generate or load Ed25519 wallet."""
    sys.path.insert(0, str(REPO / "scripts"))
    from lib.signing import keypair_from_token, public_key_hex
    import secrets

    wallet_path = Path.home() / ".asgard-wallet"
    if wallet_path.exists():
        with open(wallet_path) as f:
            wallet = json.load(f)
        return wallet, False  # not new

    if not alias:
        alias = input("Your alias (e.g., Banyan, Oak): ").strip() or "Anonymous"

    token = secrets.token_urlsafe(32)
    sk, pk = keypair_from_token(token)
    pk_hex = public_key_hex(pk)
    h = hashlib.sha256(token.encode()).hexdigest()

    wallet = {
        "alias": alias,
        "token": token,
        "hash": h,
        "public_key": pk_hex,
        "key_algorithm": "ed25519",
        "created_at": int(time.time() * 1000),
    }

    wallet_path.write_text(json.dumps(wallet, indent=2))
    os.chmod(wallet_path, 0o600)
    return wallet, True


def main():
    print("══ Mycelium init ══")
    print()
    total = 6

    # ── 1. FalkorDB ──
    step(1, total, "Checking local FalkorDB...")
    if setup_local_falkordb():
        print("       ✓ FalkorDB reachable on localhost:6380")
        os.environ["FALKORDB_HOST"] = "localhost"
        os.environ["FALKORDB_PORT"] = "6380"
    else:
        print("       ✗ FalkorDB unavailable.")
        print("       Falling back to remote FalkorDB at 5.78.206.137:6380")
        print("       (You'll be sharing a graph with the team — not ideal for solo work)")
        # Keep default env

    # ── 2. Wallet ──
    step(2, total, "Generating wallet...")
    wallet, is_new = generate_wallet()
    print(f"       alias:      {wallet['alias']}")
    print(f"       public_key: {wallet['public_key']}")
    if is_new:
        print(f"       ⚠  Wallet saved to {Path.home() / '.asgard-wallet'} (chmod 600)")
        print(f"          This is your private key. Back it up. Never share.")
    else:
        print(f"       (existing wallet loaded)")

    # ── 3. Pull canonical ──
    step(3, total, "Resolving canonical species...")
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location("ct", REPO / "scripts" / "canonical-tip.py")
        ct_mod = module_from_spec(spec)
        spec.loader.exec_module(ct_mod)
        tip = ct_mod.resolve_canonical()
        if not tip:
            print("       (no species found — this is genesis. Skipping restore.)")
            tip = None
    except Exception as e:
        print(f"       ⚠ {e}")
        tip = None

    if tip:
        print(f"       canonical: species/{tip['dna']} ({tip['sigs']} sigs)")

        # ── 4. Verify ──
        step(4, total, "Verifying species (6 cryptographic checks)...")
        r = subprocess.run(
            ["bash", str(REPO / "scripts" / "verify-species-local.sh"), tip["dna"]],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"       ✗ Verification FAILED")
            print(r.stdout[-500:])
            print()
            print("       Cannot proceed with init. Investigate and re-run.")
            sys.exit(1)
        print("       ✓ All checks pass")

        # ── 5. Restore ──
        step(5, total, "Restoring graph from canonical species...")
        r = subprocess.run(
            ["python3", str(REPO / "scripts" / "apply-species.py"), tip["dna"], "--skip-verify"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"       ✗ Restore failed: {r.stderr[-500:]}")
            sys.exit(1)
        # Show last lines
        for line in r.stdout.split("\n")[-6:]:
            print(f"       {line}")
    else:
        print("       (skipping verify + restore: no species)")

    # ── 6. Register self as Witness ──
    step(6, total, "Registering yourself as a Witness in the graph...")
    from graph import query
    try:
        query(f"""
        MERGE (p:Person {{alias: '{wallet['alias']}'}})
        SET p.public_key = '{wallet['public_key']}',
            p.token_hash = '{wallet['hash']}',
            p.key_algorithm = 'ed25519',
            p.active = true,
            p.joined_at = timestamp()
        """)
        query(f"""
        MERGE (w:Witness {{alias: '{wallet['alias']}'}})
        SET w.public_key = '{wallet['public_key']}',
            w.host = 'localhost',
            w.port = 6380,
            w.role = 'witness',
            w.active = true,
            w.last_heartbeat = timestamp(),
            w.reputation = 1.0,
            w.node_id = 'witness-{wallet['alias'].lower()}'
        """)
        print(f"       ✓ {wallet['alias']} is now a Witness")
    except Exception as e:
        print(f"       ⚠ Could not register: {e}")

    print()
    print("═══════════════════════════════════════")
    print(f"  You are now {wallet['alias']}.")
    print(f"  Your graph is living.")
    print("═══════════════════════════════════════")
    print()
    print("Next:")
    print("  mycelium status         # see the state of your graph")
    print("  mycelium ask \"...\"      # query in natural language")
    print("  mycelium mint           # crystallize your changes")
    print()


if __name__ == "__main__":
    main()
