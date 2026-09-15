# Live writer and scheduler census: targeted update

Observed on delta2 (185.192.96.100) on 2026-09-06 around 16:40–16:46 UTC.
This is a partial operational census, not a claim of complete privilege isolation.
Only paths, hashes, field names and scheduling metadata were emitted. No credential
values, message bodies, browser cookies or raw environment values were copied.

## Root scheduling

The installed root crontab contained six active jobs. Other enumerated system cron
files were operating-system maintenance entries; no other user spool crontab file
was present in the inspected directory. This does not cover arbitrary in-process
application schedulers, user systemd units or container-internal schedules.

| Original schedule | Entrypoint | Disposition |
|---|---|---|
| Every five minutes | /opt/delta/tools/ingest-fleet-state.py | Retained; writer/source contract still needs migration |
| Minutes 0 and 30 | /opt/delta/tools/graph-runner.py --cadence heartbeat | Fenced duplicate; supported systemd heartbeat remains |
| Every four hours | /opt/delta/tools/graph-runner.py --cadence dream | Fenced pending governed replacement |
| Daily 03:00 server cron time | /opt/delta/deploy/heartbeat/run-deep-cycle.sh | Fenced forbidden legacy entrypoint |
| Sunday 04:00 server cron time | /opt/delta/deploy/heartbeat/run-long-cycle.sh | Fenced forbidden password-CLI entrypoint |
| Daily 02:30 server cron time | /opt/delta/tools/context-ingest.py | Retained; privacy/source contract still needs migration |

`/opt/delta` is a separate real directory, not the canonical release symlink.
The live long-cycle script contains cypher-shell password command-line handling.
The live deep-cycle script calls invariant, immune, fleet, graph-runner, steering
and metric tools; it is explicitly unsupported by the authored legacy boundary.
Both therefore contradicted the documented operational boundary before this fix.

Decision `decision-legacy-schedule-fence-20260906` authorizes four exact line hashes.
The applied transformation comments those lines, preserves every other byte and
stores private before/after images. It refuses changed configuration, missing or
duplicate targets, and blind reruns. Graph observation
`observation-legacy-schedule-fence-20260906` records verified readback.

- Before SHA-256: 39cb16e88c7383e3fd694fd1835f865c33dd2bed00c9b49e28512527d9e50dd0
- After SHA-256: 74f34aaffbfdf33203b430f426d71b72f2184eb04694a7b6065bec3aaa0b98f9
- Backup: /opt/seedforth/shared/backups/legacy-schedule-fence-94787ea6bafb45ebbda8acd5027dceb3/before.crontab

Restoration is not automatic: these paths are deliberately unsafe/unsupported.
Use the backup for inspection and recovery under a reviewed disposition. Do not
overwrite a subsequently changed crontab or re-enable legacy effects blindly.
This fence prevents future firing from these four entries, not all possible manual
calls, already-running processes, alternate schedulers or graph writers.

## Supported and retained service boundaries

The canonical heartbeat timer is enabled/active and its service reported exit 0
at inspection. Delta and heartbeat run as delta with the external seedforth.env.
Control and runtime sensing use DynamicUser and root-private LoadCredential files;
absence of a literal User line is not evidence that those DynamicUser services run
as root. The code sensor switches from a privileged collector to capability-free
project probes. The broker is the dedicated seedforth-broker account.

WhatsApp still runs `/opt/delta/tools/whatsapp_webhook.py` with `/opt/delta/delta.env`.
It is a retained customer transport and has not been migrated or stopped. Charlie
browser/Xvfb/noVNC services also remain. Installed old delta/kanban/cloudflared unit
files exist; file existence is not proof of an active service.

## Legacy application and agent authority

Source inspection of Delta's app identifies reporting, silence-nudge, general
schedule-fire, steering digest, resource management and startup restoration loops.
The schedule-fire loop reads per-project schedule.json and writes/nudges inboxes;
it does not enforce the new ControlScope holds or bounded broker mandates. These
loops still require runtime task inventory and a governed cutover.

All eight observed old opencode processes (Cajon, Flowing, hub, ethos, two LinkedIn
agents, seedforthing and zuuro) had environment keys for GitHub, OpenRouter, Rube,
Composio, Unipile and Vercel credentials. Values were not exposed or tested against
providers. Key presence establishes credential distribution, not provider validity
or appropriate scopes. These are not the new isolated Docker pilot executor.

Therefore the new broker's isolation does not establish system-wide isolation.
Provider revocation/rotation, old credential-bearing files, shared browser access,
Neo4j writer fencing and retained account obligations remain material security work.

## Listening surfaces observed

Neo4j 7474/7687 was bound to all IPv4/IPv6 interfaces. Other wildcard listeners
included WhatsApp's 8900, noVNC 6083, printing 631 and an IPv6 VNC 5900 listener.
This is host bind evidence, not proof that each port is Internet-reachable through
every firewall. Control 8787, opencode ports, WAHA 3000 and the disposable graph
27474 were loopback-bound. Remote exposure hardening remains required before public
MCP/team access; public OAuth/MCP is not yet implemented.

## Qualification and next gates

Immutable release f81e8498dd1162917a9b086c1368b1ff359e9d6f passed 111 tests in
16.34s, including exact configuration transformation, graph-scoped recording,
idempotence and collision refusal. Production readback confirmed four fenced
schedules and retained service liveness. No UI was changed in this operation.

Next: inventory actual project schedule records and credential readers, migrate
the application dispatch boundary without dropping customer messages, close unsafe
public exposure, implement scoped remote MCP, and replace held cadences with
verified governed work. Fencing is a migration safety step, not the requested
autonomous end state.
