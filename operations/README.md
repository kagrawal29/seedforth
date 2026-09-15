# SeedForth Operations

Operational tooling must be explicit about whether it reads, proposes, or mutates state.

`reconcile.py` is currently read-only:

```bash
python3 operations/reconcile.py
python3 operations/reconcile.py --server root@185.192.96.100
python3 operations/reconcile.py --server root@185.192.96.100 --graph root@185.192.96.100
```

It inventories the repositories in `registry/repositories.json`, sanitizes Git remote URLs before reporting them, and optionally inspects declared server checkouts over SSH. It does not fetch, checkout, push, restart, move, delete, or write to the graph.

With `--graph`, it also reports non-secret Neo4j health facts through the server's Docker container.

## Controlled hardening installers

Kernel hardening scripts are run from approved release snapshots and never from mutable working trees:

```bash
python3 /opt/seedforth/current/operations/install-network-guard.py --revision <40-char-git-sha>
python3 /opt/seedforth/current/operations/install-agent-graph-guard.py --revision <40-char-git-sha>
```

Each installer verifies immutable payload integrity, network policy in the graph, installs systemd units/drop-ins, and writes an observation in graph history.
