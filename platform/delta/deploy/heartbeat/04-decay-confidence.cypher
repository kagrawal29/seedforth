// Downgrade single-source knowledge
MATCH (k:Knowledge)
WHERE k.decay_protected IS NULL OR k.decay_protected = false
OPTIONAL MATCH (k)<-[:PRODUCES]-()
WITH k, count(*) as sources
WHERE sources = 1 AND k.confidence = "high"
SET k.confidence = "medium";
