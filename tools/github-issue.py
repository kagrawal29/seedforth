#!/usr/bin/env python3
"""Create or list GitHub issues using GITHUB_TOKEN.

Usage:
    python3 tools/github-issue.py create <owner/repo> <title> [--body <body>] [--labels <l1,l2>]
    python3 tools/github-issue.py list <owner/repo> [--state open|closed|all]
    python3 tools/github-issue.py view <owner/repo> <number>

Requires GITHUB_TOKEN environment variable.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


def _token():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    return token


def _request(method, url, data=None):
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if data:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)


def create_issue(repo, title, body="", labels=None):
    url = f"https://api.github.com/repos/{repo}/issues"
    payload = {"title": title}
    if body:
        payload["body"] = body
    if labels:
        payload["labels"] = labels
    result = _request("POST", url, payload)
    print(f"Created #{result['number']}: {result['html_url']}")
    return result


def list_issues(repo, state="open"):
    url = f"https://api.github.com/repos/{repo}/issues?state={state}&per_page=20"
    issues = _request("GET", url)
    if not issues:
        print("No issues found.")
        return
    for issue in issues:
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        label_str = f" [{labels}]" if labels else ""
        print(f"  #{issue['number']} {issue['state']:6s} {issue['title']}{label_str}")


def view_issue(repo, number):
    url = f"https://api.github.com/repos/{repo}/issues/{number}"
    issue = _request("GET", url)
    print(f"#{issue['number']} [{issue['state']}] {issue['title']}")
    print(f"URL: {issue['html_url']}")
    if issue.get("body"):
        print(f"\n{issue['body']}")


def main():
    parser = argparse.ArgumentParser(description="GitHub issue management")
    sub = parser.add_subparsers(dest="command")

    c = sub.add_parser("create")
    c.add_argument("repo", help="owner/repo")
    c.add_argument("title")
    c.add_argument("--body", default="")
    c.add_argument("--labels", default="")

    l = sub.add_parser("list")
    l.add_argument("repo", help="owner/repo")
    l.add_argument("--state", default="open")

    v = sub.add_parser("view")
    v.add_argument("repo", help="owner/repo")
    v.add_argument("number", type=int)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "create":
        labels = [l.strip() for l in args.labels.split(",") if l.strip()] if args.labels else None
        create_issue(args.repo, args.title, args.body, labels)
    elif args.command == "list":
        list_issues(args.repo, args.state)
    elif args.command == "view":
        view_issue(args.repo, args.number)


if __name__ == "__main__":
    main()
