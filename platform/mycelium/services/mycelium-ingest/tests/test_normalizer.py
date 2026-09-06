"""
Unit tests for normalizer.py.

No Neo4j, no network, no GitHub API calls.
Tests that given sample fixture payloads, normalize() returns the expected
MERGE plan (correct node labels, properties, and edges).
"""

import json
import sys
from pathlib import Path

import pytest

# Make sure the service package is importable without installing
sys.path.insert(0, str(Path(__file__).parent.parent))

from normalizer import normalize

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def cypher_labels(stmts: list[dict]) -> set[str]:
    """Extract all node labels mentioned in MERGE/MATCH clauses."""
    import re
    labels = set()
    for s in stmts:
        labels |= set(re.findall(r":([A-Za-z]+)\s*\{", s["cypher"]))
    return labels


def rel_types(stmts: list[dict]) -> set[str]:
    """Extract all relationship types."""
    import re
    rels = set()
    for s in stmts:
        rels |= set(re.findall(r"\[:([A-Z_]+)\]", s["cypher"]))
    return rels


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------

class TestPush:
    def setup_method(self):
        self.payload = load("push.json")
        self.stmts = normalize("push", self.payload, "maverick-marketing")

    def test_returns_statements(self):
        assert len(self.stmts) > 0

    def test_all_stmts_have_cypher_and_params(self):
        for s in self.stmts:
            assert "cypher" in s
            assert "params" in s

    def test_creates_branch_node(self):
        assert "Branch" in cypher_labels(self.stmts)

    def test_creates_commit_nodes(self):
        assert "Commit" in cypher_labels(self.stmts)

    def test_creates_author_nodes(self):
        assert "Author" in cypher_labels(self.stmts)

    def test_on_branch_edge(self):
        assert "ON_BRANCH" in rel_types(self.stmts)

    def test_authored_by_edge(self):
        assert "AUTHORED_BY" in rel_types(self.stmts)

    def test_commit_sha_in_params(self):
        shas = [s["params"].get("sha") for s in self.stmts if "sha" in s["params"]]
        assert "abc123def456" in shas
        assert "def789ghi012" in shas

    def test_project_tag_in_all_params(self):
        for s in self.stmts:
            assert s["params"].get("project") == "maverick-marketing"

    def test_branch_name_extracted(self):
        branch_stmts = [s for s in self.stmts if "name" in s["params"] and "Branch" in s["cypher"]]
        names = [s["params"]["name"] for s in branch_stmts]
        assert "main" in names

    def test_empty_commits_ok(self):
        """A push with no commits should not crash."""
        payload = {**self.payload, "commits": []}
        stmts = normalize("push", payload, "maverick-marketing")
        # Should still have the Branch merge
        assert any("Branch" in s["cypher"] for s in stmts)


# ---------------------------------------------------------------------------
# pull_request
# ---------------------------------------------------------------------------

class TestPullRequest:
    def setup_method(self):
        self.payload = load("pull_request.json")
        self.stmts = normalize("pull_request", self.payload, "maverick")

    def test_pr_node(self):
        assert "PullRequest" in cypher_labels(self.stmts)

    def test_author_node(self):
        assert "Author" in cypher_labels(self.stmts)

    def test_targets_edge(self):
        assert "TARGETS" in rel_types(self.stmts)

    def test_authored_by_edge(self):
        assert "AUTHORED_BY" in rel_types(self.stmts)

    def test_pr_number_in_params(self):
        numbers = [s["params"].get("number") for s in self.stmts if "number" in s["params"]]
        assert 42 in numbers

    def test_project_tag(self):
        for s in self.stmts:
            assert s["params"].get("project") == "maverick"

    def test_missing_pull_request_key_returns_empty(self):
        stmts = normalize("pull_request", {"action": "opened"}, "maverick")
        assert stmts == []


# ---------------------------------------------------------------------------
# issues
# ---------------------------------------------------------------------------

class TestIssues:
    def setup_method(self):
        self.payload = load("issues.json")
        self.stmts = normalize("issues", self.payload, "vc-ai-associate")

    def test_issue_node(self):
        assert "Issue" in cypher_labels(self.stmts)

    def test_author_node(self):
        assert "Author" in cypher_labels(self.stmts)

    def test_authored_by_edge(self):
        assert "AUTHORED_BY" in rel_types(self.stmts)

    def test_issue_number(self):
        numbers = [s["params"].get("number") for s in self.stmts if "number" in s["params"]]
        assert 7 in numbers


# ---------------------------------------------------------------------------
# issue_comment
# ---------------------------------------------------------------------------

class TestIssueComment:
    def setup_method(self):
        self.payload = load("issue_comment.json")
        self.stmts = normalize("issue_comment", self.payload, "vc-ai-associate")

    def test_review_comment_node(self):
        assert "ReviewComment" in cypher_labels(self.stmts)

    def test_comments_on_edge(self):
        assert "COMMENTS_ON" in rel_types(self.stmts)

    def test_authored_by_edge(self):
        assert "AUTHORED_BY" in rel_types(self.stmts)

    def test_comment_id(self):
        ids = [s["params"].get("id") for s in self.stmts if "id" in s["params"]]
        assert 9900001 in ids


# ---------------------------------------------------------------------------
# pr_review_comment
# ---------------------------------------------------------------------------

class TestPRReviewComment:
    def setup_method(self):
        self.payload = load("pr_review_comment.json")
        self.stmts = normalize("pull_request_review_comment", self.payload, "maverick")

    def test_review_comment_node(self):
        assert "ReviewComment" in cypher_labels(self.stmts)

    def test_comments_on_pr_edge(self):
        # The MATCH in the edge stmt references PullRequest
        pr_edges = [s for s in self.stmts if "PullRequest" in s["cypher"] and "COMMENTS_ON" in s["cypher"]]
        assert len(pr_edges) == 1

    def test_comment_id(self):
        ids = [s["params"].get("id") for s in self.stmts if "id" in s["params"]]
        assert 8800001 in ids


# ---------------------------------------------------------------------------
# release
# ---------------------------------------------------------------------------

class TestRelease:
    def setup_method(self):
        self.payload = load("release.json")
        self.stmts = normalize("release", self.payload, "maverick")

    def test_release_node(self):
        assert "Release" in cypher_labels(self.stmts)

    def test_tag_in_params(self):
        tags = [s["params"].get("tag") for s in self.stmts if "tag" in s["params"]]
        assert "v1.2.0" in tags


# ---------------------------------------------------------------------------
# Unknown event type
# ---------------------------------------------------------------------------

def test_unknown_event_returns_empty():
    stmts = normalize("workflow_run", {}, "maverick")
    assert stmts == []
