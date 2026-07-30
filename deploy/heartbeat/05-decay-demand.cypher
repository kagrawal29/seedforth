// Flag knowledge no one is asking about
MATCH (k:Knowledge)
WHERE k.decay_protected IS NULL OR k.decay_protected = false
OPTIONAL MATCH (k)<-[:TOUCHES]-()
WITH k, count(*) as touches
WHERE touches = 0
SET k.decay_flagged = true;
