#!/usr/bin/env bash
# ============================================================================
# Runner: trace (helper)
# ============================================================================
# Records a QueryTrace node in the graph. Intended to be called by other
# runners before/after they execute cypher, so every meaningful invocation
# leaves a trail the graph can learn from.
#
# Usage (sourced or called inline):
#   source graph/runner/trace.sh
#   trace_emit "status" "mycelium-cli" "MATCH (b:Being) RETURN ..." 42 17
#
# Or one-shot:
#   graph/runner/trace.sh <command> <invoked_by> <cypher_summary> \
#       [duration_ms] [result_count]
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
#   TRACE_ENABLED     default: 1  (set to 0 to silently disable tracing)
# ============================================================================

BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
NEO4J_USER_VAR="${NEO4J_USER:-neo4j}"
NEO4J_PASS_VAR="${NEO4J_PASS:-localtest12}"
TRACE_ENABLED="${TRACE_ENABLED:-1}"

# Resolve the emit-trace protocol path once at source time. Using
# BASH_SOURCE[0] inside trace_emit() gave inconsistent resolution when
# the file is sourced from different working directories, so we snapshot
# it here.
__TRACE_SH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
__TRACE_PROTOCOL="${__TRACE_SH_DIR}/../protocols/emit-trace.cypher"

trace_emit() {
  [ "$TRACE_ENABLED" = "0" ] && return 0
  [ ! -f "$__TRACE_PROTOCOL" ] && return 0
  local command="${1:-unknown}"
  local invoked_by="${2:-mycelium-cli}"
  local cypher_summary="${3:-}"
  local duration_ms="${4:-0}"
  local result_count="${5:-0}"
  local create_trace="${6:-true}"  # whether to also create a QueryTrace record

  # Truncate cypher summary to 300 chars to keep traces lean
  cypher_summary="${cypher_summary:0:300}"

  local protocol="$__TRACE_PROTOCOL"

  # Quote-escape for JSON param by replacing " with \"
  local cs_escaped="${cypher_summary//\\/\\\\}"
  cs_escaped="${cs_escaped//\"/\\\"}"
  local cmd_escaped="${command//\"/\\\"}"
  local inv_escaped="${invoked_by//\"/\\\"}"

  cypher-shell -a "$BOLT" \
    -u "$NEO4J_USER_VAR" -p "$NEO4J_PASS_VAR" --encryption false --format plain \
    -P "{cypher: \"$cs_escaped\", cypher_summary: \"$cs_escaped\", invoked_by: \"$inv_escaped\", command: \"$cmd_escaped\", duration_ms: $duration_ms, result_count: $result_count, touched_ids: [], create_trace: $create_trace}" \
    < "$protocol" >/dev/null 2>&1 || true
}

# If invoked directly (not sourced), emit a one-shot trace
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  trace_emit "$@"
fi
