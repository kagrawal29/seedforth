#!/usr/bin/env bash
# Restore only into a new, isolated volume. Never mounts production data.
set -euo pipefail
test "$(hostname)" = "vmi3556896"
backup_dir=/opt/seedforth/shared/backups/upgrade-20260906.I8ocj1Ch
volume=seedforth-upgrade-restore-20260906
container=seedforth-upgrade-restore-20260906
test -s "$backup_dir/neo4j.dump"
if docker volume inspect "$volume" >/dev/null 2>&1; then
  echo 'Restore volume already exists; inspect it rather than overwrite.' >&2
  exit 1
fi
image_id=$(docker inspect --format '{{.Image}}' mycelium-neo4j)
sha256sum "$backup_dir/neo4j.dump"
docker volume create "$volume"
docker run --rm --user 0 -v "$volume:/data" -v "$backup_dir:/backups:ro" \
  --entrypoint neo4j-admin "$image_id" database load neo4j --from-path=/backups
docker run --rm --user 0 -v "$volume:/data" --entrypoint chown "$image_id" -R 7474:7474 /data
docker run -d --name "$container" --memory 1536m \
  -p 127.0.0.1:28474:7474 -v "$volume:/data" \
  -e NEO4J_AUTH=none -e NEO4J_server_memory_heap_initial__size=128m \
  -e NEO4J_server_memory_heap_max__size=512m \
  -e NEO4J_server_memory_pagecache_size=256m "$image_id"
