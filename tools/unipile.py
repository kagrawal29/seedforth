#!/usr/bin/env python3
"""
Unipile REST API client with built-in safety controls and CLI interface.

Claude Code calls this via Bash commands to interact with LinkedIn through
the Unipile API. All output is JSON to stdout for easy parsing.
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, date
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _env(name, default=None, required=False):
    val = os.environ.get(name, default)
    if required and not val:
        print(json.dumps({"error": f"Missing required env var: {name}"}), flush=True)
        sys.exit(1)
    return val


DATA_DIR = Path(_env("LINKEDIN_DATA_DIR", _env("ARIE_DATA_DIR", "data")))


def _ensure_data_dir():
    """Create data directory on first use. Deferred so import doesn't fail."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _audit_log(action: str, target: str, status: str, details: dict | None = None):
    """Append one line to the activity log."""
    _ensure_data_dir()
    entry = {
        "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "target": target,
        "status": status,
    }
    if details:
        entry["details"] = details
    log_path = DATA_DIR / "activity-log.jsonl"
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# SafetyController
# ---------------------------------------------------------------------------

class SafetyController:
    """Rate limiter and safety gate for all LinkedIn actions."""

    DAILY_CAPS = {
        "connection_request": 80,
        "message": 100,
        "profile_view": 100,
        "post": 3,
        "comment": 30,
        "reaction": 50,
        "search": 200,
    }

    DELAYS = {  # (min_seconds, max_seconds) between actions of same type
        "connection_request": (8, 15),
        "message": (5, 12),
        "profile_view": (3, 8),
        "comment": (5, 10),
        "reaction": (2, 5),
        "search": (2, 5),
    }

    WARMUP_SCHEDULE = {
        (0, 3): 0.10,
        (4, 7): 0.25,
        (8, 14): 0.50,
        (15, float("inf")): 1.0,
    }

    def __init__(self):
        _ensure_data_dir()
        self._usage_path = DATA_DIR / f"usage-{date.today().isoformat()}.json"
        self._usage = self._load_usage()

    # -- persistence --------------------------------------------------------

    def _load_usage(self) -> dict:
        if self._usage_path.exists():
            with open(self._usage_path) as f:
                return json.load(f)
        return {}

    def _save_usage(self):
        with open(self._usage_path, "w") as f:
            json.dump(self._usage, f, indent=2)

    # -- warm-up ------------------------------------------------------------

    def _get_warmup_multiplier(self) -> float:
        start_str = os.environ.get("ACCOUNT_START_DATE")
        if start_str:
            try:
                start = date.fromisoformat(start_str)
            except ValueError:
                start = date.today()
        else:
            start = date.today()

        days = (date.today() - start).days
        for (lo, hi), mult in self.WARMUP_SCHEDULE.items():
            if lo <= days <= hi:
                return mult
        return 1.0

    # -- autonomy -----------------------------------------------------------

    def _load_autonomy(self) -> dict:
        path = DATA_DIR / "autonomy.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    # -- public API ---------------------------------------------------------

    def check(self, action_type: str) -> dict:
        """Check whether an action is allowed right now.

        Returns dict with keys:
            allowed (bool), reason (str), delay (float),
            and optionally needs_approval (bool), action, details.
        """
        # Autonomy gate for write actions
        write_actions = {
            "connection_request", "message", "comment", "post", "reaction",
        }
        if action_type in write_actions:
            autonomy = self._load_autonomy()
            tier = autonomy.get(action_type, "auto")
            if tier == "blocked":
                return {"allowed": False, "reason": "action blocked by policy"}
            if tier == "approval":
                return {
                    "allowed": False,
                    "needs_approval": True,
                    "action": action_type,
                    "details": {"current_usage": self._usage.get(action_type, 0)},
                }
            # "auto" and "notify" both proceed (notify is logged after execution)

        # Daily cap check (with warm-up)
        cap = self.DAILY_CAPS.get(action_type)
        if cap is not None:
            multiplier = self._get_warmup_multiplier()
            effective_cap = int(cap * multiplier)
            used = self._usage.get(action_type, 0)
            if used >= effective_cap:
                return {
                    "allowed": False,
                    "reason": (
                        f"Daily cap reached for {action_type}: "
                        f"{used}/{effective_cap} (warmup {multiplier:.0%})"
                    ),
                    "delay": 0,
                }

        # Delay calculation
        delay_range = self.DELAYS.get(action_type)
        if delay_range:
            delay = random.uniform(delay_range[0], delay_range[1])
        else:
            delay = 0

        return {"allowed": True, "reason": "ok", "delay": delay}

    def record(self, action_type: str):
        """Record that an action was taken (increment today's counter)."""
        self._usage[action_type] = self._usage.get(action_type, 0) + 1
        self._save_usage()

    def get_usage(self) -> dict:
        """Return today's usage vs caps for all action types."""
        multiplier = self._get_warmup_multiplier()
        result = {}
        for action, cap in self.DAILY_CAPS.items():
            effective_cap = int(cap * multiplier)
            used = self._usage.get(action, 0)
            result[action] = {
                "used": used,
                "cap": effective_cap,
                "base_cap": cap,
                "warmup_multiplier": multiplier,
                "remaining": max(0, effective_cap - used),
            }
        return result


# ---------------------------------------------------------------------------
# UnipileClient
# ---------------------------------------------------------------------------

class UnipileClient:
    """Wraps the Unipile REST API with SafetyController enforcement.

    Correct API paths (verified against api31.unipile.com):
      POST /api/v1/linkedin/search?account_id=     -- search people/posts/companies
      GET  /api/v1/users/{id}?account_id=           -- view profile
      GET  /api/v1/users/me?account_id=              -- own profile
      GET  /api/v1/users/relations?account_id=       -- list connections
      GET  /api/v1/chats?account_id=                 -- list conversations
      GET  /api/v1/chats/{id}/messages?account_id=   -- read messages
      POST /api/v1/chats/{id}/messages               -- send message (body: account_id, text)
      POST /api/v1/chats                             -- new chat / connection request (body: account_id, attendees_ids, text)
      POST /api/v1/posts/{id}/comments               -- comment (body: account_id, text)
      GET  /api/v1/accounts                          -- list accounts

    Not available on current plan:
      - POST /api/v1/posts/{id}/reactions (404)
      - Invitations listing (404)
      - Analytics / notifications (404)
    """

    def __init__(self):
        self.base_url = _env("UNIPILE_DSN", required=True).rstrip("/")
        self.api_key = _env("UNIPILE_API_KEY", required=True)
        self.safety = SafetyController()
        self._account_id = _env("UNIPILE_ACCOUNT_ID") or None  # pre-set or cached after first lookup

    # -- HTTP helpers -------------------------------------------------------

    def _headers(self) -> dict:
        return {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }

    def _get_account_id(self) -> str:
        """Get the Unipile account ID (cached after first call)."""
        if self._account_id:
            return self._account_id
        accounts = self._request("GET", "/api/v1/accounts")
        if isinstance(accounts, dict) and not accounts.get("error"):
            items = accounts.get("items", accounts.get("data", []))
            if isinstance(items, list) and items:
                self._account_id = items[0].get("id", "")
        return self._account_id or ""

    def _request(self, method: str, path: str, body: dict | None = None,
                 params: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(
                method, url, headers=self._headers(),
                json=body, params=params, timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as exc:
            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text
            return {"error": str(exc), "status_code": exc.response.status_code,
                    "detail": detail}
        except requests.exceptions.RequestException as exc:
            return {"error": str(exc)}

    def _guarded(self, action_type: str, target: str,
                 method: str, path: str,
                 body: dict | None = None,
                 params: dict | None = None) -> dict:
        """Run safety check, apply delay, execute request, record, audit."""
        gate = self.safety.check(action_type)
        if not gate["allowed"]:
            _audit_log(action_type, target, "blocked", gate)
            return gate

        delay = gate.get("delay", 0)
        if delay > 0:
            time.sleep(delay)

        result = self._request(method, path, body=body, params=params)

        status = "error" if "error" in result else "success"
        self.safety.record(action_type)

        # Notify tier: log but still return result
        autonomy = self.safety._load_autonomy()
        tier = autonomy.get(action_type, "auto")
        if tier == "notify":
            _audit_log(action_type, target, f"{status}/notify", result)
        else:
            _audit_log(action_type, target, status, result)

        return result

    # -- API methods --------------------------------------------------------

    def search_profiles(self, keywords: str, limit: int = 10) -> dict:
        """POST /api/v1/linkedin/search -- search for people on LinkedIn."""
        aid = self._get_account_id()
        return self._guarded(
            "search", keywords,
            "POST", "/api/v1/linkedin/search",
            body={"api": "classic", "category": "people", "keywords": keywords},
            params={"account_id": aid} if aid else None,
        )

    def search_posts(self, keywords: str, limit: int = 10) -> dict:
        """POST /api/v1/linkedin/search -- search for posts on LinkedIn."""
        aid = self._get_account_id()
        return self._guarded(
            "search", keywords,
            "POST", "/api/v1/linkedin/search",
            body={"api": "classic", "category": "posts", "keywords": keywords},
            params={"account_id": aid} if aid else None,
        )

    def view_profile(self, provider_id: str) -> dict:
        """GET /api/v1/users/{id} -- view a LinkedIn profile."""
        aid = self._get_account_id()
        return self._guarded(
            "profile_view", provider_id,
            "GET", f"/api/v1/users/{provider_id}",
            params={"account_id": aid} if aid else None,
        )

    def get_own_profile(self) -> dict:
        """GET /api/v1/users/me -- view own LinkedIn profile."""
        aid = self._get_account_id()
        return self._guarded(
            "search", "own_profile",
            "GET", "/api/v1/users/me",
            params={"account_id": aid} if aid else None,
        )

    def get_connections(self, limit: int = 50) -> dict:
        """GET /api/v1/users/relations -- list LinkedIn connections."""
        aid = self._get_account_id()
        return self._guarded(
            "search", "connections",
            "GET", "/api/v1/users/relations",
            params={"account_id": aid, "limit": limit} if aid else {"limit": limit},
        )

    def send_connection(self, provider_id: str, message: str = "") -> dict:
        """POST /api/v1/chats -- send connection request via new chat.

        Note: May return 403 if Unipile plan doesn't support this.
        """
        aid = self._get_account_id()
        body = {"account_id": aid, "attendees_ids": [provider_id]}
        if message:
            body["text"] = message
        return self._guarded(
            "connection_request", provider_id,
            "POST", "/api/v1/chats",
            body=body,
        )

    def get_conversations(self, limit: int = 20) -> dict:
        """GET /api/v1/chats -- list conversations."""
        aid = self._get_account_id()
        return self._guarded(
            "search", "conversations",
            "GET", "/api/v1/chats",
            params={"account_id": aid, "limit": limit} if aid else {"limit": limit},
        )

    def get_messages(self, chat_id: str, limit: int = 20) -> dict:
        """GET /api/v1/chats/{id}/messages -- read messages in a conversation."""
        aid = self._get_account_id()
        params = {"limit": limit}
        if aid:
            params["account_id"] = aid
        return self._guarded(
            "search", chat_id,
            "GET", f"/api/v1/chats/{chat_id}/messages",
            params=params,
        )

    def send_message(self, chat_id: str, text: str) -> dict:
        """POST /api/v1/chats/{id}/messages -- send message in existing chat."""
        aid = self._get_account_id()
        return self._guarded(
            "message", chat_id,
            "POST", f"/api/v1/chats/{chat_id}/messages",
            body={"account_id": aid, "text": text},
        )

    def comment(self, post_id: str, text: str) -> dict:
        """POST /api/v1/posts/{id}/comments -- comment on a post."""
        aid = self._get_account_id()
        return self._guarded(
            "comment", post_id,
            "POST", f"/api/v1/posts/{post_id}/comments",
            body={"account_id": aid, "text": text},
        )

    def react(self, post_id: str, reaction_type: str = "LIKE") -> dict:
        """POST /api/v1/posts/{id}/reactions -- react to a post.

        Note: Returns 404 on current Unipile plan.
        """
        aid = self._get_account_id()
        return self._guarded(
            "reaction", post_id,
            "POST", f"/api/v1/posts/{post_id}/reactions",
            body={"account_id": aid, "reaction_type": reaction_type},
        )

    def get_accounts(self) -> dict:
        """GET /api/v1/accounts -- list connected Unipile accounts.

        Not rate-limited (admin operation, not a LinkedIn action).
        """
        return self._request("GET", "/api/v1/accounts")

    def create_connect_link(self, name: str = "user") -> dict:
        """POST /api/v1/hosted/accounts/link -- generate hosted auth URL.

        Returns a URL that a user can click to connect their LinkedIn account
        through Unipile's hosted authentication page.
        """
        from datetime import timedelta
        expires = (datetime.utcnow() + timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
        body = {
            "type": "create",
            "providers": ["LINKEDIN"],
            "api_url": self.base_url,
            "expiresOn": expires,
            "name": name,
            "success_redirect_url": "https://www.linkedin.com/feed/",
            "failure_redirect_url": "https://www.linkedin.com/",
        }
        result = self._request("POST", "/api/v1/hosted/accounts/link", body=body)
        _audit_log("connect_link", name, "success" if "url" in result else "error", result)
        return result

    def disconnect_account(self, account_id: str) -> dict:
        """DELETE /api/v1/accounts/{id} -- remove a connected account."""
        result = self._request("DELETE", f"/api/v1/accounts/{account_id}")
        _audit_log("disconnect", account_id, "success" if "error" not in result else "error", result)
        return result

    def usage(self) -> dict:
        return self.safety.get_usage()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _output(data):
    print(json.dumps(data, indent=2, default=str), flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Unipile LinkedIn API client with safety controls",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # search-profiles
    sp = sub.add_parser("search-profiles", help="Search LinkedIn profiles")
    sp.add_argument("--keywords", required=True, help="Search keywords")
    sp.add_argument("--limit", type=int, default=10, help="Max results")

    # search-posts
    sp = sub.add_parser("search-posts", help="Search LinkedIn posts")
    sp.add_argument("--keywords", required=True, help="Search keywords")
    sp.add_argument("--limit", type=int, default=10, help="Max results")

    # view-profile
    sp = sub.add_parser("view-profile", help="View a LinkedIn profile")
    sp.add_argument("--provider-id", required=True, help="Profile provider ID")

    # my-profile
    sub.add_parser("my-profile", help="View own LinkedIn profile")

    # connections
    sp = sub.add_parser("connections", help="List LinkedIn connections")
    sp.add_argument("--limit", type=int, default=50, help="Max results")

    # connect
    sp = sub.add_parser("connect", help="Send connection request (may require higher Unipile plan)")
    sp.add_argument("--provider-id", required=True, help="Profile provider ID")
    sp.add_argument("--message", default="", help="Connection message")

    # conversations
    sp = sub.add_parser("conversations", help="List conversations")
    sp.add_argument("--limit", type=int, default=20, help="Max results")

    # messages
    sp = sub.add_parser("messages", help="Get messages in a conversation")
    sp.add_argument("--chat-id", required=True, help="Chat ID")
    sp.add_argument("--limit", type=int, default=20, help="Max messages")

    # send-message
    sp = sub.add_parser("send-message", help="Send a message")
    sp.add_argument("--chat-id", required=True, help="Chat ID")
    sp.add_argument("--text", required=True, help="Message text")

    # comment
    sp = sub.add_parser("comment", help="Comment on a post")
    sp.add_argument("--post-id", required=True, help="Post ID")
    sp.add_argument("--text", required=True, help="Comment text")

    # react
    sp = sub.add_parser("react", help="React to a post (may not be available)")
    sp.add_argument("--post-id", required=True, help="Post ID")
    sp.add_argument("--type", default="LIKE", help="Reaction type")

    # accounts
    sub.add_parser("accounts", help="List connected accounts")

    # connect-linkedin
    sp = sub.add_parser("connect-linkedin", help="Generate a link for connecting a LinkedIn account")
    sp.add_argument("--name", default="user", help="Label for the account (e.g. user's name)")

    # disconnect-account
    sp = sub.add_parser("disconnect-account", help="Remove a connected account")
    sp.add_argument("--account-id", required=True, help="Account ID to disconnect")

    # usage
    sub.add_parser("usage", help="Show today's usage stats")

    args = parser.parse_args()

    try:
        client = UnipileClient()
    except SystemExit:
        # _env already printed the error JSON
        return

    try:
        if args.command == "search-profiles":
            _output(client.search_profiles(args.keywords, args.limit))
        elif args.command == "search-posts":
            _output(client.search_posts(args.keywords, args.limit))
        elif args.command == "view-profile":
            _output(client.view_profile(args.provider_id))
        elif args.command == "my-profile":
            _output(client.get_own_profile())
        elif args.command == "connections":
            _output(client.get_connections(args.limit))
        elif args.command == "connect":
            _output(client.send_connection(args.provider_id, args.message))
        elif args.command == "conversations":
            _output(client.get_conversations(args.limit))
        elif args.command == "messages":
            _output(client.get_messages(args.chat_id, args.limit))
        elif args.command == "send-message":
            _output(client.send_message(args.chat_id, args.text))
        elif args.command == "comment":
            _output(client.comment(args.post_id, args.text))
        elif args.command == "react":
            _output(client.react(args.post_id, args.type))
        elif args.command == "accounts":
            _output(client.get_accounts())
        elif args.command == "connect-linkedin":
            _output(client.create_connect_link(args.name))
        elif args.command == "disconnect-account":
            _output(client.disconnect_account(args.account_id))
        elif args.command == "usage":
            _output(client.usage())
    except Exception as exc:
        _output({"error": str(exc)})
        sys.exit(1)


if __name__ == "__main__":
    main()
