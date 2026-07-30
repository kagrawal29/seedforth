// Compare current protocol/invariant counts against last snapshot
MATCH (p:Protocol) WITH count(p) as protocol_count
MATCH (i:Invariant) WITH protocol_count, count(i) as invariant_count
MATCH (snap:Snapshot) WHERE snap.last_authorized IS NOT NULL
  AND (snap.protocol_count <> protocol_count OR snap.invariant_count <> invariant_count)
CREATE (m:Mutation {node_id:"mut-" + toString(timestamp()), detected_at:datetime(),
  expected_protocols:snap.protocol_count, actual_protocols:protocol_count,
  expected_invariants:snap.invariant_count, actual_invariants:invariant_count});
