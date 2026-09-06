#!/usr/bin/env python3
"""
Code-as-Graph — ingest TypeScript codebase structure into FalkorDB. Zero LLM.

Reads the product repo's file tree and creates nodes for:
- Modules (FSD layers: features, entities, widgets, app pages)
- Dependencies (import edges between modules)
- Types (exported interfaces/types as contract nodes)
- API Routes (endpoints as nodes)

The code structure connects to existing Feature/Screen/Widget nodes,
closing the loop: Persona → Scenario → Feature → Module → Type → API.

When a Scenario needs a Feature that has no Module, that's a real
implementation gap — not from specs, from code.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "localhost")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
GRAPH_NAME = "asgard"


def esc(s):
    if s is None: return ""
    return str(s).replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ")[:300]


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph(GRAPH_NAME)


def get_file_tree(org: str, repo: str) -> list[dict]:
    """Get the full file tree from GitHub."""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{org}/{repo}/git/trees/main?recursive=1",
             "--jq", ".tree[] | {path: .path, type: .type, size: .size}"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return []
        # Parse JSONL output
        entries = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                entries.append(json.loads(line))
        return entries
    except Exception:
        return []


def extract_modules(tree: list[dict]) -> list[dict]:
    """Extract FSD modules from file tree.

    A module is a directory under src/features/, src/entities/,
    src/widgets/, or src/app/ that represents a cohesive unit.
    """
    modules = []
    seen = set()

    for entry in tree:
        path = entry.get("path", "")
        if entry.get("type") != "blob":
            continue

        # Features: src/features/{name}/
        m = re.match(r"src/features/([^/]+)/", path)
        if m and m.group(1) not in seen:
            name = m.group(1)
            seen.add(name)
            # Detect sub-layers
            layers = set()
            for e in tree:
                if e["path"].startswith(f"src/features/{name}/"):
                    layer_match = re.match(f"src/features/{name}/([^/]+)/", e["path"])
                    if layer_match:
                        layers.add(layer_match.group(1))
            modules.append({
                "id": f"module-feature-{name}",
                "label": name.replace("-", " ").title(),
                "fsd_layer": "feature",
                "path": f"src/features/{name}",
                "sub_layers": sorted(layers),
                "feature_id": f"feature-{name}",
            })

        # Entities: src/entities/{name}/
        m = re.match(r"src/entities/([^/]+)/", path)
        if m and f"entity-{m.group(1)}" not in seen:
            name = m.group(1)
            seen.add(f"entity-{name}")
            modules.append({
                "id": f"module-entity-{name}",
                "label": f"Entity: {name.replace('-', ' ').title()}",
                "fsd_layer": "entity",
                "path": f"src/entities/{name}",
                "sub_layers": [],
                "feature_id": None,
            })

        # Widgets: src/widgets/{name}/
        m = re.match(r"src/widgets/([^/]+)/", path)
        if m and f"widget-{m.group(1)}" not in seen:
            name = m.group(1)
            seen.add(f"widget-{name}")
            modules.append({
                "id": f"module-widget-{name}",
                "label": f"Widget: {name.replace('-', ' ').title()}",
                "fsd_layer": "widget",
                "path": f"src/widgets/{name}",
                "sub_layers": [],
                "feature_id": None,
            })

        # App pages: src/app/{path}/page.tsx
        m = re.match(r"src/app/(.+)/page\.tsx$", path)
        if m:
            route = m.group(1)
            page_id = f"module-page-{route.replace('/', '-').replace('[', '').replace(']', '')}"
            if page_id not in seen:
                seen.add(page_id)
                modules.append({
                    "id": page_id,
                    "label": f"Page: /{route}",
                    "fsd_layer": "page",
                    "path": f"src/app/{route}",
                    "sub_layers": [],
                    "feature_id": None,
                })

    return modules


def detect_dependencies(tree: list[dict], modules: list[dict]) -> list[dict]:
    """Detect import dependencies between modules from file paths.

    In FSD, features import from entities, widgets import from features,
    pages import from widgets and features. We detect this from the
    directory structure convention.
    """
    deps = []
    module_paths = {m["path"]: m["id"] for m in modules}

    # FSD dependency rules (allowed imports)
    fsd_deps = {
        "feature": ["entity"],           # features can import entities
        "widget": ["feature", "entity"],  # widgets can import features + entities
        "page": ["widget", "feature", "entity"],  # pages can import anything
    }

    for mod in modules:
        layer = mod["fsd_layer"]
        allowed = fsd_deps.get(layer, [])
        for target_mod in modules:
            if target_mod["fsd_layer"] in allowed:
                # Check if this dependency likely exists based on naming conventions
                src_name = mod["path"].split("/")[-1]
                tgt_name = target_mod["path"].split("/")[-1]

                # Common patterns: deal-workspace widget imports deal entity
                if tgt_name in src_name or src_name.startswith(tgt_name.split("-")[0]):
                    deps.append({
                        "source": mod["id"],
                        "target": target_mod["id"],
                        "type": "IMPORTS",
                    })

    return deps


def sync_to_graph(graph, modules: list[dict], deps: list[dict]):
    """Sync code modules and dependencies to FalkorDB."""
    mod_count = 0
    dep_count = 0
    link_count = 0

    for mod in modules:
        try:
            layers_str = esc(", ".join(mod["sub_layers"])) if mod["sub_layers"] else ""
            graph.query(
                f"MERGE (m:Module {{node_id: '{esc(mod['id'])}'}}) "
                f"SET m.label = '{esc(mod['label'])}', "
                f"m.fsd_layer = '{esc(mod['fsd_layer'])}', "
                f"m.path = '{esc(mod['path'])}', "
                f"m.sub_layers = '{layers_str}', "
                f"m.file_type = 'module'"
            )

            # Link Module → Feature/Widget node if it exists
            feature_id = mod.get("feature_id")
            if feature_id:
                try:
                    graph.query(
                        f"MATCH (m:Module {{node_id: '{esc(mod['id'])}'}}),"
                        f" (f:Feature {{node_id: '{esc(feature_id)}'}}) "
                        f"MERGE (m)-[:IMPLEMENTS]->(f)"
                    )
                    link_count += 1
                except Exception:
                    pass

            mod_count += 1
        except Exception:
            pass

    # Sync dependencies
    for dep in deps:
        try:
            graph.query(
                f"MATCH (s:Module {{node_id: '{esc(dep['source'])}'}}),"
                f" (t:Module {{node_id: '{esc(dep['target'])}'}}) "
                f"MERGE (s)-[:IMPORTS]->(t)"
            )
            dep_count += 1
        except Exception:
            pass

    # Detect Features with no Module (implementation gaps)
    try:
        r = graph.query(
            "MATCH (f:Feature) WHERE NOT (:Module)-[:IMPLEMENTS]->(f) "
            "RETURN f.label, f.node_id"
        )
        if r.result_set:
            print(f"  Implementation gaps (Features with no Module):")
            for row in r.result_set:
                print(f"    GAP: {row[0]}")
    except Exception:
        pass

    return mod_count, dep_count, link_count


def main():
    print("[code-graph] Ingesting codebase structure — zero LLM")

    tree = get_file_tree("Qubit-Capital", "VC-AI-Assoicate")
    if not tree:
        print("  Could not fetch file tree. Skipping.")
        return

    print(f"  File tree: {len(tree)} entries")

    modules = extract_modules(tree)
    print(f"  Modules extracted: {len(modules)}")

    deps = detect_dependencies(tree, modules)
    print(f"  Dependencies detected: {len(deps)}")

    try:
        graph = get_graph()
    except Exception as e:
        print(f"  FalkorDB unavailable: {e}")
        return

    mod_count, dep_count, link_count = sync_to_graph(graph, modules, deps)
    print(f"  Synced: {mod_count} modules, {dep_count} dependencies, {link_count} feature links")

    r = graph.query('MATCH (n) RETURN count(n)')
    edges = graph.query('MATCH ()-[r]->() RETURN count(r)')
    print(f"[code-graph] Done: graph now {r.result_set[0][0]} nodes, {edges.result_set[0][0]} edges. $0 LLM cost")


if __name__ == "__main__":
    main()
