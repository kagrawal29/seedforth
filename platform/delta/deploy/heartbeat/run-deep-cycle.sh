#!/bin/bash
# Deep cycle - every 24 hours
# Immune sweep + graph-native progress/lifecycle + SuperAgent steering
set -euo pipefail
PASS="${NEO4J_PASSWORD:?set NEO4J_PASSWORD in the runtime environment}"
DIR="/opt/delta/deploy/heartbeat"
TOOLS="/opt/delta/tools"
LOG="/var/log/mycelium-deep.log"
echo "[$(date)] Deep cycle starting" >> $LOG

# 1. Immune system: invariants + heal
python3 $DIR/17-invariants.py >> $LOG 2>&1 || true
python3 $DIR/18-immune-response.py >> $LOG 2>&1 || true

# 2. SENSES (thin I/O boundary): scanner writes raw signals
python3 $TOOLS/fleet-scanner.py --all >> $LOG 2>&1 || true

# 3. THOUGHT (graph-resident): run graph-native protocols
python3 $TOOLS/graph-runner.py --protocol protocol-progress-score >> $LOG 2>&1 || true
python3 $TOOLS/graph-runner.py --protocol protocol-lifecycle >> $LOG 2>&1 || true
python3 $TOOLS/graph-runner.py --protocol protocol-direction >> $LOG 2>&1 || true

# 4. STEERING: SuperAgent acts on proposals (below-gate only)
python3 $TOOLS/steering-executor.py >> $LOG 2>&1 || true

# 5. OBSERVABILITY: opencode spend/latency metrics -> Metric nodes
python3 $TOOLS/metrics-collector.py 7 >> $LOG 2>&1 || true

echo "[$(date)] Deep cycle complete" >> $LOG
