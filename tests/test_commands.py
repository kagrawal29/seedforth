"""Tests for delta.commands."""

from delta.commands import parse, HELP_TEXT


def test_parse_help():
    assert parse("help") == ("help", {})
    assert parse("commands") == ("help", {})
    assert parse("  help  ") == ("help", {})


def test_parse_list():
    assert parse("list") == ("list", {})
    assert parse("list projects") == ("list", {})
    assert parse("projects") == ("list", {})


def test_parse_status_all():
    assert parse("status all") == ("status_all", {})


def test_parse_status_no_args():
    assert parse("status") == ("status", {})


def test_parse_status_project():
    assert parse("status audioworld") == ("status", {"project": "audioworld"})
    assert parse("status my-project") == ("status", {"project": "my-project"})


def test_parse_new_project_no_name():
    assert parse("new project") == ("new_project", {})


def test_parse_new_project_with_name():
    assert parse("new project my-app") == ("new_project", {"name": "my-app"})


def test_parse_new_project_from_github():
    result = parse("new project github.com/user/repo")
    assert result == ("new_project", {"name": "repo", "github_repo": "user/repo"})


def test_parse_new_project_from_github_https():
    result = parse("new project https://github.com/user/repo")
    assert result == ("new_project", {"name": "repo", "github_repo": "user/repo"})


def test_parse_new_project_from_github_trailing_slash():
    result = parse("new project github.com/user/repo/")
    assert result == ("new_project", {"name": "repo", "github_repo": "user/repo"})


def test_parse_teardown():
    assert parse("tear down my-app") == ("teardown", {"project": "my-app"})
    assert parse("teardown my-app") == ("teardown", {"project": "my-app"})


def test_parse_delete():
    assert parse("delete my-app") == ("teardown", {"project": "my-app"})


def test_parse_logs():
    assert parse("logs my-app") == ("logs", {"project": "my-app"})


def test_parse_peek():
    assert parse("peek my-app") == ("peek", {"project": "my-app"})


def test_parse_admin_send():
    result = parse("send my-app check the homepage")
    assert result == ("admin_send", {"project": "my-app", "text": "check the homepage"})


def test_parse_restart():
    assert parse("restart my-app") == ("restart", {"project": "my-app"})


def test_parse_schedule():
    assert parse("schedule my-app") == ("schedule", {"project": "my-app"})


def test_parse_new_shorthand():
    assert parse("new my-app") == ("new_project", {"name": "my-app"})
    assert parse("new cajon-sensei") == ("new_project", {"name": "cajon-sensei"})


def test_parse_new_shorthand_here():
    assert parse("new my-app here") == ("new_project", {"name": "my-app", "here": True})


def test_parse_new_project_here():
    result = parse("new project my-app here")
    assert result == ("new_project", {"name": "my-app", "here": True})


def test_parse_new_project_here_no_name():
    result = parse("new project here")
    assert result == ("new_project", {"here": True})


def test_parse_new_project_github_here():
    result = parse("new project github.com/user/repo here")
    assert result == ("new_project", {"name": "repo", "github_repo": "user/repo", "here": True})


def test_parse_not_a_command():
    assert parse("check the PR status") is None
    assert parse("what's going on") is None
    assert parse("") is None


def test_help_text_exists():
    assert "new project" in HELP_TEXT
    assert "status" in HELP_TEXT
    assert "list" in HELP_TEXT
    assert "tear down" in HELP_TEXT
    assert "logs" in HELP_TEXT
    assert "peek" in HELP_TEXT
    assert "restart" in HELP_TEXT
    assert "schedule" in HELP_TEXT
