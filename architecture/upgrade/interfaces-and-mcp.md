# Shared interfaces and remote MCP contract

Status: proposed. Covers U01–U16, A17, S05–S07. Compatibility not yet tested.

## Shared boundary

Board, Discord/WhatsApp adapters, and MCP submit requests to one application
boundary over Mycelium. Domain decisions execute through graph contracts. Each
surface preserves authenticated principal, effective scopes, correlation, and
expected aggregate version. No surface keeps an authoritative separate task store.

Read responses include data, as_of, evidence_status, projection_version, cursor,
and authorized evidence references. Successful empty data differs from failed or
unavailable reads. Authorization precedes search, summary generation, and caching.

Command acceptance returns request_id, accepted/denied/pending, scope, version,
and status reference. Acceptance is not execution success. Idempotency keys are
scoped to principal and request intent; reusing a key with different content fails.

## Minimal MCP surface proposal

| Capability | Contract |
|---|---|
| Discover | Authorized schema, project roots, relationship meanings, and readable properties |
| Read graph | Structured search/traversal/filter/projection with bounded results and provenance |
| Converse | Send to Delta with conversation ID, scope, context references, and optional request ID |
| Observe | Read conversation/sprint/task events after cursor and inspect durable outcomes |

This preserves broad graph exploration and conversation without exposing dozens
of business-specific tools. Graph reads use a restricted declarative request such
as root IDs, allowed edge types, maximum depth, fields, and filters. They are not
arbitrary Cypher. Admin diagnostics use a separately protected path if needed.

Conversation scope is server-bound. A model cannot change scope by adding a new
project to its text. Delta's response distinguishes explanation, proposed work,
pending approval, accepted execution, and completed result. A conversational client
can inspect decisions; privileged human approvals use a trusted confirmation path.

Charlie and Delta have separate conversation identities but shared accepted facts,
work, and decisions. Channels link through verified identity and authorization,
not merely matching a phone number or display name. Context summaries retain source
references and unresolved questions. A client reconnects to the durable conversation.

## Long work and transport lifecycle

Admit durable work quickly, returning a request/sprint reference. Background execution
is independent of a single MCP request or network stream. Cancelling a transport
request does not automatically abort accepted background work. Explicit abort is a
separate authorized domain request with recorded effects and final result.

The initial board can use REST plus event updates; MCP adapts the same read and
conversation services. Use cursor-based recovery and fresh snapshots after cursor
expiry. A slow client cannot stall graph execution. State caches are disposable;
cached content is scoped by principal/grant version and invalidated on revocation.

## Authentication research and proposed transport

Use authenticated HTTP with TLS. The inspected MCP 2025-11-25 authorization
specification describes OAuth-based resource-server authorization, protected-resource
metadata, and token audience validation. These inform the proposed gateway; the
deployment version and client support still need explicit qualification.
[Authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).

Streamable HTTP supports a server serving independent clients. Treat transport
sessions and domain sprint ownership separately. Select and pin a mutually supported
protocol version before implementation release; no claim of universal compatibility
or latest-version support is made here.
[Transport specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

Security research must cover confused-deputy behavior, token passthrough, and server
fetches of untrusted metadata. The gateway does not forward a client's token as a
provider credential. Network restrictions also apply to source and artifact fetches.
[MCP security guidance](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices).

## Compatibility qualification

Matrix per chosen client: supported protocol/version, authorization discovery,
login/consent, scope challenge, token refresh/revocation, tool/resource discovery,
structured read limits, long-work receipt, reconnect, cancellation semantics,
artifact links, and mobile operation. Test at least one desktop agent client and
one mobile browser workflow before calling remote operation ready.

An unsupported client receives a clear compatibility result; no downgrade to a
shared administrator key. Client selection is a review choice, not an assumption
that every product supporting some MCP features can use this deployment.

Acceptance: same task read through board and MCP has consistent version/evidence;
project member cannot escalate through conversation; disconnected client does not
lose accepted work; expired access cannot retrieve cached artifacts; stream loss
and explicit task abort remain distinct.
