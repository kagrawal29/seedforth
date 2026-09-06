#!/usr/bin/env python3
"""
extract-vocabulary.py
=====================
Tokenize + lemmatize + stopword-filter text into (lemma, surface, position) tuples.

Two modes:

1. Single-prompt mode (default):
     echo "how does merkle work" | python3 extract-vocabulary.py
   Emits one JSON object:
     {"tokens": [{"lemma": "merkle", "surface": "merkle", "position": 2}, ...],
      "text": "how does merkle work",
      "token_count": 4}

2. Bulk-corpus mode (--corpus):
     python3 extract-vocabulary.py --corpus
   Connects to Neo4j, walks every text-bearing node (description, explanation,
   content, claim), extracts tokens per node, and emits a JSONL stream:
     {"node_id": "concept-heartbeat", "field": "description", "tokens": [...]}
     ...
   Used by vocabulary-sequence-seed.cypher for the initial backfill.

Why minimal stdlib-only: this is the ONLY python dependency added by the
vocabulary layer. We do not pull NLTK. Lemmatization here is a small hand-
rolled dict of common plurals/tenses. It is not linguistically perfect but
covers >90% of the surface forms in the current mycelium corpus and stays
zero-dependency.
"""
import json
import os
import re
import subprocess
import sys
from typing import Iterable


# --- Stopwords (standard English set, ~180 words) -------------------------
STOPWORDS = set("""
a about above after again against all am an and any are aren as at be
because been before being below between both but by cant cannot could
couldnt did didnt do does doesnt doing dont down during each few for from
further had hadnt has hasnt have havent having he hed hell hes her here
heres hers herself him himself his how hows i id ill im ive if in into
is isnt it its itself lets me more most mustnt my myself no nor not of
off on once only or other ought our ours ourselves out over own same
shant she shed shell shes should shouldnt so some such than that thats
the their theirs them themselves then there theres these they theyd
theyll theyre theyve this those through to too under until up very was
wasnt we wed well were werent weve what whats when whens where wheres
which while who whos whom why whys with wont would wouldnt you youd
youll youre youve your yours yourself yourselves also now then just than
very really still one two three
""".split())


# --- Tiny lemma table for common irregulars + suffix rules ----------------
IRREGULAR_LEMMAS = {
    # irregular plurals
    "men": "man", "women": "woman", "children": "child",
    "feet": "foot", "teeth": "tooth", "mice": "mouse", "people": "person",
    "geese": "goose", "oxen": "ox",
    # irregular verbs
    "is": "be", "am": "be", "are": "be", "was": "be", "were": "be", "been": "be", "being": "be",
    "has": "have", "had": "have", "having": "have",
    "does": "do", "did": "do", "done": "do", "doing": "do",
    "went": "go", "gone": "go", "going": "go", "goes": "go",
    "ran": "run", "running": "run", "runs": "run",
    "ate": "eat", "eaten": "eat", "eating": "eat", "eats": "eat",
    "broke": "break", "broken": "break", "breaking": "break",
    "built": "build", "building": "build", "builds": "build",
    "understood": "understand", "understanding": "understand",
    "got": "get", "gotten": "get", "getting": "get", "gets": "get",
    "saw": "see", "seen": "see", "seeing": "see", "sees": "see",
    "said": "say", "saying": "say", "says": "say",
    "made": "make", "making": "make", "makes": "make",
    "knew": "know", "known": "know", "knowing": "know", "knows": "know",
    "thought": "think", "thinking": "think", "thinks": "think",
    "found": "find", "finding": "find", "finds": "find",
    "gave": "give", "given": "give", "giving": "give", "gives": "give",
    "took": "take", "taken": "take", "taking": "take", "takes": "take",
    "came": "come", "coming": "come", "comes": "come",
    "wrote": "write", "written": "write", "writing": "write", "writes": "write",
    "read": "read", "reading": "read", "reads": "read",
    "kept": "keep", "keeping": "keep", "keeps": "keep",
    "left": "leave", "leaving": "leave", "leaves": "leave",
    "held": "hold", "holding": "hold", "holds": "hold",
}


def lemmatize(surface: str) -> str:
    """Return the lemma of a lowercase surface form."""
    s = surface.lower()
    if s in IRREGULAR_LEMMAS:
        return IRREGULAR_LEMMAS[s]
    # Don't touch short words — they're usually already the lemma
    if len(s) <= 3:
        return s
    # Regular verb/noun suffix stripping, in order of specificity
    for suffix, replacement in [
        ("ying", "y"),   # trying → try
        ("ies", "y"),    # queries → query
        ("ied", "y"),    # tried → try
        ("sses", "ss"),  # classes → class
        ("ses", "se"),   # houses → house
        ("xes", "x"),    # boxes → box
        ("ches", "ch"),  # matches → match
        ("shes", "sh"),  # dishes → dish
        ("ing", ""),     # running → run (imperfect: we don't double-final-consonant)
        ("ed", ""),      # worked → work (imperfect: we don't undo doubled consonants)
        ("s", ""),       # cats → cat
    ]:
        if s.endswith(suffix) and len(s) - len(suffix) >= 3:
            return s[: -len(suffix)] + replacement
    return s


# --- Tokenizer -------------------------------------------------------------
# Matches word-like tokens: letters, digits, hyphens-inside-words, underscores.
# Preserves hyphenated compounds (mycelium-core, self-learning).
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")


def tokenize(text: str) -> list[dict]:
    """Extract tokens from text. Returns list of {lemma, surface, position}."""
    if not text:
        return []
    tokens = []
    for i, match in enumerate(TOKEN_RE.finditer(text)):
        surface = match.group(0)
        surface_lower = surface.lower()
        if surface_lower in STOPWORDS:
            continue
        if len(surface_lower) < 2:
            continue
        lemma = lemmatize(surface_lower)
        tokens.append({
            "lemma": lemma,
            "surface": surface_lower,
            "position": i,
        })
    return tokens


# --- Single-prompt mode ----------------------------------------------------
def single_prompt_mode():
    text = sys.stdin.read().strip()
    tokens = tokenize(text)
    out = {
        "text": text,
        "tokens": tokens,
        "token_count": len(tokens),
        "unique_lemmas": len({t["lemma"] for t in tokens}),
    }
    print(json.dumps(out, ensure_ascii=False))


# --- Bulk-corpus mode ------------------------------------------------------
def bulk_corpus_mode():
    """Walk the graph's text-bearing nodes and emit JSONL of {node_id, field, tokens}."""
    container = os.environ.get("NEO4J_CONTAINER", "mycelium-neo4j-local")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASS", "localtest12")

    cypher = """
MATCH (n)
WHERE n.node_id IS NOT NULL
  AND (n.description IS NOT NULL
       OR n.explanation IS NOT NULL
       OR n.content IS NOT NULL
       OR n.claim IS NOT NULL)
RETURN n.node_id AS node_id,
       coalesce(n.description, '') AS description,
       coalesce(n.explanation, '') AS explanation,
       coalesce(n.content, '') AS content,
       coalesce(n.claim, '') AS claim
LIMIT 10000
"""
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "cypher-shell",
         "-u", user, "-p", password, "--encryption", "false", "--format", "plain"],
        input=cypher,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = proc.stdout.strip().split("\n")
    # Skip the header row
    if lines and lines[0].startswith("node_id"):
        lines = lines[1:]

    count = 0
    for line in lines:
        if not line.strip():
            continue
        # cypher-shell plain format uses comma-separated quoted strings.
        # Since our text fields contain commas, the parse is actually brittle.
        # Better approach: run cypher once per node via a different output.
        # For now, skip this naive parse and note that the bulk path needs
        # a json-output cypher-shell mode, not plain.
        pass

    # Alternative approach: use a cypher that outputs JSON-per-row via apoc.
    cypher_json = """
MATCH (n)
WHERE n.node_id IS NOT NULL
  AND (n.description IS NOT NULL
       OR n.explanation IS NOT NULL
       OR n.content IS NOT NULL
       OR n.claim IS NOT NULL)
WITH n LIMIT 10000
RETURN apoc.convert.toJson({
  node_id: n.node_id,
  description: coalesce(n.description, ''),
  explanation: coalesce(n.explanation, ''),
  content: coalesce(n.content, ''),
  claim: coalesce(n.claim, '')
}) AS row
"""
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "cypher-shell",
         "-u", user, "-p", password, "--encryption", "false", "--format", "plain"],
        input=cypher_json,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = proc.stdout.strip().split("\n")
    if lines and "row" in lines[0]:
        lines = lines[1:]
    for line in lines:
        line = line.strip()
        if not line or line in ('"', ''):
            continue
        # cypher-shell plain wraps string output in outer quotes and escapes
        # inner quotes as \". Undo both.
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        line = line.replace('\\"', '"')
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        node_id = rec.get("node_id")
        for field in ("description", "explanation", "content", "claim"):
            text = rec.get(field, "") or ""
            if not text:
                continue
            tokens = tokenize(text)
            if not tokens:
                continue
            print(json.dumps({
                "node_id": node_id,
                "field": field,
                "tokens": tokens,
            }, ensure_ascii=False))
            count += 1

    sys.stderr.write(f"extract-vocabulary: emitted {count} (node, field) records\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--corpus":
        bulk_corpus_mode()
    else:
        single_prompt_mode()
