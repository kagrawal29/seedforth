#!/usr/bin/env python3
"""
Ask Asgard — CLI for agents and humans to converse with the knowledge graph.

Usage:
    python3 scripts/ask-asgard.py "what decisions affect the API layer?"
    python3 scripts/ask-asgard.py --demand
    python3 scripts/ask-asgard.py --demand "notification system"
    python3 scripts/ask-asgard.py --neighborhood "memory-layer-decisions"
    python3 scripts/ask-asgard.py --community 0

The graph answers in natural language. Every query is logged.
"""

import os
import sys

# Ensure repo root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.lib.ask_asgard import ask, ask_demand, ask_neighborhood, ask_community


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/ask-asgard.py \"your question\"")
        print("       python3 scripts/ask-asgard.py --demand [topic]")
        print("       python3 scripts/ask-asgard.py --neighborhood <node-id>")
        print("       python3 scripts/ask-asgard.py --community <N>")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--demand":
        topic = sys.argv[2] if len(sys.argv) > 2 else None
        print(ask_demand(topic))
    elif arg == "--neighborhood":
        if len(sys.argv) < 3:
            print("Usage: --neighborhood <node-id>")
            sys.exit(1)
        print(ask_neighborhood(sys.argv[2]))
    elif arg == "--community":
        if len(sys.argv) < 3:
            print("Usage: --community <N>")
            sys.exit(1)
        print(ask_community(int(sys.argv[2])))
    else:
        # Natural language question
        question = " ".join(sys.argv[1:])
        print(ask(question))


if __name__ == "__main__":
    main()
