// Owner-controlled deployment requalification. Runtime capability generations
// are derived from the immutable worker release and supplied as evidence; this
// operation cannot create grants, mandates, work, or product-side effects.
MATCH (:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(owner_grant:Grant {scope:'seedforth-platform',revoked:false})
WHERE 'work.control' IN owner_grant.permissions
  AND (owner_grant.expires_at IS NULL OR owner_grant.expires_at>datetime())
UNWIND $capabilities AS capability
WITH capability
WHERE capability.id IN ['capability-git-inspection-v1','capability-code-snapshot-v1','capability-code-proposal-v1']
  AND capability.generation =~ '[0-9a-f]{64}'
  AND capability.cost_units=1 AND capability.max_seconds>0 AND capability.max_seconds<=300
MERGE (c:Capability {node_id:capability.id})
SET c.enabled=true,c.policy_generation=capability.generation,
    c.cost_units=capability.cost_units,c.max_seconds=capability.max_seconds,
    c.effect_class='private_candidate_artifact_only',c.updated_at=datetime()
RETURN collect(c.node_id) AS requalified
