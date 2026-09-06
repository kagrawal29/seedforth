#!/usr/bin/env python3
"""
Graph CLI — the thinnest possible plumbing.

All intelligence lives in the graph as NLQuery nodes.
This file is ONLY: connect → read → send to graph → print.
No routing logic. No formatting. No patterns. Just pipe.

The graph IS the CLI. This file is the pipe.
"""

import os
import sys

try:
    import readline
except ImportError:
    pass

try:
    from falkordb import FalkorDB
except ImportError:
    print("pip install falkordb")
    sys.exit(1)

HOST = os.environ.get("FALKORDB_HOST", "localhost")
PORT = int(os.environ.get("FALKORDB_PORT", "6379"))
GRAPH_NAME = os.environ.get("GRAPH_NAME", "asgard")


def connect():
    db = FalkorDB(host=HOST, port=PORT)
    return db.select_graph(GRAPH_NAME)


def ask_graph(graph, text):
    """Send natural language to the graph. The graph routes and responds.

    All routing logic is in NLQuery nodes. All formatting is in the Cypher.
    This function is just the pipe.
    """
    text_lower = text.lower().strip()

    # Direct Cypher pass-through (starts with MATCH/MERGE/RETURN)
    if text_lower.startswith(("match", "merge", "return", "create", "optional")):
        try:
            r = graph.query(text)
            for row in (r.result_set or []):
                print("  " + " | ".join(str(v) for v in row))
        except Exception as e:
            print(f"  error: {e}")
        return

    # Git command handler — graph routes to __git__ prefix, CLI executes
    def run_git(cypher_or_cmd, user_text=""):
        import subprocess as sp
        git_cmds = {
            '__git__status': ['git', 'status', '-sb'],
            '__git__log': ['git', 'log', '--oneline', '-10'],
            '__git__diff': ['git', 'diff', '--stat'],
            '__git__branch': ['git', 'branch', '-a'],
            '__git__push': ['git', 'push'],
            '__git__pull': ['git', 'pull'],
            '__git__add': ['git', 'add', '-A'],
            '__git__stash': ['git', 'stash'],
            '__git__commit': None,  # needs message extraction
        }
        if cypher_or_cmd in git_cmds:
            cmd = git_cmds[cypher_or_cmd]
            if cypher_or_cmd == '__git__commit':
                # Extract commit message from user input or use default
                msg = user_text.replace('commit', '').replace('save', '').replace('changes', '').strip()
                if not msg or len(msg) < 3:
                    msg = 'graph crystallisation checkpoint'
                cmd = ['git', 'add', '-A']
                r = sp.run(cmd, capture_output=True, text=True)
                cmd = ['git', 'commit', '-m', msg]
            try:
                r = sp.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                output = (r.stdout + r.stderr).strip()
                for line in output.split('\n')[:15]:
                    print(f"  {line}")
            except Exception as e:
                print(f"  error: {e}")
            return True
        return False

    # THE GRAPH ROUTES: phrase → keyword score → intent → topology decipher
    try:
        # Load stop words from graph (cached after first call)
        if not hasattr(ask_graph, '_stops'):
            try:
                sw = graph.query("MATCH (sw:GraphConfig {node_id: 'config-stop-words'}) RETURN sw.words")
                ask_graph._stops = set(sw.result_set[0][0].split(',')) if sw.result_set else set()
            except Exception:
                ask_graph._stops = set()

        words = [w.replace("'", "") for w in text_lower.split() if len(w) > 2 and w not in ask_graph._stops]
        if not words:
            print("I need more than that. Try a question.")
            return

        # PHASE 2: Phrase matching — full phrase against stored phrases
        safe_input = text_lower.replace("'", "").replace('"', '')[:200]
        try:
            phrase_r = graph.query(
                f"MATCH (q:NLQuery) WHERE q.phrases IS NOT NULL "
                f"WITH q, [p IN split(q.phrases, '|') WHERE '{safe_input}' CONTAINS p] AS matches "
                f"WHERE size(matches) > 0 "
                f"WITH q, matches, reduce(maxlen = 0, m IN matches | CASE WHEN size(m) > maxlen THEN size(m) ELSE maxlen END) AS longest_match "
                f"RETURN q.cypher, q.answer_template, q.node_id, longest_match AS score "
                f"ORDER BY score DESC "
                f"LIMIT 1"
            )
            if phrase_r.result_set and phrase_r.result_set[0][0]:
                cypher = phrase_r.result_set[0][0]
                # Git commands — graph routed to __git__ prefix
                if cypher.startswith('__git__'):
                    if run_git(cypher, text):
                        return
                template = phrase_r.result_set[0][1]
                matched_id = phrase_r.result_set[0][2]
                try:
                    graph.query(
                        f"MERGE (qt:QuestionTrace {{question: '{safe_input}'}}) "
                        f"SET qt.matched_query = '{matched_id}', qt.score = 10, qt.match_type = 'phrase'"
                    )
                except Exception:
                    pass
                result = graph.query(cypher)
                if template:
                    print(f"  {template}")
                    print()
                for row in (result.result_set or [])[:15]:
                    val = str(row[0]) if len(row) == 1 else " | ".join(str(v) for v in row)
                    print(f"  {val}" if len(result.result_set) == 1 else f"  → {val}")
                return
        except Exception:
            pass

        # Build keyword conditions for ProductQuery fallback
        kw_conditions = " OR ".join(
            f"toLower(q.patterns) CONTAINS '{w}'"
            for w in words if len(w) > 3
        ) or "false"

        # Build score expression: count matching keywords per NLQuery
        score_parts = " + ".join(
            f"CASE WHEN q.patterns CONTAINS '{w}' THEN 1 ELSE 0 END"
            for w in words
        )

        r = graph.query(
            f"MATCH (q:NLQuery) "
            f"WITH q, ({score_parts}) AS score "
            f"WHERE score > 0 "
            f"RETURN q.cypher, q.answer_template, score "
            f"ORDER BY score DESC, size(q.patterns) ASC "
            f"LIMIT 1"
        )

        if r.result_set and r.result_set[0][0]:
            cypher = r.result_set[0][0]
            # Git commands from keyword path
            if cypher.startswith('__git__'):
                if run_git(cypher, text):
                    return
            template = r.result_set[0][1]
            match_score = r.result_set[0][2] if len(r.result_set[0]) > 2 else 0

            # TRACE: the graph remembers this question (its ear)
            try:
                safe_text = text_lower.replace("'", "").replace('"', '')[:200]
                graph.query(
                    f"MERGE (qt:QuestionTrace {{question: '{safe_text}'}}) "
                    f"SET qt.matched_query = '{r.result_set[0][0][:30] if r.result_set[0][0] else ''}...', "
                    f"qt.score = {match_score}"
                )
            except Exception:
                pass

            # Execute the matched Cypher
            result = graph.query(cypher)

            # Print template if exists
            if template:
                print(f"  {template}")
                print()

            # Print results — the Cypher formats its own output as 'answer' column
            for row in (result.result_set or [])[:15]:
                val = str(row[0]) if len(row) == 1 else " | ".join(str(v) for v in row)
                if len(result.result_set) > 1:
                    print(f"  → {val}")
                else:
                    print(f"  {val}")
            return

        # Try ProductQuery nodes
        r2 = graph.query(
            f"MATCH (q:ProductQuery) WHERE {kw_conditions.replace('q.patterns', 'toLower(q.question)')} "
            f"RETURN q.cypher, q.plain_english "
            f"LIMIT 1"
        )

        if r2.result_set and r2.result_set[0][0]:
            cypher = r2.result_set[0][0]
            template = r2.result_set[0][1]
            result = graph.query(cypher)
            if template:
                print(f"  {template}")
                print()
            for row in (result.result_set or [])[:15]:
                val = " | ".join(str(v) for v in row)
                print(f"  → {val}")
            return

        # DECIPHER MODE: no pattern matched — but the graph still has relevant topology
        # Compose a prose response from whatever nodes the keywords touch
        word_filter = " OR ".join(
            f"toLower(n.label) CONTAINS '{w.replace(chr(39), '')}'"
            for w in words if len(w) > 3
        )
        if word_filter:
            r3 = graph.query(
                f"MATCH (n) WHERE n.label IS NOT NULL AND ({word_filter}) "
                f"WITH n, labels(n)[0] AS type "
                f"ORDER BY CASE type "
                f"  WHEN 'Knowledge' THEN 1 WHEN 'Principle' THEN 2 "
                f"  WHEN 'Evidence' THEN 3 WHEN 'PainPoint' THEN 4 "
                f"  WHEN 'Feature' THEN 5 WHEN 'Competitor' THEN 6 "
                f"  ELSE 10 END "
                f"LIMIT 5 "
                f"WITH collect(type + ': ' + left(n.label, 120)) AS found "
                f"RETURN CASE WHEN size(found) = 0 THEN 'nothing' "
                f"  WHEN size(found) = 1 THEN 'I found something related: ' + found[0] + '.' "
                f"  ELSE 'Here is what I know that connects: ' + "
                f"    reduce(s = '', f IN found[0..3] | s + CASE WHEN s = '' THEN '' ELSE '. ' END + f) "
                f"    + '.' END AS answer"
            )
            if r3.result_set and r3.result_set[0][0] != 'nothing':
                print(r3.result_set[0][0])
                # TRACE: partially matched
                try:
                    safe_text = text_lower.replace("'", "").replace('"', '')[:200]
                    graph.query(
                        f"MERGE (qt:QuestionTrace {{question: '{safe_text}'}}) "
                        f"SET qt.matched_query = 'keyword-fallback', qt.score = 0"
                    )
                except Exception:
                    pass
                return

        # TRACE: completely unmatched — the richest learning signal
        try:
            safe_text = text_lower.replace("'", "").replace('"', '')[:200]
            graph.query(
                f"MERGE (qt:QuestionTrace {{question: '{safe_text}'}}) "
                f"SET qt.matched_query = NULL, qt.score = 0"
            )
        except Exception:
            pass
        print("  I don't have anything on that yet. But I just remembered your question — I'll learn from it.")

    except Exception as e:
        print(f"  error: {e}")


def main():
    graph = connect()

    # Greeting — the graph speaks first
    try:
        r = graph.query(
            "MATCH (q:NLQuery {node_id: 'nlq-greeting'}) "
            "RETURN q.cypher LIMIT 1"
        )
        if r.result_set:
            greeting = graph.query(r.result_set[0][0])
            if greeting.result_set:
                print(f"\n  graph: {greeting.result_set[0][0]}")
    except Exception:
        print("\n  graph: I'm alive. Ask me anything.")

    # One-shot mode
    if len(sys.argv) > 1:
        print()
        ask_graph(graph, " ".join(sys.argv[1:]))
        return

    # Interactive — just a loop: read → send to graph → print
    print()
    while True:
        try:
            text = input("  you: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if not text:
            continue
        if text.lower() in ("exit", "quit", "q", "bye"):
            print("  graph: goodbye. I keep crystallizing.\n")
            break

        print()
        print("  graph: ", end="")
        ask_graph(graph, text)
        print()


if __name__ == "__main__":
    main()
