#!/usr/bin/env python3
"""Minimal HTTP embedding proxy that forwards to a local Ollama.

Contract:
  POST /embed  body: {"text": "..."}  -> 200 {"vector": [...], "model": "...", "dim": N}
  GET  /health                         -> 200 {"status":"ok", "ollama":"up"} or 503
  Any other verb / path                -> 404 or 405

Design:
- Read-only: only GET /health and POST /embed are accepted. Everything else refused.
- No auth — this sits behind a UFW rule, intended for internal CI + mycelium CLI reads.
- Single-file stdlib (http.server), so the deploy has zero pip deps.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_ADDR = os.environ.get("LISTEN_ADDR", "0.0.0.0:7701")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "nomic-embed-text")
READ_ONLY = os.environ.get("READ_ONLY", "1") == "1"
MAX_BODY = 64 * 1024  # 64 KiB embed text cap


def _ollama_embed(text: str) -> list[float]:
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        payload = json.loads(r.read())
    vec = payload.get("embedding")
    if not isinstance(vec, list) or not vec:
        raise ValueError("ollama returned empty embedding")
    return vec


def _ollama_health() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = "mycelium-embed/1.0"

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # systemd captures stderr; keep the format minimal
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    def do_GET(self):
        if self.path == "/health":
            ok = _ollama_health()
            self._json(200 if ok else 503, {"status": "ok" if ok else "degraded", "ollama": "up" if ok else "down", "model": OLLAMA_MODEL})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/embed":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > MAX_BODY:
            self._json(413, {"error": "invalid content-length"})
            return
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return
        text = body.get("text")
        if not isinstance(text, str) or not text.strip():
            self._json(400, {"error": "text field required"})
            return
        try:
            vec = _ollama_embed(text)
        except Exception as e:  # noqa: BLE001
            self._json(502, {"error": "ollama failed", "detail": str(e)[:200]})
            return
        self._json(200, {"vector": vec, "model": OLLAMA_MODEL, "dim": len(vec)})

    def do_PUT(self):
        self._json(405, {"error": "read-only"})

    def do_DELETE(self):
        self._json(405, {"error": "read-only"})


def main() -> int:
    host, _, port = LISTEN_ADDR.rpartition(":")
    if not host:
        host = "0.0.0.0"
    server = ThreadingHTTPServer((host, int(port)), Handler)
    sys.stderr.write(f"mycelium-embed listening on {host}:{port} -> {OLLAMA_URL} ({OLLAMA_MODEL})\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
