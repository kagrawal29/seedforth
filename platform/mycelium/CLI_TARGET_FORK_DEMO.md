# CLI v2-09: Target & Fork Feature Demo

## Example 1: Query prod target without modifying it

```bash
$ ./mycelium --target prod ask "what is system health"

  System health check:
  - nodes: 12,341
  - edges: 141,203
  - invariants: 32/32 passing
  - autonomous_score: 100
  - last_heartbeat: 2026-04-18T16:32:15Z
```

This works because `ask` is a read-only command, and prod is marked read-only in config.

## Example 2: Try to bootstrap on prod (rejected)

```bash
$ ./mycelium --target prod bootstrap

error: target 'prod' is read-only. Use --target local for writes, or `mycelium fork dev` to get a writable copy.
Exit code: 2
```

Mutating commands (bootstrap, start, stop, dump, restore, shell) are gated on read-only targets.

## Example 3: Fork dev to local (interactive)

```bash
$ ./mycelium fork dev

Forking from dev target to local
Exporting from dev...
✓ exported to /Users/kshitiz/.mycelium/forks/dev-20260418-163245.cypher

This will WIPE the local Neo4j and import dev.
Continue? (y/N): y

Wiping local...
Importing from fork file...
Resyncing Protocols...
✓ fork complete
```

The fork command:
1. Exports all data from dev (bolt://5.78.206.137:7698, read-only proxy)
2. Asks for confirmation
3. Deletes all nodes from local
4. Imports the export
5. Resyncs Protocol nodes via decompose_protocols.py

## Example 4: Try to fork prod (rejected)

```bash
$ ./mycelium fork prod

error: only 'dev' is forkable; 'prod' is not
Exit code: 2
```

Only dev is forkable. Prod is a true read-only production replica and should never be forked locally.

## Example 5: Using env var instead of flag

```bash
$ export MYCELIUM_TARGET=dev
$ ./mycelium ask "what claim tests are failing"

Results from dev target...
```

The --target flag takes precedence, but env var allows scripts to set the target globally.

## Configuration Files

### ~/.mycelium/config.toml (from .mycelium/config.toml.example)

```toml
[targets.local]
bolt = "bolt://localhost:7687"
user = "neo4j"
mode = "rw"

[targets.dev]
bolt = "bolt://5.78.206.137:7698"
user = "team"
mode = "ro"

[targets.prod]
bolt = "bolt://5.78.206.137:7699"
user = "team"
mode = "ro"
```

### ~/.mycelium/secrets.env (from .mycelium/secrets.env.example)

```bash
MYCELIUM_PROD_PASS="your-prod-password-here"
MYCELIUM_DEV_PASS="your-dev-password-here"
```

Permissions must be 0600 for security.

## Test Results

```
Running CLI target/fork tests
==============================
config.toml loading... PASS
MYCELIUM_TARGET env var works... PASS
fork prod rejected... PASS
target mode assignment... PASS
read commands allowed on ro... PASS
secrets.env sourcing... PASS
unknown target error... PASS
bootstrap gated on ro target... PASS
dump gated on ro target... PASS

Results: 9 passed, 0 failed
```
