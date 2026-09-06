// Phase 3 — parallel agency: division subagents + workstreams (branch/worktree/subagent/milestone).
// Flowing Indian first (the flagship). Schema is reusable for every driven project.

// ---- Division subagents (Charlie's lieutenants) for flowing-indian ---------
MERGE (s:SubAgent {node_id: 'subagent-flowing-indian-revenue'})
SET s.name = 'flowing-indian-revenue', s.role = 'revenue', s.owner = 'charlie',
    s.model = 'deepseek-v4-pro', s.status = 'active', s.project = 'flowing-indian';

MERGE (s:SubAgent {node_id: 'subagent-flowing-indian-research'})
SET s.name = 'flowing-indian-research', s.role = 'research', s.owner = 'charlie',
    s.model = 'deepseek-chat', s.status = 'active', s.project = 'flowing-indian';

MERGE (s:SubAgent {node_id: 'subagent-flowing-indian-operations'})
SET s.name = 'flowing-indian-operations', s.role = 'operations', s.owner = 'charlie',
    s.model = 'deepseek-chat', s.status = 'active', s.project = 'flowing-indian';

// ---- Workstreams (branch + worktree + subagent + milestone) -----------------
MERGE (w:Workstream {node_id: 'workstream-flowing-indian-rope-sale'})
SET w.name = 'Rope Sale Organic Launch', w.branch = 'feature/rope-sale-launch',
    w.worktree_path = '/home/proj-flowing-indian/worktrees/rope-sale',
    w.status = 'active', w.project = 'flowing-indian';

MERGE (w:Workstream {node_id: 'workstream-flowing-indian-paid-marketing'})
SET w.name = 'Paid Marketing & Online Course', w.branch = 'feature/paid-marketing-course',
    w.worktree_path = '/home/proj-flowing-indian/worktrees/paid-marketing',
    w.status = 'planned', w.project = 'flowing-indian';

MERGE (w:Workstream {node_id: 'workstream-flowing-indian-studio'})
SET w.name = 'Flow Studio Inauguration', w.branch = 'feature/flow-studio',
    w.worktree_path = '/home/proj-flowing-indian/worktrees/flow-studio',
    w.status = 'planned', w.project = 'flowing-indian';

// ---- Link workstreams to project, subagent, milestone -----------------------
MATCH (p:Project {node_id: 'project-flowing-indian'})
MATCH (w:Workstream {project: 'flowing-indian'})
MERGE (p)-[:HAS_WORKSTREAM]->(w);

MATCH (w:Workstream {node_id: 'workstream-flowing-indian-rope-sale'})
MATCH (s:SubAgent {node_id: 'subagent-flowing-indian-revenue'})
MERGE (w)-[:OWNED_BY]->(s);

MATCH (w:Workstream {node_id: 'workstream-flowing-indian-paid-marketing'})
MATCH (s:SubAgent {node_id: 'subagent-flowing-indian-revenue'})
MERGE (w)-[:OWNED_BY]->(s);

MATCH (w:Workstream {node_id: 'workstream-flowing-indian-studio'})
MATCH (s:SubAgent {node_id: 'subagent-flowing-indian-operations'})
MERGE (w)-[:OWNED_BY]->(s);

MATCH (w:Workstream {node_id: 'workstream-flowing-indian-rope-sale'})
MATCH (m:Milestone {project: 'flowing-indian'}) WHERE m.title = 'Rope Sale Organic Launch'
MERGE (w)-[:SERVES]->(m);

MATCH (w:Workstream {node_id: 'workstream-flowing-indian-paid-marketing'})
MATCH (m:Milestone {project: 'flowing-indian'}) WHERE m.title = 'Paid Marketing & Online Course'
MERGE (w)-[:SERVES]->(m);

MATCH (w:Workstream {node_id: 'workstream-flowing-indian-studio'})
MATCH (m:Milestone {project: 'flowing-indian'}) WHERE m.title = 'Flow Studio Inauguration'
MERGE (w)-[:SERVES]->(m);

// ---- Charlie delegates to the divisions ------------------------------------
MATCH (c:Being {node_id: 'being-charlie'})
MATCH (s:SubAgent) WHERE s.owner = 'charlie'
MERGE (c)-[:DELEGATES_TO]->(s);
