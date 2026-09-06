"""Tests for enriched snapshot helpers.

Tests _read_project_claude_md(), _read_project_memory_files(),
_build_enriched_snapshot(), and depth parameter behavior.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


# -- Helpers ---------------------------------------------------------------

def _setup_project_dir(tmp_path, seed="", claude_md="", memory_files=None,
                       schedule=None, commits=None):
    """Create a minimal project directory structure for testing."""
    # SEED.md
    if seed:
        (tmp_path / "SEED.md").write_text(seed)

    # CLAUDE.md
    if claude_md:
        (tmp_path / "CLAUDE.md").write_text(claude_md)

    # memory/*.md
    if memory_files:
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        for name, content in memory_files.items():
            (mem_dir / name).write_text(content)

    # delta-config/
    config_dir = tmp_path / "delta-config"
    config_dir.mkdir()

    if schedule:
        (config_dir / "schedule.json").write_text(json.dumps(schedule))

    # logs dir
    (config_dir / "logs").mkdir()

    return tmp_path


# -- Tests: _read_project_claude_md ----------------------------------------

class TestReadProjectClaudeMd:

    def test_reads_claude_md(self, tmp_path):
        from delta.app import _read_project_claude_md

        content = "# My Project\n\nThis is a test project.\n" * 10
        (tmp_path / "CLAUDE.md").write_text(content)

        result = _read_project_claude_md(str(tmp_path), max_chars=50)
        assert len(result) == 50
        assert result.startswith("# My Project")

    def test_missing_claude_md(self, tmp_path):
        from delta.app import _read_project_claude_md

        result = _read_project_claude_md(str(tmp_path))
        assert result == ""

    def test_full_content_under_limit(self, tmp_path):
        from delta.app import _read_project_claude_md

        content = "# Short\nBrief."
        (tmp_path / "CLAUDE.md").write_text(content)

        result = _read_project_claude_md(str(tmp_path), max_chars=3000)
        assert result == content

    def test_default_limit_is_3000(self, tmp_path):
        from delta.app import _read_project_claude_md

        content = "x" * 5000
        (tmp_path / "CLAUDE.md").write_text(content)

        result = _read_project_claude_md(str(tmp_path))
        assert len(result) == 3000


# -- Tests: _read_project_memory_files ------------------------------------

class TestReadProjectMemoryFiles:

    def test_reads_memory_files(self, tmp_path):
        from delta.app import _read_project_memory_files

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "profile.md").write_text("User is a developer.")
        (mem_dir / "notes.md").write_text("Some notes here.")

        result = _read_project_memory_files(str(tmp_path), max_chars=5000)
        assert "## notes.md" in result
        assert "## profile.md" in result
        assert "User is a developer." in result
        assert "Some notes here." in result

    def test_empty_memory_dir(self, tmp_path):
        from delta.app import _read_project_memory_files

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()

        result = _read_project_memory_files(str(tmp_path))
        assert result == ""

    def test_no_memory_dir(self, tmp_path):
        from delta.app import _read_project_memory_files

        result = _read_project_memory_files(str(tmp_path))
        assert result == ""

    def test_truncation(self, tmp_path):
        from delta.app import _read_project_memory_files

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "big.md").write_text("x" * 3000)

        result = _read_project_memory_files(str(tmp_path), max_chars=200)
        assert len(result) <= 200

    def test_skips_non_md_files(self, tmp_path):
        from delta.app import _read_project_memory_files

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "data.json").write_text('{"key": "value"}')
        (mem_dir / "readme.md").write_text("Only this.")

        result = _read_project_memory_files(str(tmp_path), max_chars=5000)
        assert "## readme.md" in result
        assert "data.json" not in result

    def test_files_sorted_alphabetically(self, tmp_path):
        from delta.app import _read_project_memory_files

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        (mem_dir / "b-notes.md").write_text("B content")
        (mem_dir / "a-profile.md").write_text("A content")

        result = _read_project_memory_files(str(tmp_path), max_chars=5000)
        pos_a = result.index("## a-profile.md")
        pos_b = result.index("## b-notes.md")
        assert pos_a < pos_b


# -- Tests: _build_enriched_snapshot --------------------------------------

class TestBuildEnrichedSnapshot:

    def test_standard_depth_excludes_claude_md_and_memory(self, tmp_path):
        from delta.app import _build_enriched_snapshot

        _setup_project_dir(
            tmp_path,
            seed="Test seed",
            claude_md="# Architecture\nStuff here.",
            memory_files={"profile.md": "Developer"},
        )

        result = _build_enriched_snapshot(str(tmp_path), depth="standard")
        assert "seed" in result
        assert "claude_md" not in result
        assert "memory_summary" not in result

    def test_deep_depth_includes_claude_md_and_memory(self, tmp_path):
        from delta.app import _build_enriched_snapshot

        _setup_project_dir(
            tmp_path,
            seed="Test seed",
            claude_md="# Architecture\nDetailed architecture.",
            memory_files={"profile.md": "Developer who likes Python."},
        )

        result = _build_enriched_snapshot(str(tmp_path), depth="deep")
        assert "seed" in result
        assert "claude_md" in result
        assert "memory_summary" in result
        assert "Architecture" in result["claude_md"]
        assert "Developer" in result["memory_summary"]

    def test_deep_has_larger_seed_limit(self, tmp_path):
        from delta.app import _build_enriched_snapshot

        long_seed = "x" * 2000
        _setup_project_dir(tmp_path, seed=long_seed)

        standard = _build_enriched_snapshot(str(tmp_path), depth="standard")
        deep = _build_enriched_snapshot(str(tmp_path), depth="deep")

        assert len(standard.get("seed", "")) == 500
        assert len(deep.get("seed", "")) == 1500

    def test_deep_has_more_commits(self, tmp_path):
        from delta.app import _build_enriched_snapshot, _SNAPSHOT_LIMITS

        assert _SNAPSHOT_LIMITS["standard"]["commits"] == 5
        assert _SNAPSHOT_LIMITS["deep"]["commits"] == 10

    def test_deep_has_more_log_entries(self, tmp_path):
        from delta.app import _SNAPSHOT_LIMITS

        assert _SNAPSHOT_LIMITS["standard"]["log_entries"] == 10
        assert _SNAPSHOT_LIMITS["deep"]["log_entries"] == 20

    def test_deep_has_longer_log_text(self, tmp_path):
        from delta.app import _SNAPSHOT_LIMITS

        assert _SNAPSHOT_LIMITS["standard"]["log_chars"] == 200
        assert _SNAPSHOT_LIMITS["deep"]["log_chars"] == 400

    def test_empty_project_dir(self, tmp_path):
        from delta.app import _build_enriched_snapshot

        # No files at all
        result = _build_enriched_snapshot(str(tmp_path), depth="deep")
        assert result == {} or all(v in ("", [], {}) for v in result.values())

    def test_standard_depth_is_default(self, tmp_path):
        from delta.app import _build_enriched_snapshot

        _setup_project_dir(
            tmp_path,
            seed="Test",
            claude_md="# Arch",
            memory_files={"p.md": "Content"},
        )

        result = _build_enriched_snapshot(str(tmp_path))
        assert "claude_md" not in result
        assert "memory_summary" not in result
