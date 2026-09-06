// ============================================================================
// Mycelium Org Bootstrap — SeedForth initial organizational structure
// Idempotent (MERGE). Run: mycelium bootstrap --target dev
// Section 4.3 — Organisational structure seed
// ============================================================================

// --- Organization ---

// @node_id: org-organization-seedforth
MERGE (org:Organization {node_id: 'org-organization-seedforth'})
SET org.identity = 'seedforth',
    org.name = 'SeedForth',
    org.mission = 'Infinite Agency — orchestration root for autonomous projects',
    org.created_at = timestamp();

// --- Department ---

// @node_id: org-department-engineering
MERGE (dept:Department {node_id: 'org-department-engineering'})
SET dept.identity = 'seedforth/engineering',
    dept.name = 'Engineering',
    dept.purpose = 'Build and maintain the Delta agent platform and mycelium knowledge graph',
    dept.created_at = timestamp();

// --- Role ---

// @node_id: org-role-hub-orchestrator
MERGE (role:Role {node_id: 'org-role-hub-orchestrator'})
SET role.identity = 'seedforth/engineering/hub-orchestrator',
    role.name = 'Hub Orchestrator',
    role.responsibilities = 'Route users, dispatch agents, monitor project health, manage provisioning lifecycle',
    role.created_at = timestamp();

// --- BELONGS_TO structural edges (decay_protected) ---

MATCH (dept:Department {node_id: 'org-department-engineering'})
MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MERGE (dept)-[:BELONGS_TO {decay_protected: true}]->(org);

MATCH (role:Role {node_id: 'org-role-hub-orchestrator'})
MATCH (dept:Department {node_id: 'org-department-engineering'})
MERGE (role)-[:BELONGS_TO {decay_protected: true}]->(dept);

// --- Concept: Organization ---

// @node_id: org-concept-organization
MERGE (c:Concept {node_id: 'org-concept-organization'})
SET c.name = 'Organization',
    c.file_type = 'concept',
    c.definition = 'Root entity representing an organization: scope boundary, identity root, ownership container. May have Departments as children via BELONGS_TO.';

// --- Concept: Department ---

// @node_id: org-concept-department
MERGE (c:Concept {node_id: 'org-concept-department'})
SET c.name = 'Department',
    c.file_type = 'concept',
    c.definition = 'Sub-unit within an Organization housing one or more Roles. May nest sub-departments. Belongs to exactly one Organization or parent Department.';

// --- Concept: Role ---

// @node_id: org-concept-role
MERGE (c:Concept {node_id: 'org-concept-role'})
SET c.name = 'Role',
    c.file_type = 'concept',
    c.definition = 'Named position within a Department. Defines responsibilities, capability requirements, and scope. SubAgents are assigned to Roles.';

// --- Concept: Project ---

// @node_id: org-concept-project
MERGE (c:Concept {node_id: 'org-concept-project'})
SET c.name = 'Project',
    c.file_type = 'concept',
    c.definition = 'Bounded unit of work with defined goals, timeline, and deliverable. Owned by a Department or Role. Hosts decisions, learnings, and patterns.';

// --- Concept: Decision ---

// @node_id: org-concept-decision
MERGE (c:Concept {node_id: 'org-concept-decision'})
SET c.name = 'Decision',
    c.file_type = 'concept',
    c.definition = 'Recorded choice with rationale, alternatives considered, and context at decision time. Belongs to a Project or Department. Immutable (monotonic).';

// --- Concept: Learning ---

// @node_id: org-concept-learning
MERGE (c:Concept {node_id: 'org-concept-learning'})
SET c.name = 'Learning',
    c.file_type = 'concept',
    c.definition = 'Captured insight from experience: what was tried, what worked, what failed, and the extracted principle. Accumulates over time; feeds the dream pass.';

// --- Concept: Pattern ---

// @node_id: org-concept-pattern
MERGE (c:Concept {node_id: 'org-concept-pattern'})
SET c.name = 'Pattern',
    c.file_type = 'concept',
    c.definition = 'Recurring structural or process shape discovered by the dream pass or declared by operator. Hardened compound atom or design template.';

// --- Concept: Compacted Fact ---

// @node_id: org-concept-compacted-fact
MERGE (c:Concept {node_id: 'org-concept-compacted-fact'})
SET c.name = 'Compacted Fact',
    c.file_type = 'concept',
    c.definition = 'A fact that has been crystallized — past active editing, stripped to a single authoritative merged form. The stable end state of fact refinement. Prevents duplicate drift.';

// --- HAS_CONCEPT structural edges (decay_protected) ---

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-organization'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-department'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-role'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-project'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-decision'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-learning'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-pattern'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);

MATCH (org:Organization {node_id: 'org-organization-seedforth'})
MATCH (c:Concept {node_id: 'org-concept-compacted-fact'})
MERGE (org)-[:HAS_CONCEPT {decay_protected: true}]->(c);
