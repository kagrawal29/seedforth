"""Per-user account connection management via Composio SDK."""

import logging
import os
from typing import Optional

logger = logging.getLogger("delta.connections")


def _get_client():
    """Get Composio client, returns None if API key not set."""
    api_key = os.environ.get("COMPOSIO_API_KEY", "")
    if not api_key:
        logger.warning("COMPOSIO_API_KEY not set")
        return None
    from composio import Composio
    return Composio(api_key=api_key)


def initiate_connection(user_id: str, toolkit: str) -> dict:
    """Start OAuth flow for a user to connect a toolkit.

    Returns {"redirect_url": str, "connection_id": str, "status": str}
    or {"error": str} on failure.
    """
    client = _get_client()
    if not client:
        return {"error": "Composio API key not configured"}
    try:
        entity = client.get_entity(user_id)
        req = entity.initiate_connection(app_name=toolkit)
        return {
            "redirect_url": req.redirectUrl,
            "connection_id": req.connectedAccountId,
            "status": req.connectionStatus,
        }
    except Exception as e:
        logger.warning(f"Failed to initiate connection for {user_id}/{toolkit}: {e}")
        return {"error": str(e)}


def check_status(connection_id: str) -> str:
    """Check connection status. Returns 'ACTIVE', 'INITIATED', 'FAILED', or 'ERROR'."""
    client = _get_client()
    if not client:
        return "ERROR"
    try:
        conn = client.connected_accounts.get(connection_id=connection_id)
        return conn.status
    except Exception as e:
        logger.warning(f"Failed to check connection {connection_id}: {e}")
        return "ERROR"


def list_connections(user_id: str) -> list[dict]:
    """List all connections for a user."""
    client = _get_client()
    if not client:
        return []
    try:
        entity = client.get_entity(user_id)
        conns = entity.get_connections()
        return [
            {"app": c.appName, "status": c.status, "id": c.id}
            for c in conns
        ]
    except Exception as e:
        logger.warning(f"Failed to list connections for {user_id}: {e}")
        return []


def get_active_connection(user_id: str, toolkit: str) -> Optional[str]:
    """Get the connection ID for an active toolkit, or None."""
    for conn in list_connections(user_id):
        if conn["app"].lower() == toolkit.lower() and conn["status"] == "ACTIVE":
            return conn["id"]
    return None
