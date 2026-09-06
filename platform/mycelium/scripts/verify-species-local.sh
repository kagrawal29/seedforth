#!/bin/bash
# verify-species-local.sh — local trustless verification of a species file.
# No GitHub. No network. Pure local check.
#
# Called by the git post-commit hook on the server when a species/* branch
# gets a new commit. Also runnable manually:
#
#   bash scripts/verify-species-local.sh <species_dna>
#   bash scripts/verify-species-local.sh   # verifies current graph-state.cypher
#
# Runs 5 independent cryptographic checks, all local, all offline.

set -e

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SPECIES_DNA="${1:-}"

cd "$REPO"

if [ -n "$SPECIES_DNA" ]; then
    BRANCH="species/$SPECIES_DNA"
    echo "=== verify-species-local: $BRANCH ==="
    # Checkout the species branch in a temp worktree
    WORKTREE="/tmp/verify-${SPECIES_DNA}"
    rm -rf "$WORKTREE"
    git worktree add "$WORKTREE" "$BRANCH" >/dev/null 2>&1
    FILE="$WORKTREE/graph-state.cypher"
else
    echo "=== verify-species-local: current graph-state.cypher ==="
    FILE="$REPO/graph-state.cypher"
fi

test -f "$FILE" || { echo "✗ FAIL: file not found: $FILE"; exit 1; }

# ── Check 1: file sha256 matches branch name (if branch given) ──
COMPUTED=$(sha256sum "$FILE" | cut -c1-16)
echo "file:            $FILE"
echo "computed sha256: $COMPUTED"
if [ -n "$SPECIES_DNA" ]; then
    if [ "$COMPUTED" != "$SPECIES_DNA" ]; then
        echo "✗ FAIL: file hash ($COMPUTED) != branch name ($SPECIES_DNA)"
        [ -n "$WORKTREE" ] && git worktree remove --force "$WORKTREE" >/dev/null 2>&1
        exit 1
    fi
    echo "✓ file hash matches branch name"
fi

# ── Check 2-5: manifest, commitment, signature, replay ──
python3 - "$FILE" "$REPO" << 'PY'
import sys, hashlib, re, os
from pathlib import Path

file_path = Path(sys.argv[1])
repo_root = Path(sys.argv[2])
content = file_path.read_text()

# Import signing helper from the main repo
sys.path.insert(0, str(repo_root / "scripts"))
from lib.signing import verify_bytes

# Header parse
header_fields = {}
for line in content.split("\n"):
    if not line.startswith("//") and line.strip() != "":
        break
    if line.startswith("// ") and ":" in line:
        s = line[3:]
        if len(s) > 2 and s[0] in "PTI" and s[1] == " ":
            continue
        k, v = s.split(":", 1)
        if k.strip() not in header_fields:
            header_fields[k.strip()] = v.strip()

parent_dna = header_fields.get("parent_dna")
signer_pubkey = header_fields.get("signer_pubkey")
signer_alias = header_fields.get("signer_alias")
signature = header_fields.get("signature")
commitment_claim = header_fields.get("commitment")
manifest_root_claim = header_fields.get("manifest_root")
git_anchor = header_fields.get("git_anchor")

print(f"signer:          {signer_alias} ({signer_pubkey[:16] if signer_pubkey else 'none'}...)")
print(f"parent:          {parent_dna}")
print(f"git_anchor:      {git_anchor}")

# Check 2: manifest root
manifest_line_re = re.compile(r'^//   ([PTI]) ([0-9a-f]{16}) (\S+)$')
manifest_lines = [line.replace("//   ", "", 1) for line in content.split("\n")[:500] if manifest_line_re.match(line)]
manifest_text = "\n".join(manifest_lines)
computed_root = hashlib.sha256(manifest_text.encode()).hexdigest()
manifest_ok = (computed_root == manifest_root_claim)
print(f"manifest:        {len(manifest_lines)} crystals, root {'✓' if manifest_ok else '✗'}")

# Check 3: commitment
commitment_msg = f"{parent_dna}|{manifest_root_claim}|{git_anchor}"
computed_commitment = hashlib.sha256(commitment_msg.encode()).hexdigest()
commit_ok = (computed_commitment == commitment_claim)
print(f"commitment:      {'✓' if commit_ok else '✗'}")

# Check 4: signature
sig_ok = False
if signer_pubkey and signature and commitment_claim:
    sig_ok = verify_bytes(signer_pubkey, bytes.fromhex(commitment_claim), signature)
print(f"signature:       {'✓' if sig_ok else '✗'}")

if not (manifest_ok and commit_ok and sig_ok):
    print()
    print("✗ FAIL — cryptographic checks did not pass")
    sys.exit(1)

print()
print("✓ cryptographic checks: all pass")

# Check 5: deterministic replay (restore body to a temp graph, re-export, compare)
# Only if FalkorDB is available locally
try:
    from falkordb import FalkorDB
    host = os.environ.get('FALKORDB_HOST', 'localhost')
    port = int(os.environ.get('FALKORDB_PORT', '6380'))
    db = FalkorDB(host=host, port=port)
except Exception as e:
    print(f"  (skipping replay check: FalkorDB not reachable at {host}:{port})")
    sys.exit(0)

graph_name = f"replay_{hashlib.sha256(content.encode()).hexdigest()[:8]}"
try:
    db.select_graph(graph_name).delete()
except Exception:
    pass
g = db.select_graph(graph_name)

# Extract body (everything after the second "// ====" close marker)
marker = "// ============================================================\n\n"
first = content.find(marker)
second = content.find(marker, first + len(marker)) if first != -1 else -1
if second != -1:
    body = content[second + len(marker):]
else:
    body = content

executed = errors = 0
for line in body.split("\n"):
    s = line.strip()
    if not s or s.startswith("//"):
        continue
    if s.endswith(";"):
        s = s[:-1]
    try:
        g.query(s)
        executed += 1
    except Exception:
        errors += 1

print(f"replay:          {executed} ok, {errors} errors")
if errors > max(5, executed * 0.01):
    print("✗ FAIL: replay errors exceeded threshold")
    try:
        g.delete()
    except Exception:
        pass
    sys.exit(1)

# Count nodes/edges
r = g.query("MATCH (n) RETURN count(n)")
nodes = r.result_set[0][0]
r = g.query("MATCH ()-[r]->() RETURN count(r)")
edges = r.result_set[0][0]
print(f"replay state:    {nodes} nodes, {edges} edges")

# Compare to header-claimed nodes/edges (1% tolerance for replay quirks)
expected_nodes = int(header_fields.get("nodes", 0))
expected_edges = int(header_fields.get("edges", 0))
node_tol = max(10, expected_nodes // 100)
edge_tol = max(10, expected_edges // 100)
node_diff = abs(nodes - expected_nodes)
edge_diff = abs(edges - expected_edges)
if node_diff > node_tol:
    print(f"✗ FAIL: replay nodes ({nodes}) differs from claimed ({expected_nodes}) by {node_diff} (tolerance {node_tol})")
    try: g.delete()
    except: pass
    sys.exit(1)
if edge_diff > edge_tol:
    print(f"✗ FAIL: replay edges ({edges}) differs from claimed ({expected_edges}) by {edge_diff} (tolerance {edge_tol})")
    try: g.delete()
    except: pass
    sys.exit(1)

print(f"✓ replay state within tolerance of header claim (nodes Δ{node_diff}, edges Δ{edge_diff})")

# Cleanup
try:
    g.delete()
except Exception:
    pass

print()
print("═══════════════════════════════════════════════════════")
print("  SPECIES VERIFIED LOCALLY — TRUSTLESS CHECKS PASS")
print("═══════════════════════════════════════════════════════")
PY

PY_EXIT=$?

# Cleanup worktree
if [ -n "$WORKTREE" ] && [ -d "$WORKTREE" ]; then
    git worktree remove --force "$WORKTREE" >/dev/null 2>&1
fi

exit $PY_EXIT
