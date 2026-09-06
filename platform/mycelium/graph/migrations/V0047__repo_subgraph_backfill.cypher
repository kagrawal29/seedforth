// V0047 — Repo subgraph backfill (M1 of pipeline spine)
// Sets n.repo on all nodes derived from source/subgraph conventions.
// Idempotent: re-runs are safe (overwrites to same value).
// Buckets: vc-ai-associate (21,954), maverick-dev (6,294), maverick-dev-friend (28).

MATCH (n)
WITH n,
  CASE
    WHEN n.subgraph = 'maverick-dev-friend'            THEN 'maverick-dev-friend'
    WHEN n.source STARTS WITH 'vc-ai-assoicate:'       THEN 'vc-ai-associate'
    WHEN n.source STARTS WITH 'storybook:'             THEN 'vc-ai-associate'
    WHEN n.source STARTS WITH 'schema:'                THEN 'vc-ai-associate'
    WHEN n.source IN [
      'parse_ts_repo','parse_sql_functions','parse_storybook',
      'parse_api_endpoints','parse_permission_model','parse_package_json'
    ]                                                  THEN 'vc-ai-associate'
    WHEN n.source IN [
      'parse_specs','parse_tasks','parse_spec_markers','parse_spec_artifacts',
      'parse_skills','parse_claude_agents','parse_env_vars','parse_hooks',
      'parse_decisions','scripts/run_tests.py'
    ]                                                  THEN 'maverick-dev'
    ELSE null
  END AS repo
WHERE repo IS NOT NULL AND (n.repo IS NULL OR n.repo <> repo)
SET n.repo = repo
RETURN repo AS bucket, count(*) AS updated ORDER BY updated DESC;

CREATE INDEX node_repo_idx IF NOT EXISTS FOR (n:Searchable) ON (n.repo);
