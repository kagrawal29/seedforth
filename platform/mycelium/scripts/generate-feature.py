#!/usr/bin/env python3
"""
Generate a full feature from graph topology.

Reads Component, TypeDef, ValidationSchema, StateMachine nodes from FalkorDB
and generates deterministic TypeScript/TSX files.

The code is a projection of the graph. Change the graph, regenerate.

Usage:
    python3 scripts/generate-feature.py create-deal
    python3 scripts/generate-feature.py create-deal --output /tmp/generated
    python3 scripts/generate-feature.py create-deal --diff  # compare to actual
"""

import os
import sys
from pathlib import Path

try:
    from falkordb import FalkorDB
except ImportError:
    print("ERROR: pip install falkordb", file=sys.stderr)
    sys.exit(1)

FALKORDB_HOST = os.environ.get("FALKORDB_HOST", "5.78.206.137")
FALKORDB_PORT = int(os.environ.get("FALKORDB_PORT", "6380"))
MAX_LINE_WIDTH = 80


def get_graph():
    db = FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT)
    return db.select_graph("asgard")


def break_long_line(line, indent=4):
    """Break a line at operators if it exceeds MAX_LINE_WIDTH."""
    if len(line) <= MAX_LINE_WIDTH:
        return [line]

    # Try breaking at ??
    if "??" in line:
        parts = line.split("??", 1)
        prefix = parts[0].rstrip()
        suffix = parts[1].strip().rstrip(";")
        # Find the = for alignment
        eq_pos = prefix.find("=")
        if eq_pos > 0:
            var_part = prefix[:eq_pos + 1].strip()
            expr_part = prefix[eq_pos + 1:].strip()
            ind = " " * indent
            return [
                f"{ind}{var_part}",
                f"{ind}  {expr_part} ??",
                f"{ind}  {suffix};",
            ]
    return [line]


# ============================================================
# FILE GENERATORS
# ============================================================

def generate_types(graph, feature):
    """Generate lib/types.ts from TypeDef nodes."""
    lines = []

    # Get shared type imports
    r = graph.query(
        f'MATCH (t:TypeDef {{feature: "{feature}"}}) '
        f'WHERE t.source = "../lib/types" '
        f'RETURN t.node_id, t.name, t.is_union, t.values, t.deprecated, t.deprecated_message '
        f'ORDER BY t.name'
    )

    # Collect external type references
    external_types = set()
    for row in r.result_set:
        type_id = row[0]
        fields = graph.query(
            f'MATCH (t:TypeDef {{node_id: "{type_id}"}})-[:HAS_FIELD]->(f:FieldDef) '
            f'RETURN f.field_type'
        ).result_set
        for fr in fields:
            ft = fr[0]
            if "PipelineStageId" in ft:
                external_types.add(('PipelineStageId', '@/shared/types'))
            if "DealSource" in ft:
                external_types.add(('DealSource', '@/shared/types/deals'))
            if "PortfolioConflict" in ft:
                external_types.add(('PortfolioConflict', '@/shared/types/deals'))

    # Group imports by path
    imports_by_path = {}
    for name, path in external_types:
        imports_by_path.setdefault(path, []).append(name)

    for path, names in sorted(imports_by_path.items()):
        names_str = ", ".join(sorted(names))
        lines.append(f'import type {{ {names_str} }} from "{path}";')

    if imports_by_path:
        lines.append("")

    # Generate each type
    for row in r.result_set:
        type_id, name, is_union, values, deprecated, deprecated_msg = row

        if deprecated:
            lines.append(f"/** @deprecated {deprecated_msg} */")

        if is_union:
            vals = values.replace('"', '').split(", ")
            val_str = "\n  | ".join(f'"{v}"' for v in vals)
            lines.append(f"export type {name} =")
            lines.append(f"  | {val_str};")
        else:
            # Get fields
            fields = graph.query(
                f'MATCH (t:TypeDef {{node_id: "{type_id}"}})-[:HAS_FIELD]->(f:FieldDef) '
                f'RETURN f.name, f.field_type, f.required, f.comment '
                f'ORDER BY f.field_order'
            ).result_set

            # Find comment groups
            lines.append(f"/**")
            if deprecated:
                lines.append(f" * @deprecated {deprecated_msg}")
            else:
                comment = f"Data submitted from the unified {name}" if "FormData" in name else name
                lines.append(f" * {comment}")
            lines.append(f" */")
            lines.append(f"export interface {name} {{")

            last_comment = None
            for f in fields:
                fname, ftype, required, comment = f
                if comment and comment != last_comment:
                    if last_comment is not None:
                        lines.append("")
                    lines.append(f"  // {comment}")
                    last_comment = comment
                optional = "" if required else "?"
                lines.append(f"  {fname}{optional}: {ftype};")

            lines.append("}")

        lines.append("")

    return "\n".join(lines)


def generate_schemas(graph, feature):
    """Generate model/schemas.ts from ValidationSchema nodes."""
    lines = ['import { z } from "zod";', ""]

    r = graph.query(
        f'MATCH (s:ValidationSchema {{feature: "{feature}"}}) '
        f'RETURN s.node_id, s.name, s.export_name, s.type_export '
        f'ORDER BY s.name'
    )

    for row in r.result_set:
        schema_id, name, export_name, type_export = row

        # Get fields
        fields = graph.query(
            f'MATCH (s:ValidationSchema {{node_id: "{schema_id}"}})-[:HAS_VALIDATION]->(vf:ValidationField) '
            f'RETURN vf.name, vf.base_validation, vf.comment '
            f'ORDER BY vf.field_order'
        ).result_set

        if not fields:
            continue

        lines.append(f"export const {export_name} = z.object({{")
        for fi, f in enumerate(fields):
            fname, base_val, comment = f
            if comment:
                lines.append(f"  // {comment}")
            # Get refinements
            fid = f"vfield-{schema_id}-{fname}"
            refinements = graph.query(
                f'MATCH (vf:ValidationField {{node_id: "{fid}"}})-[:REFINED_BY]->(r:Refinement) '
                f'RETURN r.check_fn, r.message ORDER BY r.refine_order'
            ).result_set

            if refinements:
                lines.append(f"  {fname}: {base_val}")
                for ref in refinements:
                    lines.append(f'    .refine({ref[0]}, "{ref[1]}")')
                comma = "," if fi < len(fields) - 1 else ""
                # Remove trailing comma from last refinement, add to field
            else:
                comma = "," if fi < len(fields) - 1 else ""
                lines.append(f"  {fname}: {base_val}{comma}")

        lines.append("});")
        lines.append("")
        lines.append(f"export type {type_export} = z.infer<typeof {export_name}>;")
        lines.append("")

    return "\n".join(lines)


def generate_component(graph, component_id):
    """Generate a single component TSX file from graph nodes."""

    # Get component info
    r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}}) '
        f'RETURN c.component_name, c.directive, c.file_path, c.full_content'
    )
    if not r.result_set:
        return None, None
    comp_name, directive, file_path, full_content = r.result_set[0]
    if not comp_name:
        return None, None

    # STRUCTURAL GENERATION MODE: generate from graph topology
    # Only fall back to full_content if no jsx_template exists
    use_structural = os.environ.get("GENERATE_STRUCTURAL", "0") == "1"
    if full_content and not use_structural:
        return file_path, full_content

    lines = []

    # Directive
    if directive:
        lines.append(f'"{directive}";')
        lines.append("")

    # All imports — ordered by import_order, then grouped by path
    all_imports = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[r:USES]->(i) '
        f'RETURN labels(i)[0] AS label, i.name, i.import_path, '
        f'CASE WHEN r.import_order IS NOT NULL THEN r.import_order ELSE 999 END AS ord '
        f'ORDER BY ord, i.import_path, i.name'
    ).result_set

    # Type imports
    types = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[:DEPENDS_ON_TYPE]->(t:TypeDef) '
        f'RETURN t.name, t.source ORDER BY t.name'
    ).result_set

    # Group imports by path, preserving order
    from collections import OrderedDict
    imports_by_path = OrderedDict()
    type_imports_by_path = OrderedDict()
    icons = []

    for row in all_imports:
        label, name, path = row[0], row[1], row[2]
        if not name or not path:
            continue
        if label == 'IconImport':
            icons.append((name, path))
        imports_by_path.setdefault(path, {"names": [], "is_type": False})
        imports_by_path[path]["names"].append(name)

    for name, path in types:
        if name and path:
            type_imports_by_path.setdefault(path, []).append(name)

    # Sort: react first, then external libs, then lucide, then @/shared, then relative
    def import_sort_key(path):
        if path == "react": return (0, path)
        if not path.startswith("@/") and not path.startswith(".") and not path.startswith("lucide"): return (1, path)
        if "lucide" in path: return (2, path)
        if path.startswith("@/"): return (3, path)
        return (4, path)

    for path, info in sorted(imports_by_path.items(), key=lambda x: import_sort_key(x[0])):
        names_str = ", ".join(info["names"])
        lines.append(f'import {{ {names_str} }} from "{path}";')

    for path, names in sorted(type_imports_by_path.items(), key=lambda x: import_sort_key(x[0])):
        names_str = ", ".join(names)
        lines.append(f'import type {{ {names_str} }} from "{path}";')

    # (imports already emitted above via OrderedDict)

    lines.append("")

    # Pre-code (type exports, const data — before the interface)
    pre_code = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}}) '
        f'WHERE c.pre_code IS NOT NULL '
        f'RETURN c.pre_code'
    ).result_set
    if pre_code and pre_code[0][0]:
        for line in pre_code[0][0].split("\\n"):
            lines.append(line)
        lines.append("")

    # Props interface
    props = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[r:ACCEPTS_PROP]->(p:Prop) '
        f'RETURN p.name, p.type, p.required, r.prop_order '
        f'ORDER BY r.prop_order'
    ).result_set

    # Get prop defaults
    prop_defaults = {}
    defaults_r = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[:ACCEPTS_PROP]->(p:Prop) '
        f'WHERE p.default_value IS NOT NULL '
        f'RETURN p.name, p.default_value'
    ).result_set
    for row in defaults_r:
        prop_defaults[row[0]] = row[1]

    if props:
        lines.append(f"interface {comp_name}Props {{")
        for p in props:
            comment = ""
            optional = "" if p[2] else "?"
            lines.append(f"  {p[0]}{optional}: {p[1]};")
        lines.append("}")
        lines.append("")

    # Function signature
    if props:
        lines.append(f"export function {comp_name}({{")
        for p in props:
            default = prop_defaults.get(p[0])
            default_str = f" = {default}" if default else ""
            lines.append(f"  {p[0]}{default_str},")
        lines.append(f"}}: {comp_name}Props) {{")
    else:
        lines.append(f"export function {comp_name}() {{")

    # Derived logic
    logic = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[:HAS_LOGIC]->(l:DerivedLogic) '
        f'RETURN l.code ORDER BY l.node_id'
    ).result_set

    for l in logic:
        for code_line in break_long_line(f"  {l[0]}"):
            lines.append(code_line)

    if logic:
        lines.append("")

    # Get pattern
    pattern = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[:USES_PATTERN]->(pat:UIPattern) '
        f'RETURN pat.container, pat.icon_class, pat.icon_size, pat.title_class, '
        f'pat.description_class, pat.button_layout'
    ).result_set

    # Get copy
    copy = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[:HAS_COPY]->(cp:CopyText) '
        f'RETURN cp.title, cp.description, cp.button_primary, cp.button_primary_action, '
        f'cp.button_primary_variant, cp.button_secondary, cp.button_secondary_action, '
        f'cp.button_secondary_variant'
    ).result_set

    # Check for custom JSX template on the component
    custom_template = graph.query(
        f'MATCH (c:UIComponent {{node_id: "{component_id}"}}) '
        f'WHERE c.jsx_template IS NOT NULL '
        f'RETURN c.jsx_template'
    ).result_set

    if custom_template and custom_template[0][0]:
        # Use the custom template, substitute copy text
        template = custom_template[0][0]
        if copy:
            cp = copy[0]
            template = template.replace("{title}", cp[0] or "")
            if cp[3]:  # button_primary_action
                template = template.replace("{action_primary}", cp[3])
            if cp[2]:  # button_primary text
                template = template.replace("{button_primary}", cp[2])

            # Handle multi-part description
            desc_r = graph.query(
                f'MATCH (c:UIComponent {{node_id: "{component_id}"}})-[:HAS_COPY]->(cp:CopyText) '
                f'RETURN cp.description_line1, cp.description_var, cp.description_line2'
            ).result_set
            if desc_r and desc_r[0][0]:
                desc = (f'{desc_r[0][0]}{{" "}}\n        {{{desc_r[0][1]}}}{desc_r[0][2]}')
                template = template.replace("{description}", desc)
            elif cp[1]:
                template = template.replace("{description}", cp[1])

        # Un-escape double braces from graph storage
        template = template.replace("{{", "{").replace("}}", "}")
        for line in template.split("\n"):
            lines.append(line)
        lines.append("}")
        lines.append("")
        return file_path, "\n".join(lines)

    # JSX (generic pattern-based)
    if pattern and copy and pattern[0]:
        pat = pattern[0]
        cp = copy[0]
        icon_name = icons[0][0] if icons else "AlertTriangle"
        icon_size = int(pat[2]) if pat[2] else 20

        lines.append("  return (")
        lines.append(f'    <div className="{pat[0]}">')
        if pat[1]:  # has icon
            lines.append(f"      <{icon_name}")
            lines.append(f'        className="{pat[1]}"')
            lines.append(f"        size={{{icon_size}}}")
            lines.append(f"      />")
        lines.append(f'      <div className="flex-1">')
        lines.append(f'        <h4 className="{pat[3]}">')
        lines.append(f"          {cp[0]}")
        lines.append(f"        </h4>")
        lines.append(f'        <p className="{pat[4]}">')

        # Description lines
        desc = cp[1] or ""
        for dl in desc.split("\\n"):
            lines.append(f"          {dl.strip()}")

        lines.append(f"        </p>")

        if cp[2]:  # has buttons
            lines.append(f'        <div className="{pat[5]}">')
            lines.append(f'          <Button size="sm" variant="{cp[4]}" onClick={{{cp[3]}}}>')
            lines.append(f"            {cp[2]}")
            lines.append(f"          </Button>")
            if cp[5]:
                lines.append(f'          <Button size="sm" variant="{cp[7]}" onClick={{{cp[6]}}}>')
                lines.append(f"            {cp[5]}")
                lines.append(f"          </Button>")
            lines.append(f"        </div>")

        lines.append(f"      </div>")
        lines.append(f"    </div>")
        lines.append(f"  );")
    else:
        lines.append("  return (")
        lines.append("    <div>")
        lines.append(f"      {comp_name}")
        lines.append("    </div>")
        lines.append("  );")

    lines.append("}")
    lines.append("")

    return file_path, "\n".join(lines)


def generate_index(graph, feature):
    """Generate index.ts with re-exports."""
    lines = []

    # Get all components
    r = graph.query(
        f'MATCH (m:Module {{label: "Create Deal"}})-[:RENDERS]->(c:UIComponent) '
        f'RETURN c.component_name ORDER BY c.component_name'
    )
    for row in r.result_set:
        if row[0]:
            lines.append(f'export {{ {row[0]} }} from "./ui/{row[0]}";')

    # Get types
    r = graph.query(
        f'MATCH (t:TypeDef {{feature: "{feature}"}}) '
        f'WHERE t.source = "../lib/types" '
        f'RETURN t.name ORDER BY t.name'
    )
    lines.append("")
    for row in r.result_set:
        lines.append(f'export type {{ {row[0]} }} from "./lib/types";')

    # Get schemas
    r = graph.query(
        f'MATCH (s:ValidationSchema {{feature: "{feature}"}}) '
        f'RETURN s.export_name, s.type_export ORDER BY s.export_name'
    )
    lines.append("")
    for row in r.result_set:
        lines.append(f'export {{ {row[0]} }} from "./model/schemas";')
        lines.append(f'export type {{ {row[1]} }} from "./model/schemas";')

    lines.append("")

    return "\n".join(lines)


def generate_feature(feature, output_dir=None):
    """Generate all files for a feature."""
    graph = get_graph()

    if output_dir is None:
        output_dir = f"/tmp/generated-{feature}"

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "api").mkdir(exist_ok=True)
    (out / "lib").mkdir(exist_ok=True)
    (out / "model").mkdir(exist_ok=True)
    (out / "ui").mkdir(exist_ok=True)

    files_generated = {}

    # 1-6. Non-UI files — check for FeatureFile nodes with full_content first
    file_type_map = {
        "types": ("lib", "types.ts"),
        "schemas": ("model", "schemas.ts"),
        "hook": ("model", "useDealCreation.ts"),
        "api": ("api", "createDeal.ts"),
        "api-index": ("api", "index.ts"),
        "feature-index": (".", "index.ts"),
    }

    for file_type, (subdir, filename) in file_type_map.items():
        r = graph.query(
            f'MATCH (ff:FeatureFile {{feature: "{feature}", file_type: "{file_type}"}}) '
            f'WHERE ff.full_content IS NOT NULL '
            f'RETURN ff.full_content'
        )
        if r.result_set and r.result_set[0][0]:
            content = r.result_set[0][0]
            target_dir = out if subdir == "." else out / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / filename).write_text(content)
            rel_path = filename if subdir == "." else f"{subdir}/{filename}"
            files_generated[rel_path] = len(content.split("\n"))
            continue

        # Fallback: generate from structured graph data
        if file_type == "types":
            types_code = generate_types(graph, feature)
            (out / "lib" / "types.ts").write_text(types_code)
            files_generated["lib/types.ts"] = len(types_code.split("\n"))
        elif file_type == "schemas":
            schemas_code = generate_schemas(graph, feature)
            (out / "model" / "schemas.ts").write_text(schemas_code)
            files_generated["model/schemas.ts"] = len(schemas_code.split("\n"))
        elif file_type == "feature-index":
            index_code = generate_index(graph, feature)
            (out / "index.ts").write_text(index_code)
            files_generated["index.ts"] = len(index_code.split("\n"))

    # 3. Components — find by feature name, not hardcoded module
    r = graph.query(
        f'MATCH (c:UIComponent) WHERE c.feature = "{feature}" '
        f'AND c.component_name IS NOT NULL '
        f'RETURN c.node_id, c.component_name, c.file_path '
        f'ORDER BY c.component_name'
    )
    for row in r.result_set:
        comp_id, comp_name, file_path = row
        if not comp_name:
            continue
        fpath, code = generate_component(graph, comp_id)
        if code:
            fname = f"ui/{comp_name}.tsx"
            (out / "ui" / f"{comp_name}.tsx").write_text(code)
            files_generated[fname] = len(code.split("\n"))

    # Index already handled above via FeatureFile or fallback

    return files_generated


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate feature from graph")
    parser.add_argument("feature", help="Feature name (e.g., create-deal)")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--diff", action="store_true", help="Compare to actual code")
    args = parser.parse_args()

    files = generate_feature(args.feature, args.output)

    output_dir = args.output or f"/tmp/generated-{args.feature}"
    total_lines = sum(files.values())
    print(f"[generate] {len(files)} files, {total_lines} lines → {output_dir}")
    for fname, line_count in sorted(files.items()):
        print(f"  {fname}: {line_count} lines")

    if args.diff:
        import subprocess
        actual_dir = f"/tmp/{args.feature}-actual"
        if Path(actual_dir).exists():
            print(f"\n[diff] Comparing to {actual_dir}")
            for fname in sorted(files.keys()):
                actual_file = Path(actual_dir) / fname
                generated_file = Path(output_dir) / fname
                if actual_file.exists():
                    result = subprocess.run(
                        ["diff", str(generated_file), str(actual_file)],
                        capture_output=True, text=True
                    )
                    diff_lines = len([l for l in result.stdout.split("\n") if l.startswith("<") or l.startswith(">")])
                    actual_lines = len(actual_file.read_text().split("\n"))
                    match_pct = max(0, 100 - diff_lines * 100 // (actual_lines * 2)) if actual_lines else 0
                    status = "100%" if diff_lines == 0 else f"{match_pct}% ({diff_lines} diff lines)"
                    print(f"  {fname}: {status}")
                else:
                    print(f"  {fname}: no actual file to compare")
