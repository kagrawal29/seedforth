#!/usr/bin/env python3
"""
Dream Visualizer -- Generate an HTML visualization highlighting dream analysis findings.

Colors nodes by community health, highlights fragile bridges in red,
marks orphan nodes, and shows top missing triangle proposals as dashed lines.
"""

import json
import html
from pathlib import Path

import networkx as nx

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
GRAPH_PATH = REPO_ROOT / "graphify-out" / "graph-v4.json"
OUTPUT_PATH = REPO_ROOT / "knowledge" / "meta" / "dream-visualization.html"

# Import analysis functions from dream-analysis
import sys
sys.path.insert(0, str(SCRIPT_DIR))
from importlib import import_module

# We import the probes directly
import importlib.util
spec = importlib.util.spec_from_file_location("dream_analysis", SCRIPT_DIR / "dream-analysis.py")
dream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dream)

# Community color palette (vis.js friendly)
COMMUNITY_COLORS = [
    "#4E79A7",  # 0 - steel blue
    "#F28E2B",  # 1 - orange
    "#E15759",  # 2 - red
    "#76B7B2",  # 3 - teal
    "#59A14F",  # 4 - green
    "#EDC948",  # 5 - yellow
    "#B07AA1",  # 6 - purple
    "#FF9DA7",  # 7 - pink
    "#9C755F",  # 8 - brown
    "#BAB0AC",  # None - gray
]

# Health -> border style
HEALTH_BORDER = {
    "HEALTHY": "#59A14F",
    "MODERATE": "#EDC948",
    "SPARSE": "#E15759",
    "ISOLATED": "#E15759",
    "INSULAR": "#B07AA1",
    "MINIMAL": "#BAB0AC",
}


def build_visualization():
    print("Loading graph...")
    G, raw_data, hyperedges = dream.load_graph(GRAPH_PATH)

    print("Running probes...")
    missing_tri = dream.probe_missing_triangles(G, top_n=10)
    bridges = dream.probe_fragile_bridges(G)
    orphans = dream.probe_orphans(G)
    comm_health = dream.probe_community_health(G)
    hub_dep = dream.probe_hub_dependency(G)

    # Build community health lookup
    health_map = {}
    for ch in comm_health:
        health_map[ch["community"]] = ch["health"]

    # Build orphan set
    orphan_set = {o["node"] for o in orphans}

    # Build hub set (critical/high)
    hub_set = {h["node"] for h in hub_dep if h["risk"] in ("CRITICAL", "HIGH")}

    # Build bridge edge set
    bridge_set = {(b["u"], b["v"]) for b in bridges}
    bridge_set |= {(b["v"], b["u"]) for b in bridges}

    # Build vis.js nodes
    vis_nodes = []
    for node_id in sorted(G.nodes()):
        nd = G.nodes[node_id]
        comm = nd.get("community")
        label = nd.get("label", node_id)
        degree = G.degree(node_id)

        comm_idx = comm if comm is not None else 9
        color = COMMUNITY_COLORS[min(comm_idx, len(COMMUNITY_COLORS) - 1)]

        health = health_map.get(comm, "MODERATE")
        border_color = HEALTH_BORDER.get(health, "#BAB0AC")

        # Size by degree
        size = 8 + degree * 2
        if node_id in hub_set:
            size = max(size, 25)

        # Shape: orphans get diamond, hubs get star
        shape = "dot"
        if node_id in orphan_set:
            shape = "diamond"
        elif node_id in hub_set:
            shape = "star"

        # Border width: thicker for hubs
        border_width = 1
        if node_id in hub_set:
            border_width = 3
        elif node_id in orphan_set:
            border_width = 2

        title_parts = [
            f"<b>{html.escape(label)}</b>",
            f"Community: {comm}",
            f"Degree: {degree}",
            f"Health: {health}",
        ]
        if node_id in hub_set:
            hub_info = next((h for h in hub_dep if h["node"] == node_id), None)
            if hub_info:
                title_parts.append(f"Betweenness: {hub_info['pct_shortest_paths']:.1f}%")
                title_parts.append(f"Risk: {hub_info['risk']}")
        if node_id in orphan_set:
            title_parts.append("STATUS: ORPHAN (degree <= 1)")

        vis_nodes.append({
            "id": node_id,
            "label": label[:30] + "..." if len(label) > 30 else label,
            "title": "<br>".join(title_parts),
            "size": size,
            "shape": shape,
            "color": {
                "background": color,
                "border": border_color,
                "highlight": {"background": "#ffffff", "border": border_color},
            },
            "borderWidth": border_width,
            "font": {"color": "#e0e0e0", "size": 10},
        })

    # Build vis.js edges
    vis_edges = []
    for u, v, data in G.edges(data=True):
        is_bridge = (u, v) in bridge_set
        edge = {
            "from": u,
            "to": v,
            "title": f"{data.get('relation', '')} ({data.get('confidence', '')})",
        }
        if is_bridge:
            edge["color"] = {"color": "#E15759", "highlight": "#ff0000"}
            edge["width"] = 3
            edge["dashes"] = False
            edge["label"] = "BRIDGE"
            edge["font"] = {"color": "#E15759", "size": 8, "strokeWidth": 0}
        else:
            edge["color"] = {"color": "#444466", "highlight": "#8888aa"}
            edge["width"] = 1

        vis_edges.append(edge)

    # Add missing triangle proposals as dashed green lines
    for t in missing_tri:
        vis_edges.append({
            "from": t["a"],
            "to": t["c"],
            "dashes": [5, 5],
            "color": {"color": "#59A14F", "highlight": "#88ff88"},
            "width": 2,
            "label": "PROPOSED",
            "font": {"color": "#59A14F", "size": 8, "strokeWidth": 0},
            "title": f"Proposed: close triangle via {dream.label(G, t['bridge'])}",
        })

    # Stats for sidebar
    stats = {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "bridges": len(bridges),
        "orphans": len(orphans),
        "critical_hubs": len([h for h in hub_dep if h["risk"] == "CRITICAL"]),
        "proposals": len(missing_tri),
        "communities": len([c for c in comm_health if c["community"] is not None]),
    }

    # Build legend data
    legend_items = []
    for ch in comm_health:
        comm = ch["community"]
        comm_idx = comm if comm is not None else 9
        color = COMMUNITY_COLORS[min(comm_idx, len(COMMUNITY_COLORS) - 1)]
        legend_items.append({
            "label": f"Community {comm}" if comm is not None else "Unassigned",
            "color": color,
            "size": ch["size"],
            "health": ch["health"],
        })

    html_content = generate_html(vis_nodes, vis_edges, stats, legend_items)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(html_content)
    print(f"Visualization written to {OUTPUT_PATH}")


def generate_html(nodes, edges, stats, legend_items):
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Dream Engine -- Graph Structural Analysis</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0f0f1a; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; display: flex; height: 100vh; overflow: hidden; }}
  #graph {{ flex: 1; }}
  #sidebar {{ width: 320px; background: #1a1a2e; border-left: 1px solid #2a2a4e; display: flex; flex-direction: column; overflow-y: auto; }}
  .section {{ padding: 14px; border-bottom: 1px solid #2a2a4e; }}
  .section h3 {{ font-size: 13px; color: #aaa; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat-row {{ display: flex; justify-content: space-between; padding: 3px 0; font-size: 13px; }}
  .stat-value {{ font-weight: bold; }}
  .stat-value.critical {{ color: #E15759; }}
  .stat-value.warning {{ color: #EDC948; }}
  .stat-value.good {{ color: #59A14F; }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; }}
  .legend-dot {{ width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }}
  .legend-label {{ flex: 1; }}
  .legend-health {{ font-size: 10px; padding: 1px 5px; border-radius: 3px; }}
  .legend-health.HEALTHY {{ background: #59A14F33; color: #59A14F; }}
  .legend-health.MODERATE {{ background: #EDC94833; color: #EDC948; }}
  .legend-health.SPARSE {{ background: #E1575933; color: #E15759; }}
  .legend-health.INSULAR {{ background: #B07AA133; color: #B07AA1; }}
  .legend-health.MINIMAL {{ background: #BAB0AC33; color: #BAB0AC; }}
  .legend-health.ISOLATED {{ background: #E1575933; color: #E15759; }}
  .key-item {{ display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 12px; }}
  .key-icon {{ width: 20px; text-align: center; flex-shrink: 0; }}
  .key-line {{ width: 24px; height: 0; border-top: 3px; flex-shrink: 0; }}
  #info-content {{ font-size: 13px; color: #ccc; line-height: 1.6; }}
  #info-content .empty {{ color: #555; font-style: italic; }}
</style>
</head>
<body>
<div id="graph"></div>
<div id="sidebar">
  <div class="section">
    <h3>Dream Engine -- Structural Analysis</h3>
    <div class="stat-row"><span>Nodes</span><span class="stat-value">{stats['nodes']}</span></div>
    <div class="stat-row"><span>Edges</span><span class="stat-value">{stats['edges']}</span></div>
    <div class="stat-row"><span>Communities</span><span class="stat-value">{stats['communities']}</span></div>
    <div class="stat-row"><span>Fragile bridges</span><span class="stat-value critical">{stats['bridges']}</span></div>
    <div class="stat-row"><span>Orphan nodes</span><span class="stat-value warning">{stats['orphans']}</span></div>
    <div class="stat-row"><span>Critical hubs</span><span class="stat-value critical">{stats['critical_hubs']}</span></div>
    <div class="stat-row"><span>Proposed edges</span><span class="stat-value good">{stats['proposals']}</span></div>
  </div>

  <div class="section">
    <h3>Visual Key</h3>
    <div class="key-item"><span class="key-icon" style="color:#E15759">&#9644;</span> Red edge = fragile bridge</div>
    <div class="key-item"><span class="key-icon" style="color:#59A14F">- -</span> Green dashed = proposed edge</div>
    <div class="key-item"><span class="key-icon">&#9670;</span> Diamond = orphan node</div>
    <div class="key-item"><span class="key-icon">&#9733;</span> Star = critical hub</div>
    <div class="key-item"><span class="key-icon">&#9679;</span> Circle = normal node</div>
  </div>

  <div class="section">
    <h3>Communities</h3>
    {''.join(f'''
    <div class="legend-item">
      <div class="legend-dot" style="background:{item['color']}"></div>
      <span class="legend-label">{item['label']} ({item['size']})</span>
      <span class="legend-health {item['health']}">{item['health']}</span>
    </div>''' for item in legend_items)}
  </div>

  <div class="section">
    <h3>Node Info</h3>
    <div id="info-content"><span class="empty">Click a node to inspect</span></div>
  </div>
</div>

<script>
const nodesData = {nodes_json};
const edgesData = {edges_json};

const container = document.getElementById('graph');
const data = {{
  nodes: new vis.DataSet(nodesData),
  edges: new vis.DataSet(edgesData)
}};

const options = {{
  physics: {{
    solver: 'forceAtlas2Based',
    forceAtlas2Based: {{
      gravitationalConstant: -40,
      centralGravity: 0.005,
      springLength: 120,
      springConstant: 0.04,
      damping: 0.4,
    }},
    stabilization: {{ iterations: 200 }},
  }},
  interaction: {{
    hover: true,
    tooltipDelay: 200,
    zoomView: true,
    dragView: true,
  }},
  edges: {{
    smooth: {{ type: 'continuous' }},
    font: {{ align: 'top' }},
  }},
  nodes: {{
    font: {{ multi: 'html' }},
  }},
}};

const network = new vis.Network(container, data, options);

network.on('click', function(params) {{
  const infoEl = document.getElementById('info-content');
  if (params.nodes.length > 0) {{
    const nodeId = params.nodes[0];
    const node = data.nodes.get(nodeId);
    if (node && node.title) {{
      infoEl.innerHTML = node.title;
    }}
  }} else {{
    infoEl.innerHTML = '<span class="empty">Click a node to inspect</span>';
  }}
}});
</script>
</body>
</html>"""


if __name__ == "__main__":
    build_visualization()
