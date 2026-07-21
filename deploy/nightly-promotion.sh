#!/bin/bash
set -euo pipefail
# Nightly promotion: agent-written facts → mycelium dev graph
# Runs at 2am UTC via cron

STAGING_DIR="/opt/mycelium/graph/knowledge"
EXPORT_SCRIPT="/opt/delta/tools/export-staging.py"
MYCELIUM_DIR="/opt/mycelium"
DATE=$(date +%Y-%m-%d)

echo "[1/7] Exporting pending facts from local Neo4j..."
python3 "$EXPORT_SCRIPT" --split-by-project --output "$STAGING_DIR"

echo "[2/7] Validating exported facts..."
for f in "$STAGING_DIR"/agent-facts-*.cypher; do
    if [ -f "$f" ]; then
        echo "  Validating $f..."
        bash "$MYCELIUM_DIR/graph/runner/validate-merge.sh" "$f" || {
            echo "  FAILED validation: $f — skipping"
            mv "$f" "$f.failed"
        }
    fi
done

echo "[3/7] Committing to mycelium repo..."
cd "$MYCELIUM_DIR"
git checkout -b "agent-promotion/${DATE}" 2>/dev/null || git checkout "agent-promotion/${DATE}"
git add graph/knowledge/agent-facts-*.cypher
git commit -m "agent-promotion: nightly facts ${DATE}" || echo "  Nothing to commit"

echo "[4/7] Opening PR..."
gh pr create --repo kagrawal29/mycelium \
    --base main \
    --head "agent-promotion/${DATE}" \
    --title "agent-promotion: nightly facts ${DATE}" \
    --body "Automated nightly promotion of agent-written facts from Delta agents." \
    || echo "  PR already exists or no changes"

echo "[5/7] Waiting for CI (auto-merge on green)..."
# CI runs mycelium proof-of-merge (dry-run validation) + bootstrap
# When CI is green, PR auto-merges

echo "[6/7] Bootstrapping to dev..."
# Post-merge: mycelium bootstrap --target dev (triggered by CI)

echo "[7/7] Crystallizing (minting new Species)..."
mycelium-dev crystallize --target dev

echo "[7.5/7] Regenerating embeddings..."
mycelium embed --target dev

echo "=== Nightly promotion complete ==="
