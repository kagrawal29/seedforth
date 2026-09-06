"""
Ed25519 signing primitives for the graph's trustless layer.

A wallet derives an Ed25519 keypair from its token (SHA-256 seed).
Public keys are published to Person nodes. Signatures are verified
offline by anyone holding the pubkey + file + signature.
"""

import hashlib
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


def seed_from_token(token: str) -> bytes:
    """Deterministic 32-byte Ed25519 seed from a wallet token."""
    return hashlib.sha256(token.encode()).digest()


def keypair_from_token(token: str):
    """Derive Ed25519 (private, public) from a wallet token. Deterministic."""
    seed = seed_from_token(token)
    sk = Ed25519PrivateKey.from_private_bytes(seed)
    pk = sk.public_key()
    return sk, pk


def public_key_hex(pk: Ed25519PublicKey) -> str:
    """32-byte Ed25519 public key as 64-char hex."""
    raw = pk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex()


def load_pubkey_hex(hex_str: str) -> Ed25519PublicKey:
    raw = bytes.fromhex(hex_str)
    return Ed25519PublicKey.from_public_bytes(raw)


def sign_bytes(sk: Ed25519PrivateKey, data: bytes) -> str:
    """Sign arbitrary bytes. Returns 128-char hex signature."""
    sig = sk.sign(data)
    return sig.hex()


def verify_bytes(pk_hex: str, data: bytes, sig_hex: str) -> bool:
    """Verify signature. Returns True/False, never raises."""
    try:
        pk = load_pubkey_hex(pk_hex)
        pk.verify(bytes.fromhex(sig_hex), data)
        return True
    except (InvalidSignature, ValueError, Exception):
        return False


def load_wallet(path: Path = None) -> dict:
    """Load wallet from ~/.asgard-wallet."""
    if path is None:
        path = Path.home() / ".asgard-wallet"
    if not path.exists():
        raise FileNotFoundError(f"No wallet at {path}")
    with open(path) as f:
        return json.load(f)


def wallet_signer(wallet: dict = None):
    """Return (signer_pubkey_hex, sign_fn) ready to use."""
    if wallet is None:
        wallet = load_wallet()
    token = wallet["token"]
    sk, pk = keypair_from_token(token)
    pk_hex = public_key_hex(pk)
    return pk_hex, lambda data: sign_bytes(sk, data)
