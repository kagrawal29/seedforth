#!/bin/bash
set -euo pipefail

# Mycelium v2 Production Deployment
# Replaces standalone maverick-meta container with v2 stack (FalkorDB + maverick-meta)
#
# Run this ON the production server (delta-server):
#   bash scripts/deploy-v2.sh
#
# Prerequisites:
#   - Docker + Docker Compose installed
#   - .env file with ANTHROPIC_API_KEY, CC_LANGSMITH_API_KEY, GH_TOKEN
#   - Current maverick-meta container running (will be stopped)

REPO_URL="https://github.com/Qubit-Capital/maverick-meta.git"
DEPLOY_DIR="/opt/maverick-meta"
COMPOSE_FILE="docker/docker-compose.production.yml"

echo "=========================================="
echo "  Mycelium v2 Production Deployment"
echo "=========================================="
echo ""

# Step 1: Clone or update the repo
if [ -d "$DEPLOY_DIR/.git" ]; then
    echo "[1/7] Updating repo..."
    cd "$DEPLOY_DIR"
    git fetch origin
    git checkout main
    git pull origin main
else
    echo "[1/7] Cloning repo..."
    git clone "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Step 2: Check for .env
if [ ! -f "$DEPLOY_DIR/docker/.env" ]; then
    echo "[2/7] Creating .env from current container..."
    # Extract from running container if it exists
    if docker inspect maverick-meta > /dev/null 2>&1; then
        docker exec maverick-meta env | grep -E "^(ANTHROPIC_API_KEY|CC_LANGSMITH_API_KEY|GH_TOKEN)=" > "$DEPLOY_DIR/docker/.env"
        echo "  Extracted $(wc -l < "$DEPLOY_DIR/docker/.env") env vars from running container"
    else
        echo "  ERROR: No .env file and no running container to extract from."
        echo "  Create docker/.env with: ANTHROPIC_API_KEY, CC_LANGSMITH_API_KEY, GH_TOKEN"
        exit 1
    fi
else
    echo "[2/7] .env exists ($(wc -l < "$DEPLOY_DIR/docker/.env") vars)"
fi

# Step 3: Stop old container (gracefully)
echo "[3/7] Stopping v1 container..."
if docker inspect maverick-meta > /dev/null 2>&1; then
    docker stop maverick-meta 2>/dev/null || true
    docker rm maverick-meta 2>/dev/null || true
    echo "  v1 container stopped and removed"
else
    echo "  No v1 container found (already stopped or first deploy)"
fi

# Step 4: Build v2 image
echo "[4/7] Building v2 image..."
cd "$DEPLOY_DIR/docker"
docker compose -f docker-compose.production.yml build maverick-meta

# Step 5: Start FalkorDB first (needs to be healthy before maverick-meta)
echo "[5/7] Starting FalkorDB..."
docker compose -f docker-compose.production.yml up -d falkordb
echo "  Waiting for FalkorDB health check..."
for i in $(seq 1 30); do
    if docker compose -f docker-compose.production.yml exec falkordb redis-cli -p 6379 ping 2>/dev/null | grep -q PONG; then
        echo "  FalkorDB healthy after ${i}s"
        break
    fi
    sleep 1
done

# Step 6: Start maverick-meta
echo "[6/7] Starting maverick-meta v2..."
docker compose -f docker-compose.production.yml up -d maverick-meta
echo "  Waiting for boot..."
sleep 10

# Step 7: Verify
echo "[7/7] Verifying..."
echo ""
echo "  Containers:"
docker compose -f docker-compose.production.yml ps
echo ""
echo "  Logs (last 10 lines):"
docker compose -f docker-compose.production.yml logs maverick-meta --tail 10
echo ""
echo "  FalkorDB:"
docker compose -f docker-compose.production.yml exec falkordb redis-cli -p 6379 ping

echo ""
echo "=========================================="
echo "  Deployment complete!"
echo ""
echo "  Monitor: docker compose -f $COMPOSE_FILE logs -f maverick-meta"
echo "  Health:  docker compose -f $COMPOSE_FILE exec maverick-meta /healthcheck.sh"
echo "  Trigger: docker compose -f $COMPOSE_FILE exec maverick-meta su - maverick -c 'source /workspace/bin/env.sh && cd /workspace/maverick-meta && python3 agents/run-synthesis.py'"
echo "=========================================="
