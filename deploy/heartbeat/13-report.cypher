// Report system shape
MATCH (n) WITH count(n) as total_nodes
MATCH ()-[r]->() WITH total_nodes, count(r) as total_edges
MATCH (i:Invariant) WHERE i.health = "healthy" WITH total_nodes, total_edges, count(i) as healthy_invariants
MATCH (t:TestCase) WHERE t.last_result = "pass" WITH total_nodes, total_edges, healthy_invariants, count(t) as passing_tests
CREATE (:Report {node_id:"report-" + toString(timestamp()), created_at:datetime(),
  total_nodes:total_nodes, total_edges:total_edges,
  healthy_invariants:healthy_invariants, passing_tests:passing_tests, project:"system"});
