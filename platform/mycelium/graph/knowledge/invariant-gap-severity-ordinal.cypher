// invariant-gap-severity-ordinal.cypher
// Declares: every :Gap has severity in {'critical','high','medium','low','info'}
//           AND severity_score in [0,1]
//
// Merge idempotent -- re-running is safe.

MERGE (inv:Invariant {id: 'gap-severity-ordinal'})
SET
  inv.name         = 'Gap severity is ordinal string + bounded score',
  inv.description  = 'Every :Gap node must have severity ∈ {critical,high,medium,low,info} and severity_score ∈ [0,1]. Numeric or NULL severity values are schema violations.',
  inv.severity     = 'critical',

  // Check query: returns violating Gap ids (empty = passing)
  inv.check_cypher = '
    MATCH (g:Gap)
    WHERE g.severity IS NULL
       OR NOT g.severity IN [\'critical\',\'high\',\'medium\',\'low\',\'info\']
       OR g.severity_score IS NULL
       OR g.severity_score < 0
       OR g.severity_score > 1
    RETURN g.id AS violation, g.severity AS bad_severity, g.severity_score AS bad_score
  ',

  // Heal: run the normalisation protocol
  inv.heal_protocol  = 'normalize-gap-severity',
  inv.heal_cypher    = '
    // Step 1: numeric -> string + score
    MATCH (g:Gap)
    WHERE g.severity IS NOT NULL
      AND NOT toString(g.severity) = g.severity
    WITH g, toFloat(g.severity) AS v
    SET g.severity_score = v,
        g.severity = CASE
          WHEN v >= 0.9 THEN \'critical\'
          WHEN v >= 0.7 THEN \'high\'
          WHEN v >= 0.5 THEN \'medium\'
          WHEN v >= 0.3 THEN \'low\'
          ELSE               \'info\'
        END;

    // Step 2: string -> back-fill score
    MATCH (g:Gap)
    WHERE toString(g.severity) = g.severity
      AND g.severity IN [\'critical\',\'high\',\'medium\',\'low\',\'info\']
      AND g.severity_score IS NULL
    SET g.severity_score = CASE g.severity
      WHEN \'critical\' THEN 0.95
      WHEN \'high\'     THEN 0.80
      WHEN \'medium\'   THEN 0.60
      WHEN \'low\'      THEN 0.40
      WHEN \'info\'     THEN 0.20
    END;

    // Step 3: NULL / unknown -> medium
    MATCH (g:Gap)
    WHERE g.severity IS NULL
       OR g.severity = \'?\'
       OR NOT g.severity IN [\'critical\',\'high\',\'medium\',\'low\',\'info\']
    SET g.severity       = \'medium\',
        g.severity_score = 0.5;
  ',

  inv.created_at   = datetime(),
  inv.updated_at   = datetime(),
  inv.status       = 'active';
