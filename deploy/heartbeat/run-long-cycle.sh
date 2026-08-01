#!/bin/bash
# Long cycle - every 7 days (metabolic consolidation)
set -euo pipefail
PASS="9aac5c811e6d4f4f64a00c65666f3528"
DIR="/opt/delta/deploy/heartbeat"
LOG="/var/log/mycelium-long.log"
echo "[$(date)] Long cycle starting" >> $LOG
# Snapshot fold placeholder: merge the week's snapshots into a weekly summary
docker exec mycelium-neo4j cypher-shell -u neo4j -p $PASS --format plain <<'CYPHER' >> $LOG 2>&1 || true
MATCH (s:Snapshot)
WITH count(s) AS weekly_snapshots
MERGE (w:WeeklyFold {node_id: "weekly-fold-" + toString(date({timezone:"UTC"}))})
ON CREATE SET
  w.fold_date = date(),
  w.snapshot_count = weekly_snapshots,
  w.created_at = datetime(),
  w.project = 'system'
ON MATCH SET
  w.snapshot_count = weekly_snapshots,
  w.updated_at = datetime()
RETURN w.node_id AS fold, w.snapshot_count AS snapshots;
CYPHER
echo "[$(date)] Long cycle complete" >> $LOG
