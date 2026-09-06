# mycelium-ingest

GitHub webhook ingest pipeline for the mycelium knowledge graph.

**Read-only from GitHub. Writes only to the mycelium dev Neo4j graph.**

## Architecture

```
GitHub webhook
     |
     v (HTTPS POST)
POST /github/webhook          ← FastAPI, port 9090 (internal)
     |
     | HMAC-SHA256 verify
     v
In-process queue (thread-safe, max 1000)
     |
     v
normalizer.py                 ← pure functions, no I/O
     |
     v (list of MERGE statements)
graph_writer.py               ← neo4j driver → bolt://127.0.0.1:7688 (dev only)
     |
     v
Neo4j dev graph               ← :Commit :Branch :PullRequest :Issue :ReviewComment :Release :Author
```

## Supported events

| GitHub event | Neo4j nodes created |
|---|---|
| `push` | `:Commit`, `:Branch`, `:Author` |
| `pull_request` | `:PullRequest`, `:Branch`, `:Author` |
| `issues` | `:Issue`, `:Author` |
| `issue_comment` | `:ReviewComment`, `:Author` |
| `pull_request_review_comment` | `:ReviewComment`, `:Author` |
| `release` | `:Release` |

## Target repos (read-only ingest)

| Repo | Project tag |
|---|---|
| `Qubit-Capital/VC-AI-Assoicate` | `vc-ai-associate` |
| `Qubit-Capital/maverick-market-research` | `maverick-market-research` |
| `Qubit-Capital/maverick-marketing` | `maverick-marketing` |
| `Qubit-Capital/Maverick-Dev` | `maverick-dev` |
| `Qubit-Capital/maverick` | `maverick` |

## Security

- Validates `X-Hub-Signature-256` on every request. Unsigned requests are rejected with HTTP 401.
- Webhook secret stored at `/etc/mycelium-ingest/webhook.secret` (mode 640, root:mycelium-ingest). Never committed to git.
- Service user `mycelium-ingest` has no write access to any Qubit-Capital repo. The service has no GitHub credentials and makes no outbound GitHub API calls.
- **No writes to any Qubit-Capital repo are possible via this service.** The only outbound connection is to `bolt://127.0.0.1:7688` (dev Neo4j).

## Install

```bash
# On pulse-server, as root:
bash /opt/mycelium-ingest/services/mycelium-ingest/systemd/install-ingest.sh
```

## Running tests

```bash
cd services/mycelium-ingest
pip install pytest
python3 -m pytest tests/ -v
```

## Ingress (deferred)

The service is internal (port 9090, loopback only). GitHub requires a public HTTPS endpoint. Public ingress via Cloudflare Tunnel is a deferred step. See `docs/ingress-setup.md`.

Webhook registration (`scripts/register-webhooks.sh`) must NOT be run until ingress is live and the public URL is stable.

## Graph schema (new labels introduced)

```cypher
// Constraints (run once on dev Neo4j)
CREATE CONSTRAINT commit_sha IF NOT EXISTS
  FOR (c:Commit) REQUIRE (c.sha, c.project) IS NODE KEY;

CREATE CONSTRAINT branch_key IF NOT EXISTS
  FOR (b:Branch) REQUIRE (b.name, b.project) IS NODE KEY;

CREATE CONSTRAINT pr_key IF NOT EXISTS
  FOR (pr:PullRequest) REQUIRE (pr.number, pr.project) IS NODE KEY;

CREATE CONSTRAINT issue_key IF NOT EXISTS
  FOR (i:Issue) REQUIRE (i.number, i.project) IS NODE KEY;

CREATE CONSTRAINT review_comment_key IF NOT EXISTS
  FOR (rc:ReviewComment) REQUIRE (rc.id, rc.project) IS NODE KEY;

CREATE CONSTRAINT release_key IF NOT EXISTS
  FOR (r:Release) REQUIRE (r.tag, r.project) IS NODE KEY;

CREATE CONSTRAINT author_key IF NOT EXISTS
  FOR (a:Author) REQUIRE (a.login, a.project) IS NODE KEY;
```

Apply these via `mycelium shell` before the first webhook arrives.
