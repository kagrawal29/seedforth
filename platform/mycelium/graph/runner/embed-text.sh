#!/usr/bin/env bash
# embed-text.sh -- embed arbitrary text via Ollama, return CSV floats
# Usage: bash graph/runner/embed-text.sh "some text"
#        echo "some text" | bash graph/runner/embed-text.sh
set -euo pipefail

TEXT="${1:-$(cat)}"
if [ -z "$TEXT" ]; then
  echo "usage: embed-text.sh <text>" >&2
  exit 1
fi

python3 -c "
import sys, json, requests
text = sys.argv[1]
resp = requests.post('http://localhost:11434/api/embeddings',
                     json={'model': 'nomic-embed-text', 'prompt': text}, timeout=30)
resp.raise_for_status()
vec = resp.json().get('embedding', [])
if not vec:
    print('error: empty embedding', file=sys.stderr)
    sys.exit(1)
print(','.join(str(x) for x in vec))
" "$TEXT"
