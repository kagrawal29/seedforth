#!/bin/bash
# Deep cycle - every 24 hours (immune system full sweep + progress + lifecycle)
set -euo pipefail
PASS="9aac5c811e6d4f4f64a00c65666f3528"
DIR="/opt/delta/deploy/heartbeat"
TOOLS="/opt/delta/tools"
LOG="/var/log/mycelium-deep.log"
echo "[$(date)] Deep cycle starting" >> $LOG
# 1. Immune system: invariants + heal
python3 $DIR/17-invariants.py >> $LOG 2>&1 || true
python3 $DIR/18-immune-response.py >> $LOG 2>&1 || true
# 2. Progress markers: score real work -> ProgressEvents
python3 $TOOLS/progress-markers.py --all >> $LOG 2>&1 || true
# 3. Lifecycle: detect stalled/complete -> lifecycle events + proposals
python3 $DIR/19-lifecycle.py >> $LOG 2>&1 || true
echo "[$(date)] Deep cycle complete" >> $LOG
