#!/usr/bin/env bash
# Consistent offline backup for the explicitly identified production container.
# Run only during an authorized upgrade maintenance window on delta2.
set -euo pipefail
test "$(hostname)" = "vmi3556896"
test "$(id -u)" = 0
docker inspect mycelium-neo4j >/dev/null
umask 077
mkdir -p /opt/seedforth/shared/backups
backup_dir=$(mktemp -d /opt/seedforth/shared/backups/upgrade-20260906.XXXXXXXX)
image_id=$(docker inspect --format '{{.Image}}' mycelium-neo4j)
restore_running() {
  docker start mycelium-neo4j >/dev/null
}
trap restore_running EXIT
docker stop --time 30 mycelium-neo4j >/dev/null
docker run --rm --user 0 --volumes-from mycelium-neo4j \
  -v "$backup_dir:/backups" --entrypoint neo4j-admin "$image_id" \
  database dump neo4j --to-path=/backups
test -s "$backup_dir/neo4j.dump"
chmod 600 "$backup_dir/neo4j.dump"
sha256sum "$backup_dir/neo4j.dump"
printf 'BACKUP_DIR=%s\n' "$backup_dir"
