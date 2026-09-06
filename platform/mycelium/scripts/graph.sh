#!/usr/bin/env bash
# Wrapper for the natural-language graph CLI.
# Usage:
#   scripts/graph.sh "graph health"
#   scripts/graph.sh                     # interactive prompt

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

python3 "${REPO_ROOT}/scripts/graph-cli.py" "$@"
