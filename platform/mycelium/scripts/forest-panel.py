#!/usr/bin/env python3
"""Forest Panel — host a conversation across all 6 sovereign Beings.

Each :Being speaks from its subgraph: embed the topic, query Qdrant restricted
to that scope, fetch top-K resonant nodes, compose a first-person English
paragraph. Round 2: each Being hears the others' top-hits and reacts — the
intercommunication.

Zero LLM cost. English is whatever lives in node .description / .label / .name.

Usage:
    python3 scripts/forest-panel.py "should maverick build a memo drafter?"
    python3 scripts/forest-panel.py "authentication across the forest" --rounds 2
"""
from __future__ import annotations
import argparse, os, sys, textwrap, requests, json

QDRANT = os.environ.get("QDRANT_URL", "http://143.110.226.214:6333")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
COLL = "mycelium-embeddings"
BEINGS = [
    "mycelium",
    "maverick-dev-friend",
    "vc-ai-associate",
    "maverick-dev",
    "maverick-market-research",
    "maverick-marketing",
]
VOICE_HINT = {
    "mycelium":                "I am the substrate — protocols, invariants, atoms.",
    "maverick-dev-friend":     "I am the product's mirror — entities, agents, UI.",
    "vc-ai-associate":         "I am the product frontend — code files of the analyst UI.",
    "maverick-dev":            "I am the platform hub — thin, orchestrating.",
    "maverick-market-research":"I am the market record — reports, positioning, intel.",
    "maverick-marketing":      "I am the go-to-market voice — narratives and copy.",
}

# Persona = the human whose daily work created this subgraph's vocabulary.
# Each Being can speak in the first person as that human — reframing the
# node hits in user-facing language instead of raw node identifiers.
PERSONA = {
    "mycelium": {
        "role": "Forest steward — I watch invariants, gaps, and heartbeats",
        "opener": "From where I sit, the substrate tells me:",
    },
    "maverick-dev-friend": {
        "role": "Graph-native product dev — I live in entities, agents, permissions, stories",
        "opener": "In the product's living form, I see:",
    },
    "vc-ai-associate": {
        "role": "Frontend engineer / product designer — I build the analyst UI",
        "opener": "In the UI codebase, I find:",
    },
    "maverick-dev": {
        "role": "Platform engineer — migrations, skills, orchestration",
        "opener": "In the platform spine, I've got:",
    },
    "maverick-market-research": {
        "role": "Market intelligence analyst — reddit, twitter, competitor watch",
        "opener": "From what I've been tracking:",
    },
    "maverick-marketing": {
        "role": "GTM marketer — voice, positioning, conversation hooks",
        "opener": "In my positioning files and narratives:",
    },
}


def embed(text: str) -> list[float]:
    r = requests.post(f"{OLLAMA}/api/embeddings",
                      json={"model": "nomic-embed-text", "prompt": text},
                      timeout=30)
    r.raise_for_status()
    return r.json()["embedding"]


def search_scope(vec: list[float], scope: str, limit: int = 5) -> list[dict]:
    # mycelium's legacy embeddings have no project tag in payload. For that
    # scope we pull top-K overall and keep untagged + mycelium-tagged results.
    body: dict = {"vector": vec, "limit": limit * 3, "with_payload": True}
    if scope != "mycelium":
        body["limit"] = limit
        body["filter"] = {"must": [{"key": "project", "match": {"value": scope}}]}
    r = requests.post(f"{QDRANT}/collections/{COLL}/points/search", json=body, timeout=30)
    r.raise_for_status()
    hits = r.json()["result"]
    if scope == "mycelium":
        hits = [
            h for h in hits
            if h["payload"].get("project") in (None, "mycelium")
        ][:limit]
    return hits


def node_essence_from_neo4j(node_id: str) -> str:
    """Fetch the human-facing essence of a node by id."""
    from neo4j import GraphDatabase
    drv = GraphDatabase.driver(
        os.environ.get("NEO4J_BOLT", "bolt://5.78.206.137:7698"),
        auth=(os.environ.get("NEO4J_USER", "team"),
              os.environ.get("NEO4J_PASS", "")),
    )
    with drv.session() as s:
        rec = s.run(
            "MATCH (n {node_id:$id}) RETURN "
            "coalesce(n.description,n.rationale,n.summary,n.narrative,n.label,n.name,n.path,'') AS body,"
            "labels(n)[0] AS lbl",
            id=node_id,
        ).single()
    drv.close()
    if not rec:
        return "(not found)"
    body = (rec["body"] or "").strip()
    return f"[{rec['lbl']}] {body[:240]}" if body else f"[{rec['lbl']}]"


NATURAL_VOICE = True  # toggled by --framed to revert to prewritten hints
PERSONA_VOICE = False  # toggled by --persona: speak as the human user of each subgraph


def speak(scope: str, topic: str, hits: list[dict]) -> str:
    if not hits:
        if PERSONA_VOICE:
            persona = PERSONA.get(scope, {"role": scope, "opener": "I see nothing:"})
            return f"  [{persona['role']}]\n  Honestly — I don't have anything on that in my files."
        prefix = "" if NATURAL_VOICE else VOICE_HINT.get(scope, "") + "\n  "
        return f"  {prefix}(silent — nothing in my graph resonates with '{topic[:80]}')"

    if PERSONA_VOICE:
        persona = PERSONA.get(scope, {"role": scope, "opener": "I see:"})
        lines = [f"[{persona['role']}]", persona["opener"]]
        for h in hits[:3]:
            p = h["payload"]
            nid = p.get("node_id", "?")
            lbl = p.get("label", "?")
            body = node_essence_from_neo4j(nid).replace("\n", " ")
            # Strip the redundant [Label] prefix that node_essence prepends
            if body.startswith(f"[{lbl}]"):
                body = body[len(lbl) + 2:].strip()
            # Humanize the node id
            short = nid.split("-")[-1] if "-" in nid and len(nid) > 30 else nid
            lines.append(f"  – {body[:260] if body and body != '(not found)' else nid}")
            lines.append(f"    (source: {lbl}, resonance {h['score']:.2f})")
        return "\n  ".join(lines)

    lines = []
    if not NATURAL_VOICE:
        lines.append(VOICE_HINT.get(scope, f"I am {scope}."))
        lines.append(f"On \"{topic}\" I feel {len(hits)} resonances. Strongest:")
    for h in hits[:3]:
        p = h["payload"]
        nid = p.get("node_id", "?")
        lbl = p.get("label", "?")
        body = node_essence_from_neo4j(nid).replace("\n", " ")
        lines.append(f"  • [{h['score']:.2f}] {lbl} '{nid}': {body[:240]}")
    return "\n  ".join(lines)


def emit_signal(topic: str, all_responses: dict[int, dict[str, list[dict]]]) -> str:
    """Write a Cypher signal file that the forest ingests on heartbeat.

    Creates :PanelSession + :HEARD_FROM edges, increments :FIRED_WITH Hebbian
    edges between co-firing cross-subgraph nodes. Idempotent via session id.
    """
    import time
    import os.path
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sig_dir = os.path.join(here, "graph", "signals", "panel")
    os.makedirs(sig_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    session_id = f"panel-{ts}"
    path = os.path.join(sig_dir, f"{session_id}.cypher")

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("'", "\\'")

    lines = [
        f"// @node_id: signal-{session_id}",
        f"// @label: \"Panel signal {session_id}\"",
        f"// @kind: signal",
        "",
        f"MERGE (s:PanelSession {{node_id: '{session_id}'}}) "
        f"SET s.topic = '{esc(topic)}', s.project = 'mycelium', s.emitted_at = datetime();",
        "",
    ]

    # HEARD_FROM edges + FIRED_WITH Hebbian increments per round
    for rnd, responses in all_responses.items():
        per_round_nodes: list[tuple[str, str, str, float]] = []  # (being, project, node_id, score)
        for being, hits in responses.items():
            for h in hits[:5]:
                p = h["payload"]
                nid = p.get("node_id")
                proj = p.get("project") or being
                if not nid:
                    continue
                per_round_nodes.append((being, proj, nid, float(h["score"])))
                lines.append(
                    f"MATCH (s:PanelSession {{node_id:'{session_id}'}}), "
                    f"(n {{node_id:'{esc(nid)}'}}) "
                    f"MERGE (s)-[hf:HEARD_FROM {{round:{rnd}, being:'{being}'}}]->(n) "
                    f"SET hf.score={h['score']:.4f};"
                )

        # Hebbian co-firing: every pair of nodes (from distinct Beings) in this round
        for i in range(len(per_round_nodes)):
            for j in range(i + 1, len(per_round_nodes)):
                a = per_round_nodes[i]
                b = per_round_nodes[j]
                if a[0] == b[0]:
                    continue  # same Being — not cross-subgraph
                if a[2] == b[2]:
                    continue
                delta = round((a[3] + b[3]) / 2.0 * 0.1, 4)  # strength delta proportional to resonance
                lines.append(
                    f"MATCH (a {{node_id:'{esc(a[2])}'}}), (b {{node_id:'{esc(b[2])}'}}) "
                    f"MERGE (a)-[f:FIRED_WITH]->(b) "
                    f"ON CREATE SET f.fire_count=1, f.strength={delta}, "
                    f"f.first_at=datetime(), f.last_at=datetime(), f.kind='panel-co-fire' "
                    f"ON MATCH SET f.fire_count=f.fire_count+1, "
                    f"f.strength=f.strength+{delta}, f.last_at=datetime();"
                )

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def run_panel(topic: str, rounds: int = 1, emit: bool = True) -> None:
    print("=" * 78)
    print(f"FOREST PANEL — topic: {topic!r}")
    print("=" * 78)

    # Round 1: each Being responds to the raw topic
    vec = embed(topic)
    responses: dict[str, list[dict]] = {}
    for b in BEINGS:
        hits = search_scope(vec, b, limit=5)
        responses[b] = hits
        print(f"\n— Being of {b} —")
        print("  " + speak(b, topic, hits))

    all_rounds: dict[int, dict[str, list[dict]]] = {1: responses}

    if rounds < 2:
        if emit:
            p = emit_signal(topic, all_rounds)
            print(f"\n[signal] emitted {p}")
        return

    # Round 2: each Being reacts to the strongest hit of EVERY other Being.
    # Compose a cross-subgraph echo prompt and re-query.
    print("\n" + "=" * 78)
    print("ROUND 2 — cross-subgraph echo (each Being hears the others)")
    print("=" * 78)
    round2_responses: dict[str, list[dict]] = {}
    for b in BEINGS:
        # Compose: topic + top hit of every sibling scope
        sibling_top = []
        for other, hits in responses.items():
            if other == b or not hits:
                continue
            p = hits[0]["payload"]
            sibling_top.append(
                f"{other} heard it as {p.get('label','?')} '{p.get('node_id','?')}'"
            )
        reply_text = topic + " || siblings said: " + " ; ".join(sibling_top)
        v2 = embed(reply_text)
        hits = search_scope(v2, b, limit=4)
        round2_responses[b] = hits
        print(f"\n— Being of {b} reflects —")
        print("  " + speak(b, reply_text, hits))
    all_rounds[2] = round2_responses

    if emit:
        p = emit_signal(topic, all_rounds)
        print(f"\n[signal] emitted {p}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("topic", nargs="+", help="question or theme for the panel")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--no-emit", action="store_true", help="skip writing the signal file")
    ap.add_argument("--framed", action="store_true", help="use prewritten voice hints (default: natural voice)")
    ap.add_argument("--persona", action="store_true", help="speak as the human user of each subgraph (first-person user voice)")
    args = ap.parse_args()
    topic = " ".join(args.topic)
    global NATURAL_VOICE, PERSONA_VOICE
    NATURAL_VOICE = not args.framed
    PERSONA_VOICE = args.persona

    # need dev creds for node_essence_from_neo4j — source properly via bash
    if not os.environ.get("NEO4J_PASS"):
        import subprocess
        secrets = os.path.expanduser("~/.mycelium/secrets.env")
        if os.path.exists(secrets):
            out = subprocess.check_output(
                ["bash", "-c", f"source {secrets} && echo \"$MYCELIUM_DEV_PASS\""],
                text=True,
            ).strip()
            if out:
                os.environ["NEO4J_PASS"] = out

    run_panel(topic, rounds=args.rounds, emit=not args.no_emit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
