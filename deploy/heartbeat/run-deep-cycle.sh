#!/bin/bash
# Deep cycle - every 24 hours (immune system full sweep)
set -euo pipefail
PASS="9aac5c811e6d4f4f64a00c65666f3528"
DIR="/opt/delta/deploy/heartbeat"
LOG="/var/log/mycelium-deep.log"
echo "[$(date)] Deep cycle starting" >> $LOG
python3 $DIR/17-invariants.py >> $LOG 2>&1 || true
python3 $DIR/18-immune-response.py >> $LOG 2>&1 || true
echo "[$(date)] Deep cycle complete" >> $LOG
