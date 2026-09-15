// Owner-only short-lived renewal for the capability broker's Flowing settlement.
// It changes no work state and cannot authorize a new invocation.
MATCH (owner:Principal {node_id:$actor,enabled:true})-[:HAS_GRANT]->(control:Grant {scope:'seedforth-platform',revoked:false})
WHERE $actor='principal-seedforth-owner'
  AND 'work.control' IN control.permissions
  AND (control.expires_at IS NULL OR control.expires_at>datetime())
  AND size($expires_at)>=20 AND datetime($expires_at)>datetime()
  AND datetime($expires_at)<=datetime()+duration('PT1H')
MATCH (broker:Principal {node_id:'principal-capability-broker',enabled:true})
MATCH (grant:Grant {node_id:'grant-capability-broker-flowing',scope:'flowing-indian',revoked:false})
      <-[:HAS_GRANT]-(broker)
SET grant.expires_at=datetime($expires_at),grant.authority='owner-settlement-renewal'
CREATE (signal:Signal {node_id:$event_id,scope_id:'flowing-indian',issuer:$actor,
    type:'settlement_authority_renewed',status:'accepted',created_at:datetime(),
    result:'short_lived_flowing_settlement_authority',enabled:false,expires_at:$expires_at})
RETURN broker.node_id AS principal,grant.node_id AS grant_id,
       grant.scope AS scope,grant.expires_at AS expires_at
