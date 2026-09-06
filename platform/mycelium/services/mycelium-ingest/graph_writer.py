"""
graph_writer.py — applies normalised MERGE statements to the mycelium Neo4j graph.

Target: bolt://127.0.0.1:7688 (dev Neo4j).  NEVER targets prod (7687).
Credentials: loaded from /root/.mycelium-secrets (key neo4j_dev_password).

IMPORTANT: this module contains ZERO GitHub API calls.  It only writes to Neo4j.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger("mycelium-ingest.graph_writer")

# ---------------------------------------------------------------------------
# Neo4j connection settings (dev only)
# ---------------------------------------------------------------------------
_DEV_BOLT_URI = os.environ.get("NEO4J_DEV_URI", "bolt://127.0.0.1:7688")
_SECRETS_PATH = Path(os.environ.get("MYCELIUM_SECRETS_PATH", "/root/.mycelium-secrets"))


def _load_creds() -> tuple[str, str]:
    """Return (user, password) for dev Neo4j.  Reads from secrets file."""
    user = os.environ.get("NEO4J_DEV_USER", "neo4j")
    password = os.environ.get("NEO4J_DEV_PASSWORD", "")

    if not password and _SECRETS_PATH.exists():
        for line in _SECRETS_PATH.read_text().splitlines():
            line = line.strip()
            if line.startswith("neo4j_dev_password"):
                _, _, val = line.partition("=")
                password = val.strip().strip('"').strip("'")
                break

    if not password:
        # fallback for local dev
        password = os.environ.get("NEO4J_PASSWORD", "localtest12")

    return user, password


# ---------------------------------------------------------------------------
# GraphWriter
# ---------------------------------------------------------------------------

class GraphWriter:
    """Applies MergeStatements to the dev Neo4j instance."""

    def __init__(self):
        try:
            from neo4j import GraphDatabase  # type: ignore
        except ImportError as exc:
            raise RuntimeError("neo4j package not installed. Run: pip install neo4j") from exc

        user, password = _load_creds()
        self._driver = GraphDatabase.driver(
            _DEV_BOLT_URI,
            auth=(user, password),
            connection_timeout=10,
            max_connection_lifetime=300,
        )
        log.info("GraphWriter connected to %s as %s", _DEV_BOLT_URI, user)

    def close(self):
        self._driver.close()

    def apply(self, statements: list[dict[str, Any]]):
        """Execute a list of MergeStatements in a single transaction."""
        with self._driver.session() as session:
            with session.begin_transaction() as tx:
                for stmt in statements:
                    tx.run(stmt["cypher"], **stmt["params"])
                tx.commit()
        log.debug("Applied %d statement(s)", len(statements))
