#!/usr/bin/env python3
"""
Sync L5/L6/Phase nodes into FalkorDB — makes intents, convergences,
and phase transitions queryable in the live graph.

Reads:
  - signals/demand/*-intents.json (per-person intents from L5)
  - signals/demand/cross-person-intents.json (alignments from L5)
  - signals/demand/convergence-events.json (from L6)

Writes to FalkorDB:
  - Intent nodes with EXPRESSES edges to Demand nodes
  - Convergence nodes with CONVERGES_TO edges from Intent nodes
  - Phase nodes with CONSTITUTED_BY edges from Convergence nodes

Deterministic Python, no LLM. Runs after convergence-detect.py in the pipeline.
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMAND_DIR = REPO_ROOT / "signals" / "demand"
SNAPSHOT_DIR = REPO_ROOT / "knowledge" / "meta" / "layer-snapshots"

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"

# Phase detection: minimum convergence events to declare a phase
MIN_CONVERGENCES_FOR_PHASE = 2


def esc(s):
    """Escape string for Cypher."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(GRAPH_NAME)


def load_demand_files():
    """Load all per-person demand JSON files from the demand engine."""
    demands = []
    for fp in sorted(DEMAND_DIR.glob("*-demand.json")):
        if fp.name == "cross-person-demands.json":
            continue
        try:
            data = json.loads(fp.read_text())
            person = data.get("person", "")
            for cluster in data.get("question_clusters", []):
                cluster["_person"] = person
                demands.append(cluster)
        except (json.JSONDecodeError, KeyError):
            continue
    return demands


def load_cross_demands():
    """Load cross-person demand signals."""
    fp = DEMAND_DIR / "cross-person-demands.json"
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text())
        return data.get("cross_demands", [])
    except (json.JSONDecodeError, KeyError):
        return []


def load_intent_files():
    """Load all per-person intent files."""
    intents = []
    for fp in sorted(DEMAND_DIR.glob("*-intents.json")):
        if fp.name == "cross-person-intents.json":
            continue
        try:
            data = json.loads(fp.read_text())
            person = data.get("person", "")
            for intent in data.get("intents", []):
                intent["_person"] = person
                intents.append(intent)
        except (json.JSONDecodeError, KeyError):
            continue
    return intents


def load_convergence_events():
    """Load convergence events from L6."""
    fp = DEMAND_DIR / "convergence-events.json"
    if not fp.exists():
        return []
    try:
        data = json.loads(fp.read_text())
        return data.get("events", [])
    except (json.JSONDecodeError, KeyError):
        return []


def classify_demand_character(events):
    """Determine the dominant demand character from convergence events.

    Looks at the graph regions and intent domains across all events
    to classify the overall phase.
    """
    if not events:
        return "unknown"

    regions = []
    for event in events:
        regions.append(event.get("graph_region", ""))
        for intent in event.get("intents", []):
            regions.append(intent.get("intent_domain", ""))

    region_text = " ".join(r.lower() for r in regions if r)

    # Heuristics based on demand patterns
    spec_signals = ["spec", "routing", "contract", "boundary", "schema", "structure",
                    "configurab", "architecture", "how does", "connect"]
    explore_signals = ["should we", "what about", "which", "evaluate", "compare", "vs"]
    impl_signals = ["implement", "build", "deploy", "ship", "test", "debug", "fix"]

    spec_score = sum(1 for s in spec_signals if s in region_text)
    explore_score = sum(1 for s in explore_signals if s in region_text)
    impl_score = sum(1 for s in impl_signals if s in region_text)

    if spec_score > explore_score and spec_score > impl_score:
        return "specification"
    elif impl_score > explore_score:
        return "implementation"
    elif explore_score > 0:
        return "exploration"
    return "mixed"


def sync_demands(graph, demands, cross_demands):
    """Sync Demand nodes from the demand engine to FalkorDB.

    Replaces stale seed demand nodes with fresh cycle data.
    Creates ASKED edges from Person nodes and CROSS_PERSON_DEMAND edges.
    """
    # Clear old demand nodes (they're regenerated each cycle)
    try:
        graph.query("MATCH (d:Demand) DETACH DELETE d")
    except Exception:
        pass

    synced = 0
    for cluster in demands:
        cluster_id = esc(cluster.get("id", ""))
        if not cluster_id:
            continue

        person = esc(cluster.get("_person", ""))
        node_id = f"demand_{esc(person.lower())}_{cluster_id}"
        label = esc(cluster.get("representative_question", "")[:200])
        domain = esc(cluster.get("domain", ""))
        frequency = cluster.get("frequency", 1)
        frustration = esc(cluster.get("frustration", "low"))
        gap = cluster.get("gap_signal", False)
        coverage = 0.0
        matched = cluster.get("matched_entries", [])
        if matched:
            coverage = max(m.get("coverage_score", 0) for m in matched)

        graph.query(
            f"MERGE (d:Demand {{node_id: '{node_id}'}}) "
            f"SET d.label = '{label}', "
            f"d.person = '{person}', "
            f"d.domain = '{domain}', "
            f"d.frequency = {frequency}, "
            f"d.frustration = '{frustration}', "
            f"d.gap_signal = {str(gap).lower()}, "
            f"d.coverage_score = {coverage}, "
            f"d.cluster_id = '{esc(cluster_id)}', "
            f"d.file_type = 'demand'"
        )

        # Link to nearest Knowledge nodes from matched_entries
        for match in matched:
            entry_id = esc(match.get("entry_id", ""))
            if entry_id:
                try:
                    edge_type = "ANSWERED_BY" if match.get("coverage_score", 0) >= 0.7 else \
                                "PARTIALLY_ANSWERED_BY" if match.get("coverage_score", 0) >= 0.3 else \
                                "UNANSWERED_NEAR"
                    graph.query(
                        f"MATCH (d:Demand {{node_id: '{node_id}'}}), "
                        f"(k:Knowledge {{node_id: '{entry_id}'}}) "
                        f"MERGE (d)-[r:{edge_type}]->(k)"
                    )
                except Exception:
                    pass

        synced += 1

    # Sync cross-person demand edges
    cross_count = 0
    for xd in cross_demands:
        persons = xd.get("persons", [])
        concept = esc(xd.get("shared_concept", ""))
        if len(persons) < 2 or not concept:
            continue
        # Find demand nodes for each person that relate to this concept
        for i in range(len(persons)):
            for j in range(i + 1, len(persons)):
                p1 = esc(persons[i].lower())
                p2 = esc(persons[j].lower())
                try:
                    graph.query(
                        f"MATCH (d1:Demand) WHERE d1.person = '{esc(persons[i])}' "
                        f"MATCH (d2:Demand) WHERE d2.person = '{esc(persons[j])}' "
                        f"AND d1.node_id <> d2.node_id "
                        f"WITH d1, d2 LIMIT 1 "
                        f"MERGE (d1)-[r:CROSS_PERSON_DEMAND]->(d2) "
                        f"SET r.shared_concept = '{concept}'"
                    )
                    cross_count += 1
                except Exception:
                    pass

    return synced, cross_count


def sync_intents(graph, intents):
    """Sync Intent nodes and EXPRESSES edges to FalkorDB."""
    synced = 0
    for intent in intents:
        intent_id = esc(intent.get("intent_id", ""))
        if not intent_id:
            continue

        label = esc(intent.get("underlying_intent") or intent.get("surface_question", ""))
        domain = esc(intent.get("intent_domain", ""))
        region = esc(intent.get("graph_region", ""))
        person = esc(intent.get("_person", ""))
        recurrence = intent.get("recurrence_count", 1)
        source_cluster = esc(intent.get("source_cluster_id", ""))

        # Create/merge Intent node
        graph.query(
            f"MERGE (i:Intent {{node_id: '{intent_id}'}}) "
            f"SET i.label = '{label[:200]}', "
            f"i.domain = '{domain}', "
            f"i.graph_region = '{region}', "
            f"i.person = '{person}', "
            f"i.recurrence_count = {recurrence}, "
            f"i.source_cluster = '{source_cluster}', "
            f"i.file_type = 'intent'"
        )

        # Link intent to its source demand cluster if it exists
        if source_cluster:
            try:
                graph.query(
                    f"MATCH (i:Intent {{node_id: '{intent_id}'}}), "
                    f"(d:Demand {{node_id: '{source_cluster}'}}) "
                    f"MERGE (i)-[r:EXPRESSES]->(d)"
                )
            except Exception:
                pass  # Demand node may not exist with this exact ID

        synced += 1

    return synced


def sync_convergences(graph, events):
    """Sync Convergence nodes and CONVERGES_TO edges to FalkorDB."""
    synced = 0
    for event in events:
        conv_id = esc(event.get("convergence_id", ""))
        if not conv_id:
            continue

        region = esc(event.get("graph_region", ""))
        conv_type = esc(event.get("type", ""))
        strength = event.get("strength", 0)
        person_count = event.get("person_count", 0)
        intent_count = event.get("intent_count", 0)
        persons = esc(", ".join(event.get("persons", [])))

        # Create/merge Convergence node
        graph.query(
            f"MERGE (c:Convergence {{node_id: '{conv_id}'}}) "
            f"SET c.label = '{region}', "
            f"c.convergence_type = '{conv_type}', "
            f"c.strength = {strength}, "
            f"c.person_count = {person_count}, "
            f"c.intent_count = {intent_count}, "
            f"c.persons = '{persons}', "
            f"c.graph_region = '{region}', "
            f"c.file_type = 'convergence'"
        )

        # Link contributing intents → convergence
        for intent_data in event.get("intents", []):
            intent_id = esc(intent_data.get("intent_id", ""))
            if intent_id:
                try:
                    graph.query(
                        f"MATCH (i:Intent {{node_id: '{intent_id}'}}), "
                        f"(c:Convergence {{node_id: '{conv_id}'}}) "
                        f"MERGE (i)-[r:CONVERGES_TO]->(c)"
                    )
                except Exception:
                    pass

        synced += 1

    return synced


def detect_micro_phases_cypher(graph):
    """Group intents into micro-phases — Cypher-native.

    One query replaces 40 lines of Python defaultdict grouping.
    """
    char_map = {
        "architecture": "specification", "workflow": "specification",
        "integration": "specification", "process": "specification",
        "debugging": "trust-repair", "tooling": "tooling-setup",
    }

    try:
        r = graph.query(
            "MATCH (i:Intent) "
            "WITH i.person AS person, i.graph_region AS region, "
            "  i.domain AS domain, count(i) AS intent_count, "
            "  sum(i.recurrence_count) AS recurrence "
            "WHERE person IS NOT NULL "
            "RETURN person, region, domain, intent_count, recurrence "
            "ORDER BY recurrence DESC"
        )
    except Exception:
        return []

    micro_phases = []
    for row in (r.result_set or []):
        person, region, domain, count, recurrence = row
        character = char_map.get(domain or "", domain or "mixed")
        micro_phases.append({
            "person": person,
            "region": region or "unknown",
            "primary_domain": domain or "mixed",
            "character": character,
            "intent_count": count,
            "recurrence": recurrence,
        })

    return micro_phases


def sync_phase(graph, events, intents):
    """Detect and sync Phase as a topology snapshot — distribution of micro-phases,
    not a single label.

    The Phase node stores:
    - macro_character: the gravitational center (most common micro-phase character)
    - micro_phases: JSON array of per-person orbits
    - dispersion: how scattered vs concentrated the team is (0=uniform, 1=scattered)
    """
    micro_phases = detect_micro_phases_cypher(graph)
    if not micro_phases:
        print(f"  [phase] No intents to analyze.")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Compute macro character (most common)
    char_counts = defaultdict(int)
    for mp in micro_phases:
        char_counts[mp["character"]] += mp["recurrence"]
    macro_character = max(char_counts, key=char_counts.get)

    # Compute dispersion: how many distinct characters exist relative to people
    all_persons = set(mp["person"] for mp in micro_phases)
    unique_characters = set(mp["character"] for mp in micro_phases)
    dispersion = round(len(unique_characters) / max(len(all_persons), 1), 2)

    # Build topology summary
    person_orbits = defaultdict(list)
    for mp in micro_phases:
        person_orbits[mp["person"]].append({
            "region": mp["region"],
            "character": mp["character"],
            "recurrence": mp["recurrence"],
        })

    topology = {
        "persons": {p: orbits for p, orbits in sorted(person_orbits.items())},
        "micro_phases": micro_phases,
        "character_distribution": dict(char_counts),
    }

    total_strength = sum(e.get("strength", 0) for e in events)
    phase_id = f"phase-{date_str}"
    persons_str = esc(", ".join(sorted(all_persons)))
    topology_json = esc(json.dumps(topology, default=str))

    # Deactivate previous active phase
    try:
        graph.query("MATCH (p:Phase {active: true}) SET p.active = false")
    except Exception:
        pass

    # Create Phase node with topology
    graph.query(
        f"MERGE (p:Phase {{node_id: '{esc(phase_id)}'}}) "
        f"SET p.label = '{esc(macro_character)} phase (dispersion: {dispersion})', "
        f"p.demand_character = '{esc(macro_character)}', "
        f"p.detected_at = '{esc(now)}', "
        f"p.active = true, "
        f"p.convergence_count = {len(events)}, "
        f"p.person_count = {len(all_persons)}, "
        f"p.persons = '{persons_str}', "
        f"p.strength = {total_strength}, "
        f"p.dispersion = {dispersion}, "
        f"p.micro_phase_count = {len(unique_characters)}, "
        f"p.topology = '{topology_json}', "
        f"p.file_type = 'phase'"
    )

    # Link convergence events → phase
    for event in events:
        conv_id = esc(event.get("convergence_id", ""))
        if conv_id:
            try:
                graph.query(
                    f"MATCH (p:Phase {{node_id: '{esc(phase_id)}'}}), "
                    f"(c:Convergence {{node_id: '{conv_id}'}}) "
                    f"MERGE (p)-[r:CONSTITUTED_BY]->(c)"
                )
            except Exception:
                pass

    # Print topology
    print(f"  [phase] Macro: {macro_character} | Dispersion: {dispersion} | "
          f"{len(all_persons)} people, {len(unique_characters)} micro-phases")
    for person, orbits in sorted(person_orbits.items()):
        orbit_str = ", ".join(f"{o['character']}({o['region'][:30]})" for o in orbits)
        print(f"    {person}: {orbit_str}")

    return 1


def propagate_communities(graph):
    """Propagate community labels from Knowledge nodes to connected layers.

    Knowledge nodes have community assignments (0-8) from the original graph.
    New layers (Demand, Intent, Convergence, Concept, Document) land in
    community -1. This function flows community through edges:

    Knowledge → Demand (via ANSWERED_BY, PARTIALLY_ANSWERED_BY, UNANSWERED_NEAR)
    Demand → Intent (via EXPRESSES)
    Intent → Convergence (via CONVERGES_TO)
    Convergence → Phase (via CONSTITUTED_BY)
    Knowledge → Concept (via IMPLEMENTS, REFERENCES, EXTENDS, CONSTRAINS)
    Concept → Document (via CONTAINS_CONCEPT, reversed)

    When a node connects to multiple Knowledge communities, it takes
    the community of the highest-degree Knowledge neighbor (strongest pull).
    """
    propagated = 0

    # 1. Demand nodes: match domain to Knowledge community via label text similarity
    #    (direct edges don't exist due to node_id format mismatch)
    try:
        result = graph.query(
            "MATCH (d:Demand) "
            "WHERE d.community IS NULL OR d.community < 0 "
            "MATCH (k:Knowledge) "
            "WHERE k.community IS NOT NULL AND k.community >= 0 "
            "AND ("
            "  toLower(k.label) CONTAINS toLower(d.domain) OR "
            "  toLower(k.tags) CONTAINS toLower(d.domain)"
            ") "
            "WITH d, k.community AS comm, count(k) AS hits "
            "ORDER BY hits DESC "
            "WITH d, collect(comm)[0] AS best_comm "
            "SET d.community = best_comm "
            "RETURN count(d)"
        )
        n = result.result_set[0][0] if result.result_set else 0
        propagated += n
    except Exception:
        pass

    # 2. Concept nodes: inherit from Knowledge they link to (edges exist here)
    try:
        result = graph.query(
            "MATCH (c:Concept)-[]->(k:Knowledge) "
            "WHERE k.community IS NOT NULL AND k.community >= 0 "
            "WITH c, k.community AS comm "
            "ORDER BY comm "
            "WITH c, collect(comm)[0] AS best_comm "
            "WHERE c.community IS NULL OR c.community < 0 "
            "SET c.community = best_comm "
            "RETURN count(c)"
        )
        n = result.result_set[0][0] if result.result_set else 0
        propagated += n
    except Exception:
        pass

    # Concepts without edges to Knowledge: match by label similarity
    try:
        result = graph.query(
            "MATCH (c:Concept) "
            "WHERE c.community IS NULL OR c.community < 0 "
            "MATCH (k:Knowledge) "
            "WHERE k.community IS NOT NULL AND k.community >= 0 "
            "AND ("
            "  toLower(k.label) CONTAINS toLower(c.label) OR "
            "  toLower(c.label) CONTAINS toLower(k.label)"
            ") "
            "WITH c, k.community AS comm "
            "ORDER BY comm "
            "WITH c, collect(comm)[0] AS best_comm "
            "SET c.community = best_comm "
            "RETURN count(c)"
        )
        n = result.result_set[0][0] if result.result_set else 0
        propagated += n
    except Exception:
        pass

    # 2b. Orphan Concepts: inherit from parent Document (which inherits from its other Concepts)
    try:
        result = graph.query(
            "MATCH (d:Document)-[:CONTAINS_CONCEPT]->(c:Concept) "
            "WHERE (c.community IS NULL OR c.community < 0) "
            "AND d.community IS NOT NULL AND d.community >= 0 "
            "SET c.community = d.community "
            "RETURN count(c)"
        )
        n = result.result_set[0][0] if result.result_set else 0
        propagated += n
    except Exception:
        pass

    # 3. Document nodes: inherit from their Concepts' communities (majority vote)
    try:
        result = graph.query(
            "MATCH (d:Document)-[:CONTAINS_CONCEPT]->(c:Concept) "
            "WHERE c.community IS NOT NULL AND c.community >= 0 "
            "WITH d, c.community AS comm, count(c) AS weight "
            "ORDER BY weight DESC "
            "WITH d, collect(comm)[0] AS best_comm "
            "WHERE d.community IS NULL OR d.community < 0 "
            "SET d.community = best_comm "
            "RETURN count(d)"
        )
        n = result.result_set[0][0] if result.result_set else 0
        propagated += n
    except Exception:
        pass

    # 4. Intent and Demand fallback: domain-to-community mapping
    #    When edges and label matching fail, use domain keywords
    domain_map = {
        "rule-builder": 5, "notification": 2, "data-room": 2, "webhook": 2,
        "memory": 0, "continuity": 0, "agent": 0, "harness": 0,
        "configurable": 1, "fund": 1, "frontend": 1, "deal": 1,
        "security": 2, "infrastructure": 2, "deploy": 2, "ci": 2, "api": 2,
        "meta": 3, "intelligence": 3, "process": 3, "tooling": 3,
        "knowledge": 4, "documentation": 4,
        "research": 5, "debugging": 5,
        "architecture": 1, "workflow": 0,
        "codebase": 7, "quality": 7,
    }

    for node_label in ("Demand", "Intent"):
        try:
            result = graph.query(
                f"MATCH (n:{node_label}) "
                f"WHERE n.community IS NULL OR n.community < 0 "
                f"RETURN n.node_id, n.domain"
            )
            for nid, domain in result.result_set:
                if not domain:
                    continue
                dom = domain.lower()
                comm = None
                for key, c in domain_map.items():
                    if key in dom:
                        comm = c
                        break
                if comm is not None:
                    graph.query(
                        f"MATCH (n:{node_label} {{node_id: '{esc(nid)}'}}) "
                        f"SET n.community = {comm}"
                    )
                    propagated += 1
        except Exception:
            pass

    # 5. Convergence nodes: inherit from their contributing Intents (majority vote)
    try:
        result = graph.query(
            "MATCH (i:Intent)-[:CONVERGES_TO]->(c:Convergence) "
            "WHERE i.community IS NOT NULL AND i.community >= 0 "
            "WITH c, i.community AS comm, count(i) AS weight "
            "ORDER BY weight DESC "
            "WITH c, collect(comm)[0] AS best_comm "
            "WHERE c.community IS NULL OR c.community < 0 "
            "SET c.community = best_comm "
            "RETURN count(c)"
        )
        n = result.result_set[0][0] if result.result_set else 0
        propagated += n
    except Exception:
        pass

    # 6. Phase: inherits from strongest Convergence
    try:
        result = graph.query(
            "MATCH (p:Phase)-[:CONSTITUTED_BY]->(c:Convergence) "
            "WHERE c.community IS NOT NULL AND c.community >= 0 "
            "WITH p, c.community AS comm, c.strength AS s "
            "ORDER BY s DESC "
            "WITH p, collect(comm)[0] AS best_comm "
            "WHERE p.community IS NULL OR p.community < 0 "
            "SET p.community = best_comm "
            "RETURN count(p)"
        )
        n = result.result_set[0][0] if result.result_set else 0
        propagated += n
    except Exception:
        pass

    return propagated


def snapshot_current_state(graph):
    """Export current Intent, Convergence, Phase nodes to JSONL before overwriting.

    The graph stays clean (current state only). History lives here.
    Each line is one node with its edges, timestamped.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_str = now.strftime("%Y-%m-%d")

    snapshot_file = SNAPSHOT_DIR / f"{date_str}.jsonl"

    records = []

    # Snapshot intents + their edges
    try:
        result = graph.query(
            "MATCH (i:Intent) "
            "OPTIONAL MATCH (i)-[r]->(target) "
            "RETURN i.node_id, i.label, i.domain, i.graph_region, i.person, "
            "i.recurrence_count, type(r), target.node_id, labels(target)"
        )
        intent_nodes = {}
        for row in result.result_set:
            nid = row[0]
            if nid not in intent_nodes:
                intent_nodes[nid] = {
                    "snapshot_ts": ts, "node_type": "Intent",
                    "node_id": nid, "label": row[1], "domain": row[2],
                    "graph_region": row[3], "person": row[4],
                    "recurrence_count": row[5], "edges": [],
                }
            if row[6]:
                intent_nodes[nid]["edges"].append({
                    "type": row[6], "target": row[7],
                    "target_labels": row[8],
                })
        records.extend(intent_nodes.values())
    except Exception:
        pass

    # Snapshot convergences + their edges
    try:
        result = graph.query(
            "MATCH (c:Convergence) "
            "OPTIONAL MATCH (source)-[r]->(c) "
            "RETURN c.node_id, c.label, c.convergence_type, c.strength, "
            "c.person_count, c.intent_count, c.persons, "
            "type(r), source.node_id, labels(source)"
        )
        conv_nodes = {}
        for row in result.result_set:
            nid = row[0]
            if nid not in conv_nodes:
                conv_nodes[nid] = {
                    "snapshot_ts": ts, "node_type": "Convergence",
                    "node_id": nid, "label": row[1], "type": row[2],
                    "strength": row[3], "person_count": row[4],
                    "intent_count": row[5], "persons": row[6],
                    "inbound_edges": [],
                }
            if row[7]:
                conv_nodes[nid]["inbound_edges"].append({
                    "type": row[7], "source": row[8],
                    "source_labels": row[9],
                })
        records.extend(conv_nodes.values())
    except Exception:
        pass

    # Snapshot phases
    try:
        result = graph.query(
            "MATCH (p:Phase) "
            "OPTIONAL MATCH (p)-[r:CONSTITUTED_BY]->(c:Convergence) "
            "RETURN p.node_id, p.label, p.demand_character, p.active, "
            "p.strength, p.person_count, p.convergence_count, p.persons, "
            "p.detected_at, c.node_id"
        )
        phase_nodes = {}
        for row in result.result_set:
            nid = row[0]
            if nid not in phase_nodes:
                phase_nodes[nid] = {
                    "snapshot_ts": ts, "node_type": "Phase",
                    "node_id": nid, "label": row[1],
                    "demand_character": row[2], "active": row[3],
                    "strength": row[4], "person_count": row[5],
                    "convergence_count": row[6], "persons": row[7],
                    "detected_at": row[8], "convergences": [],
                }
            if row[9]:
                phase_nodes[nid]["convergences"].append(row[9])
        records.extend(phase_nodes.values())
    except Exception:
        pass

    if not records:
        return 0

    # Append to today's snapshot file (multiple cycles per day append, not overwrite)
    with open(snapshot_file, "a") as f:
        for record in records:
            f.write(json.dumps(record, default=str) + "\n")

    return len(records)


def main():
    print(f"[sync-layers] Syncing demand/intent/convergence/phase to FalkorDB...")

    demands = load_demand_files()
    cross_demands = load_cross_demands()
    intents = load_intent_files()
    events = load_convergence_events()

    print(f"  Demand clusters: {len(demands)}")
    print(f"  Cross-person demands: {len(cross_demands)}")
    print(f"  Intents: {len(intents)}")
    print(f"  Convergence events: {len(events)}")

    if not demands and not intents and not events:
        print("  Nothing to sync.")
        return

    try:
        graph = get_graph()
    except Exception as e:
        print(f"  FalkorDB connection failed: {e}")
        print(f"  Non-fatal: sync-layers skipped.")
        return

    # Snapshot current state before overwriting
    snap_count = snapshot_current_state(graph)
    if snap_count:
        print(f"  Snapshot: {snap_count} nodes archived to {SNAPSHOT_DIR.name}/")

    # Sync in order: demands first (intents link to them), then intents, convergences, phase
    demand_count, cross_count = sync_demands(graph, demands, cross_demands)
    print(f"  Synced {demand_count} demand nodes, {cross_count} cross-person edges")

    intent_count = sync_intents(graph, intents)
    print(f"  Synced {intent_count} intent nodes")

    conv_count = sync_convergences(graph, events)
    print(f"  Synced {conv_count} convergence nodes")

    phase_count = sync_phase(graph, events, intents)
    print(f"  Phase nodes: {phase_count}")

    # Propagate communities from Knowledge layer to all other layers
    propagated = propagate_communities(graph)
    print(f"  Community propagation: {propagated} nodes assigned")

    # Summary
    total = demand_count + intent_count + conv_count + phase_count
    print(f"[sync-layers] Done: {total} nodes synced to graph")


if __name__ == "__main__":
    main()
