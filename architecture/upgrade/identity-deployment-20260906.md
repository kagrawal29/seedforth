# Private identity deployment and security gate

The identity runtime is live at127.0.0.1:8788 on delta2. Source:
8dd42c0b3b915dd8101e611fcb974842f2617983. The separate root operator client is
d6bf2f82034338a5829d5e12405a1f256dfba7dc. Main/control/worker/security component
pointers are unchanged. New public HTTP application routes still return503.

## Verified deployment

- seedforth-identity.service runs as seedforth-identity UID997/GID984, not root.
  State directory0700, database0600 and operator socket0600. Runtime/state directory
  lifecycle is owned by systemd. Dependencies live in shared/identity-venv, separate
  from Delta. Loaded graph credentials are not exported as password values.
- Reviewed DeploymentPolicy binds the issuer/resource and three existing scopes,
  loopback8788 and closed public ingress. The reviewed identity-scope reader was
  promoted. Runtime validates that envelope and fails closed if it is changed.
- Actual login GET with expected Host returned200 and protected cookie flags;
  foreign Host returned421. A real socket connection from the service UID was
  rejected with root_operator_required. Root invitation and backup operations worked.
- Initial invitation preflight refused shared/env, which is750 root:delta. No
  invitation was created by that attempt. Its permissions were preserved. Root
  delivery now uses shared/identity-operator0700 with new0600 files only.
- Owner invitation saved privately at
  /opt/seedforth/shared/identity-operator/human-invitation-owner-20260906.json.
  Its value was never printed. Exact digest lookup confirmed it remained valid
  after restarts. It expires24hours after issuance. No human account, passphrase
  or authenticator was enrolled in production.
- Normal service restart and forced SIGKILL recovery both returned to healthy
  login responses. NRestarts=1 after the crash drill. Socket cleanup/recreation and
  persistent invitation state were verified. This is process recovery, not a VM
  reboot, network outage, or unattended-month test.
- Online SQLite snapshots passed integrity checks. Latest root-private retained
  copy: /opt/seedforth/shared/backups/identity-fe5202c0421a458bb45287c496a61f92.sqlite,
  SHA25663c03c5efff42e4367ef682126a40a3081eea44173047a406f9f44df280e28a4.
  Restore tests proved the resurrection risk and verified mandatory invalidation
  of restored OAuth families, sessions, recovery codes, invites and logins while
  preserving identity mappings for operator re-enrollment. Full operational restore
  tooling, off-host backup and recurring backup/identity sensing remain required.
- Runtime source passed144 tests. Latest operator-source full qualification passed
  145 in29.02s, no skips, one SDK deprecation warning. JUnit hash
  0f36e1363996bf2032fc1daf7fa6a71afd8702ac41574998d38e3bfdb287eecc
  is admitted in live Mycelium. The human UI is unchanged from its exact-source
  Playwright qualification; this deployment added no new human interface.

## Confirmed legacy graph credential exposure

A read-only comparison against the current protected graph credential found that
exact value in12 legacy Python tools under /opt/delta/tools. No value or password
fingerprint was emitted or recorded. The matched paths are neo4j_helper.py,
seed-fleet-graph.py, kanban-server.py, division-worker.py, graph-tool.py, nl-query.py,
ingest-fleet-state.py, run-invariants.py, fix-invariants.py, whatsapp_webhook.py,
founder-trip.py and graph-ui/server.py. All were644 except founder-trip.py755.

Actual read checks under proj-cajon-sensei UID1003 and proj-flowing-indian UID1005
both succeeded for neo4j_helper.py. This is stronger evidence than mode inspection
alone. Selected canonical platform roots contained no literal match in the scanned
file types. Initial /proc environments showed the current credential in the Delta
UID1001 process and Neo4j container startup environments. This is a targeted census,
not proof that other files, inherited memory or credential copies are absent.

Do not publish scoped team access on top of this unqualified legacy writer boundary.
Next work must inventory/migrate retained transport and ingest consumers, fence
credential-bearing legacy model workers and schedulers, rotate graph credentials
without dropping incoming messages, and verify that project agents cannot recover
the replacement credential or directly mutate graph authority. Provider credentials
and shared browser access need their own fencing/rotation; graph-password rotation
alone is not complete isolation. Then enable and qualify narrow public routing and
continue the board, governed Delta processor and the full upgrade scope.
