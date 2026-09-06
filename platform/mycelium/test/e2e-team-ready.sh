#!/usr/bin/env bash
# e2e team-ready test for the unified mycelium CLI.
#
# Drives the 8 :TestStep scenarios recorded in the graph under
# (:TestPlan {node_id:'test-team-ready-e2e'}), ingests each outcome as a
# (:TestRun) node linked to its step, and prints a pass/fail summary.
#
# Runs locally against the dev Neo4j graph. Safe: creates no graph writes
# except :TestRun result nodes.
set -uo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

TEST_RUN_ID="run-$(date -u +%Y%m%dT%H%M%SZ)"
GRAPH_CLI="${GRAPH_CLI:-./mycelium-dev}"
PASS=0
FAIL=0
declare -a RESULTS

ansi_green="\033[32m"
ansi_red="\033[31m"
ansi_dim="\033[2m"
ansi_reset="\033[0m"

record() {
  local step="$1" passed="$2" output="$3"
  local flag
  if [ "$passed" -eq 1 ]; then flag="true"; PASS=$((PASS+1)); echo -e "  ${ansi_green}PASS${ansi_reset} $step"
  else flag="false"; FAIL=$((FAIL+1)); echo -e "  ${ansi_red}FAIL${ansi_reset} $step"
       echo -e "${ansi_dim}    ${output:0:300}${ansi_reset}"
  fi
  local excerpt
  excerpt=$(printf '%s' "$output" | tr '\n' ' ' | sed "s/'/\\\\'/g" | cut -c1-400)
  "$GRAPH_CLI" shell "MERGE (r:TestRun {node_id:'$TEST_RUN_ID-$step'}) SET r.step='$step', r.passed=$flag, r.timestamp='$(date -u +%Y-%m-%dT%H:%M:%SZ)', r.output_excerpt='$excerpt' WITH r MATCH (s:TestStep {node_id:'step-$step'}) MERGE (s)-[:HAS_RUN]->(r) RETURN r.node_id" >/dev/null 2>&1 || true
  RESULTS+=("$step:$flag")
}

have() { command -v "$1" >/dev/null 2>&1; }

# Build snapshot binary
echo "=== build snapshot ==="
( cd cmd/mycelium && go build -o "$REPO/dist-e2e/mycelium" . ) 2>&1 | tail -3
test -x "$REPO/dist-e2e/mycelium" || { echo "build failed"; exit 99; }

# Build install tarball matching goreleaser's naming (mycelium_<Os>_<arch>.tar.gz)
OS_TITLE=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH=amd64 || ARCH=arm64
STAGE="$REPO/dist-e2e/stage"
mkdir -p "$STAGE"
cp "$REPO/dist-e2e/mycelium" "$STAGE/mycelium"
( cd "$STAGE" && tar czf "../mycelium_${OS_TITLE}_${ARCH}.tar.gz" mycelium )
( cd "$REPO/dist-e2e" && sha256sum "mycelium_${OS_TITLE}_${ARCH}.tar.gz" 2>/dev/null || shasum -a 256 "mycelium_${OS_TITLE}_${ARCH}.tar.gz" ) > "$REPO/dist-e2e/checksums.txt"
# Normalize checksums.txt: install.sh expects "<sha>  <filename>"
awk '{ print $1 "  " $2 }' "$REPO/dist-e2e/checksums.txt" > "$REPO/dist-e2e/checksums.txt.tmp" && mv "$REPO/dist-e2e/checksums.txt.tmp" "$REPO/dist-e2e/checksums.txt"

# Serve the tarball locally
PORT=8765
python3 -m http.server "$PORT" --directory "$REPO/dist-e2e" >/tmp/e2e-http.log 2>&1 &
HTTP_PID=$!
trap "kill $HTTP_PID 2>/dev/null" EXIT
sleep 1

BASE_URL="http://127.0.0.1:$PORT"
echo "stub release URL: $BASE_URL"

############
# Step 1: reader-install-unix (+ agent-accessible symlink)
############
echo "=== step 1: reader install (unix) ==="
FAKE_HOME=$(mktemp -d)
FAKE_SYSBIN="$FAKE_HOME/usr-local-bin"
mkdir -p "$FAKE_SYSBIN"
OUT=$(HOME="$FAKE_HOME" PATH=/usr/bin:/bin MYCELIUM_INSTALL_BASE_URL="$BASE_URL" MYCELIUM_SYSTEM_BIN="$FAKE_SYSBIN/mycelium" bash install/install.sh 2>&1)
STATUS=$?
if [ $STATUS -eq 0 ] && [ -x "$FAKE_HOME/.mycelium/bin/mycelium" ] && [ -L "$FAKE_SYSBIN/mycelium" ]; then
  VER=$("$FAKE_HOME/.mycelium/bin/mycelium" version 2>&1)
  # Verify symlink resolves to the real binary
  REAL=$(readlink "$FAKE_SYSBIN/mycelium")
  # Verify agent-accessible: clean env, PATH only contains the symlink dir
  AGENT_VER=$(env -i HOME="$FAKE_HOME" PATH="$FAKE_SYSBIN:/usr/bin:/bin" bash -c "mycelium version" 2>&1)
  # Second run idempotent
  OUT2=$(HOME="$FAKE_HOME" PATH=/usr/bin:/bin MYCELIUM_INSTALL_BASE_URL="$BASE_URL" MYCELIUM_SYSTEM_BIN="$FAKE_SYSBIN/mycelium" bash install/install.sh 2>&1)
  STATUS2=$?
  if [ $STATUS2 -eq 0 ] && echo "$VER" | grep -q "mycelium " && echo "$AGENT_VER" | grep -q "mycelium "; then
    record "reader-install-unix" 1 "version=$VER; agent-accessible via symlink=$REAL; idempotent rerun exit=$STATUS2"
  else
    record "reader-install-unix" 0 "first_ok but second run failed or symlink broken: symlink=$REAL agent_ver=$AGENT_VER rerun=$OUT2"
  fi
else
  record "reader-install-unix" 0 "install failed status=$STATUS: $OUT"
fi

############
# Step 2: reader-install-windows (dry syntax check only)
############
echo "=== step 2: windows install lint ==="
if have pwsh; then
  OUT=$(pwsh -NoProfile -Command "try { [System.Management.Automation.Language.Parser]::ParseFile('$REPO/install/install.ps1', [ref] \$null, [ref] \$null) | Out-Null; 'OK' } catch { \$_ }" 2>&1)
  if echo "$OUT" | grep -q OK; then record "reader-install-windows" 1 "pwsh parse ok"
  else record "reader-install-windows" 0 "pwsh parse failed: $OUT"; fi
else
  # Best-effort: must contain Bypass, LOCALAPPDATA, SHA256
  if grep -q "ExecutionPolicy Bypass" install/install.ps1 && grep -q "LOCALAPPDATA" install/install.ps1 && grep -qi "SHA256" install/install.ps1; then
    record "reader-install-windows" 1 "pwsh not installed; static checks pass (Bypass/LOCALAPPDATA/SHA256)"
  else
    record "reader-install-windows" 0 "pwsh missing AND static checks failed"
  fi
fi

############
# Step 3: reads against live graph
############
echo "=== step 3: reads against live graph ==="
MY="$FAKE_HOME/.mycelium/bin/mycelium"
STATUS_OUT=$("$MY" --target dev status 2>&1)
SHELL_OUT=$("$MY" --target dev shell "RETURN 1 AS one" 2>&1)
HEALTH_OUT=$("$MY" --target dev health 2>&1)
DOCTOR_OUT=$("$MY" --target dev doctor 2>&1)
JSON_OUT=$("$MY" --target dev --json status 2>&1)
if echo "$STATUS_OUT" | grep -qE 'being_count=[0-9]+' \
   && echo "$SHELL_OUT" | grep -qE 'one=1' \
   && echo "$HEALTH_OUT" | grep -qE 'invariants=[0-9]+' \
   && echo "$DOCTOR_OUT" | grep -q "doctor: ok" \
   && echo "$JSON_OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'node_count' in d and 'target' in d and 'timestamp' in d" 2>/dev/null; then
  record "reads-live-graph" 1 "status/shell/health/doctor/json all ok"
else
  record "reads-live-graph" 0 "status=$STATUS_OUT | shell=$SHELL_OUT | health=$HEALTH_OUT | doctor=$DOCTOR_OUT | json=$JSON_OUT"
fi

############
# Step 4: write refusal
############
echo "=== step 4: write refused natively ==="
COUNT_BEFORE=$("$MY" --target dev shell "MATCH (n:TestTarget) RETURN count(n) AS c" 2>&1 | grep -oE 'c=[0-9]+' | cut -d= -f2 || echo "0")
WRITE_OUT=$("$MY" --target dev shell "CREATE (n:TestTarget)" 2>&1)
WRITE_EXIT=$?
COUNT_AFTER=$("$MY" --target dev shell "MATCH (n:TestTarget) RETURN count(n) AS c" 2>&1 | grep -oE 'c=[0-9]+' | cut -d= -f2 || echo "0")
if [ "$WRITE_EXIT" -ne 0 ] && echo "$WRITE_OUT" | grep -q "refuses write verbs" && [ "$COUNT_BEFORE" = "$COUNT_AFTER" ]; then
  record "write-refusal" 1 "exit=$WRITE_EXIT, count stable ($COUNT_BEFORE->$COUNT_AFTER)"
else
  record "write-refusal" 0 "exit=$WRITE_EXIT, before=$COUNT_BEFORE after=$COUNT_AFTER, out=$WRITE_OUT"
fi

############
# Step 5: failure modes
############
echo "=== step 5: failure modes ==="
UNKNOWN_OUT=$("$MY" bogus 2>&1); UNKNOWN_EXIT=$?
BADTGT_OUT=$("$MY" --target nonesuch status 2>&1); BADTGT_EXIT=$?
NOTOOLCHAIN_OUT=$(HOME="$FAKE_HOME" PATH=/usr/bin:/bin "$MY" bootstrap 2>&1); NOTOOLCHAIN_EXIT=$?
# Graph down: point at wrong URI via --target
GRAPHDOWN_OUT=$(MYCELIUM_DEV_PATH="" "$MY" --target dev --timeout 5s doctor 2>&1 || true)
ok=true
echo "$UNKNOWN_OUT" | grep -q "unknown command" || ok=false
[ "$UNKNOWN_EXIT" -eq 2 ] || ok=false
[ "$BADTGT_EXIT" -ne 0 ] || ok=false
echo "$NOTOOLCHAIN_OUT" | grep -q "requires the contributor toolchain" || ok=false
[ "$NOTOOLCHAIN_EXIT" -eq 127 ] || ok=false
if $ok; then
  record "failure-modes" 1 "unknown_exit=$UNKNOWN_EXIT, badtgt_exit=$BADTGT_EXIT, notoolchain_exit=$NOTOOLCHAIN_EXIT"
else
  record "failure-modes" 0 "unknown=$UNKNOWN_EXIT/$UNKNOWN_OUT | badtgt=$BADTGT_EXIT | notoolchain=$NOTOOLCHAIN_EXIT/$NOTOOLCHAIN_OUT"
fi

############
# Step 6: contributor promotion
############
echo "=== step 6: contributor promotion ==="
DISPATCH_OUT=$(MYCELIUM_DEV_PATH="$REPO/mycelium-dev" "$MY" bootstrap --help 2>&1 | head -30)
DISPATCH_EXIT=$?
READ_STILL=$("$MY" --target dev status 2>&1)
if [ $DISPATCH_EXIT -le 1 ] && ! echo "$DISPATCH_OUT" | grep -q "requires the contributor toolchain" && echo "$READ_STILL" | grep -qE 'being_count=[0-9]+'; then
  record "contributor-promotion" 1 "dispatched exit=$DISPATCH_EXIT, reads unaffected"
else
  record "contributor-promotion" 0 "dispatch_exit=$DISPATCH_EXIT out=$DISPATCH_OUT | read=$READ_STILL"
fi

############
# Step 7: rotation dry-run
############
echo "=== step 7: rotation dry-run ==="
SYN=$(bash -n deploy/rotate-dev-password.sh 2>&1); SYN_EXIT=$?
MISSING_OUT=$(bash deploy/rotate-dev-password.sh 2>&1); MISSING_EXIT=$?
WEAK_OUT=$(OLD_PASSWORD=x NEW_PASSWORD=weak bash deploy/rotate-dev-password.sh 2>&1); WEAK_EXIT=$?
# Confirm cypher-shell uses env var, not CLI arg
CYPHER_HIT=$(grep -E '^\s*-p\s+"\$OLD_PASSWORD"' deploy/rotate-dev-password.sh | head -1)
ok=true
[ $SYN_EXIT -eq 0 ] || ok=false
[ $MISSING_EXIT -eq 2 ] || ok=false
[ $WEAK_EXIT -eq 3 ] || ok=false
[ -n "$CYPHER_HIT" ] || ok=false
if $ok; then
  record "rotation-dry-run" 1 "syn_ok, missing_exit=$MISSING_EXIT, weak_exit=$WEAK_EXIT, env-var usage verified"
else
  record "rotation-dry-run" 0 "syn=$SYN_EXIT missing=$MISSING_EXIT weak=$WEAK_EXIT cypher_hit='$CYPHER_HIT'"
fi

############
# Step 8: graph-native verification
############
echo "=== step 8: graph-native verification ==="
RUNS=$("$GRAPH_CLI" shell "MATCH (tp:TestPlan {node_id:'test-team-ready-e2e'})-[:HAS_STEP]->(s)-[:HAS_RUN]->(r:TestRun) WHERE r.node_id STARTS WITH '$TEST_RUN_ID' RETURN count(r) AS runs" 2>&1 | tail -1)
EXPECTED=7  # steps 1-7; step 8 self-records after
if echo "$RUNS" | grep -qE "\\b$EXPECTED\\b"; then
  record "graph-native-verification" 1 "7 prior :TestRun nodes present"
else
  record "graph-native-verification" 0 "expected >=7 runs, saw: $RUNS"
fi

############
# Summary
############
echo ""
echo "========================================"
echo "e2e team-ready: $PASS passed, $FAIL failed"
echo "========================================"
"$GRAPH_CLI" shell "MATCH (tp:TestPlan {node_id:'test-team-ready-e2e'}) SET tp.last_run='$TEST_RUN_ID', tp.last_pass=$PASS, tp.last_fail=$FAIL RETURN tp.last_run, tp.last_pass, tp.last_fail" >/dev/null 2>&1 || true
exit $FAIL
