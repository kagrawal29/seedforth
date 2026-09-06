#!/bin/bash
set -euo pipefail
BACKUP_DIR="/opt/backups/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

echo "Backing up to $BACKUP_DIR..."

# 1. Supervisor configs (critical for DR restore)
mkdir -p "$BACKUP_DIR/supervisor-confs"
cp -r /etc/supervisor/conf.d/proj-*.conf "$BACKUP_DIR/supervisor-confs/" 2>/dev/null || true

# 2. Project directories (SQLite session DBs, conversation logs, git repos)
rsync -a --exclude 'node_modules' --exclude '.npm' /home/proj-*/ "$BACKUP_DIR/home-proj/"

# 3. Delta registry
cp /opt/delta/delta-registry.json "$BACKUP_DIR/"

# 4. Environment config
cp /opt/delta/delta.env "$BACKUP_DIR/"

# 5. Local Neo4j staging data
cp -r /var/lib/neo4j/data/ "$BACKUP_DIR/neo4j-data/"

# 6. Auth template
cp /opt/delta/auth.json.template "$BACKUP_DIR/" 2>/dev/null || true

echo "Backup complete: $BACKUP_DIR"
tar -czf "$BACKUP_DIR.tar.gz" -C "$BACKUP_DIR" .
rm -rf "$BACKUP_DIR"
echo "Compressed: $BACKUP_DIR.tar.gz"

# Cleanup old backups (keep 7 days)
find /opt/backups/ -name "*.tar.gz" -mtime +7 -delete
