# Asgard Query Log

Append-only. Each row is one agent interaction with the knowledge graph.
Agent queries are demand signals — the demand engine reads this file.

| timestamp (UTC) | agent / source | action | question / file | results | response_bytes |
|-----------------|----------------|--------|-----------------|---------|----------------|
| 2026-04-10T12:14:48Z | ask_asgard | ask | what is the team working on right now? | 3 | 1870 |
| 2026-04-10T12:29:27Z | ask_asgard | ask | what are the settled architecture decisions? | 10 | 3622 |
| 2026-04-10T12:32:00Z | ask_asgard | ask | what is the team struggling with right now? | 3 | 1875 |
| 2026-04-10T12:32:15Z | ask_asgard | ask_demand | (all) | 17 | 1156 |
| 2026-04-10T12:32:15Z | ask_asgard | ask | cross person demand dependencies | 3 | 2852 |
| 2026-04-10T12:32:15Z | ask_asgard | ask | rule builder frustration conditions | 6 | 3055 |
| 2026-04-10T13:10:43Z | ask_asgard | ask_bridges | 0 | 14 | 1926 |
| 2026-04-10T13:10:49Z | ask_asgard | ask | what decisions affect the API layer? | 10 | 3092 |
| 2026-04-10T13:10:49Z | ask_asgard | ask_neighborhood | memory_layer_decisions | 17 | 1131 |
| 2026-04-10T13:10:49Z | ask_asgard | ask_bridges | 2 | 9 | 1261 |
| 2026-04-10T13:11:28Z | ask_asgard | ask | what decisions affect the memory layer? | 10 | 3892 |
| 2026-04-10T13:11:28Z | ask_asgard | ask_demand | (all) | 17 | 1156 |
| 2026-04-10T13:11:28Z | ask_asgard | ask_neighborhood | memory_layer_decisions | 17 | 1131 |
| 2026-04-10T13:11:28Z | ask_asgard | ask_bridges | 0 | 14 | 1926 |
| 2026-04-10T13:17:19Z | ask_asgard | ask | memory layer decisions | 10 | 3875 |
| 2026-04-10T13:17:19Z | ask_asgard | ask_demand | (all) | 17 | 1156 |
| 2026-04-10T13:17:19Z | ask_asgard | ask_neighborhood | memory_layer_decisions | 17 | 1131 |
| 2026-04-10T13:17:19Z | ask_asgard | ask_bridges | 0 | 14 | 1926 |
| 2026-04-10T13:46:12Z | mcp | asgard_graph_schema | (schema request) | 12 | 125ms |
| 2026-04-10T13:46:12Z | ask_asgard | ask | what decisions affect the memory layer? | 10 | 3892 |
| 2026-04-10T13:46:12Z | mcp | asgard_graph_ask | what decisions affect the memory layer? | 45 | 9ms |
| 2026-04-10T13:46:12Z | mcp | asgard_graph_query | MATCH (n) RETURN count(n) as total | 1 | 4ms |
| 2026-04-10T13:46:12Z | ask_asgard | ask_demand | (all) | 17 | 1156 |
| 2026-04-10T13:46:12Z | mcp | asgard_graph_demand | (all) | 17 | 3ms |
| 2026-04-10T13:46:12Z | Mycelium | asgard_graph_trace | MCP client test query | 1 | 9ms |
| 2026-04-10T13:46:12Z | ask_asgard | ask_neighborhood | memory_layer_decisions | 17 | 1131 |
| 2026-04-10T13:46:12Z | mcp | asgard_graph_neighborhood | memory_layer_decisions | 17 | 4ms |
| 2026-04-10T13:46:12Z | ask_asgard | ask_bridges | 0 | 14 | 1926 |
| 2026-04-10T13:46:12Z | mcp | asgard_graph_bridges | community 0 | 22 | 4ms |
| 2026-04-10T14:28:14Z | mcp | asgard_graph_schema | (schema request) | 11 | 100ms |
| 2026-04-10T14:28:24Z | ask_asgard | ask_demand | (all) | 2 | 40 |
| 2026-04-10T14:28:24Z | mcp | asgard_graph_demand | (all) | 2 | 22ms |
| 2026-04-10T14:28:25Z | ask_asgard | ask_bridges | 0 | 11 | 1508 |
| 2026-04-10T14:28:25Z | mcp | asgard_graph_bridges | community 0 | 19 | 13ms |
| 2026-04-10T14:28:25Z | ask_asgard | ask_bridges | 8 | 5 | 682 |
| 2026-04-10T14:28:25Z | mcp | asgard_graph_bridges | community 8 | 14 | 9ms |
| 2026-04-10T14:28:25Z | mcp | asgard_graph_query | MATCH (n)-[r]-() RETURN n.label, n.community, count(r) as degree ORDER BY degree | 15 | 9ms |
| 2026-04-10T18:40:27Z | ask_asgard | ask_demand | (all) | 17 | 1156 |
| 2026-04-10T18:40:27Z | mcp | asgard_graph_demand | (all) | 17 | 127ms |
| 2026-04-10T18:40:28Z | mcp | asgard_graph_query | MATCH (d:Demand) RETURN d.node_id, d.label, d.community, d.tags ORDER BY d.commu | 9 | 14ms |
| 2026-04-10T18:40:33Z | mcp | asgard_graph_query | MATCH (d:Demand)-[r]-(k:Knowledge) RETURN d.label, type(r), k.label, k.community | 9 | 17ms |
| 2026-04-10T18:40:35Z | mcp | asgard_graph_query | MATCH (k:Knowledge) WHERE k.community IS NOT NULL RETURN k.community AS comm, co | 9 | 13ms |
| 2026-04-10T18:40:40Z | mcp | asgard_graph_query | MATCH (d:Demand)-[r]-(k:Knowledge) RETURN k.community AS comm, count(DISTINCT d) | 4 | 24ms |
| 2026-04-10T18:44:40Z | mcp | asgard_graph_query | MATCH (p:Phase) RETURN p.node_id, p.label, p.demand_character, p.person_count, p | 1 | 19ms |
| 2026-04-10T18:44:40Z | mcp | asgard_graph_query | MATCH (p:Phase)-[r:CONSTITUTED_BY]->(c:Convergence) RETURN p.label, c.label, c.p | 3 | 8ms |
| 2026-04-10T18:44:45Z | mcp | asgard_graph_query | MATCH (p:Phase)-[:CONSTITUTED_BY]->(c:Convergence)<-[:CONVERGES_TO]-(i:Intent) R | 12 | 14ms |
| 2026-04-10T18:48:55Z | mcp | asgard_graph_query | MATCH (i:Intent) RETURN i.person, i.graph_region, i.domain, i.recurrence_count,  | 18 | 152ms |
| 2026-04-10T18:50:13Z | mcp | asgard_graph_query | MATCH (p:Phase {active: true}) RETURN p.label, p.dispersion, p.micro_phase_count | 1 | 11ms |
| 2026-04-10T19:01:42Z | mcp | asgard_graph_query | MATCH (d:Demand) RETURN count(d), collect(d.node_id)[0..3] | 1 | 34ms |
| 2026-04-10T19:03:09Z | mcp | asgard_graph_query | MATCH (d:Demand) RETURN count(d), collect(d.person) AS persons, collect(d.frustr | 1 | 11ms |
| 2026-04-10T19:03:15Z | mcp | asgard_graph_query | MATCH (d:Demand) WHERE d.frustration = 'high' RETURN d.person, d.label, d.freque | 2 | 13ms |
| 2026-04-10T19:21:43Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 5 | 40ms |
| 2026-04-10T19:21:49Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS c ORDER BY c DESC | 7 | 23ms |
| 2026-04-10T19:22:05Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 5 | 15ms |
| 2026-04-10T19:22:05Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS c ORDER BY c DESC | 7 | 10ms |
| 2026-04-10T19:22:11Z | mcp | asgard_graph_query | MATCH (p:Phase) RETURN p.node_id, p.label, p.active, p.demand_character, p.dispe | 2 | 11ms |
| 2026-04-10T19:22:17Z | mcp | asgard_graph_query | MATCH (p:Phase {node_id: 'phase-specification-2026-04-11'}) DETACH DELETE p RETU | 1 | 17ms |
| 2026-04-10T19:22:25Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 5 | 23ms |
| 2026-04-10T19:22:25Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS c ORDER BY c DESC | 7 | 8ms |
| 2026-04-10T19:25:49Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 5 | 20ms |
| 2026-04-10T19:30:48Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 7 | 11ms |
| 2026-04-10T19:30:48Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS c ORDER BY c DESC | 12 | 12ms |
| 2026-04-10T19:30:58Z | mcp | asgard_graph_query | MATCH (c:Concept)-[r]->(k:Knowledge) RETURN c.label, type(r), k.label LIMIT 15 | 14 | 17ms |
| 2026-04-10T19:47:53Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 7 | 26ms |
| 2026-04-10T19:51:33Z | mcp | asgard_graph_query | MATCH (n) WHERE n.community IS NOT NULL AND n.community >= 0 RETURN labels(n) AS | 19 | 19ms |
| 2026-04-10T19:51:38Z | mcp | asgard_graph_query | MATCH (n) WHERE n.community IS NULL OR n.community < 0 RETURN labels(n) AS type, | 5 | 6ms |
| 2026-04-10T19:51:48Z | mcp | asgard_graph_query | MATCH (d:Demand)-[r]-(k:Knowledge) RETURN d.node_id, type(r), k.node_id, k.commu | 0 | 8ms |
| 2026-04-10T19:51:59Z | mcp | asgard_graph_query | MATCH (d:Demand) RETURN d.node_id, d.label LIMIT 3 | 3 | 7ms |
| 2026-04-10T19:52:00Z | mcp | asgard_graph_query | MATCH (k:Knowledge) RETURN k.node_id LIMIT 5 | 5 | 4ms |
| 2026-04-10T19:52:48Z | mcp | asgard_graph_query | MATCH (n) WHERE n.community IS NULL OR n.community < 0 RETURN labels(n) AS type, | 3 | 7ms |
| 2026-04-10T19:56:47Z | mcp | asgard_graph_query | MATCH (n) RETURN count(n) | 1 | 6ms |
| 2026-04-10T19:56:48Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN count(r) | 1 | 6ms |
| 2026-04-10T19:56:48Z | mcp | asgard_graph_query | MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() WHERE r.source = 'dream-round' RETURN c | 1 | 7ms |
| 2026-04-10T19:58:47Z | mcp | asgard_graph_schema | (schema request) | 19 | 24ms |
| 2026-04-10T19:59:26Z | mcp | asgard_graph_query | MATCH (n)-[r]-() WITH n, count(r) AS degree ORDER BY degree DESC LIMIT 5 RETURN  | 5 | 19ms |
| 2026-04-10T19:59:28Z | mcp | asgard_graph_query | MATCH (p:Phase {active: true}) OPTIONAL MATCH (p)-[:CONSTITUTED_BY]->(c:Converge | 1 | 9ms |
| 2026-04-10T19:59:29Z | mcp | asgard_graph_query | MATCH (d:Demand) WHERE d.frustration = 'high' RETURN d.person, d.label, d.freque | 0 | 6ms |
| 2026-04-10T19:59:30Z | mcp | asgard_graph_query | MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() WHERE r.source = 'dream-round' MATCH (a | 0 | 8ms |
| 2026-04-10T19:59:40Z | mcp | asgard_graph_query | MATCH (a)-[r:CONCEPTUALLY_RELATED_TO]->(b) WHERE r.source = 'dream-round' RETURN | 10 | 4ms |
| 2026-04-10T19:59:40Z | mcp | asgard_graph_query | MATCH (a)-[r]->(b) WHERE a.community <> b.community RETURN a.community, b.commun | 5 | 8ms |
| 2026-04-10T20:02:47Z | mcp | asgard_graph_query | MATCH (d:Demand) RETURN d.person, count(d) AS demands, collect(d.domain) AS doma | 5 | 13ms |
| 2026-04-10T20:02:47Z | mcp | asgard_graph_query | MATCH (i:Intent) RETURN i.person, i.graph_region, i.recurrence_count ORDER BY i. | 12 | 7ms |
| 2026-04-10T20:02:48Z | mcp | asgard_graph_query | MATCH (c:Convergence) RETURN c.label, c.person_count, c.intent_count, c.strength | 3 | 5ms |
| 2026-04-10T20:04:42Z | mcp | asgard_graph_query | MATCH (c:Convergence) RETURN c.label, c.strength, c.person_count, c.persons | 3 | 10ms |
| 2026-04-10T20:04:43Z | mcp | asgard_graph_query | MATCH (d:Demand) WHERE d.gap_signal = true RETURN d.label, d.person, d.frustrati | 3 | 7ms |
| 2026-04-10T20:04:44Z | mcp | asgard_graph_query | MATCH (i:Intent) WHERE i.recurrence_count >= 5 RETURN i.label, i.person, i.recur | 5 | 6ms |
| 2026-04-10T20:05:23Z | mcp | asgard_graph_query | MATCH (c:Convergence)-[:COULD_TRIGGER]->(tr:ActionTrigger)-[:ACTIVATES]->(a:Acti | 3 | 8ms |
| 2026-04-10T20:05:24Z | mcp | asgard_graph_query | MATCH (i:Intent)-[:COULD_TRIGGER]->(tr:ActionTrigger)-[:ACTIVATES]->(a:ActionTem | 5 | 7ms |
| 2026-04-10T20:10:06Z | mcp | asgard_graph_query | MATCH (p:Phase)-[:CONSTITUTED_BY]->(c:Convergence)<-[:CONVERGES_TO]-(i:Intent) R | 12 | 11ms |
| 2026-04-10T20:10:10Z | mcp | asgard_graph_query | MATCH (i:Intent) RETURN i.person, i.label, i.graph_region, i.recurrence_count OR | 12 | 5ms |
| 2026-04-10T20:10:12Z | mcp | asgard_graph_query | MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() WHERE r.source = 'dream-round' MATCH (a | 100 | 17ms |
| 2026-04-10T20:10:13Z | mcp | asgard_graph_query | MATCH (k:Knowledge) WHERE k.category = 'architecture' AND k.confidence = 'high'  | 0 | 7ms |
| 2026-04-10T20:10:23Z | mcp | asgard_graph_query | MATCH (i:Intent) WITH i.graph_region AS region, collect(i.person) AS people, cou | 3 | 10ms |
| 2026-04-10T20:13:01Z | mcp | asgard_graph_query | MATCH (pur:Purpose)-[r]->(target) RETURN type(r), labels(target), target.label | 7 | 8ms |
| 2026-04-10T20:13:06Z | mcp | asgard_graph_query | MATCH (c:Canary)-[r]->(target) RETURN type(r), labels(target), target.label | 2 | 7ms |
| 2026-04-10T20:19:07Z | mcp | asgard_graph_query | MATCH (d:Dream) RETURN d.node_id, d.label, d.triangles_closed, d.orphans_pruned, | 1 | 11ms |
| 2026-04-10T20:19:09Z | mcp | asgard_graph_query | MATCH (d:Dream)-[:PROPOSED]->(p:ActionProposal) OPTIONAL MATCH (p)-[:RESPONDS_TO | 1 | 13ms |
| 2026-04-10T20:19:34Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 15 | 9ms |
| 2026-04-10T20:20:30Z | mcp | asgard_graph_query | MATCH (d:Dream)-[:PROPOSED]->(p:ActionProposal) OPTIONAL MATCH (p)-[:RESPONDS_TO | 1 | 15ms |
| 2026-04-10T20:29:43Z | mcp | asgard_graph_query | MATCH (n) WHERE toLower(n.label) CONTAINS 'deal' OR toLower(n.label) CONTAINS 'f | 20 | 30ms |
| 2026-04-10T20:29:44Z | mcp | asgard_graph_query | MATCH (n) WHERE toLower(n.label) CONTAINS 'user' OR toLower(n.label) CONTAINS 's | 9 | 9ms |
| 2026-04-10T20:37:55Z | mcp | asgard_graph_query | MATCH (p:Persona) RETURN p.node_id, p.label, p.fund_size, p.deal_volume | 4 | 14ms |
| 2026-04-10T20:37:55Z | mcp | asgard_graph_query | MATCH (s:Scenario) RETURN s.node_id, s.label, s.trigger LIMIT 10 | 8 | 7ms |
| 2026-04-10T20:37:56Z | mcp | asgard_graph_query | MATCH (p:Pain) RETURN p.label, p.severity, p.frequency ORDER BY p.severity | 11 | 7ms |
| 2026-04-10T20:38:03Z | mcp | asgard_graph_query | MATCH (u)-[r]->(e) WHERE u:Scenario OR u:Pain OR u:Persona RETURN labels(u) AS f | 20 | 21ms |
| 2026-04-10T20:38:08Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 19 | 8ms |
| 2026-04-10T20:38:09Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN count(r) | 1 | 7ms |
| 2026-04-10T21:04:50Z | mcp | asgard_graph_query | MATCH (i:Intent) WHERE i.person = 'Abhishek' RETURN i.label, i.graph_region, i.r | 3 | 31ms |
| 2026-04-10T21:04:50Z | mcp | asgard_graph_query | MATCH (d:Demand) WHERE d.person = 'Abhishek' RETURN d.label, d.domain, d.frustra | 1 | 10ms |
| 2026-04-10T21:04:52Z | mcp | asgard_graph_query | MATCH (p:Pain)--(per:Persona) MATCH (s:Scenario) WHERE s.node_id IN ['sourcing-p | 33 | 21ms |
| 2026-04-10T21:04:58Z | mcp | asgard_graph_query | MATCH (s:Scenario) WHERE NOT (s)-[:ENABLES]->(:Knowledge) AND NOT (s)-[:ENABLES] | 1 | 8ms |
| 2026-04-10T21:04:58Z | mcp | asgard_graph_query | MATCH (p:Pain) WHERE NOT (p)--(:Scenario) RETURN p.label, p.severity | 11 | 8ms |
| 2026-04-10T21:09:44Z | mcp | asgard_graph_query | MATCH (s:Scenario) WHERE NOT (:Feature)-[:SERVES]->(s) RETURN s.label, s.need | 1 | 16ms |
| 2026-04-10T21:09:45Z | mcp | asgard_graph_query | MATCH (p:Pain) WHERE NOT (:Feature)-[:ADDRESSES]->(p) RETURN p.label, p.severity | 6 | 10ms |
| 2026-04-10T21:11:38Z | mcp | asgard_graph_query | MATCH (s:Scenario) WHERE NOT (:Feature)-[:SERVES]->(s) OPTIONAL MATCH (s)-[:LEAD | 1 | 19ms |
| 2026-04-10T21:11:40Z | mcp | asgard_graph_query | MATCH (p:Pain) WHERE NOT (:Feature)-[:ADDRESSES]->(p) AND p.severity = 'high' OP | 5 | 10ms |
| 2026-04-10T21:11:41Z | mcp | asgard_graph_query | MATCH (s:Scenario) WHERE NOT (:Feature)-[:SERVES]->(s) OR s.node_id = 'portfolio | 1 | 10ms |
| 2026-04-10T21:24:47Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 26 | 17ms |
| 2026-04-10T21:24:48Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN count(r) | 1 | 8ms |
| 2026-04-10T21:27:57Z | mcp | asgard_graph_query | MATCH (n) WHERE toLower(n.label) CONTAINS 'capra' OR toLower(n.label) CONTAINS ' | 1 | 31ms |
| 2026-04-10T21:28:01Z | mcp | asgard_graph_query | MATCH (p:Purpose) RETURN p.label, p.description | 1 | 9ms |
| 2026-04-10T21:28:01Z | mcp | asgard_graph_query | MATCH (pr:Principle) RETURN pr.label, pr.description | 1 | 8ms |
| 2026-04-10T21:28:02Z | mcp | asgard_graph_query | MATCH (inv:Invariant) RETURN inv.label, inv.mechanism | 12 | 7ms |
| 2026-04-10T21:28:03Z | mcp | asgard_graph_query | MATCH (d:Dream) RETURN d.label, d.triangles_closed, d.orphans_pruned | 1 | 7ms |
| 2026-04-10T21:31:54Z | mcp | asgard_graph_query | MATCH (d:Dream) RETURN d.node_id, d.triangles_closed, d.orphans_pruned, d.timest | 1 | 13ms |
| 2026-04-10T21:31:55Z | mcp | asgard_graph_query | MATCH (ap:ActionProposal) RETURN ap.label, ap.status, ap.action, ap.person, ap.s | 1 | 8ms |
| 2026-04-10T21:33:38Z | mcp | asgard_graph_query | MATCH (d:Dream)-[:PROPOSED]->(ap:ActionProposal) OPTIONAL MATCH (ap)-[:RESPONDS_ | 1 | 16ms |
| 2026-04-10T21:33:38Z | mcp | asgard_graph_query | MATCH ()-[r:CONCEPTUALLY_RELATED_TO]->() WHERE r.source = 'dream-round' RETURN c | 1 | 9ms |
| 2026-04-10T21:33:39Z | mcp | asgard_graph_query | MATCH (t:Trace)-[:TOUCHES]->(k:Knowledge) WITH k, count(t) AS touches RETURN k.l | 5 | 10ms |
| 2026-04-10T21:38:31Z | mcp | asgard_graph_query | MATCH (l:Learning) RETURN l.label, l.insight, l.confidence | 2 | 42ms |
| 2026-04-10T21:38:32Z | mcp | asgard_graph_query | MATCH (adj:Adjustment) WHERE adj.file_type = 'adjustment' RETURN adj.label, adj. | 1 | 6ms |
| 2026-04-10T21:38:33Z | mcp | asgard_graph_query | MATCH (m:Measurement) WHERE m.file_type = 'measurement' RETURN m.label, m.dream_ | 1 | 7ms |
| 2026-04-10T21:42:13Z | mcp | asgard_graph_query | MATCH (s:Scenario)-[:ENABLES]->(k:Knowledge) OPTIONAL MATCH (f:Feature)-[:SERVES | 13 | 22ms |
| 2026-04-10T21:42:20Z | mcp | asgard_graph_query | MATCH (p:Pain) WHERE p.severity = 'high' OPTIONAL MATCH (f:Feature)-[:ADDRESSES] | 8 | 17ms |
| 2026-04-10T21:42:29Z | mcp | asgard_graph_query | MATCH (i:Intent) WHERE i.recurrence_count >= 5 OPTIONAL MATCH (f:Feature) WHERE  | 7 | 11ms |
| 2026-04-10T21:42:35Z | mcp | asgard_graph_query | MATCH (l:Learning) WHERE l.confidence = 'confirmed' RETURN l.label, l.insight | 1 | 7ms |
| 2026-04-10T21:42:36Z | mcp | asgard_graph_query | MATCH (adj:Adjustment) WHERE adj.file_type = 'adjustment' RETURN adj.label, adj. | 1 | 7ms |
| 2026-04-10T21:45:04Z | mcp | asgard_graph_query | MATCH (sn:SpecNeed)-[:ADDRESSES_SCENARIO]->(sc:Scenario) OPTIONAL MATCH (sc)-[:E | 6 | 17ms |
| 2026-04-10T21:48:20Z | mcp | asgard_graph_query | MATCH (per:Persona)-[:SUFFERS]->(p:Pain) OPTIONAL MATCH (per)-[:EXPERIENCES]->(s | 11 | 36ms |
| 2026-04-11T03:32:15Z | mcp | asgard_graph_query | MATCH (ce:CouplingEvent) RETURN count(ce) AS coupling_events | 1 | 61ms |
| 2026-04-11T03:32:15Z | mcp | asgard_graph_query | MATCH (t:Trace) RETURN count(t) AS traces | 1 | 16ms |
| 2026-04-11T03:32:16Z | mcp | asgard_graph_query | MATCH (ap:ActionProposal) WHERE ap.status = 'proposed' RETURN ap.label, ap.perso | 2 | 14ms |
| 2026-04-11T03:32:49Z | mcp | asgard_graph_query | MATCH (n) RETURN labels(n) AS type, count(n) AS c ORDER BY c DESC | 37 | 26ms |
| 2026-04-11T03:32:49Z | mcp | asgard_graph_query | MATCH ()-[r]->() RETURN count(r) | 1 | 25ms |
| 2026-04-11T03:33:02Z | mcp | asgard_graph_query | MATCH (l:Learning) RETURN l.label, l.confidence, l.timestamp ORDER BY l.timestam | 4 | 17ms |
| 2026-04-11T03:33:02Z | mcp | asgard_graph_query | MATCH (adj:Adjustment) RETURN adj.label, adj.action, adj.timestamp ORDER BY adj. | 4 | 14ms |
| 2026-04-11T03:36:04Z | mcp | asgard_graph_query | MATCH (k:Knowledge)-[r:ROUTED_TO]->(pc:PersonContext) RETURN k.label, r.routed_a | 1 | 22ms |
| 2026-04-11T03:37:36Z | mcp | asgard_graph_schema | (schema request) | 116 | 60ms |
| 2026-04-11T03:53:58Z | mcp | asgard_graph_query | MATCH (s:Server) RETURN s.node_id, s.label, s.role | 2 | 22ms |
| 2026-04-11T03:58:31Z | mcp | asgard_graph_query | MATCH (n) WHERE n.person IS NOT NULL AND n.person <> '' AND NOT n.person IN ['Ba | 12 | 32ms |
| 2026-04-11T03:59:17Z | mcp | asgard_graph_query | MATCH (inv:Invariant) OPTIONAL MATCH (inv)<-[:UPHOLDS]-(d:Dream) OPTIONAL MATCH  | 0 | 23ms |
| 2026-04-11T03:59:24Z | mcp | asgard_graph_query | MATCH (inv:Invariant) RETURN inv.node_id, inv.label, inv.health, inv.last_checke | 12 | 12ms |
| 2026-04-11T03:59:34Z | mcp | asgard_graph_query | MATCH (inv:Invariant {node_id: 'invariant-1'}) SET inv.check_cypher = 'MATCH (ce | 1 | 10ms |
| 2026-04-11T03:59:37Z | mcp | asgard_graph_query | MATCH (inv:Invariant {node_id: 'invariant-12'}) SET inv.check_cypher = 'MATCH (n | 1 | 12ms |
| 2026-04-11T03:59:38Z | mcp | asgard_graph_query | MATCH (inv:Invariant {node_id: 'invariant-4'}) SET inv.check_cypher = 'MATCH (d: | 1 | 10ms |
| 2026-04-11T03:59:39Z | mcp | asgard_graph_query | MATCH (inv:Invariant {node_id: 'invariant-5'}) SET inv.check_cypher = 'MATCH (c: | 1 | 8ms |
| 2026-04-11T03:59:40Z | mcp | asgard_graph_query | MATCH (inv:Invariant {node_id: 'invariant-9'}) SET inv.check_cypher = 'MATCH (m: | 1 | 9ms |
| 2026-04-11T04:02:01Z | ask_asgard | ask | what do we know about rule builder logic? | 10 | 4874 |
| 2026-04-11T04:02:01Z | mcp | asgard_graph_ask | what do we know about rule builder logic? | 48 | 49ms |
| 2026-04-11T04:02:14Z | ask_asgard | ask | how does rule builder work? | 10 | 4746 |
| 2026-04-11T04:02:14Z | mcp | asgard_graph_ask | how does rule builder work? | 44 | 27ms |
| 2026-04-11T04:06:32Z | mcp | asgard_graph_query | MATCH (ps:PipelineStage) WHERE ps.uses_llm = true RETURN ps.label, ps.cost_usd O | 7 | 26ms |
| 2026-04-11T04:06:33Z | mcp | asgard_graph_query | MATCH (ps:PipelineStage) WHERE ps.uses_llm = false OR ps.uses_llm IS NULL RETURN | 7 | 10ms |
| 2026-04-11T04:06:33Z | mcp | asgard_graph_query | MATCH (cs:CouplingStep) RETURN cs.label ORDER BY cs.node_id | 5 | 8ms |
| 2026-04-11T04:08:51Z | mcp | asgard_graph_query | MERGE (hb:HeartbeatCycle {node_id: 'heartbeat'}) SET hb.label = 'Heartbeat: 30 m | 1 | 25ms |
| 2026-04-11T04:08:54Z | mcp | asgard_graph_query | MERGE (fb:FullBreath {node_id: 'full-breath'}) SET fb.label = 'Full Breath: 2x/d | 1 | 11ms |
| 2026-04-11T04:08:55Z | mcp | asgard_graph_query | MERGE (rt:RealtimeCoupling {node_id: 'realtime-coupling'}) SET rt.label = 'Real- | 1 | 20ms |
| 2026-04-11T04:09:04Z | mcp | asgard_graph_query | MATCH (m:Membrane {node_id: 'membrane-mcp'}) MATCH (rt:RealtimeCoupling {node_id | 1 | 26ms |
| 2026-04-11T04:09:05Z | mcp | asgard_graph_query | MATCH (hb:HeartbeatCycle {node_id: 'heartbeat'}) MATCH (al:AgencyLoop {node_id:  | 1 | 10ms |
| 2026-04-11T04:09:05Z | mcp | asgard_graph_query | MATCH (fb:FullBreath {node_id: 'full-breath'}) MATCH (pur:Purpose {active: true} | 1 | 10ms |
| 2026-04-11T04:15:40Z | mcp | asgard_graph_query | MATCH (n) WHERE n.file_type = 'rhythm' RETURN n.node_id, n.label, n.stages, n.fr | 3 | 34ms |
| 2026-04-11T04:16:34Z | mcp | asgard_graph_query | MATCH (ce:CouplingEvent) RETURN ce.person, ce.tool, ce.label, ce.timestamp ORDER | 0 | 12ms |
| 2026-04-11T04:17:15Z | Mycelium | asgard_graph_trace | testing structural coupling from this session | 1 | 17ms |
