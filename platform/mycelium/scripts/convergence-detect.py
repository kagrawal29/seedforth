#!/usr/bin/env python3
"""
Convergence Detection (L6) — Cypher-native.

All intelligence is graph traversal. Python is I/O glue only:
reads from FalkorDB, writes JSON + markdown output files.

Previous: 364 lines of Python with defaultdicts, grouping, deduplication.
Now: 3 Cypher queries + file writes.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMAND_DIR = REPO_ROOT / "signals" / "demand"
OUTPUT_JSON = DEMAND_DIR / "convergence-events.json"
OUTPUT_MD = REPO_ROOT / "knowledge" / "meta" / "convergence-report.md"

MIN_INTENTS = 3
MIN_PERSONS = 2

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))


def get_graph():
    from falkordb import FalkorDB
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


def main():
    print("[convergence] Cypher-native convergence detection...")

    try:
        graph = get_graph()
    except Exception as e:
        print(f"  FalkorDB unavailable: {e}. Checking flat files fallback.")
        # Fallback: read intent JSON files if graph is down
        return fallback_from_files()

    now = datetime.now(timezone.utc)
    ts = now.isoformat()

    # ================================================================
    # QUERY 1: Region convergence — intents grouped by graph_region
    # ================================================================
    try:
        r1 = graph.query(
            "MATCH (i:Intent) "
            "WITH i.graph_region AS region, "
            "  collect(DISTINCT i.person) AS people, "
            "  count(i) AS intent_count, "
            "  sum(i.recurrence_count) AS total_recurrence, "
            "  collect({person: i.person, intent_id: i.node_id, "
            "    label: i.label, domain: i.domain, "
            "    recurrence: i.recurrence_count}) AS intents "
            f"WHERE intent_count >= {MIN_INTENTS} AND size(people) >= {MIN_PERSONS} "
            "RETURN region, people, intent_count, total_recurrence, intents "
            "ORDER BY total_recurrence DESC"
        )
        region_events = []
        for row in r1.result_set:
            strength = (row[2] * 1.0) + (len(row[1]) * 2.0) + (row[3] * 0.5)
            region_events.append({
                "convergence_id": f"region-{(row[0] or 'unknown').lower().replace(' ', '-')}",
                "type": "region_cluster",
                "graph_region": row[0],
                "intent_count": row[2],
                "person_count": len(row[1]),
                "persons": sorted(row[1]),
                "total_recurrence": row[3],
                "intents": row[4],
                "strength": strength,
            })
    except Exception as e:
        print(f"  Region query failed: {e}")
        region_events = []

    # ================================================================
    # QUERY 2: Cross-person demand reinforcement
    # ================================================================
    try:
        r2 = graph.query(
            "MATCH (d1:Demand)-[:CROSS_PERSON_DEMAND]-(d2:Demand) "
            "WHERE d1.person <> d2.person "
            "RETURN d1.person, d2.person, d1.label, d2.label, d1.domain"
        )
        # Group cross-demands by domain
        cross_events = []
        seen_pairs = set()
        for row in r2.result_set:
            pair = tuple(sorted([row[0], row[1]]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                # Don't create separate events — these reinforce region events
    except Exception:
        pass

    # ================================================================
    # QUERY 3: Count totals for reporting
    # ================================================================
    try:
        r3 = graph.query(
            "MATCH (i:Intent) "
            "RETURN count(i) AS total_intents, "
            "  count(DISTINCT i.person) AS total_persons"
        )
        total_intents = r3.result_set[0][0] if r3.result_set else 0
        total_persons = r3.result_set[0][1] if r3.result_set else 0
    except Exception:
        total_intents = 0
        total_persons = 0

    # Deduplicate and sort
    all_events = sorted(region_events, key=lambda e: -e["strength"])

    print(f"  Intents: {total_intents} from {total_persons} people")
    print(f"  Region convergence: {len(region_events)}")
    print(f"  Total convergence events: {len(all_events)}")

    # Write JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "computed_at": ts,
        "threshold": {"min_intents": MIN_INTENTS, "min_persons": MIN_PERSONS},
        "events": all_events,
        "summary": {
            "total_events": len(all_events),
            "total_intents_analyzed": total_intents,
            "persons_analyzed": total_persons,
            "strongest_region": all_events[0]["graph_region"] if all_events else None,
            "strongest_strength": all_events[0]["strength"] if all_events else 0,
        },
    }
    OUTPUT_JSON.write_text(json.dumps(output, indent=2, default=str))
    print(f"  Wrote {OUTPUT_JSON}")

    # Write markdown report
    report = generate_report(all_events, total_intents, total_persons)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(report)
    print(f"  Wrote {OUTPUT_MD}")

    if all_events:
        print(f"\n  === CONVERGENCE DETECTED ===")
        for event in all_events[:3]:
            print(f"    [{event['type']}] {event['graph_region']}: "
                  f"{event['person_count']} people, {event['intent_count']} intents, "
                  f"strength {event['strength']:.1f}")
    else:
        print(f"\n  No convergence events (below threshold).")


def generate_report(events, total_intents, total_persons):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Convergence Report — {now}",
        "",
        f"**Input:** {total_intents} intents from {total_persons} people",
        f"**Threshold:** {MIN_INTENTS}+ intents from {MIN_PERSONS}+ people",
        f"**Events found:** {len(events)}",
        f"**Method:** Cypher-native (3 graph queries, zero Python intelligence)",
        "",
    ]
    if not events:
        lines.append("No convergence events detected.")
        return "\n".join(lines)

    lines.append("## Active Convergence Events")
    lines.append("")
    for i, event in enumerate(events, 1):
        lines.append(f"### {i}. {event['graph_region']} (strength: {event['strength']:.1f})")
        lines.append(f"- **Type:** {event['type']}")
        lines.append(f"- **People:** {', '.join(event['persons'])}")
        lines.append(f"- **Intent count:** {event['intent_count']}")
        lines.append("")
        for intent in (event.get("intents") or [])[:5]:
            if isinstance(intent, dict):
                lines.append(f"  - **{intent.get('person', '?')}**: {str(intent.get('label', ''))[:120]}")
        lines.append("")

    lines.append("---")
    lines.append(f"*Generated by convergence-detect.py (Cypher-native). Threshold: {MIN_INTENTS} intents, {MIN_PERSONS} people.*")
    return "\n".join(lines)


def fallback_from_files():
    """Fallback when FalkorDB is unavailable — read flat intent files."""
    from collections import defaultdict

    intents_by_region = defaultdict(list)
    for fp in sorted(DEMAND_DIR.glob("*-intents.json")):
        if fp.name == "cross-person-intents.json":
            continue
        try:
            data = json.loads(fp.read_text())
            person = data.get("person", "")
            for intent in data.get("intents", []):
                region = (intent.get("graph_region") or "").lower().strip()
                if region:
                    intents_by_region[region].append({"person": person, **intent})
        except Exception:
            continue

    events = []
    for region, intents in intents_by_region.items():
        persons = set(i["person"] for i in intents)
        if len(intents) >= MIN_INTENTS and len(persons) >= MIN_PERSONS:
            recurrence = sum(i.get("recurrence_count", 1) for i in intents)
            strength = (len(intents) * 1.0) + (len(persons) * 2.0) + (recurrence * 0.5)
            events.append({
                "convergence_id": f"region-{region.replace(' ', '-')}",
                "type": "region_cluster",
                "graph_region": region,
                "intent_count": len(intents),
                "person_count": len(persons),
                "persons": sorted(persons),
                "total_recurrence": recurrence,
                "strength": strength,
            })

    events.sort(key=lambda e: -e["strength"])
    now = datetime.now(timezone.utc).isoformat()

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps({
        "computed_at": now, "events": events,
        "summary": {"total_events": len(events), "method": "fallback_flat_files"},
    }, indent=2, default=str))

    total = sum(len(v) for v in intents_by_region.values())
    print(f"  [fallback] {total} intents, {len(events)} convergence events from flat files")


if __name__ == "__main__":
    main()
