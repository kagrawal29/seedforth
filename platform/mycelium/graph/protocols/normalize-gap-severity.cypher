// normalize-gap-severity.cypher
// Idempotent. Safe to re-run. Never deletes nodes or properties.
//
// Canonical schema:
//   severity       : String  {'critical','high','medium','low','info'}  -- source of truth
//   severity_score : Float   [0,1]                                      -- ordinal index
//
// Mapping (float -> string, score):
//   0.9 .. 1.0  -> critical  (0.95)
//   0.7 .. 0.89 -> high      (0.80)
//   0.5 .. 0.69 -> medium    (0.60)
//   0.3 .. 0.49 -> low       (0.40)
//   < 0.3       -> info      (0.20)
//
// String score back-fill:
//   critical -> 0.95
//   high     -> 0.80
//   medium   -> 0.60
//   low      -> 0.40
//   info     -> 0.20
//
// NULL / unknown ('?') -> medium / 0.5

// ── Step 1: numeric severity → canonical string + score ──────────────────────
MATCH (g:Gap)
WHERE g.severity IS NOT NULL
  AND NOT toString(g.severity) = g.severity   // numeric (float/int)
WITH g, toFloat(g.severity) AS v
SET g.severity_score = v,
    g.severity = CASE
      WHEN v >= 0.9  THEN 'critical'
      WHEN v >= 0.7  THEN 'high'
      WHEN v >= 0.5  THEN 'medium'
      WHEN v >= 0.3  THEN 'low'
      ELSE                'info'
    END;

// ── Step 2: string severity → back-fill score where missing ──────────────────
MATCH (g:Gap)
WHERE toString(g.severity) = g.severity
  AND g.severity IN ['critical','high','medium','low','info']
  AND g.severity_score IS NULL
SET g.severity_score = CASE g.severity
  WHEN 'critical' THEN 0.95
  WHEN 'high'     THEN 0.80
  WHEN 'medium'   THEN 0.60
  WHEN 'low'      THEN 0.40
  WHEN 'info'     THEN 0.20
END;

// ── Step 3: NULL / '?' / unrecognised → default medium ───────────────────────
MATCH (g:Gap)
WHERE g.severity IS NULL
   OR g.severity = '?'
   OR NOT g.severity IN ['critical','high','medium','low','info']
SET g.severity       = 'medium',
    g.severity_score = 0.5;
