# Protected worker service

`worker_service.py` is the external I/O entry point for the graph-governed broker.
It is not a planner, scheduler, grant writer, or source promoter. It accepts only
the worker operation allowlist and immutable deployment-selected adapters.

The service consumes exactly one Unix stream listener using the systemd
`LISTEN_PID`/`LISTEN_FDS` contract and descriptor 3. It verifies the endpoint and
listening state, clears activation variables and sets close-on-exec before any
adapter launches a process. Systemd retains the socket across broker restarts.
See the [upstream activation contract](https://github.com/systemd/systemd/blob/main/src/systemd/sd-daemon.h).

Deployment contract (Cajon pilot provisioned; broader lifecycle remains pending):

- A dedicated `seedforth-workers` group; only launcher-selected isolated workers
  receive the corresponding supplemental GID and a bind-mounted socket file.
  The host socket directory remains root-private. Never grant Docker or graph
  access to workers to make the socket reachable.
- External `worker-access.json` contains expiring per-worker token digests and
  exact scopes. It is loaded as a service credential, so rotation requires service
  restart; graph grant revocation remains authoritative on each operation.
- External `worker-bindings.json` contains only `repositories`, mapping canonical
  pilot/platform scope IDs to trusted absolute repository directories. No module,
  command, permission, mandate or budget is accepted in this I/O binding file.
  Repositories are private copies readable by the unprivileged `seedforth-broker`
  account through `seedforth-source-read`, and not writable by the broker or
  workers. Workers never receive this group or the legacy project directories.
- Author `principal-capability-broker` with only required settlement grants and
  promote `capability-git-inspection-v1` with the exact computed generation/cost/
  duration. Neither action is performed by service startup. Work needs separately
  authorized graph mandates, budgets, readiness and an isolated launcher.
- Provision the service/socket units explicitly after qualification. The existing
  control deployment adapter deliberately does not activate them automatically.

The initial pilot uses a one-hour credential/graph grant and two artifact action
units with no monetary spending. Provisioning does not enable the Cajon scope or
launch work. Refreshing expired authority is an explicit owner-delegated operation,
not automatic extension by a worker. The source copy is a shallow read-only bare
Git repository pinned to the reviewed base revision. The broker component has its
own `worker-current` link; changing it does not replace Delta or the human gateway.

Receipts persist in the service-private StateDirectory. Startup drains recoverable
receipts before accepting requests. Each dispatch also drains receipts under a
process lock; conflicting evidence denies new external actions. Recovery never
executes an adapter. Unknown effects without durable result evidence still need
capability-specific reconciliation; this service does not turn them into success.

Current immutable adapters are Git commit/tree inspection, explicitly covered
code snapshots, and bounded candidate code proposals. Source coverage is fixed
in the release. Proposal edits require a unique old-string match at the exact
base commit and produce untrusted artifacts, never repository writes or deployment.
Workers read only their own successful invocation artifacts, after graph grant
checks, exact location validation and content hash verification. Host paths are
not returned. Revocation denies subsequent reads; it cannot retract prior reads.

These primitives are not a substitute for product outcomes. Model capabilities,
monetary limits, independent verification, candidate application and production
worker launch remain required. Do not claim useful autonomy from service health.
