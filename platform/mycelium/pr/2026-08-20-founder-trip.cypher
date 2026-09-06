// Charlie founder trip — graph-native scheduling (2026-08-20)
// The behavior (what Charlie does) is in protocol-charlie-founder + atoms.
// This ExternalAtom is the I/O shell (trigger the LLM + send WhatsApp report).
// The deep-cycle cron fires this protocol once a day.

MERGE (e:ExternalAtom {node_id: 'atom-external-charlie-founder-trip'})
SET e.script = '/opt/delta/tools/founder-trip.py',
    e.semantic = 'Charlie founder trip: run the founder loop for the projects he drives and report the status update to the team over WhatsApp';

MERGE (pr:Protocol {node_id: 'protocol-charlie-founder-trip'})
SET pr.label = 'Charlie Founder Trip', pr.cadence = 'deep', pr.enabled = true;

MATCH (pr:Protocol {node_id: 'protocol-charlie-founder-trip'})
MATCH (e:ExternalAtom {node_id: 'atom-external-charlie-founder-trip'})
MERGE (pr)-[:FIRST_ATOM]->(e);

MATCH (c:Being {node_id: 'being-charlie'})
MATCH (pr:Protocol {node_id: 'protocol-charlie-founder-trip'})
MERGE (c)-[:HAS_PROTOCOL]->(pr);
