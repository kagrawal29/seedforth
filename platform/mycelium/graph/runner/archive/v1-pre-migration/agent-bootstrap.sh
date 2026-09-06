#!/usr/bin/env bash
# ============================================================================
# Agent Bootstrap — runs BEFORE any subagent gets control
# ============================================================================
# This script is the enforcement mechanism for the agent contract.
# Every subagent dispatch prompt should begin with:
#   bash graph/runner/agent-bootstrap.sh
#
# It runs 10 diverse NL queries through mycelium ask, depositing:
#   - 10 :Prompt nodes with embeddings
#   - ~50 :Word nodes with CONTAINS/BIGRAM edges
#   - ~10 :RESOLVED_TO edges (linking asks to graph answers)
#   - ~7000 walk-counted edges (from structural self-walk)
#
# The graph's vocabulary layer grows from EVERY agent invocation,
# not just the ones that remember to follow the contract.
#
# After the bootstrap, the agent's actual task begins. The bootstrap
# is mandatory, not advisory. The graph learns before the agent acts.
# ============================================================================

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MYCELIUM="$SCRIPT_DIR/../../mycelium-dev"

echo "[bootstrap] Running 10 NL discovery queries..."

# These questions are diverse by design — they touch different subsystems
# so the vocabulary layer grows across the full graph, not just one corner.
"$MYCELIUM" ask "what is the mycelium agent contract" > /dev/null 2>&1
"$MYCELIUM" ask "what subsystems does mycelium have" > /dev/null 2>&1
"$MYCELIUM" ask "how does the heartbeat work" > /dev/null 2>&1
"$MYCELIUM" ask "what invariants exist" > /dev/null 2>&1
"$MYCELIUM" ask "what protocols can be healed" > /dev/null 2>&1
"$MYCELIUM" ask "how do embeddings work" > /dev/null 2>&1
"$MYCELIUM" ask "what is the current density" > /dev/null 2>&1
"$MYCELIUM" ask "what dreams has the graph had" > /dev/null 2>&1
"$MYCELIUM" ask "what purposes does mycelium serve" > /dev/null 2>&1
"$MYCELIUM" ask "what frustrations exist right now" > /dev/null 2>&1

echo "[bootstrap] Discovery complete. Graph vocabulary updated."
echo "[bootstrap] Agent task begins now."
