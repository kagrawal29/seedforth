#!/bin/bash
set -euo pipefail
PASS="9aac5c811e6d4f4f64a00c65666f3528"
DIR="/opt/delta/deploy/heartbeat"
LOG="/var/log/mycelium-heartbeat.log"

echo "[$(date)] Heartbeat starting" >> $LOG

for f in $DIR/*.cypher; do
    name=$(basename $f .cypher)
    echo "  $name..." >> $LOG
    docker exec mycelium-neo4j cypher-shell -u neo4j -p $PASS --format plain < $f 2>> $LOG || true
done

echo "[$(date)] Heartbeat complete" >> $LOG
