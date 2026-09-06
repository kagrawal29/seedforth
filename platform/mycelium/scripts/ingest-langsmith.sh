#!/bin/bash
# Fetches recent LangSmith traces across all team projects
# Usage: ./scripts/ingest-langsmith.sh [--quick|--full]
set -euo pipefail

MODE="${1:---quick}"
API_KEY="${CC_LANGSMITH_API_KEY:?CC_LANGSMITH_API_KEY env var required}"
BASE="https://api.smith.langchain.com/api/v1"
OUTPUT_DIR="signals/langsmith"
DATE=$(date +%Y-%m-%d)

# All team projects
declare -A PROJECTS
PROJECTS=(
  ["Pranav"]="7d991519-fad6-4ede-bed1-9be395152ebe"
  ["Ankit-S"]="3473bc94-aa22-40ab-80bd-8588c9b00861"
  ["Kshitiz"]="ce70362b-3f8f-499b-b90c-a09f45bb000b"
  ["Sahiram"]="f6b7d95f-ebda-48e6-81f9-9cfdbe28294c"
  ["Abhishek"]="43265e84-4cad-452b-b2d2-65859553e043"
  ["Sahil"]="bf63ca28-62c6-4466-9c3b-97e6f6bbc32a"
)

if [ "$MODE" = "--quick" ]; then
  LIMIT=3
  echo "=== Quick LangSmith Poll (last 3 turns per person) ==="
else
  LIMIT=20
  echo "=== Full LangSmith Ingest (last 20 turns per person) ==="
fi

mkdir -p "$OUTPUT_DIR"
OUTFILE="$OUTPUT_DIR/$DATE.md"

{
  echo "# LangSmith Trace Digest — $DATE"
  echo "Ingested at: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""

  for PERSON in "${!PROJECTS[@]}"; do
    PID="${PROJECTS[$PERSON]}"

    TRACE_DATA=$(curl -s "$BASE/runs/query" \
      -H "x-api-key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"session\": [\"$PID\"], \"limit\": $LIMIT, \"is_root\": true}" 2>/dev/null)

    RUN_COUNT=$(echo "$TRACE_DATA" | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('runs',[])))" 2>/dev/null || echo "0")

    if [ "$RUN_COUNT" = "0" ]; then
      continue
    fi

    echo "## $PERSON ($RUN_COUNT turns)"
    echo ""

    echo "$TRACE_DATA" | python3 -c "
import json, sys
data = json.load(sys.stdin)
runs = data.get('runs', [])
total_tokens = sum((r.get('total_tokens',0) or 0) for r in runs)
print(f'Total tokens: {total_tokens:,}')
print()

for r in runs:
    status = r.get('status','?')
    start = str(r.get('start_time','?'))[:19]
    tokens = r.get('total_tokens',0) or 0

    # Extract user message
    user_msg = ''
    inp = r.get('inputs', {})
    if isinstance(inp, dict):
        msgs = inp.get('messages', [])
        if isinstance(msgs, list):
            for m in reversed(msgs):
                if isinstance(m, dict) and m.get('role') == 'user':
                    c = m.get('content','')
                    if isinstance(c, str):
                        user_msg = c[:300]
                    elif isinstance(c, list):
                        for part in c:
                            if isinstance(part, dict) and part.get('type') == 'text':
                                user_msg = part.get('text','')[:300]
                                break
                    break

    # Extract Claude response
    claude_msg = ''
    out = r.get('outputs', {})
    if isinstance(out, dict):
        msgs = out.get('messages', [])
        if isinstance(msgs, list) and msgs:
            c = msgs[-1].get('content','') if isinstance(msgs[-1], dict) else ''
            claude_msg = str(c)[:500]

    # Skip task-notification noise
    if user_msg.startswith('<task-notification>'):
        user_msg = '[subagent task completion]'

    print(f'### [{status}] {start} | {tokens:,} tokens')
    print(f'**User:** {user_msg}')
    if claude_msg:
        print(f'**Claude:** {claude_msg}')
    print()
" 2>/dev/null

  done
} >> "$OUTFILE"

echo "Written to $OUTFILE"
