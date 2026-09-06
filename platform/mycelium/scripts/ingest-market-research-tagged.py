#!/usr/bin/env python3
"""
Zero-cost market research ingestion: tagged data → Asgard Graph
No LLM needed. Field mapping only.

Sources:
  - data/tagged/reddit/*.json   (~287 records)
  - data/tagged/twitter/*.json  (~947 records)
  - data/tagged/linkedin/*.json (~101 records)
  - data/raw/g2/parsed/*.json   (~360 reviews)

Target: FalkorDB (asgard graph) via Redis
"""

import json
import os
import sys
import re

try:
    from falkordb import FalkorDB
    USE_FALKORDB = True
except ImportError:
    USE_FALKORDB = False
    import redis
    from redis.commands.graph import Graph

# --- Config ---
REPO_PATH = os.environ.get("MARKET_RESEARCH_REPO", "/tmp/maverick-market-research")
FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"

# --- Mappings ---
WORKFLOW_TO_FC = {
    "deal_flow": "fc-deal-flow", "pipeline": "fc-deal-flow", "deal flow": "fc-deal-flow",
    "crm": "fc-crm", "contact": "fc-crm", "crm_workflow": "fc-crm", "crm_data_entry": "fc-crm",
    "relationship_management": "fc-crm", "contact_management": "fc-crm",
    "due_diligence": "fc-due-diligence", "diligence": "fc-due-diligence", "research": "fc-due-diligence",
    "deal_screening": "fc-due-diligence", "memo": "fc-due-diligence",
    "lp_reporting": "fc-lp-reporting", "lp reporting": "fc-lp-reporting",
    "investor_reporting": "fc-lp-reporting", "investor reporting": "fc-lp-reporting",
    "lp_update": "fc-lp-reporting", "quarterly_reporting": "fc-lp-reporting",
    "portfolio": "fc-portfolio-monitoring", "portfolio_monitoring": "fc-portfolio-monitoring",
    "portfolio monitoring": "fc-portfolio-monitoring", "portfolio_management": "fc-portfolio-monitoring",
    "fund_ops": "fc-fund-ops", "fund operations": "fc-fund-ops", "fund_admin": "fc-fund-ops",
    "fund_administration": "fc-fund-ops", "capital_calls": "fc-fund-ops",
    "sourcing": "fc-sourcing", "deal_sourcing": "fc-sourcing", "deal sourcing": "fc-sourcing",
    "outbound": "fc-sourcing",
    "email": "fc-email-comms", "communications": "fc-email-comms",
    "data": "fc-data-enrichment", "enrichment": "fc-data-enrichment",
    "market_intelligence": "fc-data-enrichment", "data_quality": "fc-data-enrichment",
    "ai": "fc-ai-agent", "agent": "fc-ai-agent", "automation": "fc-workflow-automation",
    "workflow": "fc-workflow-automation", "cap_table": "fc-cap-table",
    "general_operations": "fc-workflow-automation", "general_operation": "fc-workflow-automation",
}

BRAND_TO_COMPETITOR = {
    "affinity": "comp-affinity", "attio": "comp-attio", "carta": "comp-carta",
    "pitchbook": "comp-pitchbook", "dealcloud": "comp-dealcloud", "intapp": "comp-dealcloud",
    "harmonic": "comp-harmonic", "meridian": "comp-meridian-ai", "totem": "comp-totem-vc",
    "kruncher": "comp-kruncher", "visible": "comp-visible", "standard metrics": "comp-standard-metrics",
    "standard_metrics": "comp-standard-metrics", "evertrace": "comp-evertrace",
    "edda": "comp-edda", "hanover": "comp-hanover-park", "hanover park": "comp-hanover-park",
    "reubenai": "comp-reubenai", "angellist": "comp-angellist", "angel list": "comp-angellist",
    "juniper square": "comp-juniper-square", "juniper_square": "comp-juniper-square",
    "4degrees": "comp-4degrees", "zapflow": "comp-zapflow", "venture360": "comp-venture360",
    "vestberry": "comp-vestberry", "allvue": "comp-allvue", "folk": "comp-folk",
    "clarify": "comp-clarify", "specter": "comp-specter", "brightwave": "comp-brightwave",
    "alphalens": "comp-alphalens", "deckmatch": "comp-alphalens",
    "granola": "comp-granola", "dynamo": "comp-dynamo", "dealmatter": "comp-dealmatter",
    "hubspot": "comp-hubspot", "salesforce": "comp-salesforce",
    "chronograph": "comp-chronograph", "oncorps": "comp-oncorps-ai",
    "cap vc": "comp-cap-vc", "vcos": "comp-vcos", "grata": "comp-grata",
    "alphasense": "comp-alphasense", "cyndx": "comp-cyndx",
    "crunchbase": "comp-crunchbase", "accorata": "comp-accorata",
}

PLATFORM_IDS = {
    "reddit": "platform-reddit",
    "twitter": "platform-twitter",
    "linkedin": "platform-linkedin",
    "g2": "platform-g2",
}


def escape_cypher(s):
    """Escape string for Cypher single-quoted literals."""
    if not s:
        return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")


def truncate(s, n=120):
    s = str(s).replace("\n", " ").strip()
    return s[:n] + "..." if len(s) > n else s


def map_workflow(workflow_area):
    """Map a workflow_area string to a FeatureCategory node_id."""
    if not workflow_area:
        return None
    wa = workflow_area.lower().strip()
    if wa in WORKFLOW_TO_FC:
        return WORKFLOW_TO_FC[wa]
    # Fuzzy: check if any key is a substring
    for key, fc_id in WORKFLOW_TO_FC.items():
        if key in wa or wa in key:
            return fc_id
    return None


def map_brand(brand_name):
    """Map a brand name to a Competitor node_id."""
    if not brand_name:
        return None
    bn = brand_name.lower().strip()
    if bn in BRAND_TO_COMPETITOR:
        return BRAND_TO_COMPETITOR[bn]
    for key, comp_id in BRAND_TO_COMPETITOR.items():
        if key in bn or bn in key:
            return comp_id
    return None


def ingest_reddit(graph):
    """Ingest tagged Reddit data."""
    path = os.path.join(REPO_PATH, "data/tagged/reddit")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return 0

    total = 0
    for fname in sorted(os.listdir(path)):
        if not fname.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(path, fname)))
            items = data.get("tagged_items", data if isinstance(data, list) else [])
            if not isinstance(items, list):
                continue

            for item in items:
                nid = f"ev-reddit-{escape_cypher(item.get('id', f'{fname}_{total}'))}"
                quote = escape_cypher(item.get("exact_quote", ""))
                if not quote:
                    continue

                label = escape_cypher(truncate(item.get("exact_quote", "")))
                url = escape_cypher(item.get("url", ""))
                author = escape_cypher(item.get("author", ""))
                subreddit = escape_cypher(item.get("subreddit", ""))
                date = escape_cypher(item.get("date", ""))
                sentiment = escape_cypher(item.get("sentiment", ""))
                signal_type = escape_cypher(item.get("signal_type", ""))
                workflow_area = item.get("workflow_area", "")
                topics = escape_cypher(", ".join(item.get("topics", [])))

                cypher = f"""
                MERGE (ev:Evidence {{node_id: '{nid}'}})
                SET ev.label = '{label}',
                    ev.platform = 'Reddit',
                    ev.quote = '{quote}',
                    ev.source = 'r/{subreddit} u/{author}',
                    ev.url = '{url}',
                    ev.date = '{date}',
                    ev.sentiment = '{sentiment}',
                    ev.signal_type = '{signal_type}',
                    ev.workflow_area = '{escape_cypher(workflow_area)}',
                    ev.topics = '{topics}',
                    ev.ingestion = 'script'
                """
                try:
                    graph.query(cypher)
                except Exception as e:
                    print(f"    ERR node {nid}: {e}")
                    continue

                # Wire to platform
                graph.query(f"""
                    MATCH (ev:Evidence {{node_id: '{nid}'}}), (p:Platform {{node_id: 'platform-reddit'}})
                    MERGE (ev)-[:ON]->(p)
                """)

                # Wire to competitors
                for brand in item.get("brands_mentioned", []):
                    comp_id = map_brand(brand)
                    if comp_id:
                        graph.query(f"""
                            MATCH (ev:Evidence {{node_id: '{nid}'}}), (c:Competitor {{node_id: '{comp_id}'}})
                            MERGE (ev)-[:ABOUT]->(c)
                        """)

                # Wire to feature category
                fc_id = map_workflow(workflow_area)
                if fc_id:
                    graph.query(f"""
                        MATCH (ev:Evidence {{node_id: '{nid}'}}), (fc:FeatureCategory {{node_id: '{fc_id}'}})
                        MERGE (ev)-[:RELATES_TO]->(fc)
                    """)

                total += 1

            print(f"  Reddit: {fname} → {len(items)} items")
        except Exception as e:
            print(f"  ERR file {fname}: {e}")

    return total


def ingest_twitter(graph):
    """Ingest tagged Twitter data."""
    path = os.path.join(REPO_PATH, "data/tagged/twitter")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return 0

    total = 0
    for fname in sorted(os.listdir(path)):
        if not fname.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(path, fname)))
            items = data.get("tagged_items", data if isinstance(data, list) else [])
            if not isinstance(items, list):
                continue

            brand_ctx = data.get("brand", data.get("handle", fname.replace(".json", "")))
            file_count = 0

            for item in items:
                text = item.get("text", "")
                if not text:
                    continue

                # Filter noise: only notable or engagement > 5
                engagement = 0
                if isinstance(item.get("engagement"), dict):
                    engagement = item["engagement"].get("favorites", 0) or 0
                notable = item.get("notable", False)

                # For brand files, include all (they're already curated)
                # For keyword files, filter
                is_brand_file = "_brand" in fname or "_replies" in fname
                if not is_brand_file and not notable and engagement < 5:
                    continue

                idx = item.get("idx", item.get("tweet_id", f"{fname}_{total}"))
                nid = f"ev-twitter-{escape_cypher(str(idx))}_{escape_cypher(fname[:20])}"
                label = escape_cypher(truncate(text))
                quote = escape_cypher(text)
                date = escape_cypher(item.get("date", ""))
                author = escape_cypher(item.get("author", ""))
                voice = escape_cypher(item.get("voice", ""))
                signal_type = escape_cypher(item.get("signal_type", item.get("tweet_type", "")))
                topics = escape_cypher(", ".join(item.get("topics", [])))
                pain = escape_cypher(", ".join(item.get("pain_addressed", item.get("pain_points", []))))
                vc_rel = escape_cypher(item.get("vc_relevance", ""))

                cypher = f"""
                MERGE (ev:Evidence {{node_id: '{nid}'}})
                SET ev.label = '{label}',
                    ev.platform = 'Twitter',
                    ev.quote = '{quote}',
                    ev.source = '@{author}',
                    ev.date = '{date}',
                    ev.engagement = {engagement},
                    ev.voice = '{voice}',
                    ev.signal_type = '{signal_type}',
                    ev.topics = '{topics}',
                    ev.pain_addressed = '{pain}',
                    ev.vc_relevance = '{vc_rel}',
                    ev.ingestion = 'script'
                """
                try:
                    graph.query(cypher)
                except Exception as e:
                    print(f"    ERR node {nid}: {e}")
                    continue

                # Wire to platform
                graph.query(f"""
                    MATCH (ev:Evidence {{node_id: '{nid}'}}), (p:Platform {{node_id: 'platform-twitter'}})
                    MERGE (ev)-[:ON]->(p)
                """)

                # Wire to competitors from brands_mentioned or brand context
                brands = item.get("brands_mentioned", [])
                if not brands and brand_ctx:
                    brands = [brand_ctx]
                for brand in brands:
                    comp_id = map_brand(brand)
                    if comp_id:
                        graph.query(f"""
                            MATCH (ev:Evidence {{node_id: '{nid}'}}), (c:Competitor {{node_id: '{comp_id}'}})
                            MERGE (ev)-[:ABOUT]->(c)
                        """)

                # Wire to feature category from topics
                for topic in item.get("topics", []):
                    fc_id = map_workflow(topic)
                    if fc_id:
                        graph.query(f"""
                            MATCH (ev:Evidence {{node_id: '{nid}'}}), (fc:FeatureCategory {{node_id: '{fc_id}'}})
                            MERGE (ev)-[:RELATES_TO]->(fc)
                        """)
                        break  # one FC per evidence to avoid over-wiring

                total += 1
                file_count += 1

            print(f"  Twitter: {fname} → {file_count} items ingested")
        except Exception as e:
            print(f"  ERR file {fname}: {e}")

    return total


def ingest_linkedin(graph):
    """Ingest tagged LinkedIn data."""
    path = os.path.join(REPO_PATH, "data/tagged/linkedin")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return 0

    total = 0
    for fname in sorted(os.listdir(path)):
        if not fname.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(path, fname)))
            items = data.get("tagged_items", data if isinstance(data, list) else [])
            if not isinstance(items, list):
                continue

            for item in items:
                quote = item.get("exact_quote", "")
                if not quote:
                    continue

                nid = f"ev-linkedin-{escape_cypher(item.get('id', f'{fname}_{total}'))}"
                label = escape_cypher(truncate(quote))
                quote_esc = escape_cypher(quote)
                url = escape_cypher(item.get("url", ""))
                author = escape_cypher(item.get("author", ""))
                date = escape_cypher(item.get("date", ""))
                sentiment = escape_cypher(item.get("sentiment", ""))
                signal_type = escape_cypher(item.get("signal_type", ""))
                source_type = escape_cypher(item.get("source_type", ""))
                workflow_area = item.get("workflow_area", "")
                topics = escape_cypher(", ".join(item.get("topics", [])))

                cypher = f"""
                MERGE (ev:Evidence {{node_id: '{nid}'}})
                SET ev.label = '{label}',
                    ev.platform = 'LinkedIn',
                    ev.quote = '{quote_esc}',
                    ev.source = '{author}',
                    ev.url = '{url}',
                    ev.date = '{date}',
                    ev.sentiment = '{sentiment}',
                    ev.signal_type = '{signal_type}',
                    ev.source_type = '{source_type}',
                    ev.workflow_area = '{escape_cypher(workflow_area)}',
                    ev.topics = '{topics}',
                    ev.ingestion = 'script'
                """
                try:
                    graph.query(cypher)
                except Exception as e:
                    print(f"    ERR node {nid}: {e}")
                    continue

                # Wire to platform
                graph.query(f"""
                    MATCH (ev:Evidence {{node_id: '{nid}'}}), (p:Platform {{node_id: 'platform-linkedin'}})
                    MERGE (ev)-[:ON]->(p)
                """)

                # Wire to competitors
                for brand in item.get("brands_mentioned", []):
                    comp_id = map_brand(brand)
                    if comp_id:
                        graph.query(f"""
                            MATCH (ev:Evidence {{node_id: '{nid}'}}), (c:Competitor {{node_id: '{comp_id}'}})
                            MERGE (ev)-[:ABOUT]->(c)
                        """)

                # Wire to feature category
                fc_id = map_workflow(workflow_area)
                if fc_id:
                    graph.query(f"""
                        MATCH (ev:Evidence {{node_id: '{nid}'}}), (fc:FeatureCategory {{node_id: '{fc_id}'}})
                        MERGE (ev)-[:RELATES_TO]->(fc)
                    """)

                total += 1

            print(f"  LinkedIn: {fname} → {len(items)} items")
        except Exception as e:
            print(f"  ERR file {fname}: {e}")

    return total


def ingest_g2(graph):
    """Ingest parsed G2 reviews."""
    path = os.path.join(REPO_PATH, "data/raw/g2/parsed")
    if not os.path.exists(path):
        print(f"  SKIP: {path} not found")
        return 0

    total = 0
    for fname in sorted(os.listdir(path)):
        if not fname.endswith(".json"):
            continue
        try:
            data = json.load(open(os.path.join(path, fname)))
            reviews = data.get("reviews", data if isinstance(data, list) else [])
            brand = data.get("product", fname.replace(".json", ""))
            comp_id = map_brand(brand)

            for i, review in enumerate(reviews):
                nid = f"review-g2-{escape_cypher(brand)}-{i}"
                like = escape_cypher(review.get("like", ""))
                dislike = escape_cypher(review.get("dislike", ""))
                problems = escape_cypher(review.get("problems", ""))
                rating = review.get("rating", 0)
                role = escape_cypher(review.get("role", ""))
                company_size = escape_cypher(review.get("company_size", ""))
                date = escape_cypher(review.get("date", ""))
                label = escape_cypher(truncate(like or dislike or "G2 review", 80))

                cypher = f"""
                MERGE (r:Review {{node_id: '{nid}'}})
                SET r.label = '{label}',
                    r.platform = 'G2',
                    r.brand = '{escape_cypher(brand)}',
                    r.rating = {rating if isinstance(rating, (int, float)) else 0},
                    r.like_text = '{like}',
                    r.dislike_text = '{dislike}',
                    r.problems = '{problems}',
                    r.reviewer_role = '{role}',
                    r.company_size = '{company_size}',
                    r.date = '{date}',
                    r.ingestion = 'script'
                """
                try:
                    graph.query(cypher)
                except Exception as e:
                    print(f"    ERR review {nid}: {e}")
                    continue

                # Wire to platform
                graph.query(f"""
                    MATCH (r:Review {{node_id: '{nid}'}}), (p:Platform {{node_id: 'platform-g2'}})
                    MERGE (r)-[:ON]->(p)
                """)

                # Wire to competitor
                if comp_id:
                    graph.query(f"""
                        MATCH (r:Review {{node_id: '{nid}'}}), (c:Competitor {{node_id: '{comp_id}'}})
                        MERGE (r)-[:REVIEWS]->(c)
                    """)

                total += 1

            print(f"  G2: {fname} → {len(reviews)} reviews")
        except Exception as e:
            print(f"  ERR file {fname}: {e}")

    return total


def main():
    print(f"Connecting to FalkorDB at {FALKORDB_HOST}:{FALKORDB_PORT}...")
    if USE_FALKORDB:
        db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
        graph = db.select_graph(GRAPH_NAME)
    else:
        r = redis.Redis(host=FALKORDB_HOST, port=FALKORDB_PORT, decode_responses=True)
        graph = Graph(r, GRAPH_NAME)
    print(f"Connected. Graph: {GRAPH_NAME}")

    print(f"\nRepo path: {REPO_PATH}")
    if not os.path.exists(REPO_PATH):
        print(f"ERROR: {REPO_PATH} not found. Clone the repo first:")
        print(f"  git clone https://github.com/Qubit-Capital/maverick-market-research.git {REPO_PATH}")
        sys.exit(1)

    print("\n=== Ingesting Tagged Reddit ===")
    reddit_count = ingest_reddit(graph)

    print("\n=== Ingesting Tagged Twitter ===")
    twitter_count = ingest_twitter(graph)

    print("\n=== Ingesting Tagged LinkedIn ===")
    linkedin_count = ingest_linkedin(graph)

    print("\n=== Ingesting G2 Reviews ===")
    g2_count = ingest_g2(graph)

    print("\n=== DONE ===")
    print(f"Reddit:   {reddit_count} evidence nodes")
    print(f"Twitter:  {twitter_count} evidence nodes")
    print(f"LinkedIn: {linkedin_count} evidence nodes")
    print(f"G2:       {g2_count} review nodes")
    print(f"TOTAL:    {reddit_count + twitter_count + linkedin_count + g2_count} nodes ingested")

    # Verify
    result = graph.query("MATCH (ev:Evidence) RETURN count(ev) AS total")
    print(f"\nTotal Evidence nodes in graph: {result.result_set[0][0]}")
    result = graph.query("MATCH (r:Review) RETURN count(r) AS total")
    print(f"Total Review nodes in graph: {result.result_set[0][0]}")
    result = graph.query("MATCH ()-[r]->() RETURN type(r), count(r) ORDER BY count(r) DESC LIMIT 15")
    print("\nEdge counts:")
    for row in result.result_set:
        print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    main()
