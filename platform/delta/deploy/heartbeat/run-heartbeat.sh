#!/bin/bash
set -euo pipefail
PASS="9aac5c811e6d4f4f64a00c65666f3528"
DIR="/opt/delta/deploy/heartbeat"
LOG="/var/log/mycelium-heartbeat.log"

echo "[$(date)] Heartbeat starting" >> $LOG

# Fast signal processing only (01-09, 12-14): wake, connect, converge, decay,
# dedup, heal-orphans, liveness, report, snapshot.
# Dream protocols (10-heal-dream, 11-immune, 15-health-check,
# 16-agent-fatal-check) moved to the 4h dream cycle; invariants (17) moved to
# the 24h deep cycle.
for f in $DIR/0[1-9]-*.cypher $DIR/1[2-4]-*.cypher; do
    [ -e "$f" ] || continue
    echo "  $(basename "$f" .cypher)..." >> $LOG
    docker exec mycelium-neo4j cypher-shell -u neo4j -p $PASS --format plain < "$f" 2>> $LOG || true
done

echo "[$(date)] Heartbeat complete" >> $LOG
