#!/usr/bin/env bash
# ============================================================================
# Mycelium — one-shot installer (multi-target, team distribution)
# ============================================================================
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/kagrawal29/mycelium/dev/kshitiz/cypher-native-v1/install.sh | bash
#
# Installs to $HOME/.mycelium. Bakes read tokens for prod + dev on pulse.
# After install:
#   mycelium targets           # list configured targets
#   mycelium use prod          # set default target
#   mycelium status            # run against default
#   mycelium --target dev health
# ============================================================================
set -euo pipefail

MYCELIUM_DIR="${MYCELIUM_DIR:-$HOME/.mycelium}"
BRANCH="${MAVERICK_BRANCH:-main}"
REPO_SLUG="${MAVERICK_REPO:-Qubit-Capital/maverick}"
PROD_HOST="${MYCELIUM_PROD_HOST:-5.78.206.137}"
DEV_HOST="${MYCELIUM_DEV_HOST:-5.78.206.137}"

say() { printf '\e[1;36m[maverick]\e[0m %s\n' "$*"; }
ok()  { printf '\e[32m✓\e[0m %s\n' "$*"; }

command -v git >/dev/null     || { echo "git required"; exit 1; }
command -v python3 >/dev/null || { echo "python3 required"; exit 1; }
command -v gh >/dev/null      || { echo "gh CLI required (https://cli.github.com). Then: gh auth login"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "run 'gh auth login' first (you need Qubit-Capital org access)"; exit 1; }

say "installing to $MYCELIUM_DIR"
mkdir -p "$MYCELIUM_DIR/config" "$MYCELIUM_DIR/bin"

say "fetching $REPO_SLUG (branch: $BRANCH)"
if [ -d "$MYCELIUM_DIR/source/.git" ]; then
  git -C "$MYCELIUM_DIR/source" fetch origin "$BRANCH" --quiet
  git -C "$MYCELIUM_DIR/source" checkout --quiet "$BRANCH"
  git -C "$MYCELIUM_DIR/source" pull --ff-only --quiet
else
  gh repo clone "$REPO_SLUG" "$MYCELIUM_DIR/source" -- -b "$BRANCH" --quiet
fi

say "writing target config (prod, dev, local)"
cat > "$MYCELIUM_DIR/config/targets.json" <<CFG
{
  "prod": {
    "http": "http://$PROD_HOST:7474",
    "bolt": "bolt://$PROD_HOST:7687",
    "user": "neo4j",
    "pass": "mycelium-prod-9f3k2",
    "note": "pulse — canonical loaded state, ticking"
  },
  "dev": {
    "http": "http://$DEV_HOST:7475",
    "bolt": "bolt://$DEV_HOST:7688",
    "user": "neo4j",
    "pass": "mycelium-dev-7r8p4",
    "note": "pulse — alive, evolving"
  },
  "local": {
    "http": "http://127.0.0.1:7474",
    "bolt": "bolt://127.0.0.1:7687",
    "user": "neo4j",
    "pass": "localtest12",
    "note": "your laptop (requires native Neo4j install)"
  }
}
CFG

say "writing multi-target dispatcher"
cat > "$MYCELIUM_DIR/bin/mycelium" <<'WRAP'
#!/usr/bin/env bash
# Multi-target mycelium CLI. See `mycelium help`.
set -euo pipefail
MROOT="${MYCELIUM_DIR:-$HOME/.mycelium}"
CFG="$MROOT/config/targets.json"
CUR="$MROOT/config/current"
SRC="$MROOT/source"

TARGET="${MYCELIUM_TARGET:-}"
if [ "${1:-}" = "--target" ] && [ -n "${2:-}" ]; then TARGET="$2"; shift 2; fi
if [ -z "$TARGET" ] && [ -f "$CUR" ]; then TARGET=$(cat "$CUR"); fi
[ -z "$TARGET" ] && TARGET="local"

case "${1:-}" in
  use)
    [ -z "${2:-}" ] && { echo "usage: mycelium use <prod|dev|local>"; exit 1; }
    echo "$2" > "$CUR"; echo "default target: $2"; exit 0 ;;
  targets)
    python3 -c "import json; d=json.load(open('$CFG')); [print(f'  {k:8s} {v[\"http\"]:36s} {v.get(\"note\",\"\")}') for k,v in d.items()]"
    exit 0 ;;
  current)
    echo "$TARGET"; exit 0 ;;
  help|--help|-h)
    cat <<HLP
mycelium — cypher-native operator CLI (multi-target)

Target selection:
  mycelium use <name>            set sticky default (~/.mycelium/config/current)
  mycelium --target <n> <cmd>    one-shot override
  MYCELIUM_TARGET env var        session default
  fallback: local

Commands (all targets):
  status  health  doctor  test  protocols  verify  dream  ask  backup  bench  swarm
  shell "CYPHER"                 raw query
  targets                        list configured targets
  current                        show active target
  use <name>                     set default
HLP
    exit 0 ;;
esac

eval "$(python3 - <<PY
import json,sys
try:
    d=json.load(open("$CFG"))["$TARGET"]
except KeyError:
    sys.exit(f"unknown target: $TARGET  (try: mycelium targets)")
print(f'export NEO4J_BOLT={d["bolt"]}')
print(f'export NEO4J_HTTP={d["http"]}')
print(f'export NEO4J_USER={d["user"]}')
print(f'export NEO4J_PASS={d["pass"]}')
PY
)"

cd "$SRC" && exec ./mycelium "$@"
WRAP
chmod +x "$MYCELIUM_DIR/bin/mycelium"

say "linking into PATH"
mkdir -p "$HOME/.local/bin"
ln -sf "$MYCELIUM_DIR/bin/mycelium" "$HOME/.local/bin/mycelium"

if ! echo ":$PATH:" | grep -q ":$HOME/.local/bin:"; then
  case "${SHELL##*/}" in
    zsh)  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"  ;;
    bash) echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc" ;;
  esac
  say "added ~/.local/bin to PATH — restart shell or: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# ============================================================================
# Install CLAUDE.md directives (wi-tc-01)
# ============================================================================
install_claude_md_directives() {
  local claude_md="${HOME}/.claude/CLAUDE.md"

  # Ensure ~/.claude exists
  mkdir -p "$(dirname "$claude_md")"

  # Create CLAUDE.md if missing
  if [ ! -f "$claude_md" ]; then
    say "creating ~/.claude/CLAUDE.md"
    cat > "$claude_md" <<EOF
# Team CLAUDE.md — Directives for Claude Code Sessions

This file is auto-managed. Do not edit the MAVERICK_BLOCK.
EOF
  fi

  # Check if block already exists
  if grep -q "<!-- MAVERICK_BLOCK_START -->" "$claude_md"; then
    say "CLAUDE.md directives already installed, updating"
    # Remove old block and insert new one
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' '/<!-- MAVERICK_BLOCK_START -->/,/<!-- MAVERICK_BLOCK_END -->/d' "$claude_md"
    else
      sed -i '/<!-- MAVERICK_BLOCK_START -->/,/<!-- MAVERICK_BLOCK_END -->/d' "$claude_md"
    fi
  else
    say "installing CLAUDE.md directives"
  fi

  # Append the block
  bash "$(dirname "$0")/install/claude-md-block.sh" >> "$claude_md"
}

install_claude_md_directives

ok "installed. try:  mycelium targets  |  mycelium use prod  |  mycelium status"
