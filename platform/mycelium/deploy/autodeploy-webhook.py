#!/usr/bin/env python3
"""
GitHub webhook receiver for mycelium autodeploy.

Listens on 127.0.0.1:9091. Validates the X-Hub-Signature-256 HMAC header,
checks that the event is a push to main/master, then fires
`systemctl start mycelium-autodeploy-<target>.service` for each configured
target.

Zero external deps: stdlib only. Caddy fronts it with TLS + public URL.

Secret:       read from $MAVERICK_WEBHOOK_SECRET (set via systemd drop-in
              at /etc/systemd/system/maverick-autodeploy-webhook.service.d/
              secret.conf — never in the repo, never in journal).
Targets:      $MAVERICK_WEBHOOK_TARGETS (space-separated, e.g. "dev prod").
Port:         $MAVERICK_WEBHOOK_PORT (default 9091).

Failure modes:
  - Missing/invalid signature        → 401
  - Wrong event type (not push)      → 204 (no-op but acknowledged)
  - Push to non-main branch          → 204
  - systemctl start fails             → still 200 to GitHub; logged to journal
    (the 5-min timer fallback will retry regardless)

We intentionally do NOT run autodeploy synchronously — just fire the unit
and return 200 fast. GitHub retries on 5xx / timeout, so fast ACK avoids
duplicate deploys.

Design principle: this process has zero state. Crash-safe by construction.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BRANCHES_TO_DEPLOY = {"refs/heads/main", "refs/heads/master"}
MAX_BODY = 1 << 20  # 1 MiB — GitHub push events stay well under this

log = logging.getLogger("autodeploy-webhook")


def load_env() -> tuple[bytes, list[str], int]:
    secret = os.environ.get("MAVERICK_WEBHOOK_SECRET", "")
    if not secret:
        log.error("MAVERICK_WEBHOOK_SECRET not set — refusing to start")
        sys.exit(2)
    targets = os.environ.get("MAVERICK_WEBHOOK_TARGETS", "dev prod").split()
    port = int(os.environ.get("MAVERICK_WEBHOOK_PORT", "9091"))
    return secret.encode(), targets, port


def valid_signature(secret: bytes, body: bytes, header: str) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


def fire_autodeploy(targets: list[str]) -> None:
    for target in targets:
        unit = f"mycelium-autodeploy-{target}.service"
        try:
            subprocess.Popen(
                ["systemctl", "start", unit],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            log.info("fired %s", unit)
        except Exception as e:
            log.error("failed to fire %s: %s", unit, e)


def make_handler(secret: bytes, targets: list[str]):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:  # route to stdlib logger
            log.info("%s - %s", self.address_string(), fmt % args)

        def _respond(self, code: int, body: bytes = b"") -> None:
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/hooks/maverick-autodeploy":
                return self._respond(404, b"not found")
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._respond(400, b"bad length")
            body = self.rfile.read(length)
            sig = self.headers.get("X-Hub-Signature-256", "")
            if not valid_signature(secret, body, sig):
                log.warning("signature check failed")
                return self._respond(401, b"bad signature")
            event = self.headers.get("X-GitHub-Event", "")
            if event == "ping":
                return self._respond(200, b"pong")
            if event != "push":
                return self._respond(204)
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return self._respond(400, b"bad json")
            ref = payload.get("ref", "")
            if ref not in BRANCHES_TO_DEPLOY:
                log.info("ignoring push to %s", ref)
                return self._respond(204)
            fire_autodeploy(targets)
            return self._respond(200, b"autodeploy fired")

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                return self._respond(200, b"ok")
            return self._respond(404, b"not found")

    return Handler


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("MAVERICK_WEBHOOK_LOG", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    secret, targets, port = load_env()
    log.info("starting on 127.0.0.1:%d, targets=%s", port, targets)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(secret, targets))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
