"""Unipile API client for Delta.

Provides sync helpers for account management and async polling
for new LinkedIn account connections after hosted auth flows.

Credentials are read from env vars:
    UNIPILE_DSN    -- e.g. https://your-dsn.unipile.com:13000
    UNIPILE_API_KEY
"""

import asyncio
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger("delta.unipile")


def get_config() -> tuple[str, str]:
    """Return (dsn, api_key) from env vars. Raises ValueError if missing."""
    dsn = os.environ.get("UNIPILE_DSN", "").rstrip("/")
    api_key = os.environ.get("UNIPILE_API_KEY", "")
    missing = []
    if not dsn:
        missing.append("UNIPILE_DSN")
    if not api_key:
        missing.append("UNIPILE_API_KEY")
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)}")
    return dsn, api_key


def _request(method: str, url: str, api_key: str, body: dict | None = None) -> dict:
    """Make an HTTP request to the Unipile API. Returns parsed JSON dict."""
    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        logger.warning(f"Unipile HTTP {e.code} {method} {url}: {body_text[:200]}")
        raise


def list_accounts(dsn: str, api_key: str, provider: str = "LINKEDIN") -> list[dict]:
    """GET {dsn}/api/v1/accounts?provider={provider}. Returns items list."""
    url = f"{dsn}/api/v1/accounts?provider={provider}"
    data = _request("GET", url, api_key)
    return data.get("items", [])


def get_account(dsn: str, api_key: str, account_id: str) -> dict:
    """GET {dsn}/api/v1/accounts/{account_id}. Returns account dict."""
    url = f"{dsn}/api/v1/accounts/{account_id}"
    return _request("GET", url, api_key)


def generate_hosted_auth_link(dsn: str, api_key: str,
                               name: str = "", redirect_url: str = "") -> str:
    """POST {dsn}/api/v1/hosted/accounts/link.

    Creates a Unipile hosted auth URL for connecting a LinkedIn account.
    Returns the auth URL string from response["url"].
    """
    url = f"{dsn}/api/v1/hosted/accounts/link"
    body: dict = {
        "type": "create",
        "providers_filter": ["LINKEDIN"],
    }
    if name:
        body["name"] = name
    if redirect_url:
        body["redirect_url"] = redirect_url

    data = _request("POST", url, api_key, body=body)
    auth_url = data.get("url", "")
    if not auth_url:
        raise ValueError(f"Unipile hosted auth link response missing 'url': {data}")
    return auth_url


async def poll_for_new_account(
    dsn: str,
    api_key: str,
    known_ids: set[str],
    check_interval: int = 30,
    timeout: int = 900,
) -> Optional[dict]:
    """Async poll Unipile until a new LinkedIn account appears.

    Checks every check_interval seconds. Gives up after timeout seconds.
    Returns the new account dict or None on timeout.
    """
    elapsed = 0
    while elapsed < timeout:
        await asyncio.sleep(check_interval)
        elapsed += check_interval
        try:
            accounts = list_accounts(dsn, api_key)
        except Exception as e:
            logger.warning(f"poll_for_new_account: list_accounts failed: {e}")
            continue

        for account in accounts:
            if account.get("id") not in known_ids:
                logger.info(f"New Unipile account detected: {account.get('id')}")
                return account

    logger.info("poll_for_new_account: timeout reached, no new account found")
    return None


def account_display_name(account: dict) -> str:
    """Return a slug-safe display name from an account dict.

    Tries: name, username, id.
    Lowercases, replaces spaces and special chars with hyphens.
    Truncated to 20 characters.
    """
    raw = (
        account.get("name")
        or account.get("username")
        or account.get("id", "unknown")
    )
    slug = raw.lower().strip()
    # Replace any run of non-alphanumeric chars with a single hyphen
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:20]
