#!/bin/bash
set -euo pipefail
PASS="9aac5c811e6d4f4f64a00c65666f3528"
DIR="/opt/delta/deploy/heartbeat"
LOG="/var/log/mycelium-heartbeat.log"

echo "[$(date)] Heartbeat starting" >> $LOG

# 1. Cypher protocols (maintenance: connect, decay, heal, dream, report, health)
for f in $DIR/[0-9][0-9]-*.cypher; do
    [ -e "$f" ] || continue
    name=$(basename $f .cypher)
    echo "  $name..." >> $LOG
    docker exec mycelium-neo4j cypher-shell -u neo4j -p $PASS --format plain < $f 2>> $LOG || true
done

# 2. Invariant verification (system checks itself) — fast HTTP API
echo "  17-invariants..." >> $LOG
python3 $DIR/17-invariants.py >> $LOG 2>&1 || echo "  invariants failed" >> $LOG

echo "[$(date)] Heartbeat complete" >> $LOG
