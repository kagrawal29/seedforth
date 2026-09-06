# Mycelium legacy boundary

The active SeedForth graph program is `platform/delta/tools/graph-runner.py`
executed by `seedforth-mycelium-heartbeat.service`. The following imported
areas are not active server entrypoints:

- `graph/runner/` — pre-consolidation shell/Python runner family;
- `install.sh`, `install-deps.sh`, and `setup-team.sh` — historical workstation
  installers;
- `agents/`, `services/`, and `scripts/` utilities that target old local/dev
  graph layouts unless explicitly invoked with runtime credentials;
- `archive/` — historical implementation material.

These files remain for provenance and migration reference. They must not be
installed as services or invoked by production timers. New graph behavior is
authored as graph-resident `Protocol`/`CypherAtom` state and executed by the
platform runner; external scripts are limited to I/O adapters.
