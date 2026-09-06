// Flowing Indian — fleet-schema reconciliation + seed (2026-08-19)
// Converges the legacy mycelium node `proj-flowing-indian` onto the delta fleet
// convention `project-flowing-indian`, preserving all bootcamp content (values,
// goals, team, milestones, treasury), and adds the fleet types (SubAgent,
// EntityMandate, Tool). Idempotent (MERGE). Re-run safe.

// ---- 1. Fleet-convention Project node (merged seed + fleet fields) ----------
MERGE (p:Project {node_id: 'project-flowing-indian'})
SET p.name = 'flowing-indian',
    p.project = 'flowing-indian',
    p.category = 'client',
    p.status = 'active',
    p.lifecycle_state = 'active',
    p.runtime = 'opencode',
    p.has_mandate = true,
    p.goal_count = 17,
    p.profile_count = 3,
    p.decision_count = 4,
    p.milestone_count = 4,
    p.tool_count = 7,
    p.artifact_count = 0,
    p.context_ingested = datetime(),
    p.updated_at = datetime();

// ---- 2. Re-point incoming edges (a)-[:R]->(old)  =>  (a)-[:R]->(new) --------
MATCH (a)-[:SERVES]->(old:Project {node_id: 'proj-flowing-indian'})
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (a)-[:SERVES]->(new);

MATCH (a)-[:INVOLVED_IN]->(old:Project {node_id: 'proj-flowing-indian'})
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (a)-[:INVOLVED_IN]->(new);

MATCH (a)-[:MILESTONE_OF]->(old:Project {node_id: 'proj-flowing-indian'})
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (a)-[:MILESTONE_OF]->(new);

MATCH (a)-[:GOVERNS]->(old:Project {node_id: 'proj-flowing-indian'})
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (a)-[:GOVERNS]->(new);

MATCH (a)-[:DRIVES]->(old:Project {node_id: 'proj-flowing-indian'})
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (a)-[:DRIVES]->(new);

MATCH (a)-[:CONCERNS]->(old:Project {node_id: 'proj-flowing-indian'})
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (a)-[:CONCERNS]->(new);

MATCH (a)-[:TRANSITIONS]->(old:Project {node_id: 'proj-flowing-indian'})
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (a)-[:TRANSITIONS]->(new);

// ---- 3. Re-point outgoing edges (old)-[:R]->(b)  =>  (new)-[:R]->(b) --------
MATCH (old:Project {node_id: 'proj-flowing-indian'})-[:BELONGS_TO]->(b)
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (new)-[:BELONGS_TO]->(b);

MATCH (old:Project {node_id: 'proj-flowing-indian'})-[:HAS_REPO]->(b)
MATCH (new:Project {node_id: 'project-flowing-indian'})
CREATE (new)-[:HAS_REPO]->(b);

// ---- 4. Delete the legacy project node -------------------------------------
MATCH (old:Project {node_id: 'proj-flowing-indian'})
DETACH DELETE old;

// ---- 5. SubAgent (pending until provisioned on server) ---------------------
MERGE (s:SubAgent {node_id: 'subagent-flowing-indian'})
SET s.name = 'flowing-indian',
    s.role = 'project agent',
    s.owner = 'delta',
    s.project = 'flowing-indian',
    s.model = 'deepseek-v4-pro',
    s.status = 'pending',
    s.updated_at = datetime();

MATCH (p:Project {node_id: 'project-flowing-indian'})
MATCH (s:SubAgent {node_id: 'subagent-flowing-indian'})
MERGE (p)-[:HAS_AGENT]->(s);

MATCH (s:SubAgent {node_id: 'subagent-flowing-indian'})
MATCH (o:Organization {node_id: 'org-seedforth'})
MERGE (s)-[:BELONGS_TO]->(o);

// ---- 6. EntityMandate (north star) -----------------------------------------
MERGE (m:EntityMandate {node_id: 'mandate-flowing-indian'})
SET m.project = 'flowing-indian',
    m.source = 'SEED.md',
    m.status = 'active',
    m.needs_llm = false,
    m.north_star = 'Move people from living in their mind to living in their body; build a movement-practice business through the rope-flow course (2 SKUs), workshops, and events, rooted in a safe non-judgmental space.',
    m.updated_at = datetime();

// ---- 7. Link existing bootcamp goals to the mandate (DERIVED_FROM) ---------
MATCH (m:EntityMandate {node_id: 'mandate-flowing-indian'})
MATCH (g:EntityGoal) WHERE g.project = 'flowing-indian'
MERGE (g)-[:DERIVED_FROM {decay_protected: true}]->(m);

// ---- 8. Tool nodes (capability map — self-describability) ------------------
MERGE (t:Tool {node_id: 'tool-flowing-indian-vercel'})
  SET t.name='vercel', t.status='present', t.project='flowing-indian', t.updated_at=datetime();
MERGE (t:Tool {node_id: 'tool-flowing-indian-razorpay'})
  SET t.name='razorpay', t.status='present', t.project='flowing-indian', t.updated_at=datetime();
MERGE (t:Tool {node_id: 'tool-flowing-indian-bunny'})
  SET t.name='bunny', t.status='present', t.project='flowing-indian', t.updated_at=datetime();
MERGE (t:Tool {node_id: 'tool-flowing-indian-clerk'})
  SET t.name='clerk', t.status='present', t.project='flowing-indian', t.updated_at=datetime();
MERGE (t:Tool {node_id: 'tool-flowing-indian-github'})
  SET t.name='github', t.status='present', t.project='flowing-indian', t.updated_at=datetime();
MERGE (t:Tool {node_id: 'tool-flowing-indian-unipile'})
  SET t.name='unipile', t.status='present', t.project='flowing-indian', t.updated_at=datetime();
MERGE (t:Tool {node_id: 'tool-flowing-indian-whatsapp'})
  SET t.name='whatsapp', t.status='present', t.project='flowing-indian', t.updated_at=datetime();

MATCH (t:Tool) WHERE t.project = 'flowing-indian'
MATCH (s:SubAgent {node_id: 'subagent-flowing-indian'})
MERGE (t)-[:USED_BY {decay_protected: true}]->(s);

// ---- 9. Fix Repository visibility (actually private) -----------------------
MATCH (r:Repository {node_id: 'repo-flowing-indian'})
SET r.visibility = 'private';
