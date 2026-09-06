# UX Test Harness — Persona Scripts

This directory contains TDD red tests for the three teammate personas defined in the v1.1 plan.

## Philosophy

These tests are intentionally RED (failing). They codify the exact UX promises in the plan before the implementation work begins. As each track lands, the corresponding test turns green.

## The Three Personas

### persona-reader.sh
The common case: query the team's shared knowledge without write access.

- No local setup beyond installing the maverick binary
- 7 steps from "receive Slack message" to "first successful query"
- Tests: binary install, querying maverick-dev, `maverick ask`, cross-target queries (maverick-prod)
- Success criteria: <5 minutes from Slack read to first successful query; zero Python/JDK/Docker required

### persona-contributor.sh
The minority: write Cypher locally and land it in maverick-dev.

- Docker Desktop prerequisite
- Includes local bootstrap, fork, edit, verify, commit, and PR workflow
- 21 steps from "clone repo" to "PR created"
- Tests: `maverick local bootstrap`, `maverick fork`, `maverick-dev test`, `maverick-dev verify`, `maverick-dev diff`, git workflow, GitHub PR creation, teardown
- Success criteria: <10 minutes from cloned repo to first PR-ready diff; Docker Desktop only prerequisite beyond Reader

### persona-maintainer.sh
Kshitiz + future ops. Keep the shared graph healthy, ship releases.

- SSH access to pulse-server
- Operations subcommands: rotation, smoke-tests, trace-analytics, guide-export-drift
- Release workflow: git tag, goreleaser
- 24 steps covering ops dashboards and service monitoring
- Tests: ops commands, query analytics from graph, health/doctor commands, service status on pulse
- Success criteria: all ops tasks are one command each; dashboards live in graph queries

## Running the Tests

### Current Status (RED)

All three tests will **fail** because the commands haven't been implemented yet. This is expected.

```bash
# Reader test (should fail at step 4-7)
bash test/ux/persona-reader.sh

# Contributor test (should fail at step 5-21)
bash test/ux/persona-contributor.sh

# Maintainer test (should fail at step 4-24)
bash test/ux/persona-maintainer.sh
```

Exit code will be 1 for failures (RED), 0 when all steps pass (GREEN).

### Turning Tests Green

Each red test guides implementation work. When the corresponding impl WI lands:

1. Reader test: turns green when Track A + B rebrand and binary install work
2. Contributor test: turns green when Track E (local bootstrap + fork) and Track G (sync + diff) are complete
3. Maintainer test: turns green when all ops commands (Track C + D) and service deployments (Track E) are done

### CI Integration

These scripts will be run in CI on every PR:

- **persona-reader.sh**: Runs on Ubuntu, macOS (arm64 + amd64), Windows (PowerShell) runners. Requires gh CLI auth.
- **persona-contributor.sh**: Requires Docker-in-Docker or Docker service on runner; skipped if unavailable.
- **persona-maintainer.sh**: Requires SSH key and pulse-server access; runs in private CI jobs only.

## Implementation Guidelines

When building impl WIs:

1. Keep step definitions in these scripts in sync with the plan (doc/plan-v1.1-maverick.md)
2. Each step is atomic — test exactly one feature or command
3. Do not combine steps (e.g., don't merge "repo clone" and "bootstrap" into one step)
4. Use `--help` checks to detect command existence before running the full flow
5. Capture actual errors in failed steps — the test output will guide debugging

## TDD Discipline

Per the plan (Track F):

- Test WI (wi-ux-01) lands FIRST
- Impl WI lands SECOND, turning the test green
- No squashing — history shows both commits

This ensures:
- Clear acceptance criteria from the start
- Reviewers can see the test → impl pairing
- Easy revert if implementation has issues
- No "implement first, figure out UX later"

---

Created: 2026-04-20  
Part of: v1.1 plan, Track F (UX test harness)  
Acceptance: All three scripts RED before Track A lands; all GREEN before v1.1.0 ships
