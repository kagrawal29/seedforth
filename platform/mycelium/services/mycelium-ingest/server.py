"""
mycelium-ingest: GitHub webhook receiver.

Endpoint: POST /github/webhook
- Validates X-Hub-Signature-256 HMAC
- Enqueues valid payloads for normalisation + graph write
- NEVER writes back to GitHub (read-only ingest)
"""

import hashlib
import hmac
import json
import logging
import os
import queue
import threading
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request, Response
import uvicorn

from normalizer import normalize
from graph_writer import GraphWriter

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("mycelium-ingest")

# ---------------------------------------------------------------------------
# Webhook secret
# ---------------------------------------------------------------------------
SECRET_PATH = Path(os.environ.get("WEBHOOK_SECRET_PATH", "/etc/mycelium-ingest/webhook.secret"))

def _load_secret() -> bytes:
    path = SECRET_PATH
    if not path.exists():
        raise RuntimeError(f"Webhook secret not found at {path}. Run install-ingest.sh first.")
    return path.read_bytes().strip()

# Load once at startup; kept in module scope so tests can monkey-patch.
WEBHOOK_SECRET: bytes = b""  # populated in lifespan

# ---------------------------------------------------------------------------
# In-process work queue
# ---------------------------------------------------------------------------
_queue: queue.Queue = queue.Queue(maxsize=1000)

def _worker():
    writer = GraphWriter()
    while True:
        item = _queue.get()
        if item is None:
            break
        event_type, payload, project = item
        try:
            merges = normalize(event_type, payload, project)
            if merges:
                writer.apply(merges)
                log.info("Applied %d merge(s) for event=%s project=%s", len(merges), event_type, project)
        except Exception as exc:
            log.exception("Failed to process event=%s project=%s: %s", event_type, project, exc)
        finally:
            _queue.task_done()

# ---------------------------------------------------------------------------
# Repo → project mapping (READ-ONLY — these repos are never written to)
# ---------------------------------------------------------------------------
REPO_PROJECT_MAP: dict[str, str] = {
    "Qubit-Capital/VC-AI-Assoicate":           "vc-ai-associate",
    "Qubit-Capital/maverick-market-research":  "maverick-market-research",
    "Qubit-Capital/maverick-marketing":        "maverick-marketing",
    "Qubit-Capital/Maverick-Dev":              "maverick-dev",
    "Qubit-Capital/maverick":                  "maverick",
}

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="mycelium-ingest", version="1.0.0")

@app.on_event("startup")
def _startup():
    global WEBHOOK_SECRET
    WEBHOOK_SECRET = _load_secret()
    t = threading.Thread(target=_worker, daemon=True, name="ingest-worker")
    t.start()
    log.info("mycelium-ingest started; secret loaded from %s", SECRET_PATH)


def _verify_signature(body: bytes, sig_header: str) -> bool:
    """Validate X-Hub-Signature-256 header against the shared secret."""
    if not sig_header or not sig_header.startswith("sha256="):
        return False
    expected = hmac.new(WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    received = sig_header[len("sha256="):]
    return hmac.compare_digest(expected, received)


@app.post("/github/webhook", status_code=202)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(default=""),
    x_github_event: str = Header(default=""),
):
    body = await request.body()

    # --- HMAC verification (reject before any processing) ---
    if not _verify_signature(body, x_hub_signature_256):
        log.warning("Invalid signature on incoming webhook (event=%s)", x_github_event)
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # --- Resolve project name from repo ---
    repo_full = (payload.get("repository") or {}).get("full_name", "")
    project = REPO_PROJECT_MAP.get(repo_full)
    if not project:
        log.info("Ignoring event from unregistered repo: %s", repo_full)
        return Response(status_code=204)

    # --- Enqueue (non-blocking; drop if full) ---
    try:
        _queue.put_nowait((x_github_event, payload, project))
    except queue.Full:
        log.error("Ingest queue full — dropping event=%s project=%s", x_github_event, project)
        raise HTTPException(status_code=503, detail="Queue full, retry later")

    return {"status": "queued", "event": x_github_event, "project": project}


@app.get("/health")
def health():
    return {"status": "ok", "queue_size": _queue.qsize()}


if __name__ == "__main__":
    port = int(os.environ.get("INGEST_PORT", "9090"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")
