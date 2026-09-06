"""
Shared config loader for the meta intelligence system.

All scripts and agents read from config.yaml via this module.
Change the config file to deploy for a different team — no code changes needed.

Usage:
    from scripts.lib.config import load_config, get_team, get_repos, get_settings

    config = load_config()
    team = get_team()           # list of {name, langsmith_project}
    repos = get_repos()         # list of {name, org, domain}
    settings = get_settings()   # dict of thresholds and limits
"""

import os
import yaml
from pathlib import Path
from functools import lru_cache


def _find_config_path():
    """Find config.yaml by walking up from this file or from cwd."""
    # Try relative to this file (scripts/lib/config.py → ../../config.yaml)
    here = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    if here.exists():
        return here

    # Try from cwd
    cwd = Path.cwd() / "config.yaml"
    if cwd.exists():
        return cwd

    # Try MAVERICK_META_ROOT env var
    root = os.environ.get("MAVERICK_META_ROOT")
    if root:
        p = Path(root) / "config.yaml"
        if p.exists():
            return p

    raise FileNotFoundError(
        "config.yaml not found. Set MAVERICK_META_ROOT or run from the repo root."
    )


@lru_cache(maxsize=1)
def load_config():
    """Load and cache the full config."""
    path = _find_config_path()
    with open(path) as f:
        return yaml.safe_load(f)


def get_team():
    """Return list of team members: [{name, langsmith_project}, ...]"""
    return load_config()["team"]


def get_repos():
    """Return list of target repos: [{name, org, domain}, ...]"""
    return load_config()["repos"]


def get_settings():
    """Return settings dict: {max_rules, staleness_warn_days, ...}"""
    return load_config()["settings"]


def get_langsmith_config():
    """Return LangSmith config with API key resolved from env."""
    ls = load_config()["langsmith"]
    api_key = os.environ.get(ls["api_key_env"], "")
    return {
        "api_key": api_key,
        "base_url": ls["base_url"],
    }


def get_repo_strings():
    """Return list of 'org/name' strings for GitHub API calls."""
    return [f"{r['org']}/{r['name']}" for r in get_repos()]


def get_artifact_patterns():
    """Return list of glob patterns for team artifact detection."""
    return load_config().get("artifact_patterns", [])
