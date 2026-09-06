"""
Mycelium Schema — Complete node, edge, and type definitions for the living knowledge graph.

This module defines the data model that sits on top of Graphiti/FalkorDB.
Graphiti provides: temporal tracking, bi-temporal edges, episode provenance,
community detection, vector search. Mycelium adds: domain-specific node types
(KnowledgeEntry, Person, DemandSignal, Intent, Convergence, Concept, Decision),
domain-specific edge types, the dual-truth sync model (markdown → graph), and
demand/supply gap analysis.

Architecture:
    Markdown files (knowledge/) are source of truth.
    FalkorDB graph is the queryable projection.
    Sync is write-behind: markdown changes → graph updates.
    If graph-sync fails, the pipeline continues unaffected.

Graphiti mapping:
    - Each knowledge entry becomes a Graphiti Episode (provenance) AND an EntityNode
    - Custom entity types (Pydantic models below) → Graphiti's entity_types parameter
    - Custom edge names → Graphiti's RELATES_TO edges with typed `name` field
    - Communities → Graphiti's built-in community detection (Leiden algorithm)
    - Temporal tracking → Graphiti's valid_at / invalid_at / expired_at on EntityEdge

Usage:
    from scripts.lib.mycelium_schema import (
        MYCELIUM_ENTITY_TYPES,
        MYCELIUM_EDGE_TYPES,
        MyceliumSyncState,
    )
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =============================================================================
# NODE TYPES — Graphiti custom entity types
# =============================================================================
# These are passed as entity_types=MYCELIUM_ENTITY_TYPES to graphiti.add_episode()
# Graphiti stores them as EntityNode.labels + EntityNode.attributes


class KnowledgeEntry(BaseModel):
    """A curated knowledge entry from the markdown knowledge base.

    This is the primary node type. Each .md file in knowledge/ maps to one of these.
    The markdown file is source of truth; this node is the graph projection.
    """

    entry_id: str = Field(description="Frontmatter id, e.g. 'architecture-tech-stack-completed'")
    category: str | None = Field(
        default=None,
        description="Entry category: patterns, anti-patterns, architecture, workflows, tool-configs",
    )
    entry_type: str | None = Field(
        default=None,
        description="Entry type: knowledge, procedure, exploration",
    )
    confidence: str | None = Field(
        default=None,
        description="Confidence level: low, medium, high",
    )
    source_file: str | None = Field(
        default=None,
        description="Relative path to the markdown file, e.g. 'knowledge/patterns/foo.md'",
    )
    discovered_at: str | None = Field(
        default=None,
        description="ISO date when the entry was first discovered",
    )
    last_validated_at: str | None = Field(
        default=None,
        description="ISO date of last validation",
    )
    tags: list[str] = Field(default_factory=list, description="Searchable tags from frontmatter")
    relevant_when: str | None = Field(
        default=None,
        description="Situations when this entry is useful (from frontmatter)",
    )
    content_hash: str | None = Field(
        default=None,
        description="SHA-256 of the markdown file content, for change detection",
    )
    # Effectiveness metrics (from frontmatter)
    effectiveness_score: float = Field(
        default=0.0,
        description="(cited - correction) / max(surfaced, 1). Range -1 to +1.",
    )
    surfaced_count: int = Field(default=0, description="Times this entry was surfaced in sessions")
    cited_count: int = Field(default=0, description="Times explicitly cited")


class Person(BaseModel):
    """A team member who interacts with the knowledge base.

    Tracks structural coupling: which knowledge nodes each person has engaged with,
    when, and how deeply. This powers personalized relevance and demand detection.
    """

    person_name: str = Field(description="Display name, e.g. 'Abhishek', 'Sahiram'")
    langsmith_project_uuid: str | None = Field(
        default=None,
        description="LangSmith project UUID for trace monitoring",
    )
    role: str | None = Field(default=None, description="Team role if known")
    active_workstreams: list[str] = Field(
        default_factory=list,
        description="Current workstream names this person is on",
    )


class DemandSignal(BaseModel):
    """A detected information need — a question someone asked or a gap discovered.

    Demand signals come from LangSmith traces (questions asked), manual reports,
    or gap analysis (knowledge area with no coverage). Each DemandSignal may have
    one or more Intent nodes beneath it.
    """

    original_question: str = Field(description="The raw question or need as detected")
    source_type: str | None = Field(
        default=None,
        description="Where this demand was detected: trace, report, gap_analysis",
    )
    source_person: str | None = Field(
        default=None,
        description="Person who asked/triggered this demand",
    )
    detected_at: str | None = Field(
        default=None,
        description="ISO datetime when the demand was detected",
    )
    satisfaction_status: str = Field(
        default="unmet",
        description="Status: met, partially_met, unmet",
    )
    satisfaction_score: float = Field(
        default=0.0,
        description="0.0 (unmet) to 1.0 (fully met). Based on matching knowledge coverage.",
    )


class Intent(BaseModel):
    """The question beneath the question — the underlying information need.

    Multiple DemandSignals may share the same Intent. When 3+ Intents converge
    across different people, that triggers a Convergence event.
    """

    intent_description: str = Field(description="The underlying need, abstracted from raw question")
    domain: str | None = Field(
        default=None,
        description="Knowledge domain: architecture, patterns, workflows, tooling, security, etc.",
    )
    recurrence_count: int = Field(
        default=1,
        description="How many times this intent has been observed across different demands",
    )
    first_seen_at: str | None = Field(default=None, description="ISO datetime")
    last_seen_at: str | None = Field(default=None, description="ISO datetime")


class Convergence(BaseModel):
    """A convergence event — when 3+ intents from different people align.

    This is the highest-signal indicator that the knowledge base has a gap
    that multiple people are hitting independently. Convergence events
    should trigger knowledge creation or escalation.
    """

    convergence_label: str = Field(description="Human-readable label for this convergence")
    intent_count: int = Field(default=0, description="Number of contributing intents")
    person_count: int = Field(default=0, description="Number of distinct people involved")
    detected_at: str | None = Field(default=None, description="ISO datetime of detection")
    resolved: bool = Field(default=False, description="Whether knowledge was created to address this")
    resolution_entry_id: str | None = Field(
        default=None,
        description="ID of the knowledge entry created to resolve this, if any",
    )


class Concept(BaseModel):
    """An abstract concept, technology, or domain term extracted from knowledge entries.

    Concepts are the connective tissue — they link knowledge entries that discuss
    the same underlying idea even if they don't reference each other directly.
    """

    concept_type: str | None = Field(
        default=None,
        description="Type: technology, methodology, principle, domain_term",
    )
    definition: str | None = Field(
        default=None,
        description="Brief definition if available",
    )


class Phase(BaseModel):
    """A macro-level phase transition — when the team's collective demand shifts character.

    Phases are detected when convergence events cluster in the same direction.
    Example: team shifts from "exploration" (scattered what-should-we-use questions)
    to "specification" (concentrated how-does-X-connect-to-Y questions).

    Phase nodes connect to Convergence nodes via CONSTITUTED_BY edges.
    The full chain: Phase ← Convergence ← Intent ← Demand → Knowledge.
    """

    phase_label: str = Field(description="Human-readable phase name, e.g. 'spec-writing'")
    phase_type: str = Field(
        default="detected",
        description="How this was identified: detected (automatic), declared (manual)",
    )
    demand_character: str | None = Field(
        default=None,
        description="Nature of demand in this phase: exploration, specification, implementation, debugging",
    )
    detected_at: str | None = Field(default=None, description="ISO datetime when phase was detected")
    active: bool = Field(default=True, description="Whether this phase is currently active")
    convergence_count: int = Field(default=0, description="Number of convergence events constituting this phase")
    person_count: int = Field(default=0, description="Number of people whose intents align with this phase")
    strength: float = Field(default=0.0, description="Aggregate convergence strength")


class Decision(BaseModel):
    """An explicit architectural or process decision.

    Decisions are extracted from knowledge entries of type 'knowledge' with
    high confidence. They represent settled choices that should not be re-explored.
    """

    decision_status: str = Field(
        default="decided",
        description="Status: decided, open, deprecated",
    )
    decided_at: str | None = Field(default=None, description="ISO date when decided")
    rationale: str | None = Field(default=None, description="Why this was decided")
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Other options that were evaluated",
    )


# Map of label name → Pydantic model, passed to Graphiti's entity_types parameter
MYCELIUM_ENTITY_TYPES: dict[str, type[BaseModel]] = {
    "KnowledgeEntry": KnowledgeEntry,
    "Person": Person,
    "DemandSignal": DemandSignal,
    "Intent": Intent,
    "Convergence": Convergence,
    "Phase": Phase,
    "Concept": Concept,
    "Decision": Decision,
}


# =============================================================================
# EDGE TYPES — Named relationships for Graphiti's EntityEdge.name field
# =============================================================================
# Graphiti stores all entity relationships as RELATES_TO in FalkorDB.
# The edge *name* field differentiates types. We define them here as an enum
# and provide metadata for each.


class EdgeType(str, Enum):
    """All relationship types in the Mycelium graph.

    Split into two confidence classes:
    - EXTRACTED: directly derived from markdown content (verified)
    - INFERRED: derived from dream rounds, trace analysis, or LLM inference (needs verification)
    """

    # --- Knowledge structure edges (EXTRACTED confidence) ---
    CONTAINS_CONCEPT = "CONTAINS_CONCEPT"  # KnowledgeEntry → Concept
    RELATES_TO_ENTRY = "RELATES_TO_ENTRY"  # KnowledgeEntry → KnowledgeEntry (from 'related' field)
    HAS_DECISION = "HAS_DECISION"  # KnowledgeEntry → Decision
    SUPERSEDES = "SUPERSEDES"  # KnowledgeEntry → KnowledgeEntry (newer replaces older)

    # --- Demand/supply edges ---
    ANSWERED_BY = "ANSWERED_BY"  # DemandSignal → KnowledgeEntry (fully met)
    PARTIALLY_ANSWERED_BY = "PARTIALLY_ANSWERED_BY"  # DemandSignal → KnowledgeEntry
    UNANSWERED_NEAR = "UNANSWERED_NEAR"  # DemandSignal → KnowledgeEntry (near but no match)
    HAS_INTENT = "HAS_INTENT"  # DemandSignal → Intent
    CONVERGES_TO = "CONVERGES_TO"  # Intent → Convergence

    # --- Person/structural coupling edges ---
    AUTHORED = "AUTHORED"  # Person → KnowledgeEntry
    ASKED = "ASKED"  # Person → DemandSignal
    STRUCTURALLY_COUPLED = "STRUCTURALLY_COUPLED"  # Person → KnowledgeEntry/Concept (engagement)
    SAME_PERSON_PATTERN = "SAME_PERSON_PATTERN"  # DemandSignal → DemandSignal (same person)
    CROSS_PERSON_DEMAND = "CROSS_PERSON_DEMAND"  # DemandSignal → DemandSignal (different people)

    # --- Community/cluster edges (managed by Graphiti's built-in community detection) ---
    # HAS_MEMBER is built-in to Graphiti — we don't define it here

    # --- Phase edges ---
    CONSTITUTED_BY = "CONSTITUTED_BY"  # Phase → Convergence (convergence events that form this phase)
    EXPRESSES = "EXPRESSES"  # Intent → DemandSignal (intent surfaces from this demand)

    # --- Inference edges (INFERRED confidence, need verification) ---
    INFERRED_RELATION = "INFERRED_RELATION"  # Any → Any (LLM-detected but unverified)


class EdgeConfig(BaseModel):
    """Metadata for each edge type — used by sync and query logic."""

    edge_type: EdgeType
    source_labels: list[str]
    target_labels: list[str]
    confidence_class: str = Field(description="EXTRACTED or INFERRED")
    weight_default: float = Field(default=1.0, description="Default edge weight 0.0-1.0")
    decay_days: int | None = Field(
        default=None,
        description="Days after which this edge loses confidence if not revalidated. None = no decay.",
    )
    description: str = ""


EDGE_CONFIGS: dict[EdgeType, EdgeConfig] = {
    EdgeType.CONTAINS_CONCEPT: EdgeConfig(
        edge_type=EdgeType.CONTAINS_CONCEPT,
        source_labels=["KnowledgeEntry"],
        target_labels=["Concept"],
        confidence_class="EXTRACTED",
        description="Knowledge entry discusses or defines this concept",
    ),
    EdgeType.RELATES_TO_ENTRY: EdgeConfig(
        edge_type=EdgeType.RELATES_TO_ENTRY,
        source_labels=["KnowledgeEntry"],
        target_labels=["KnowledgeEntry"],
        confidence_class="EXTRACTED",
        description="Explicit cross-reference from frontmatter 'related' field",
    ),
    EdgeType.HAS_DECISION: EdgeConfig(
        edge_type=EdgeType.HAS_DECISION,
        source_labels=["KnowledgeEntry"],
        target_labels=["Decision"],
        confidence_class="EXTRACTED",
        description="Knowledge entry contains a settled decision",
    ),
    EdgeType.SUPERSEDES: EdgeConfig(
        edge_type=EdgeType.SUPERSEDES,
        source_labels=["KnowledgeEntry"],
        target_labels=["KnowledgeEntry"],
        confidence_class="EXTRACTED",
        weight_default=1.0,
        description="Newer entry replaces older one (temporal invalidation)",
    ),
    EdgeType.ANSWERED_BY: EdgeConfig(
        edge_type=EdgeType.ANSWERED_BY,
        source_labels=["DemandSignal"],
        target_labels=["KnowledgeEntry"],
        confidence_class="EXTRACTED",
        description="Demand fully satisfied by this knowledge entry",
    ),
    EdgeType.PARTIALLY_ANSWERED_BY: EdgeConfig(
        edge_type=EdgeType.PARTIALLY_ANSWERED_BY,
        source_labels=["DemandSignal"],
        target_labels=["KnowledgeEntry"],
        confidence_class="INFERRED",
        weight_default=0.5,
        description="Demand partially covered — entry addresses part of the need",
    ),
    EdgeType.UNANSWERED_NEAR: EdgeConfig(
        edge_type=EdgeType.UNANSWERED_NEAR,
        source_labels=["DemandSignal"],
        target_labels=["KnowledgeEntry"],
        confidence_class="INFERRED",
        weight_default=0.3,
        description="Demand is semantically near this entry but not addressed by it",
    ),
    EdgeType.HAS_INTENT: EdgeConfig(
        edge_type=EdgeType.HAS_INTENT,
        source_labels=["DemandSignal"],
        target_labels=["Intent"],
        confidence_class="INFERRED",
        description="Demand signal maps to this underlying intent",
    ),
    EdgeType.CONVERGES_TO: EdgeConfig(
        edge_type=EdgeType.CONVERGES_TO,
        source_labels=["Intent"],
        target_labels=["Convergence"],
        confidence_class="INFERRED",
        description="Intent contributes to a convergence event (3+ intents aligning)",
    ),
    EdgeType.AUTHORED: EdgeConfig(
        edge_type=EdgeType.AUTHORED,
        source_labels=["Person"],
        target_labels=["KnowledgeEntry"],
        confidence_class="EXTRACTED",
        description="Person authored or contributed this knowledge entry",
    ),
    EdgeType.ASKED: EdgeConfig(
        edge_type=EdgeType.ASKED,
        source_labels=["Person"],
        target_labels=["DemandSignal"],
        confidence_class="EXTRACTED",
        description="Person asked the question / triggered the demand",
    ),
    EdgeType.STRUCTURALLY_COUPLED: EdgeConfig(
        edge_type=EdgeType.STRUCTURALLY_COUPLED,
        source_labels=["Person"],
        target_labels=["KnowledgeEntry", "Concept"],
        confidence_class="INFERRED",
        weight_default=0.5,
        decay_days=14,
        description="Person has engaged with this node (queried, cited, or worked on related code)",
    ),
    EdgeType.SAME_PERSON_PATTERN: EdgeConfig(
        edge_type=EdgeType.SAME_PERSON_PATTERN,
        source_labels=["DemandSignal"],
        target_labels=["DemandSignal"],
        confidence_class="INFERRED",
        weight_default=0.6,
        description="Same person asked both — clustering signal",
    ),
    EdgeType.CROSS_PERSON_DEMAND: EdgeConfig(
        edge_type=EdgeType.CROSS_PERSON_DEMAND,
        source_labels=["DemandSignal"],
        target_labels=["DemandSignal"],
        confidence_class="INFERRED",
        weight_default=0.8,
        description="Different people hit the same need — convergence signal",
    ),
    EdgeType.CONSTITUTED_BY: EdgeConfig(
        edge_type=EdgeType.CONSTITUTED_BY,
        source_labels=["Phase"],
        target_labels=["Convergence"],
        confidence_class="INFERRED",
        description="Convergence event is part of this phase transition",
    ),
    EdgeType.EXPRESSES: EdgeConfig(
        edge_type=EdgeType.EXPRESSES,
        source_labels=["Intent"],
        target_labels=["DemandSignal"],
        confidence_class="INFERRED",
        description="Intent was extracted from this demand signal",
    ),
    EdgeType.INFERRED_RELATION: EdgeConfig(
        edge_type=EdgeType.INFERRED_RELATION,
        source_labels=["KnowledgeEntry", "Concept", "Decision"],
        target_labels=["KnowledgeEntry", "Concept", "Decision"],
        confidence_class="INFERRED",
        weight_default=0.4,
        decay_days=14,
        description="LLM-inferred relationship, needs verification via trace evidence",
    ),
}


# =============================================================================
# SYNC STATE — Tracking what's been synced between markdown and graph
# =============================================================================


class SyncStatus(str, Enum):
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    ERROR = "error"
    DELETED = "deleted"  # markdown file removed, graph node needs cleanup


class SyncRecord(BaseModel):
    """Tracks sync state for a single knowledge entry."""

    entry_id: str
    source_file: str
    content_hash: str = Field(description="SHA-256 of markdown file content")
    graph_node_uuid: str | None = Field(default=None, description="UUID in FalkorDB")
    graph_episode_uuid: str | None = Field(default=None, description="Graphiti episode UUID")
    status: SyncStatus = SyncStatus.PENDING
    last_synced_at: str | None = Field(default=None, description="ISO datetime of last successful sync")
    last_error: str | None = Field(default=None, description="Error message if status is ERROR")
    sync_attempts: int = Field(default=0, description="Number of sync attempts since last success")


class MyceliumSyncState(BaseModel):
    """Full sync state for the dual-truth model.

    Persisted to .mycelium/sync-state.json at repo root.
    Read before every sync cycle, written after.
    """

    last_full_sync: str | None = Field(default=None, description="ISO datetime of last full sync")
    last_incremental_sync: str | None = Field(default=None, description="ISO datetime of last delta sync")
    entries: dict[str, SyncRecord] = Field(
        default_factory=dict,
        description="Map of entry_id → SyncRecord",
    )
    graph_node_count: int = Field(default=0, description="Last known node count in graph")
    graph_edge_count: int = Field(default=0, description="Last known edge count in graph")

    def needs_sync(self, entry_id: str, current_hash: str) -> bool:
        """Check if an entry needs re-syncing based on content hash."""
        record = self.entries.get(entry_id)
        if not record:
            return True
        if record.status in (SyncStatus.PENDING, SyncStatus.ERROR):
            return True
        return record.content_hash != current_hash

    def mark_synced(self, entry_id: str, source_file: str, content_hash: str,
                    node_uuid: str, episode_uuid: str) -> None:
        """Mark an entry as successfully synced."""
        now = datetime.now(timezone.utc).isoformat()
        self.entries[entry_id] = SyncRecord(
            entry_id=entry_id,
            source_file=source_file,
            content_hash=content_hash,
            graph_node_uuid=node_uuid,
            graph_episode_uuid=episode_uuid,
            status=SyncStatus.SYNCED,
            last_synced_at=now,
            sync_attempts=0,
        )

    def mark_error(self, entry_id: str, source_file: str, content_hash: str, error: str) -> None:
        """Mark an entry as failed to sync."""
        existing = self.entries.get(entry_id)
        attempts = (existing.sync_attempts + 1) if existing else 1
        self.entries[entry_id] = SyncRecord(
            entry_id=entry_id,
            source_file=source_file,
            content_hash=content_hash,
            status=SyncStatus.ERROR,
            last_error=error,
            sync_attempts=attempts,
            graph_node_uuid=existing.graph_node_uuid if existing else None,
            graph_episode_uuid=existing.graph_episode_uuid if existing else None,
        )

    def detect_deletions(self, current_entry_ids: set[str]) -> list[str]:
        """Find entries in sync state that no longer exist in markdown."""
        deleted = []
        for entry_id, record in self.entries.items():
            if entry_id not in current_entry_ids and record.status != SyncStatus.DELETED:
                deleted.append(entry_id)
        return deleted


# =============================================================================
# HELPER: Content hash for change detection
# =============================================================================


def compute_content_hash(content: str) -> str:
    """SHA-256 hash of file content for change detection in dual-truth sync."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# =============================================================================
# CYPHER QUERY TEMPLATES — FalkorDB queries for the 10 core operations
# =============================================================================
# These use FalkorDB's Cypher dialect (compatible with openCypher).
# Parameterized with $variables for safe query execution.

CYPHER_QUERIES = {
    # -------------------------------------------------------------------------
    # 1. Person-relevance: Given person X, find most relevant knowledge nodes
    # -------------------------------------------------------------------------
    # Walks structural coupling edges, weighs by recency and engagement depth.
    # Falls back to community co-membership if no direct coupling exists.
    "person_relevant_knowledge": """
        MATCH (p:Entity:Person {name: $person_name})
        OPTIONAL MATCH (p)-[sc:RELATES_TO]->(k:Entity:KnowledgeEntry)
            WHERE sc.name = 'STRUCTURALLY_COUPLED'
        OPTIONAL MATCH (p)-[:RELATES_TO {name: 'AUTHORED'}]->(authored:Entity:KnowledgeEntry)
        WITH p, collect(DISTINCT k) + collect(DISTINCT authored) AS direct_nodes
        UNWIND direct_nodes AS node
        RETURN DISTINCT node.name AS name,
               node.uuid AS uuid,
               node.summary AS summary,
               node.attributes AS attributes
        ORDER BY node.created_at DESC
        LIMIT $limit
    """,

    # -------------------------------------------------------------------------
    # 2. Demand-supply gap: What demands are unmet or partially met?
    # -------------------------------------------------------------------------
    "unmet_demands": """
        MATCH (d:Entity:DemandSignal)
        WHERE NOT EXISTS {
            MATCH (d)-[:RELATES_TO {name: 'ANSWERED_BY'}]->(:Entity:KnowledgeEntry)
        }
        OPTIONAL MATCH (d)-[r:RELATES_TO {name: 'PARTIALLY_ANSWERED_BY'}]->(k:Entity:KnowledgeEntry)
        OPTIONAL MATCH (d)<-[:RELATES_TO {name: 'ASKED'}]-(p:Entity:Person)
        RETURN d.name AS demand,
               d.uuid AS demand_uuid,
               d.attributes AS demand_attrs,
               collect(DISTINCT k.name) AS partial_matches,
               collect(DISTINCT p.name) AS askers
        ORDER BY d.created_at DESC
        LIMIT $limit
    """,

    # -------------------------------------------------------------------------
    # 3. Convergence detection: Intents shared across 3+ people
    # -------------------------------------------------------------------------
    "convergence_candidates": """
        MATCH (d:Entity:DemandSignal)-[:RELATES_TO {name: 'HAS_INTENT'}]->(i:Entity:Intent)
        MATCH (p:Entity:Person)-[:RELATES_TO {name: 'ASKED'}]->(d)
        WITH i, collect(DISTINCT p.name) AS people, count(DISTINCT d) AS demand_count
        WHERE size(people) >= $min_people
        RETURN i.name AS intent,
               i.uuid AS intent_uuid,
               people,
               demand_count
        ORDER BY demand_count DESC
        LIMIT $limit
    """,

    # -------------------------------------------------------------------------
    # 4. Stale inferred edges: Edges that are INFERRED and older than N days
    # -------------------------------------------------------------------------
    "stale_inferred_edges": """
        MATCH (s:Entity)-[r:RELATES_TO]->(t:Entity)
        WHERE r.name IN ['INFERRED_RELATION', 'STRUCTURALLY_COUPLED',
                         'PARTIALLY_ANSWERED_BY', 'UNANSWERED_NEAR',
                         'HAS_INTENT', 'CONVERGES_TO',
                         'SAME_PERSON_PATTERN', 'CROSS_PERSON_DEMAND']
          AND r.created_at < datetime($cutoff_iso)
          AND r.expired_at IS NULL
        RETURN s.name AS source,
               t.name AS target,
               r.name AS edge_type,
               r.uuid AS edge_uuid,
               r.fact AS fact,
               r.created_at AS created_at
        ORDER BY r.created_at ASC
        LIMIT $limit
    """,

    # -------------------------------------------------------------------------
    # 5. Community overview: All communities with member counts
    # -------------------------------------------------------------------------
    "community_overview": """
        MATCH (c:Community)-[:HAS_MEMBER]->(n:Entity)
        RETURN c.name AS community_name,
               c.uuid AS community_uuid,
               c.summary AS summary,
               count(n) AS member_count,
               collect(n.name)[0..5] AS sample_members
        ORDER BY member_count DESC
    """,

    # -------------------------------------------------------------------------
    # 6. Knowledge entry neighbors: All nodes connected to a specific entry
    # -------------------------------------------------------------------------
    "entry_neighborhood": """
        MATCH (k:Entity {uuid: $entry_uuid})
        OPTIONAL MATCH (k)-[r:RELATES_TO]-(neighbor:Entity)
        RETURN k.name AS entry_name,
               neighbor.name AS neighbor_name,
               neighbor.uuid AS neighbor_uuid,
               labels(neighbor) AS neighbor_labels,
               r.name AS edge_type,
               r.fact AS fact,
               type(r) AS rel_type
        LIMIT $limit
    """,

    # -------------------------------------------------------------------------
    # 7. Person activity: What has a person authored, asked, and coupled to?
    # -------------------------------------------------------------------------
    "person_activity": """
        MATCH (p:Entity:Person {name: $person_name})
        OPTIONAL MATCH (p)-[:RELATES_TO {name: 'AUTHORED'}]->(authored:Entity)
        OPTIONAL MATCH (p)-[:RELATES_TO {name: 'ASKED'}]->(asked:Entity)
        OPTIONAL MATCH (p)-[:RELATES_TO {name: 'STRUCTURALLY_COUPLED'}]->(coupled:Entity)
        RETURN p.name AS person,
               collect(DISTINCT authored.name) AS authored,
               collect(DISTINCT asked.name) AS demands,
               collect(DISTINCT coupled.name) AS coupled_to
    """,

    # -------------------------------------------------------------------------
    # 8. Decision map: All settled decisions with their knowledge entries
    # -------------------------------------------------------------------------
    "decision_map": """
        MATCH (k:Entity:KnowledgeEntry)-[:RELATES_TO {name: 'HAS_DECISION'}]->(d:Entity:Decision)
        RETURN d.name AS decision,
               d.uuid AS decision_uuid,
               d.attributes AS decision_attrs,
               k.name AS source_entry,
               k.uuid AS entry_uuid
        ORDER BY d.created_at DESC
        LIMIT $limit
    """,

    # -------------------------------------------------------------------------
    # 9. Cross-person demand clusters: Demands linked across different people
    # -------------------------------------------------------------------------
    "cross_person_clusters": """
        MATCH (d1:Entity:DemandSignal)-[:RELATES_TO {name: 'CROSS_PERSON_DEMAND'}]->(d2:Entity:DemandSignal)
        MATCH (p1:Entity:Person)-[:RELATES_TO {name: 'ASKED'}]->(d1)
        MATCH (p2:Entity:Person)-[:RELATES_TO {name: 'ASKED'}]->(d2)
        WHERE p1.name <> p2.name
        RETURN d1.name AS demand_1,
               p1.name AS person_1,
               d2.name AS demand_2,
               p2.name AS person_2,
               d1.uuid AS d1_uuid,
               d2.uuid AS d2_uuid
        LIMIT $limit
    """,

    # -------------------------------------------------------------------------
    # 10. Sync verification: Entries in graph vs expected (by source_description)
    # -------------------------------------------------------------------------
    "synced_entries": """
        MATCH (e:Episodic)
        WHERE e.source_description STARTS WITH 'knowledge-entry:'
        RETURN e.source_description AS source,
               e.uuid AS episode_uuid,
               e.created_at AS synced_at,
               e.name AS name
        ORDER BY e.created_at DESC
    """,
}


# =============================================================================
# SYNC ALGORITHM — Pseudocode for the dual-truth reconciliation
# =============================================================================
#
# The sync runs in two modes:
#
# FULL SYNC (on first run or manual trigger):
#   1. Walk knowledge/**/*.md, parse frontmatter + body for each
#   2. Compute content_hash for each file
#   3. For each entry:
#      a. If not in sync state → add_episode with entity_types=MYCELIUM_ENTITY_TYPES
#      b. If in sync state but hash differs → re-add episode (Graphiti handles dedup/update)
#      c. If in sync state and hash matches → skip
#   4. After all episodes added:
#      a. Extract explicit edges from frontmatter 'related' field → add_triplet for each
#      b. Extract author edges from frontmatter 'source' field → add_triplet
#   5. Run graphiti.build_communities() to detect/update clusters
#   6. Detect deletions: entries in sync state but not in filesystem → mark DELETED
#   7. Persist sync state to .mycelium/sync-state.json
#
# INCREMENTAL SYNC (on each pipeline cycle):
#   1. Read sync state from .mycelium/sync-state.json
#   2. Walk knowledge/**/*.md, compute hashes
#   3. Only process entries where needs_sync() returns True
#   4. For changed entries: re-add episode (Graphiti's dedup handles it)
#   5. For new entries: add_episode
#   6. For deleted entries: mark in sync state (graph nodes remain for provenance)
#   7. Optionally rebuild communities if >5 entries changed
#   8. Persist updated sync state
#
# CONFLICT RESOLUTION:
#   - Markdown always wins (it's source of truth)
#   - If graph has data not in markdown (e.g., inferred edges), graph data is preserved
#   - If markdown contradicts graph, markdown overwrites via Graphiti's temporal invalidation
#   - Deleted markdown files: graph nodes are NOT deleted (provenance), but marked expired
#   - The sync state file tracks all of this for auditability
#
# FAILURE HANDLING:
#   - If sync fails for an entry, mark it ERROR in sync state with error message
#   - Retry up to 3 times on next cycle
#   - After 3 failures, log and skip (human review needed)
#   - Pipeline continues regardless — graph sync is non-blocking


# =============================================================================
# COMMUNITY DETECTION STRATEGY
# =============================================================================
#
# Graphiti uses the Leiden algorithm for community detection internally.
# We layer Mycelium-specific behavior on top:
#
# 1. INITIAL CLUSTERING: After full sync, call graphiti.build_communities()
#    - Graphiti clusters EntityNodes based on edge connectivity
#    - Creates CommunityNode with summary + HAS_MEMBER edges
#    - This replaces the static 9 communities from the graphify-out snapshot
#
# 2. INCREMENTAL UPDATES: After each incremental sync
#    - If <= 5 entries changed: skip reclustering (too expensive for small changes)
#    - If > 5 entries changed: rebuild communities
#    - Pass update_communities=True to add_episode when adding individual episodes
#      to get per-episode community updates (lighter than full rebuild)
#
# 3. COMMUNITY NAMING: Graphiti auto-generates names via LLM. We post-process
#    to ensure names are actionable (e.g., "Architecture Decisions: Deployment Stack"
#    not "Cluster 7").
#
# 4. COMMUNITY STABILITY: Communities should be mostly stable across syncs.
#    The Leiden algorithm is deterministic given the same graph structure.
#    New nodes may shift boundaries, but existing communities persist.
#
# 5. MONITORING: Track community count, member distribution, and drift across cycles.
#    Alert if community count changes by >30% between syncs (indicates structural shift).


# =============================================================================
# GRAPHITI INTEGRATION MAP
# =============================================================================
#
# How Mycelium's design maps to Graphiti primitives:
#
# | Mycelium Concept         | Graphiti Primitive       | Notes                                    |
# |--------------------------|--------------------------|------------------------------------------|
# | KnowledgeEntry node      | EntityNode + label       | Custom type via entity_types parameter    |
# | Person node              | EntityNode + label       | Custom type via entity_types parameter    |
# | DemandSignal node        | EntityNode + label       | Custom type via entity_types parameter    |
# | Intent node              | EntityNode + label       | Custom type via entity_types parameter    |
# | Convergence node         | EntityNode + label       | Custom type via entity_types parameter    |
# | Concept node             | EntityNode + label       | Custom type via entity_types parameter    |
# | Decision node            | EntityNode + label       | Custom type via entity_types parameter    |
# | Markdown file            | EpisodicNode (episode)   | Provenance: every fact traces back here   |
# | Frontmatter 'related'    | EntityEdge (RELATES_TO)  | name='RELATES_TO_ENTRY', EXTRACTED        |
# | LLM-inferred connection  | EntityEdge (RELATES_TO)  | name='INFERRED_RELATION', needs verify    |
# | Demand → Knowledge link  | EntityEdge (RELATES_TO)  | name='ANSWERED_BY' etc.                   |
# | Person engagement history| EntityEdge (RELATES_TO)  | name='STRUCTURALLY_COUPLED', valid_at     |
# | Community cluster        | CommunityNode            | Built-in Leiden algorithm                 |
# | Community membership     | CommunityEdge            | Built-in HAS_MEMBER edge                  |
# | Temporal validity        | EntityEdge.valid_at/     | Graphiti's bi-temporal model              |
# |                          |   invalid_at/expired_at  |                                           |
# | Content change detection | content_hash in attrs    | Mycelium-specific, not Graphiti           |
# | Sync state               | .mycelium/sync-state.json| Mycelium-specific, not Graphiti           |
# | group_id partitioning    | group_id='maverick-meta' | One group for the whole meta repo         |
# | Vector search            | Graphiti search()        | Hybrid semantic + keyword + graph         |
# | Saga (episode chains)    | SagaNode                 | Could chain sync cycles as sagas          |
#
# What we use from Graphiti (not custom):
#   - Episode ingestion and entity extraction (add_episode)
#   - Entity deduplication and resolution (built-in)
#   - Bi-temporal edge tracking (valid_at, invalid_at, expired_at)
#   - Vector embeddings (name_embedding, fact_embedding)
#   - Hybrid search (semantic + BM25 + graph traversal)
#   - Community detection (Leiden algorithm)
#   - Contradiction handling (automatic fact invalidation)
#
# What we add on top (Mycelium-specific):
#   - Custom entity types (7 domain-specific node types)
#   - Dual-truth sync model (markdown → graph reconciliation)
#   - Sync state tracking (.mycelium/sync-state.json)
#   - Demand/supply gap analysis (queries + edge types)
#   - Convergence detection (3+ intents → convergence event)
#   - Structural coupling (person engagement tracking with decay)
#   - Content hash change detection (avoids re-syncing unchanged files)
#   - Edge confidence classification (EXTRACTED vs INFERRED)
#   - Edge decay (INFERRED edges lose confidence after 14 days)


# =============================================================================
# GRAPH TOPOLOGY DIAGRAM (ASCII)
# =============================================================================
#
#                          +----------------+
#                          |  Convergence   |
#                          +-------^--------+
#                                  |
#                           CONVERGES_TO
#                                  |
#                          +-------+--------+
#                          |    Intent      |
#                          +-------^--------+
#                                  |
#                             HAS_INTENT
#                                  |
#   +---------+   ASKED    +------+--------+   ANSWERED_BY    +-----------------+
#   |  Person |----------->| DemandSignal  |----------------->| KnowledgeEntry  |
#   +----+----+            +------+--------+                  +---+----+--------+
#        |                        |                               |    |
#        | AUTHORED               | PARTIALLY_ANSWERED_BY         |    | HAS_DECISION
#        | STRUCTURALLY_COUPLED   | UNANSWERED_NEAR               |    |
#        |                        |                               |    v
#        +----------------------->+<------------------------------+  +---------+
#                                                                    | Decision|
#                                 CONTAINS_CONCEPT                   +---------+
#                                        |
#                                        v
#                                  +-----------+
#                                  |  Concept  |
#                                  +-----------+
#
#   Cross-cutting:
#     DemandSignal --SAME_PERSON_PATTERN--> DemandSignal (same person)
#     DemandSignal --CROSS_PERSON_DEMAND--> DemandSignal (different people)
#     KnowledgeEntry --RELATES_TO_ENTRY--> KnowledgeEntry (explicit xref)
#     KnowledgeEntry --SUPERSEDES--> KnowledgeEntry (temporal replacement)
#     Any --INFERRED_RELATION--> Any (LLM-inferred, needs verification)
#
#   Managed by Graphiti:
#     Community --HAS_MEMBER--> Entity (any node type)
#     Episodic --MENTIONS--> Entity (provenance link)
