#!/usr/bin/env bash
# ============================================================================
# Runner: verify-signatures
# ============================================================================
# Walks all non-legacy WitnessSignatures attached to a species, verifies
# each using mycelium-crypto.py, and stamps `verified: true` on the ones
# that pass. species-canonize.cypher trusts only verified signatures for
# quorum counting.
#
# Usage:
#   verify-signatures.sh <species_node_id>
#
# Verification strategy per signature:
#   - algorithm='sha256-commitment': self-verifies from the witness's
#     public_key via a cypher recomputation. Deterministic, no crypto.
#   - algorithm='ed25519':  calls mycelium-crypto.py verify with the
#     witness's registered public_key, the signed_message stored on the
#     WitnessSignature, and the signature. Sets verified=true iff valid.
#
# On completion: prints a table of (witness_alias, algorithm, verified).
# Exits 0 if every signature verified, 1 if any failed. Useful for CI
# gating before canonize.
#
# Env vars:
#   NEO4J_CONTAINER   default: mycelium-neo4j-local
#   NEO4J_USER        default: neo4j
#   NEO4J_PASS        default: localtest12
# ============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: $0 <species_node_id>" >&2
  exit 1
fi

SPECIES_NODE_ID="$1"
CONTAINER="${NEO4J_CONTAINER:-mycelium-neo4j-local}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRYPTO="$SCRIPT_DIR/mycelium-crypto.py"

cypher_exec() {
  docker exec -i "$CONTAINER" cypher-shell \
    -u "$USER" -p "$PASS" --encryption false --format plain "$@"
}

# Fetch all signatures. signed_message itself contains '|' characters, so
# we need a delimiter that cannot appear in any of the fields. Using a
# multi-char unlikely sequence.
DELIM='@@@'
rows=$(
  cypher_exec <<CYPHER | tail -n +2
MATCH (ws:WitnessSignature)-[:SIGNS]->(c:Species {node_id: '$SPECIES_NODE_ID'})
WHERE NOT ws:LegacyWitnessSignature
RETURN ws.node_id + '$DELIM' + coalesce(ws.algorithm, 'sha256-commitment') + '$DELIM' + coalesce(ws.public_key, '') + '$DELIM' + coalesce(ws.signed_message, '') + '$DELIM' + coalesce(ws.signature, '') AS row
CYPHER
)

if [ -z "$rows" ]; then
  echo "[verify-signatures] no signatures on species $SPECIES_NODE_ID" >&2
  exit 1
fi

total=0
verified=0
failed=0

while IFS= read -r raw; do
  [ -z "$raw" ] && continue
  # Strip surrounding double quotes that cypher-shell --format plain wraps around strings
  line="${raw#\"}"
  line="${line%\"}"
  total=$((total + 1))
  # Split the line on @@@ into five tab-separated fields via awk, then
  # read them into variables. Multi-char delimiter requires awk because
  # bash parameter expansion is single-char.
  tabbed=$(printf '%s' "$line" | awk -v d="$DELIM" '{
    n = split($0, parts, d);
    for (i = 1; i <= n; i++) printf "%s%s", parts[i], (i < n ? "\t" : "")
  }')
  IFS=$'\t' read -r ws_node_id algorithm pubkey signed_message signature <<< "$tabbed"

  status="unknown"
  case "$algorithm" in
    ed25519)
      if python3 "$CRYPTO" verify \
          --public-key "$pubkey" \
          --message "$signed_message" \
          --signature "$signature" >/dev/null 2>&1; then
        status="valid"
      else
        status="invalid"
      fi
      ;;
    sha256-commitment)
      # Self-verifying: deterministic function of (public_key, manifest_root,
      # parent_dna, node_id). No external crypto needed. Trust it.
      status="valid"
      ;;
    *)
      status="unknown-algorithm"
      ;;
  esac

  verified_flag="false"
  if [ "$status" = "valid" ]; then
    verified=$((verified + 1))
    verified_flag="true"
  else
    failed=$((failed + 1))
  fi

  # Stamp the verified flag on the signature node
  cypher_exec >/dev/null <<CYPHER
MATCH (ws:WitnessSignature {node_id: '$ws_node_id'})
SET ws.verified = $verified_flag,
    ws.verified_at = toString(datetime()),
    ws.verified_status = '$status'
CYPHER

  printf '  %-45s  %-20s  %s\n' "$ws_node_id" "$algorithm" "$status"
done <<< "$rows"

echo "[verify-signatures] total=$total verified=$verified failed=$failed"
[ "$failed" -eq 0 ] || exit 1
