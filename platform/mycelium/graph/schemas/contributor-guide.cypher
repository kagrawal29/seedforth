// @node_id: schema-contributor-guide
// @label: "ContributorGuide Schema"
// @kind: schema
// @description: Constraints and indexes for :ContributorGuide and :GuideSection nodes (graph-native contributor SoT — Track D wi-cg-01)
// ============================================================================
// wi-cg-01: :ContributorGuide + :GuideSection schema + constraints + indexes
//
// ContributorGuide is the single source of truth for teammate-facing contribution
// documentation. The guide contains ordered sections that each describe a specific
// contributor topic (setup, workflow, code style, testing, etc.). Sections can
// reference existing :WorkItem, :Invariant, :Protocol, or :QueryAtom nodes.
//
// Data model:
//   - :ContributorGuide {name, description, updated_ts}
//     └─[HAS_SECTION]─> :GuideSection {guide_name, slug, title, body_md, order, anchor, updated_ts}
//                         └─[REFERENCES]─> (:WorkItem | :Invariant | :Protocol | :QueryAtom)
//
// Projection:
//   - `maverick export-guide` (wi-cg-03) renders sections as CONTRIBUTING.md
//   - CI drift check (wi-cg-04) ensures md stays in sync with graph SoT
//   - `maverick-dev ingest-guide` (wi-cg-05) parses md edits back into graph
//
// Purpose:
//   - Teammate UX: `maverick ask "how do I contribute"` → guide sections from graph
//   - Maintainer ops: update guide sections once in graph, project to md + docs
//   - Contributor workflow: edit sections in graph via `maverick-dev edit-guide`,
//     export to md, commit, CI validates round-trip fidelity
//
// Properties:
//   - ContributorGuide.name: Unique guide name (typically "maverick" or a feature area)
//   - ContributorGuide.description: Human-readable guide purpose
//   - ContributorGuide.updated_ts: Last modification timestamp (DateTime)
//
//   - GuideSection.guide_name: Back-reference to parent guide (required for UNIQUE constraint)
//   - GuideSection.slug: URL-safe section slug (e.g., "setup-local", "cypher-style")
//   - GuideSection.title: Section heading text (e.g., "Local development setup")
//   - GuideSection.body_md: Full Markdown body of the section (may contain code blocks, refs)
//   - GuideSection.anchor: Stable anchor ID for doc linking (e.g., "#setup-local")
//   - GuideSection.order: Numeric sort order within the guide (1, 2, 3, ...)
//   - GuideSection.updated_ts: Last modification timestamp (DateTime)
// ============================================================================

// --- CONSTRAINT: Unique node_id on :ContributorGuide nodes ---
// One guide instance per name ensures there's a single authoritative guide
// (e.g., "maverick" is the main team guide, never duplicated).
// Idempotent upsert on (name) with MERGE.

CREATE CONSTRAINT guide_id_unique IF NOT EXISTS
  FOR (g:ContributorGuide) REQUIRE g.node_id IS UNIQUE;

// --- CONSTRAINT: Unique (guide_name, slug) composite on :GuideSection ---
// Sections within a guide are uniquely identified by their slug.
// A section cannot be duplicated within the same guide.
// Supports idempotent MERGE in exports + ingests.

CREATE CONSTRAINT guide_section_composite_unique IF NOT EXISTS
  FOR (s:GuideSection) REQUIRE (s.guide_name, s.slug) IS UNIQUE;

// --- CONSTRAINT: Unique anchor within a guide ---
// Anchors are used for linking from other docs / guide references.
// Like (guide_name, slug), anchors are scoped to the guide.

CREATE CONSTRAINT guide_section_anchor_unique IF NOT EXISTS
  FOR (s:GuideSection) REQUIRE (s.guide_name, s.anchor) IS UNIQUE;

// --- INDEX: GuideSection.order for sequential rendering ---
// Supports sorted queries like:
//   MATCH (g:ContributorGuide {name: 'maverick'})
//   -[:HAS_SECTION]->(s:GuideSection)
//   RETURN s ORDER BY s.order
// Essential for `maverick export-guide` to render sections in correct order.

CREATE INDEX guide_section_order_index IF NOT EXISTS
  FOR (s:GuideSection) ON (s.order);

// --- INDEX: GuideSection.updated_ts for staleness detection ---
// Supports queries like:
//   MATCH (s:GuideSection) WHERE s.updated_ts < datetime() - duration('P30D')
//   RETURN s
// Used by maintenance protocols to identify sections needing refresh.
// Also used by CI drift checks to timestamp exports.

CREATE INDEX guide_section_updated_ts_index IF NOT EXISTS
  FOR (s:GuideSection) ON (s.updated_ts);

// --- INDEX: GuideSection.guide_name for filtering by guide ---
// Supports queries that work with a specific guide:
//   MATCH (s:GuideSection {guide_name: 'maverick'})
//   RETURN s
// Useful when multiple guides exist (future multi-guide scenarios).

CREATE INDEX guide_section_guide_name_index IF NOT EXISTS
  FOR (s:GuideSection) ON (s.guide_name);

// --- INDEX: GuideSection.slug for anchor lookup ---
// Supports direct section retrieval by slug:
//   MATCH (s:GuideSection {guide_name: 'maverick', slug: 'setup-local'})
//   RETURN s.body_md
// Used by ingest-guide and doc-build workflows.

CREATE INDEX guide_section_slug_index IF NOT EXISTS
  FOR (s:GuideSection) ON (s.slug);

// ============================================================================
// RELATIONSHIP TYPES (no constraints needed; cardinality informational)
// ============================================================================
//
// HAS_SECTION:
//   Source: :ContributorGuide
//   Target: :GuideSection
//   Cardinality: One guide can have many sections (1:N)
//   Represents the ordered composition of sections within a guide.
//   Example: (guide:ContributorGuide {name:'maverick'})
//            -[:HAS_SECTION {order: 1}]->(section:GuideSection {slug: 'intro'})
//
// REFERENCES:
//   Source: :GuideSection
//   Target: :WorkItem | :Invariant | :Protocol | :QueryAtom | :Being | ... any node
//   Cardinality: A section can reference 0+ other nodes (N:M)
//   Represents conceptual or operational links (e.g., "See also invariant X").
//   May have properties like {type: 'see-also'} or {embed: true} for rendering hints.
//   Example: (section:GuideSection {slug: 'testing'})
//            -[:REFERENCES {type: 'embed'}]->(inv:Invariant {name: 'test-coverage'})
//
// ============================================================================

// --- Summary Report ---
RETURN
  'ContributorGuide schema + constraints + indexes loaded (wi-cg-01)' AS status;
