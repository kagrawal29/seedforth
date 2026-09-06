#!/usr/bin/env python3
"""
Direct FalkorDB graph interface. No MCP. No middleware.

Usage:
    python3 scripts/graph.py "MATCH (n) RETURN count(n)"
    python3 scripts/graph.py --auth          # verify your wallet
    python3 scripts/graph.py --who           # who am I
    python3 scripts/graph.py --schema        # node types + counts
    python3 scripts/graph.py --ask "what decisions exist about auth"

Python:
    from scripts.graph import query, admin, whoami
    result = query("MATCH (n) RETURN count(n)")
    me = whoami()
"""

import hashlib
import json
import os
import sys
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("pip install falkordb", file=sys.stderr)
    sys.exit(1)

# Connection: local Docker or remote server
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"

_db = None
_graph = None


def graph():
    global _db, _graph
    if _graph is None:
        _db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        _graph = _db.select_graph(GRAPH_NAME)
    return _graph


def query(cypher: str) -> list:
    """Execute a read query. Returns result_set."""
    r = graph().query(cypher)
    return r.result_set


def admin(cypher: str) -> list:
    """Execute a write query. Auth via wallet hash."""
    me = whoami()
    if not me:
        raise PermissionError("No wallet found. Run: python3 scripts/wallet.py")
    return query(cypher)


def whoami() -> str | None:
    """Resolve current identity from wallet hash."""
    token = _get_token()
    if not token:
        return None
    h = hashlib.sha256(token.encode()).hexdigest()
    r = query(f"MATCH (p:Person {{token_hash: '{h}'}}) RETURN p.alias")
    if r and r[0][0]:
        return str(r[0][0])
    return None


def schema() -> dict:
    """Node types and counts."""
    r = query("MATCH (n) RETURN labels(n)[0] AS type, count(n) AS c ORDER BY c DESC")
    return {row[0]: row[1] for row in r}


def ask(question: str) -> list:
    """Search nodes by label text."""
    safe_q = question.replace("'", "\\'").lower()
    return query(
        f"MATCH (n) WHERE toLower(n.label) CONTAINS '{safe_q}' "
        f"RETURN labels(n)[0], n.node_id, n.label LIMIT 20"
    )


def neighborhood(node_id: str) -> list:
    """What connects to a node."""
    safe_id = node_id.replace("'", "\\'")
    return query(
        f"MATCH (n {{node_id: '{safe_id}'}})-[r]-(m) "
        f"RETURN type(r), labels(m)[0], m.node_id, m.label LIMIT 30"
    )


def _get_token() -> str | None:
    """Read token from wallet or env."""
    wallet_path = Path.home() / ".asgard-wallet"
    if wallet_path.exists():
        with open(wallet_path) as f:
            return json.load(f).get("token")
    return os.environ.get("ASGARD_GRAPH_TOKEN")


def _print_result(result_set):
    if not result_set:
        print("(empty)")
        return
    for row in result_set:
        if len(row) == 1:
            print(row[0])
        else:
            print("\t".join(str(x) for x in row))


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: graph.py <cypher> | --auth | --who | --schema | --ask <question>")
        sys.exit(1)

    if args[0] == "--auth":
        token = _get_token()
        if not token:
            print("No wallet. Run: python3 scripts/wallet.py")
            sys.exit(1)
        h = hashlib.sha256(token.encode()).hexdigest()
        r = query(f"MATCH (p:Person {{token_hash: '{h}'}}) RETURN p.alias, p.active")
        if r:
            print(f"Authenticated: {r[0][0]} (active: {r[0][1]})")
            print(f"Public key: {h}")
        else:
            print(f"Hash {h[:16]}... not found in graph")
            sys.exit(1)

    elif args[0] == "--who":
        me = whoami()
        print(me or "Unknown — no wallet match")

    elif args[0] == "--schema":
        for t, c in schema().items():
            print(f"  {c:>5}  {t}")

    elif args[0] == "--ask":
        q = " ".join(args[1:])
        _print_result(ask(q))

    elif args[0] == "--neighborhood":
        nid = args[1] if len(args) > 1 else ""
        _print_result(neighborhood(nid))

    else:
        cypher = " ".join(args)
        _print_result(query(cypher))


if __name__ == "__main__":
    main()
