# Platform Integration Debt

**Status:** Active migration backlog  
**Last reviewed:** 2026-09-06

## Delta runtime migration debt

The imported Delta source contains a mixed state:

- `delta/agent_runner.py` describes opencode as the sole runtime.
- `delta/project_bridge.py` still exposes legacy tmux-named compatibility methods.
- `delta/app.py` and `delta/provisioner.py` retain legacy Claude/tmux references.
- Several operator documents and behavior specifications still describe tmux/Claude as current.
- The test suite currently fails during collection because `test_agent_runner.py` imports the removed `ClaudeCodeRunner`.

The runner contract has now been corrected in the platform copy and 44 focused registry/runner/router/command tests pass. Full collection still stops on four legacy or undeclared dependency modules, so the platform test gate remains open.

This is not a platform-repository import failure. It is evidence that the Delta migration to opencode was operationally completed before the code/test/documentation contract was fully normalized.

## Required resolution

1. Classify every remaining tmux/Claude reference as active, compatibility, historical, or dead.
2. Update the runtime contract to opencode-only where that is the actual supported state.
3. Rewrite or quarantine obsolete tests and operator documentation.
4. Add tests for supervisor/opencode lifecycle, HTTP health, session expiry, and bridge delivery.
5. Run the complete Delta suite from the imported platform path.
6. Verify the new platform checkout against the live server before deployment.

## Mycelium import debt

The initial Mycelium working-tree snapshot is intentionally uncommitted because it contains:

- legacy Maverick/Pulse deployment assets;
- credential-related implementation and test files requiring review;
- embedded credential TOML and legacy credential/configuration paths;
- current graph/Charlie work that was uncommitted in the source checkout;
- historical and runtime artifacts that need classification.

The separate Mycelium repository remains the source/reference checkout until the snapshot is classified and a safe import boundary is committed.

## Cutover rule

Neither platform component may be deployed from the consolidated path until:

- the source boundary is sanitized;
- tests pass or explicit failures are classified;
- server SHA and graph bootstrap version are recorded;
- rollback to the current `/opt/delta` deployment is tested.
