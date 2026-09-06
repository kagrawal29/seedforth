#!/usr/bin/env bash
# ============================================================================
# Runner: atom-run
# ============================================================================
# Executes a Protocol by walking its :CypherAtom chain.
#
# Phase 15c — first interpreter for the atom decomposition model. Reads the
# Protocol's :FIRST_ATOM, walks :FOLLOWS edges, concatenates each atom's
# cypher into a single script with `;\n` separators, and streams the result
# through cypher-shell.
#
# This runner is equivalent to "pipe the file through cypher-shell" but the
# SOURCE of truth is the atom graph, not a .cypher file. Editing an atom in
# Neo4j takes immediate effect. Atoms can be shared between protocols.
# Fire-count gets incremented per run so the atom graph learns which atoms
# are load-bearing.
#
# Usage:
#   atom-run.sh <protocol_node_id>
#
# Example:
#   atom-run.sh protocol-heartbeat
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <protocol_node_id>" >&2
  exit 1
fi

PROTOCOL_ID="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

cypher_exec() {
  cypher-shell -a "$BOLT" \
    -u "$USER" -p "$PASS" --encryption false --format plain "$@"
}

# --- Step 1: walk the atom chain ordered by atom_order ---------------------
# Also return how each atom connects to the next, so the runner can decide
# whether to insert a semicolon (independent statement) or just a newline
# (variable-threaded continuation):
#
#   :FEEDS {var}  → atoms share a variable, must run as one cypher statement
#                    (no semicolon between them; scope threads naturally)
#   :FOLLOWS      → atoms are independent, separate statements (semicolon)
#
# Defaults to FOLLOWS (semicolon) if neither edge exists.
rows=$(
  cypher_exec <<CYPHER | tail -n +2
MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'})
WHERE a.cypher IS NOT NULL
WITH a ORDER BY a.atom_order ASC
OPTIONAL MATCH (a)-[f:FEEDS]->(next:CypherAtom)
RETURN replace(a.cypher, '\n', '|||NL|||') + '@@@SEP@@@' + CASE WHEN f IS NOT NULL THEN 'feeds' ELSE 'follows' END AS row
CYPHER
)

if [ -z "$rows" ]; then
  # No inline cypher atoms -- check for file-based atoms
  file_atoms=$(
    cypher_exec <<CYPHER2 | tail -n +2
MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'})
WHERE a.file_path IS NOT NULL
RETURN a.file_path AS path
ORDER BY a.atom_order ASC
CYPHER2
  )
  if [ -n "$file_atoms" ]; then
    # Execute file-based atoms directly
    echo "[atom-run] executing $PROTOCOL_ID via file-based atoms..."
    cypher_exec \
      "MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'}) SET a.fire_count = coalesce(a.fire_count, 0) + 1, a.last_fired_at = toString(datetime()) RETURN count(a) AS atoms_fired" \
      | tail -3
    cypher_exec \
      "MATCH (p:Protocol {node_id: '$PROTOCOL_ID'}) WITH p, coalesce(p.fire_count, 0) + 1 AS fc SET p.fire_count = fc, p.last_run = toString(datetime()), p.amortization_status = CASE WHEN fc >= 51 THEN 'critical' WHEN fc >= 11 THEN 'strengthened' WHEN fc >= 3 THEN 'active' WHEN fc >= 1 THEN 'experimental' ELSE 'dead' END RETURN p.node_id, fc, p.amortization_status" \
      | tail -3
    while IFS= read -r fline; do
      [ -z "$fline" ] && continue
      fpath="${fline#\"}"
      fpath="${fpath%\"}"
      fpath="${fpath## }"
      fpath="${fpath%% }"
      if [ -f "$REPO_ROOT/$fpath" ]; then
        echo "[atom-run] running file: $fpath"
        cypher-shell -a "$BOLT" \
          -u "$USER" -p "$PASS" --encryption false --format plain \
          < "$REPO_ROOT/$fpath" 2>&1 | tail -5
      elif [ -f "$fpath" ]; then
        echo "[atom-run] running file: $fpath"
        cypher-shell -a "$BOLT" \
          -u "$USER" -p "$PASS" --encryption false --format plain \
          < "$fpath" 2>&1 | tail -5
      else
        echo "[atom-run] WARNING: file not found: $fpath" >&2
      fi
    done <<< "$file_atoms"
    echo "[atom-run] ok"
    exit 0
  fi
  echo "[atom-run] ERROR: no atoms for protocol $PROTOCOL_ID" >&2
  echo "[atom-run] hint: atomize first with" >&2
  echo "           python3 graph/runner/atomize-protocol.py $PROTOCOL_ID graph/protocols/<name>.cypher" >&2
  exit 2
fi

# --- Step 2: strip cypher-shell --format plain quoting + pick separator ----
# cypher-shell wraps string results in double quotes and escapes inner
# quotes. We need the raw cypher text. Plus, we split each row on @@@SEP@@@
# to recover the FEEDS/FOLLOWS hint for the separator.
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

printf '%s\n' "$rows" | while IFS= read -r line; do
  raw="${line#\"}"
  raw="${raw%\"}"
  raw="${raw//\\\"/\"}"
  raw="${raw//\\n/$'\n'}"
  body="${raw%@@@SEP@@@*}"
  link="${raw##*@@@SEP@@@}"
  body="${body//|||NL|||/$'\n'}"
  if [ "$link" = "feeds" ]; then
    # FEEDS: keep variables in scope, no semicolon before next atom
    printf '%s\n' "$body"
  else
    # FOLLOWS or no edge: independent statement, add semicolon
    printf '%s\n;\n' "$body"
  fi
done > "$tmp"

# --- Step 3: fire-count increment + emit a trace (synapse visibility) ------
# Every atom in this protocol gets fire_count++. The existing trace system
# (Phase 14) captures the synapse moment — we emit a QueryTrace per atom
# so any external observer watching QueryTrace nodes sees live cognition.
# "Currently firing" = trace node with invoked_epoch_ms close to now.
# CRITICAL FIX: also increment fire_count on the parent Protocol itself.
cypher_exec \
  "MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'}) SET a.fire_count = coalesce(a.fire_count, 0) + 1, a.last_fired_at = toString(datetime()), a.last_fired_ms = timestamp() RETURN count(a) AS atoms_fired" \
  | tail -3

# Increment fire_count on the parent Protocol and update amortization_status
cypher_exec \
  "MATCH (p:Protocol {node_id: '$PROTOCOL_ID'}) WITH p, coalesce(p.fire_count, 0) + 1 AS new_fire_count SET p.fire_count = new_fire_count, p.last_run = toString(datetime()), p.amortization_status = CASE WHEN new_fire_count = 0 THEN 'dead' WHEN new_fire_count >= 1 AND new_fire_count <= 2 THEN 'experimental' WHEN new_fire_count >= 3 AND new_fire_count <= 10 THEN 'active' WHEN new_fire_count >= 11 AND new_fire_count <= 50 THEN 'strengthened' WHEN new_fire_count >= 51 THEN 'critical' ELSE 'unknown' END RETURN p.node_id AS protocol_id, new_fire_count AS fire_count, p.amortization_status AS status" \
  | tail -3

# Pull in trace_emit for per-atom synapse events
# shellcheck disable=SC1091
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/trace.sh"

# Emit one trace per atom just before the protocol runs. touched_ids
# contains the atom node_ids so strengthen-edges can walk them.
atom_rows=$(
  cypher_exec \
    "MATCH (a:CypherAtom {source_protocol: '$PROTOCOL_ID'}) RETURN a.node_id + '@@@' + substring(coalesce(a.cypher, ''), 0, 120) AS row ORDER BY a.atom_order" \
    | tail -n +2
)
while IFS= read -r raw; do
  [ -z "$raw" ] && continue
  raw="${raw#\"}"
  raw="${raw%\"}"
  atom_node_id="${raw%%@@@*}"
  atom_cypher="${raw##*@@@}"
  trace_emit "atom-fire:$atom_node_id" "atom-run" "$atom_cypher" 0 0 true || true
done <<< "$atom_rows"

# --- Step 4: execute the concatenated chain --------------------------------
echo "[atom-run] executing $PROTOCOL_ID ($(wc -l < "$tmp" | tr -d ' ') lines)..."
if cypher-shell -a "$BOLT" \
      -u "$USER" -p "$PASS" --encryption false --format plain \
      < "$tmp" > /tmp/atom-run.out 2>&1; then
  tail -10 /tmp/atom-run.out
  echo "[atom-run] ok"
else
  echo "[atom-run] FAILED:" >&2
  tail -20 /tmp/atom-run.out >&2
  exit 3
fi
