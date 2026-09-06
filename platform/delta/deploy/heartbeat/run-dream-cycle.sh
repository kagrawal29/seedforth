#!/bin/bash
# Dream cycle - every 4 hours (deep cognition)
set -euo pipefail
PASS="9aac5c811e6d4f4f64a00c65666f3528"
DIR="/opt/delta/deploy/heartbeat"
LOG="/var/log/mycelium-dream.log"
echo "[$(date)] Dream cycle starting" >> $LOG
# Deep protocols: dream round, immune, health, fatal
for f in 10-heal-dream.cypher 11-immune.cypher 15-health-check.cypher 16-agent-fatal-check.cypher; do
  echo "  $f..." >> $LOG
  docker exec mycelium-neo4j cypher-shell -u neo4j -p $PASS --format plain < $DIR/$f 2>> $LOG || true
done
echo "[$(date)] Dream cycle complete" >> $LOG
