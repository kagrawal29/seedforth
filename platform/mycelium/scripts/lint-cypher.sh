#!/usr/bin/env bash
# lint-cypher.sh — validate every .cypher file in graph/ against a live Neo4j.
#
# Catches the Cypher 2026 "statement scope across semicolons" class of bug
# that breaks files which look fine but fail at bootstrap/ingest time. Run
# this in CI; run it locally before pushing.
#
# Usage:
#   bash scripts/lint-cypher.sh              # tests all .cypher files in graph/
#   bash scripts/lint-cypher.sh path/one.cypher path/two.cypher
#
# Exit 0 if all files execute cleanly, non-zero otherwise with a summary.

set -u

BOLT="${NEO4J_BOLT:-bolt://localhost:7687}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASS:-localtest12}"

if ! command -v cypher-shell >/dev/null 2>&1; then
  echo "lint-cypher: cypher-shell not on PATH — run install-deps.sh first"
  exit 2
fi

files=("$@")
if [ "${#files[@]}" -eq 0 ]; then
  while IFS= read -r f; do files+=("$f"); done < <(find graph -name '*.cypher' -type f 2>/dev/null | sort)
fi

if [ "${#files[@]}" -eq 0 ]; then
  echo "lint-cypher: no .cypher files found under graph/"
  exit 0
fi

passed=0
failed=0
skipped=0
errors=()

for f in "${files[@]}"; do
  # Wrap the file body through apoc.cypher.runMany to get a single-transaction
  # execution that still respects statement-level scope. If the file has the
  # WITH-across-; bug, this surfaces it.
  body="$(cat "$f")"
  wrapped=$(BODY="$body" python3 -c '
import os
b = os.environ["BODY"]
esc = b.replace("\\", "\\\\").replace("\x27", "\\\x27")
print(f"CALL apoc.cypher.runMany(\x27{esc}\x27, {{}}, {{statistics:false}}) YIELD row RETURN count(row)")
')

  out=$(printf '%s\n' "$wrapped" | cypher-shell -a "$BOLT" -u "$USER" -p "$PASS" --format plain 2>&1)
  err=$(printf '%s' "$out" | grep -E "^(Neo\.|42N|52N|08N|syntax|error)" | head -1 || true)

  # Classify errors:
  #   - Parameter errors ("Expected $paramName, but got nothing") are expected
  #     for parameterized protocols that require runtime injection. SKIP.
  #   - Everything else (statement scope, type mismatch, syntax) is a REAL fail.
  if [ -z "$err" ]; then
    printf '  \033[32m✓\033[0m %s\n' "$f"
    passed=$((passed + 1))
  elif printf '%s' "$err" | grep -qE "42N81.*missing request parameter|Expected \\\$"; then
    printf '  \033[33m○\033[0m %s (parameterized, skipped)\n' "$f"
    skipped=$((skipped + 1))
  else
    printf '  \033[31m✗\033[0m %s\n      %s\n' "$f" "$err"
    errors+=("$f :: $err")
    failed=$((failed + 1))
  fi
done

echo
echo "lint-cypher: $passed passed, $skipped skipped (parameterized), $failed failed"
[ "$failed" -eq 0 ] && exit 0 || exit 1
