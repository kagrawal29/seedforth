# SeedForth control boundary

Implementation in progress; not yet deployed as a human or MCP service.

Domain operations are authored under platform/mycelium/graph/control and promoted
as ControlOperation:CypherAtom records. The external transport verifies the exact
release source hash before executing graph-resident code. Caller identity/scope
must come from authenticated server context; they are not model-authorized values.

The current implementation includes scoped read/create/schedule/hold/claim/renew/
finish/review transitions, expired-attempt reconciliation, durable attempts, and
independent verification gates. A loopback HTTP gateway and responsive board use
external expiring per-principal credentials and live graph grants. No arbitrary
Cypher, credential provisioning, or worker execution is exposed to that gateway.
External tool execution, provider grants, public TLS/OAuth/MCP, sensing, and a full
human console remain separate delivery work. This is not useful autonomy yet.

Launch with `PYTHONPATH=platform python3 -m control.server`. Supply
CONTROL_CREDENTIALS_FILE externally (mode 0600 or 0640), containing an array of
objects with sha256 (opaque bearer token digest), principal, scopes, and a zoned
ISO expires_at. Tokens must have at least 32 characters and must never enter Git.
NEO4J_PASSWORD and optional CONTROL_NEO4J_URL are external runtime settings.
The server binds only 127.0.0.1:8787. Do not publish it directly to the internet.

`python3 -m control.migrate --endpoint URL --revision SHA` explicitly applies the
authored additive schema, verified pilot identities, and operation generation.
First validate on a restored snapshot. It does not switch any scheduler or enable
pilot execution. Graph operation source changes require a new tested promotion.

Use only the dedicated disposable endpoint for integration tests:

```text
CONTROL_TEST_URL=http://127.0.0.1:27474 python -m pytest platform/integration-tests
```

Test fixtures have random scopes and never load production credentials. Bootstrap
tests apply authored schema twice and exercise actual concurrent Neo4j transactions.
