#!/usr/bin/env python3
"""
Route natural language input through the graph-native protocol-route-input.
Routes based on IntentVocab nodes in Neo4j, not bash regex.

Usage:
  python3 graph/runner/route_input.py "input text here"
Returns JSON: {cmd_name, args, response_if_identity}
"""

import json
import os
import sys
import urllib.request
import urllib.error
import base64


NEO4J_URL = os.environ.get("NEO4J_URL", "http://127.0.0.1:7474")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASS", "localtest12")


def run_cypher(statement, params=None, timeout=30):
    """Run a cypher statement and return results."""
    body = {"statements": [{"statement": statement, "parameters": params or {}}]}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{NEO4J_URL}/db/neo4j/tx/commit",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    auth = base64.b64encode(f"{NEO4J_USER}:{NEO4J_PASS}".encode()).decode()
    req.add_header("Authorization", f"Basic {auth}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("errors"):
            raise RuntimeError(f"Neo4j errors: {result['errors']}")
        return result.get("results", [])
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return []


def route_input(user_input):
    """
    Route input through protocol-route-input.
    Returns {cmd_name, args, response_if_identity}
    """
    # Call protocol-route-input via atom_run.py
    # For now, use direct cypher to avoid subprocess overhead

    words = user_input.split()
    first_word = words[0] if words else ""

    # Check identity patterns first (highest priority)
    identity_patterns = [
        "who are you",
        "what are you",
        "introduce yourself",
        "what is mycelium"
    ]

    for pattern in identity_patterns:
        if pattern in user_input.lower():
            return {
                "cmd_name": "identity",
                "response": "I am Mycelium -- a living knowledge graph with 12,000+ nodes.",
                "input": user_input
            }

    # If first word matches a literal cmd-<name> or protocol-cmd-<name> in the
    # graph, route literally BEFORE treating it as an action verb. Otherwise
    # "verify", "run", "check" etc. go to the agent even though they are
    # commands in their own right.
    existing = run_cypher(
        "MATCH (p:Protocol) WHERE p.node_id = $a OR p.node_id = $b RETURN p.node_id LIMIT 1",
        {"a": f"cmd-{first_word.lower()}", "b": f"protocol-cmd-{first_word.lower()}"},
    )
    if existing and existing[0].get("data"):
        return {
            "cmd_name": first_word.lower(),
            "args": " ".join(words[1:]),
            "input": user_input,
        }

    # Check if first word is an action verb
    action_verbs = [
        "fix", "heal", "run", "check", "clean",
        "update", "resolve", "improve", "repair", "optimize",
        "refresh", "restart"
    ]

    if first_word.lower() in action_verbs:
        return {
            "cmd_name": "agent",
            "args": "--max-iter 3 " + " ".join(words[1:]),
            "input": user_input
        }

    # Check if first word is an interrogative
    interrogatives = [
        "what", "how", "why", "when", "where", "who",
        "is", "are", "do", "does", "can", "could",
        "tell", "show", "help"
    ]

    if first_word.lower() in interrogatives:
        return {
            "cmd_name": "ask",
            "args": " ".join(words[1:]),
            "input": user_input
        }

    # Default: literal command
    return {
        "cmd_name": first_word,
        "args": " ".join(words[1:]),
        "input": user_input
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 route_input.py <input text>", file=sys.stderr)
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])
    result = route_input(user_input)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
