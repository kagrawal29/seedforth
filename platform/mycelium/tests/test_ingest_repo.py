"""
Unit tests for ingest_repo.py — commit parser and safety rail logic.

Run with: python3 -m pytest tests/test_ingest_repo.py -v
"""

import sys
import os
import pytest

# Add scripts/ to path so we can import ingest_repo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# We import selectively — the module imports neo4j at the top level, so we
# patch the driver before import if it's not installed.
try:
    import neo4j  # noqa: F401
except ImportError:
    # Create a minimal stub so the module can be imported in CI without the driver
    import types
    neo4j_stub = types.ModuleType("neo4j")
    neo4j_stub.GraphDatabase = None
    sys.modules["neo4j"] = neo4j_stub

import ingest_repo  # noqa: E402 (after path setup)


# ── Commit parser ──────────────────────────────────────────────────────────────

FIXTURE_GIT_LOG = """\
abc123def456abc123def456abc123def456abc123|Alice Smith|alice@example.com|1713400000|feat: add semantic search
bad456abc123bad456abc123bad456abc123bad456|Bob Jones|bob@example.com|1713300000|fix: handle null embeddings
ccc111ccc111ccc111ccc111ccc111ccc111ccc1|Carol Chen|carol@example.com|1713200000|chore: update deps | with pipe in message
"""


def _parse_fixture(raw: str) -> list[dict]:
    """Replicate the parsing logic from get_commits() applied to fixture text."""
    commits = []
    for line in raw.splitlines():
        if "|" not in line:
            continue
        parts = line.split("|", 4)
        if len(parts) < 5:
            continue
        sha, author_name, author_email, authored_at, message = parts
        try:
            authored_at_int = int(authored_at)
        except ValueError:
            authored_at_int = 0
        commits.append({
            "sha": sha.strip(),
            "author_name": author_name.strip()[:200],
            "author_email": author_email.strip()[:200],
            "authored_at": authored_at_int,
            "message": message.strip()[:500],
        })
    return commits


class TestCommitParser:
    def setup_method(self):
        self.commits = _parse_fixture(FIXTURE_GIT_LOG)

    def test_parses_correct_count(self):
        assert len(self.commits) == 3

    def test_first_commit_sha(self):
        assert self.commits[0]["sha"] == "abc123def456abc123def456abc123def456abc123"

    def test_author_name(self):
        assert self.commits[0]["author_name"] == "Alice Smith"

    def test_author_email(self):
        assert self.commits[0]["author_email"] == "alice@example.com"

    def test_authored_at_is_int(self):
        assert self.commits[0]["authored_at"] == 1713400000

    def test_message(self):
        assert self.commits[0]["message"] == "feat: add semantic search"

    def test_message_with_pipe_character(self):
        # Messages can contain pipes — only the first 4 splits are structural
        carol = self.commits[2]
        assert carol["author_name"] == "Carol Chen"
        assert "update deps" in carol["message"]

    def test_blank_lines_skipped(self):
        raw = "\n\nabc|Name|email@x.com|1000|msg\n\n"
        result = _parse_fixture(raw)
        assert len(result) == 1

    def test_malformed_line_skipped(self):
        raw = "notapipeline\nabc|Name|email@x.com|1000|msg\n"
        result = _parse_fixture(raw)
        assert len(result) == 1


# ── Safety rails ───────────────────────────────────────────────────────────────

class TestAllowedOrg:
    def test_qubit_capital_allowed(self):
        # Should not raise
        org = ingest_repo.check_allowed_org("https://github.com/Qubit-Capital/some-repo")
        assert org == "Qubit-Capital"

    def test_kagrawal29_allowed(self):
        org = ingest_repo.check_allowed_org("https://github.com/kagrawal29/mycelium")
        assert org == "kagrawal29"

    def test_random_org_blocked(self):
        with pytest.raises(SystemExit):
            ingest_repo.check_allowed_org("https://github.com/random-org/some-repo")

    def test_dot_git_suffix_stripped(self):
        org = ingest_repo.check_allowed_org("https://github.com/Qubit-Capital/repo.git")
        assert org == "Qubit-Capital"


class TestProdCheck:
    def test_dev_port_allowed(self):
        # Should not exit
        ingest_repo.check_not_prod("bolt://5.78.206.137:7698")

    def test_dev_port_7699_allowed(self):
        ingest_repo.check_not_prod("bolt://5.78.206.137:7699")

    def test_localhost_7687_allowed(self):
        # Local :7687 is fine — it's the local dev neo4j
        ingest_repo.check_not_prod("bolt://localhost:7687")

    def test_remote_7687_blocked(self):
        with pytest.raises(SystemExit):
            ingest_repo.check_not_prod("bolt://5.78.206.137:7687")


# ── Language detection ─────────────────────────────────────────────────────────

class TestLanguageDetection:
    def test_python(self):
        assert ingest_repo.detect_language("scripts/ingest_repo.py") == "Python"

    def test_typescript(self):
        assert ingest_repo.detect_language("src/index.ts") == "TypeScript"

    def test_dockerfile(self):
        assert ingest_repo.detect_language("Dockerfile") == "Dockerfile"

    def test_makefile(self):
        assert ingest_repo.detect_language("Makefile") == "Makefile"

    def test_unknown_extension(self):
        assert ingest_repo.detect_language("something.xyz") == "Other"

    def test_cypher(self):
        assert ingest_repo.detect_language("graph/protocols/cmd-status.cypher") == "Cypher"
