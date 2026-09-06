#!/usr/bin/env python3
"""
ed25519 signing sidecar for the mycelium chain layer.

Three subcommands:

  keygen    --alias <witness> [--key-dir ~/.mycelium]
                Generates a fresh ed25519 keypair. Writes the private key to
                <key-dir>/witness-<alias>.key with mode 600. Prints the hex
                public key to stdout so the caller can register it on the
                Witness node.

  sign      --alias <witness> --message <payload> [--key-dir ~/.mycelium]
                Reads the private key, signs the payload, prints hex signature
                to stdout.

  verify    --public-key <hex> --message <payload> --signature <hex>
                Verifies. Exits 0 if valid, 1 if not.

Payload convention for species signing:
  payload = manifest_root + '|' + parent_dna + '|' + species_node_id
(parent_dna uses the literal string 'genesis' for genesis species where
parent is null.)

Keeps signing + verification outside the graph so private keys never enter
Neo4j. The graph stores only public keys and signatures.
"""

import argparse
import json
import os
import stat
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


DEFAULT_KEY_DIR = Path.home() / ".mycelium"


def key_path(key_dir: Path, alias: str) -> Path:
    return key_dir / f"witness-{alias}.key"


def cmd_keygen(args: argparse.Namespace) -> int:
    kd = Path(args.key_dir).expanduser()
    kd.mkdir(mode=0o700, exist_ok=True)
    kp = key_path(kd, args.alias)
    if kp.exists() and not args.force:
        print(f"error: {kp} already exists (use --force to overwrite)", file=sys.stderr)
        return 1
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    kp.write_bytes(priv_bytes)
    os.chmod(kp, stat.S_IRUSR | stat.S_IWUSR)
    pub_hex = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()
    print(pub_hex)
    return 0


def cmd_sign(args: argparse.Namespace) -> int:
    kd = Path(args.key_dir).expanduser()
    kp = key_path(kd, args.alias)
    if not kp.exists():
        print(f"error: no key for witness {args.alias} at {kp}", file=sys.stderr)
        return 1
    priv = Ed25519PrivateKey.from_private_bytes(kp.read_bytes())
    sig = priv.sign(args.message.encode("utf-8"))
    print(sig.hex())
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    try:
        pub_bytes = bytes.fromhex(args.public_key)
        sig_bytes = bytes.fromhex(args.signature)
    except ValueError as exc:
        print(f"error: hex decode failed: {exc}", file=sys.stderr)
        return 1
    pub = Ed25519PublicKey.from_public_bytes(pub_bytes)
    try:
        pub.verify(sig_bytes, args.message.encode("utf-8"))
    except InvalidSignature:
        print("invalid", file=sys.stderr)
        return 1
    print("valid")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="mycelium ed25519 signing sidecar")
    sub = parser.add_subparsers(dest="cmd", required=True)

    k = sub.add_parser("keygen")
    k.add_argument("--alias", required=True)
    k.add_argument("--key-dir", default=str(DEFAULT_KEY_DIR))
    k.add_argument("--force", action="store_true")
    k.set_defaults(func=cmd_keygen)

    s = sub.add_parser("sign")
    s.add_argument("--alias", required=True)
    s.add_argument("--message", required=True)
    s.add_argument("--key-dir", default=str(DEFAULT_KEY_DIR))
    s.set_defaults(func=cmd_sign)

    v = sub.add_parser("verify")
    v.add_argument("--public-key", required=True)
    v.add_argument("--message", required=True)
    v.add_argument("--signature", required=True)
    v.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
