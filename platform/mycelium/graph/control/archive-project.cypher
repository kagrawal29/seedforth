// Owner-authorized portfolio transition. Archiving changes portfolio authority,
// not service/process state, and is refused while a project agent or execution
// is still active. Pending legacy work is held and retained for restoration.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(grant:Grant {scope:'seedforth-platform',revoked:false})
WHERE 'work.control' IN grant.permissions
  AND (grant.expires_at IS NULL OR grant.expires_at>datetime())
WITH DISTINCT grant
MATCH (p:Project {node_id:$project_id})
WHERE coalesce(p.category,'')<>'core'
  AND NOT (p.node_id IN ['project-flowing-indian','project-cajon-sensei'])
  AND coalesce(p.portfolio_state,'proposed')<>'archived'
  AND NOT EXISTS {
    MATCH (a:SubAgent {project:p.name})
    WHERE coalesce(a.status,'unknown') IN ['active','running','starting']
  }
  AND NOT EXISTS {
    MATCH (e:ExecutionSession {project:p.name})
    WHERE coalesce(e.status,'unknown') IN ['queued','running']
  }
  AND NOT EXISTS {
    MATCH (x:AgentProcess {project:p.name})
    WHERE coalesce(x.status,'unknown') IN ['ready','running','starting','active']
  }
SET p._lock=coalesce(p._lock,0)+1
WITH p WHERE coalesce(p.portfolio_state,'proposed')<>'archived'
SET p.portfolio_state='archived',p.new_work='disabled',p.archive_reason=$reason,
    p.archive_decision=$decision_id,p.archived_at=datetime(),p.updated_at=datetime()
WITH p
OPTIONAL MATCH (w:WorkItem {project:p.name})
WHERE NOT coalesce(w.status,'') IN ['done','cancelled']
SET w.hold=true,w.archive_reason='project_archived',
    w.updated_at=datetime(),w._lock=coalesce(w._lock,0)+1
WITH p,collect(w) AS work
CREATE (d:Decision {node_id:$decision_id,scope_id:'seedforth-platform',actor:$actor,
    outcome:'archive',project_id:p.node_id,reason:$reason,created_at:datetime()})
CREATE (t:StateTransition {node_id:$event_id,scope_id:'seedforth-platform',actor:$actor,
    from_state:'portfolio_active_or_proposed',to_state:'archived',project_id:p.node_id,
    created_at:datetime()})
CREATE (t)-[:CHANGED]->(p)
CREATE (t)-[:AUTHORIZED_BY]->(d)
FOREACH (w IN work | CREATE (t)-[:HELD]->(w))
RETURN p.node_id AS project,p.portfolio_state AS portfolio_state,
       p.new_work AS new_work,size(work) AS pending_work,
       coalesce(p.archive_reason,'') AS reason
