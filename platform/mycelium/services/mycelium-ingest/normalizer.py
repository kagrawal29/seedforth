"""
normalizer.py — converts raw GitHub webhook payloads into a list of
MergeStatement dicts understood by graph_writer.GraphWriter.

Each MergeStatement has:
  {
    "cypher": "<MERGE ... SET ...>",
    "params": { ... },
  }

IMPORTANT: this module has ZERO side effects.  It never opens a network
connection, never calls the GitHub API, and never writes to any file.
"""

from __future__ import annotations
from typing import Any

MergeStatement = dict[str, Any]


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def normalize(event_type: str, payload: dict, project: str) -> list[MergeStatement]:
    """Return a list of MergeStatements for the given GitHub event."""
    handlers = {
        "push":                          _handle_push,
        "pull_request":                  _handle_pull_request,
        "issues":                        _handle_issues,
        "issue_comment":                 _handle_issue_comment,
        "pull_request_review_comment":   _handle_pr_review_comment,
        "release":                       _handle_release,
    }
    handler = handlers.get(event_type)
    if handler is None:
        return []
    return handler(payload, project)


# ---------------------------------------------------------------------------
# Author helper
# ---------------------------------------------------------------------------

def _author_merge(login: str, email: str | None, project: str) -> MergeStatement:
    cypher = (
        "MERGE (a:Author {login: $login, project: $project}) "
        "ON CREATE SET a.email = $email, a.created_at = datetime() "
        "ON MATCH SET a.email = coalesce($email, a.email)"
    )
    return {"cypher": cypher, "params": {"login": login, "project": project, "email": email}}


def _edge(
    src_label: str, src_key: str, src_val: Any,
    rel: str,
    dst_label: str, dst_key: str, dst_val: Any,
    project: str,
) -> MergeStatement:
    cypher = (
        f"MATCH (src:{src_label} {{{src_key}: $src_val, project: $project}}) "
        f"MATCH (dst:{dst_label} {{{dst_key}: $dst_val, project: $project}}) "
        f"MERGE (src)-[:{rel}]->(dst)"
    )
    return {"cypher": cypher, "params": {"src_val": src_val, "dst_val": dst_val, "project": project}}


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------

def _handle_push(payload: dict, project: str) -> list[MergeStatement]:
    stmts: list[MergeStatement] = []

    ref = payload.get("ref", "")
    branch_name = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

    # MERGE :Branch
    stmts.append({
        "cypher": (
            "MERGE (b:Branch {name: $name, project: $project}) "
            "ON CREATE SET b.created_at = datetime()"
        ),
        "params": {"name": branch_name, "project": project},
    })

    for commit in payload.get("commits", []):
        sha = commit.get("id", "")
        author = commit.get("author", {})
        login = author.get("username") or author.get("name") or "unknown"
        email = author.get("email")
        message = (commit.get("message") or "")[:4096]
        authored_at = commit.get("timestamp", "")
        url = commit.get("url", "")

        # MERGE :Commit
        stmts.append({
            "cypher": (
                "MERGE (c:Commit {sha: $sha, project: $project}) "
                "SET c.author_login = $author_login, "
                "    c.author_email = $author_email, "
                "    c.message = $message, "
                "    c.authored_at = $authored_at, "
                "    c.url = $url"
            ),
            "params": {
                "sha": sha, "project": project,
                "author_login": login, "author_email": email,
                "message": message, "authored_at": authored_at, "url": url,
            },
        })

        # MERGE :Author
        stmts.append(_author_merge(login, email, project))

        # (:Commit)-[:ON_BRANCH]->(:Branch)
        stmts.append(_edge("Commit", "sha", sha, "ON_BRANCH", "Branch", "name", branch_name, project))

        # (:Commit)-[:AUTHORED_BY]->(:Author)
        stmts.append(_edge("Commit", "sha", sha, "AUTHORED_BY", "Author", "login", login, project))

    return stmts


# ---------------------------------------------------------------------------
# pull_request
# ---------------------------------------------------------------------------

def _handle_pull_request(payload: dict, project: str) -> list[MergeStatement]:
    stmts: list[MergeStatement] = []
    pr = payload.get("pull_request", {})
    if not pr:
        return stmts

    number = pr.get("number")
    title = (pr.get("title") or "")[:1024]
    body = (pr.get("body") or "")[:8192]
    state = pr.get("state", "open")
    author_login = (pr.get("user") or {}).get("login", "unknown")
    created_at = pr.get("created_at", "")
    merged_at = pr.get("merged_at")
    url = pr.get("html_url", "")
    base_branch = (pr.get("base") or {}).get("ref", "")

    stmts.append({
        "cypher": (
            "MERGE (pr:PullRequest {number: $number, project: $project}) "
            "SET pr.title = $title, pr.body = $body, pr.state = $state, "
            "    pr.author_login = $author_login, pr.created_at = $created_at, "
            "    pr.merged_at = $merged_at, pr.url = $url"
        ),
        "params": {
            "number": number, "project": project,
            "title": title, "body": body, "state": state,
            "author_login": author_login, "created_at": created_at,
            "merged_at": merged_at, "url": url,
        },
    })

    stmts.append(_author_merge(author_login, None, project))

    # Ensure base branch node exists
    if base_branch:
        stmts.append({
            "cypher": (
                "MERGE (b:Branch {name: $name, project: $project}) "
                "ON CREATE SET b.created_at = datetime()"
            ),
            "params": {"name": base_branch, "project": project},
        })
        stmts.append(_edge("PullRequest", "number", number, "TARGETS", "Branch", "name", base_branch, project))

    stmts.append(_edge("PullRequest", "number", number, "AUTHORED_BY", "Author", "login", author_login, project))

    return stmts


# ---------------------------------------------------------------------------
# issues
# ---------------------------------------------------------------------------

def _handle_issues(payload: dict, project: str) -> list[MergeStatement]:
    stmts: list[MergeStatement] = []
    issue = payload.get("issue", {})
    if not issue:
        return stmts

    number = issue.get("number")
    title = (issue.get("title") or "")[:1024]
    body = (issue.get("body") or "")[:8192]
    state = issue.get("state", "open")
    author_login = (issue.get("user") or {}).get("login", "unknown")
    created_at = issue.get("created_at", "")
    url = issue.get("html_url", "")

    stmts.append({
        "cypher": (
            "MERGE (i:Issue {number: $number, project: $project}) "
            "SET i.title = $title, i.body = $body, i.state = $state, "
            "    i.author_login = $author_login, i.created_at = $created_at, i.url = $url"
        ),
        "params": {
            "number": number, "project": project,
            "title": title, "body": body, "state": state,
            "author_login": author_login, "created_at": created_at, "url": url,
        },
    })

    stmts.append(_author_merge(author_login, None, project))
    stmts.append(_edge("Issue", "number", number, "AUTHORED_BY", "Author", "login", author_login, project))

    return stmts


# ---------------------------------------------------------------------------
# issue_comment
# ---------------------------------------------------------------------------

def _handle_issue_comment(payload: dict, project: str) -> list[MergeStatement]:
    stmts: list[MergeStatement] = []
    comment = payload.get("comment", {})
    issue = payload.get("issue", {})
    if not comment or not issue:
        return stmts

    cid = comment.get("id")
    body = (comment.get("body") or "")[:4096]
    author_login = (comment.get("user") or {}).get("login", "unknown")
    created_at = comment.get("created_at", "")
    url = comment.get("html_url", "")
    issue_number = issue.get("number")

    stmts.append({
        "cypher": (
            "MERGE (rc:ReviewComment {id: $id, project: $project}) "
            "SET rc.body = $body, rc.author_login = $author_login, "
            "    rc.created_at = $created_at, rc.url = $url"
        ),
        "params": {
            "id": cid, "project": project,
            "body": body, "author_login": author_login,
            "created_at": created_at, "url": url,
        },
    })

    stmts.append(_author_merge(author_login, None, project))
    stmts.append(_edge("ReviewComment", "id", cid, "AUTHORED_BY", "Author", "login", author_login, project))

    # Edge to parent Issue
    stmts.append({
        "cypher": (
            "MATCH (rc:ReviewComment {id: $cid, project: $project}) "
            "MATCH (i:Issue {number: $issue_number, project: $project}) "
            "MERGE (rc)-[:COMMENTS_ON]->(i)"
        ),
        "params": {"cid": cid, "issue_number": issue_number, "project": project},
    })

    return stmts


# ---------------------------------------------------------------------------
# pull_request_review_comment
# ---------------------------------------------------------------------------

def _handle_pr_review_comment(payload: dict, project: str) -> list[MergeStatement]:
    stmts: list[MergeStatement] = []
    comment = payload.get("comment", {})
    pr = payload.get("pull_request", {})
    if not comment or not pr:
        return stmts

    cid = comment.get("id")
    body = (comment.get("body") or "")[:4096]
    author_login = (comment.get("user") or {}).get("login", "unknown")
    created_at = comment.get("created_at", "")
    url = comment.get("html_url", "")
    pr_number = pr.get("number")

    stmts.append({
        "cypher": (
            "MERGE (rc:ReviewComment {id: $id, project: $project}) "
            "SET rc.body = $body, rc.author_login = $author_login, "
            "    rc.created_at = $created_at, rc.url = $url"
        ),
        "params": {
            "id": cid, "project": project,
            "body": body, "author_login": author_login,
            "created_at": created_at, "url": url,
        },
    })

    stmts.append(_author_merge(author_login, None, project))
    stmts.append(_edge("ReviewComment", "id", cid, "AUTHORED_BY", "Author", "login", author_login, project))

    # Edge to parent PR
    stmts.append({
        "cypher": (
            "MATCH (rc:ReviewComment {id: $cid, project: $project}) "
            "MATCH (pr:PullRequest {number: $pr_number, project: $project}) "
            "MERGE (rc)-[:COMMENTS_ON]->(pr)"
        ),
        "params": {"cid": cid, "pr_number": pr_number, "project": project},
    })

    return stmts


# ---------------------------------------------------------------------------
# release
# ---------------------------------------------------------------------------

def _handle_release(payload: dict, project: str) -> list[MergeStatement]:
    stmts: list[MergeStatement] = []
    release = payload.get("release", {})
    if not release:
        return stmts

    tag = release.get("tag_name", "")
    name = (release.get("name") or "")[:512]
    body = (release.get("body") or "")[:8192]
    published_at = release.get("published_at", "")

    stmts.append({
        "cypher": (
            "MERGE (r:Release {tag: $tag, project: $project}) "
            "SET r.name = $name, r.body = $body, r.published_at = $published_at"
        ),
        "params": {
            "tag": tag, "project": project,
            "name": name, "body": body, "published_at": published_at,
        },
    })

    return stmts
