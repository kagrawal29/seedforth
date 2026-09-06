// @node_id: schema-querytrace
// @label: "QueryTrace Schema"
// @kind: schema
// @description: Constraints and indexes for :QueryTrace nodes (graph-native query tracing — Track C wi-qt-01)
// ============================================================================
// wi-qt-01: :QueryTrace schema + constraints + indexes
//
// QueryTrace captures every `maverick ask`, `maverick shell`, and other read/write
// invocations with structured metadata for analytics, debugging, and audit.
//
// Emission:
//   - Client-side (Go binary): fire-and-forget HTTP POST to :7702 (trace-ingest service)
//   - Server-side (trace-ingest.py): validates, then writes via admin creds
//   - Storage: idempotent MERGE on node_id (derived from timestamp + user + payload hash)
//
// Purpose:
//   - Ops visibility: who queries what, how often, how slow
//   - Graph-native analytics: "top N users", "most-asked questions", "slow queries"
//   - Retention policy: 90-day pruned by :Invariant query-traces-retained-90d (wi-qt-04)
// ============================================================================

// --- CONSTRAINT: Unique node_id on :QueryTrace nodes ---
// Enforces that each query invocation is stored exactly once, identified by
// a stable node_id derived from (timestamp_ns + user + payload_hash).
// Re-ingestion of the same event (client retry, duplicate POST) is idempotent.

CREATE CONSTRAINT querytrace_id_unique IF NOT EXISTS
  FOR (q:QueryTrace) REQUIRE q.node_id IS UNIQUE;

// --- INDEX: ts (timestamp) for time-based analytics ---
// Supports range queries like:
//   MATCH (q:QueryTrace) WHERE q.ts > datetime() - duration('P1D') RETURN q
// Used by analytics queries and retention protocols (wi-qt-05, wi-qt-04).

CREATE INDEX querytrace_ts_index IF NOT EXISTS
  FOR (q:QueryTrace) ON (q.ts);

// --- INDEX: user for user-centric analytics ---
// Supports queries like:
//   MATCH (q:QueryTrace {user: 'alice'}) RETURN count(q)
// Used to answer "who queries the graph most" (wi-qt-05).

CREATE INDEX querytrace_user_index IF NOT EXISTS
  FOR (q:QueryTrace) ON (q.user);

// --- COMPOSITE INDEX: (target, verb) for multi-target analysis ---
// Supports efficient filtering by both target environment and command verb:
//   MATCH (q:QueryTrace {target: 'maverick-dev', verb: 'ask'}) RETURN q
// Answers "which verbs are used most on which targets" and cross-env analytics.

CREATE INDEX querytrace_target_verb_index IF NOT EXISTS
  FOR (q:QueryTrace) ON (q.target, q.verb);

// --- INDEX: session_id for request correlation ---
// Supports grouping multiple query events within a single user session:
//   MATCH (q:QueryTrace {session_id: $sid}) RETURN q ORDER BY q.ts
// Used for session-based audit trails and cohort analysis.

CREATE INDEX querytrace_session_id_index IF NOT EXISTS
  FOR (q:QueryTrace) ON (q.session_id);

// --- INDEX: duration_ms for performance analytics ---
// Supports queries that identify slow operations:
//   MATCH (q:QueryTrace) WHERE q.duration_ms > 1000 RETURN q
// Used by wi-qt-05 "slow queries" analytics atom.

CREATE INDEX querytrace_duration_ms_index IF NOT EXISTS
  FOR (q:QueryTrace) ON (q.duration_ms);

// ============================================================================
// SCHEMA PROPERTIES ON :QueryTrace NODES
// ============================================================================
//
// When trace-ingest.py writes a `:QueryTrace` node, it includes:
//
//   - node_id (required, unique): Stable identifier for idempotent upsert.
//                 Format: hash(ts_ns + user + payload_hash)
//                 Re-ingestion produces identical node_id → MERGE is safe.
//
//   - ts (required): ISO 8601 datetime when the query was initiated.
//          Type: DateTime (Neo4j temporal type)
//          Used for: time-range filtering, retention policy, chronological analysis
//
//   - user (required): Identity of the caller.
//          Type: String (email, username, or service name)
//          Example: 'kshitiz@qubit.capital', 'test-harness'
//
//   - target (required): Environment name, one of:
//          'maverick-dev', 'maverick-prod', 'maverick-staging', 'maverick-local'
//          Backcompat aliases accepted during ingestion (wi-nt-01):
//          'dev' → 'maverick-dev', 'prod' → 'maverick-prod', etc.
//
//   - verb (required): The command executed, one of:
//          'ask' - semantic search + inference (mycelium ask ...)
//          'shell' - raw Cypher (mycelium shell ...)
//          'health' - invariant check (mycelium health)
//          'status' - graph vitals (mycelium status)
//          'doctor' - infrastructure diagnostics (mycelium doctor)
//          'apply' - manifest apply (mycelium-dev apply ...)
//          'test' - claim tests (mycelium test)
//          Plus: 'fork', 'sync', 'export-diff', 'export-guide', 'ingest-guide', etc.
//
//   - prompt (optional): The natural-language question or Cypher query string.
//          Type: String (truncated to 500 chars to reduce PII risk)
//          May be omitted if MAVERICK_TRACE=0 or for sensitive verbs.
//
//   - cypher (optional): The Cypher query sent to Neo4j (for 'shell' verb).
//          Type: String (truncated to 1000 chars)
//          Omitted for 'ask' (semantic router emits routed Cypher separately).
//
//   - result_count (optional): Number of rows returned.
//          Type: Integer ≥ 0
//          Omitted for verbs that don't return tabular results (health, status).
//
//   - duration_ms (optional): Wall-clock time from initiation to result.
//          Type: Integer ≥ 0
//          Used for performance analysis; alerts if > 5s (wi-qt-05).
//
//   - embedding_id (optional): Reference to the embedding computed by local Ollama.
//          Type: String (ULID or UUID of the embedding vector in Qdrant)
//          Populated for 'ask' verb when semantic routing is used.
//          Allows cross-reference with Qdrant for model-inference debugging.
//
//   - error (optional): Error message if the query failed.
//          Type: String (truncated, no stack trace)
//          Presence indicates query failure; absence indicates success.
//
//   - payload_hash (optional): Hash of the full untruncated payload.
//          Type: String (SHA-256 hex)
//          Used for dedup (same prompt + cypher + user + ts_bucket → same hash).
//
//   - created_at (optional): Server-side timestamp when the trace was written.
//          Type: DateTime
//          May differ from `ts` (client clock skew); used for server-side retention.
//
// ============================================================================

// --- Summary Report ---
RETURN
  'QueryTrace schema + constraints + indexes loaded (wi-qt-01)' AS status;
