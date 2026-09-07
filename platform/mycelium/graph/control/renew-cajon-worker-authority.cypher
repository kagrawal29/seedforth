// Owner-only short-lived renewal for the already provisioned Cajon worker.
// Authority is bounded to the existing worker identity and cannot enable work.
MATCH (owner:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(control:Grant {scope:'seedforth-platform',revoked:false})
WHERE $actor='principal-seedforth-owner'
  AND 'work.control' IN control.permissions
  AND (control.expires_at IS NULL OR control.expires_at>datetime())
  AND size($expires_at)>=20 AND datetime($expires_at)>datetime()
  AND datetime($expires_at)<=datetime()+duration('PT1H')
MATCH (worker:Principal {node_id:'principal-cajon-upgrade-worker',enabled:true})
MATCH (grant:Grant {node_id:'grant-cajon-upgrade-worker',scope:'cajon-sensei',revoked:false})
      <-[:HAS_GRANT]-(worker)
SET grant.expires_at=datetime($expires_at),grant.authority='owner-worker-credential-renewal'
CREATE (signal:Signal {node_id:$event_id,scope_id:'cajon-sensei',issuer:$actor,
    type:'worker_authority_renewed',status:'accepted',created_at:datetime(),
    result:'short_lived_cajon_worker_authority',enabled:false,expires_at:$expires_at})
RETURN worker.node_id AS principal,grant.node_id AS grant_id,
       grant.scope AS scope,grant.expires_at AS expires_at
