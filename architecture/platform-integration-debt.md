# Platform Integration Debt

**Status:** Active migration backlog  
**Last reviewed:** 2026-09-06

## Delta runtime migration debt

The imported Delta source contains a mixed state:

- `delta/agent_runner.py` describes opencode as the sole runtime.
- `delta/project_bridge.py` still exposes legacy tmux-named compatibility methods.
- `delta/app.py` and `delta/provisioner.py` retain legacy Claude/tmux references.
- Several operator documents and behavior specifications still describe tmux/Claude as current.
- The imported test tree includes legacy lifecycle assumptions and optional
  Discord/async dependencies that may not be installed in every local environment.

The runner contract has now been corrected in the platform copy. The obsolete
direct-DM-to-project and tmux/Claude restore suites are explicitly retained as
migration evidence and excluded from the active suite; current hub routing,
supervisor lifecycle, bridge delivery, registry, command, and envelope tests
are covered. The active Delta suite is green: 240 passed.

This is not a platform-repository import failure. It is evidence that the Delta migration to opencode was operationally completed before the code/test/documentation contract was fully normalized.

## Required resolution

1. Classify every remaining tmux/Claude reference as active, compatibility, historical, or dead.
2. Update the runtime contract to opencode-only where that is the actual supported state.
3. Rewrite or quarantine obsolete tests and operator documentation. The main
   obsolete test suites are now quarantined; replacement hub/runtime coverage
   must continue to grow as cutover proceeds.
4. Add tests for supervisor/opencode lifecycle, HTTP health, session expiry, and bridge delivery.
5. Run the complete active Delta suite from the imported platform path. This is
   now reproducible through `requirements-test.txt` and passes 240 tests.
6. Verify each new platform checkout against the live server before deployment.

## Mycelium import debt

The initial Mycelium working-tree snapshot is intentionally uncommitted because it contains:

- legacy Maverick/Pulse deployment assets;
- credential-related implementation and test files requiring review;
- embedded credential TOML and legacy credential/configuration paths;
- current graph/Charlie work that was uncommitted in the source checkout;
- historical and runtime artifacts that need classification.

The separate Mycelium repository remains preserved as provenance/reference;
the sanitized platform snapshot is the reviewed production source.

## Credential cleanup debt

The known exact Neo4j credential literal has been removed from active Delta
provisioning, bridge, tool, and heartbeat paths. Some imported local-development
helpers still mention the historical `localtest12` default, and those paths
must be converted to runtime environment configuration or moved under an
explicit historical boundary before public release. Test fixtures may retain
test-only credentials when they are isolated and clearly labeled.

## Cutover rule

Future platform releases may be deployed from the consolidated path only after:

- the source boundary is sanitized;
- tests pass or explicit failures are classified;
- server SHA and graph bootstrap version are recorded;
- rollback to the current `/opt/delta` deployment is tested.
