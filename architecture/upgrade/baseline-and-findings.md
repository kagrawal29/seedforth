# Live delta2 baseline and findings

Status: partial read-only baseline. Observed 2026-09-06, 13:49:05–13:49:55 UTC.
Parent: [upgrade plan](../seedforth-upgrade-plan.md).

## Target and method

SSH target: root@185.192.96.100. Hostname: vmi3556896.
Release: /opt/seedforth/releases/1770e7c.
Git SHA: 1770e7cdc085e36840ed5b2d5b116811348a5ae0.
Database: neo4j through 127.0.0.1:7474 on delta2.
Database ID: CFA30D60071ABB16E9E586681C9531E4CDBDD972E1586DAE4B32E817C47D1E99.
Container: mycelium-neo4j, image neo4j:5.26-community, reported up 30 hours.

Inspected deployed neo4j_helper.py before using q_strict for explicit read queries.
This helper raises database errors and does not write query traces. Its q/ql
alternatives return empty results on errors, a potential ambiguity to inspect in
callers. Authentication was loaded remotely from the existing environment without
printing secrets. Existing access is privileged: read-only describes operations
performed, not enforcement by a database read-only account.

## Runtime

Delta service and heartbeat timer are active. Heartbeat service runs as delta:

```text
/usr/bin/python3 /opt/seedforth/current/platform/delta/tools/graph-runner.py --cadence heartbeat
```

Service Result=success. Timer OnUnitActiveUSec=1min, OnBootUSec=2min. This differs
from historical 30-minute documentation. Other cron/user schedules remain to be
inspected; overlapping execution is not yet established.

Supervisor reports eight running agents: cajon-sensei, delta-hub, ethos,
flowing-indian, linkedin-himanshu-ghiya, linkedin-kshitiz-agarwal, seedforthing,
and zuuro. WAHA container is up 26 hours. These facts establish process presence,
not useful autonomous work or successful external delivery.

## Findings and audit implications

| ID | Observed evidence | Interpretation |
|---|---|---|
| B01 | project-flowing-indian is hibernated/stalled; project-cajon-sensei is hibernated/dormant | A02 mismatch with running processes and intended portfolio confirmed; writer untraced |
| B02 | 47 Project nodes; project-cajon-sensei and proj-cajon-sensei-eco have no direct Project neighbor | A01 multiple identity populations remain; equivalence of the eco record unverified |
| B03 | 10 uniqueness constraints, including WorkItem, Workstream, AgentProcess, ExecutionSession, Signal, ActivityLog, CodeChange | A11 old count of three no longer applies; complete schema coverage unverified |
| B04 | 8 AgentProcess nodes | Foundation has added runtime representation; relationships not yet verified |
| B05 | ExecutionSession, Signal, ActivityLog, CodeChange, TestRun each have zero nodes | A03/A10 evidence gaps remain; absence does not prove no external work happened |
| B06 | Four of six WorkItems with project=flowing-indian have ASSIGNED_TO edges to division agents | A04 historical no-assignment finding needs narrowing |
| B07 | Those six work items have only four adjacent edges total; products and bunny tasks have no edges | No parent milestone/workstream or execution evidence edges in this exact population |
| B08 | Fresh heartbeat ProtocolRuns around 13:49:43 UTC | Scheduled graph activity exists; postcondition success not established |
| B09 | No direct relationship of any type between ProtocolRun and CypherAtom | A07 atom attribution gap confirmed for this pattern |
| B10 | q/ql helper returns [] on query errors, while q_strict raises | Consumers may confuse failed reads with empty data; caller impact pending |

No WorkItem matched project=cajon-sensei. This narrow property filter does not
establish absence of work under other identifiers or labels.

Snapshot counts: ProtocolRun=25,948; WorkItem=78; Project=47; Protocol=33;
CypherAtom=55; ProgressEvent=217; QueryTrace=215; TestCase=19. Label counts are not
a total node count. Protocol inventory returned 32 enabled and one enabled unset.

Latest timestamps grouped by ProtocolRun.protocol:

| Group | Latest observed run |
|---|---|
| Core heartbeat, activity sync, Charlie focus | 2026-09-06 around 13:49:43 UTC |
| Flowing Indian revenue/research/operations | 2026-09-06 around 10:00:04 UTC |
| Dream/immune/health/fatal checks | 2026-09-06 around 10:00:03 UTC |
| Direction/lifecycle/progress score | 2026-09-06 around 01:00 UTC |
| Charlie founder trip | 2026-09-05 03:00:44 UTC |
| Charlie founder | 2026-08-21 03:00:03 UTC |
| Fleet-ingest protocol | 2026-08-02 07:13:26 UTC |

No grouped run rows appeared for protocol-run-tests or protocol-sys-health-verify.
Direct ingestion may operate outside these protocol records; an old fleet protocol
timestamp is not proof of failed fleet ingestion. Protocol.last_run and
last_run_status were null in queried records despite fresh ProtocolRun evidence.

## Key reproducible queries

```cypher
CALL db.info() YIELD name, id RETURN name, id;
SHOW CONSTRAINTS YIELD name,type,labelsOrTypes,properties
RETURN name,type,labelsOrTypes,properties;
MATCH (p:Project)
RETURN p.node_id,p.name,p.status,p.lifecycle_state,p.updated_at ORDER BY p.node_id;
MATCH (r:ProtocolRun)
RETURN r.protocol,count(*),max(r.timestamp) ORDER BY max(r.timestamp) DESC;
MATCH (w:WorkItem {project:'flowing-indian'}) OPTIONAL MATCH (w)-[r]-(n)
RETURN w.node_id,type(r),labels(n),n.node_id LIMIT 45;
MATCH (r:ProtocolRun)-[e]-(a:CypherAtom) RETURN type(e),count(*);
UNWIND ['ExecutionSession','AgentProcess','Signal','ActivityLog','CodeChange','TestRun'] AS label
OPTIONAL MATCH (n) WHERE label IN labels(n) RETURN label,count(n);
```

## Next investigation

1. Inspect graph-runner, all actual schedulers, lifecycle/focus atoms, and identify
   precisely which mechanism updates pilot project status.
2. Trace one Flowing Indian division trigger through ExternalAtom and worker to
   existing results and ProgressEvent without executing work.
3. Check AgentProcess relationships and actual fleet observation freshness.
4. Inspect test timestamps, invariant checks, and repair postconditions read-only.
5. Inventory Graphify artifacts and expand writer/signal coverage.

No graph mutations, restarts, archival, or runtime file edits were performed.
This is the start of Phase 0, not a completed system baseline.

## Agent usefulness investigation — 13:52–13:54 UTC

User concern: running agents do not appear to produce useful work. Inspect
actual outputs and execution rather than infer autonomy from process liveness.

### B11 — all recorded Flowing Indian division runs failed

Each of revenue, research, and operations has ten ProtocolRun records between
2026-09-04 20:00 UTC and 2026-09-06 10:00 UTC. Each has atoms_ok=0 and
atoms_total=1: thirty recorded failed runs, zero successful ones.

Live ExternalAtom.script contains the following command form:

```text
/opt/delta/tools/division-worker.py --project flowing-indian --division revenue
```

The deployed runner's run_atom passes ['python3', atom['script']] to subprocess.
Thus Python treats the entire path-plus-arguments string as its script filename.
The actual /var/log/mycelium-dream.log confirms the resulting cannot-open-file
error for all three divisions. This establishes an execution contract mismatch,
not just a hypothesis inferred from failed counters.

The worker exists under /opt/delta/tools but not at the consolidated release's
platform/delta/tools/division-worker.py. Graph-resident external behavior still
depends on legacy-path source outside that release. Inventory this as release
lineage debt before changing any invocation.

### B12 — process availability is not a work loop

All eight supervisor commands launch opencode serve with a project port. These
are persistent request-serving processes. Their RUNNING status cannot establish
work selection, active model execution, or output. Other callers and schedules
remain to be inventoried before classifying each agent as idle or productive.

No Protocol.node_id containing cajon was found. This does not exclude generic
schedulers or direct user requests; it means no specifically named Cajon protocol
was found by this query.

### B13 — recent sampled commits mostly contain operational bookkeeping

Read Git as the project Linux users to preserve ownership protections.
Flowing Indian main's three latest commits (all September 4):
54ced2f changes AGENTS.md; 049d13d and 62a81df change opencode-stdout.log.
Cajon Sensei's two latest commits (September 4), 2a518d9 and bcb5a88, change
opencode-stdout.log; its preceding commit is labeled hibernate.

These sampled commits are not demonstrated product delivery. Inspection has not
yet covered all branches, uncommitted artifacts, conversations, or external APIs.

There is one concrete Flowing Indian product-code artifact: rope-sale worktree
commit faf9c5b02a37620a9495702a7b71a94a134ea2a5 from September 4 18:35:58 UTC,
"Add Rope Flow Bundle to product offerings", changes lib/products.ts (+38/-1).
It is on feature/rope-sale-launch. Review, merge, deployment, and commercial
effect are not established. Commit authorship alone does not prove which autonomous
or human-triggered path produced it.

### B14 — failure is represented as positive-weight progress

The eight Flowing Indian ProgressEvents include five type=blocked events, each
weight=1, one type=commit event weight=1 referring to the bundle artifact, and two
AGENTS.md artifact events weight=0.4. Latest event is September 5 10:55:54 UTC:
revenue loop produced no commit. Cajon's twenty ProgressEvents have latest
created_at August 13 03:41:16 UTC.

The legacy worker records blocked outcomes with default weight=1. It exits zero
after a nonempty agent response that produces no new commit. The graph runner
uses process exit code for ExternalAtom success, continues after atom failures,
and does not set a nonzero final exit code for failed protocols. Its record_run
stores total/ok counts but omits error details and atom identities.

Implications: scheduler success, protocol success, progress weight, accepted
artifact, and business value must be separate. Downstream use of blocked event
weights has not yet been traced; inflated scores are a risk, not a verified result.

### B15 — worker isolation and credential concerns

Source inspection shows a hard-coded database credential in the legacy worker;
its value is deliberately not recorded here. Validity and exposure scope require
a dedicated credential inventory. The worker also writes session_id into the
shared project registry, chooses the first matching workstream without an active
status filter, and relies on prompt instructions to use a worktree. It has no
WorkItem claim or current execution receipt model in the inspected code.

The runner timeout is 120 seconds while worker model-request timeout is 300
seconds. This mismatch could interrupt working calls once launch is repaired.
Do not simply fix argument splitting and enable previously failing autonomous
effects before scope, credentials, permissions, and bounded execution are reviewed.

### B16 — partial lifecycle/focus lineage

Live lifecycle atoms update lifecycle_state based on FleetProgress.producing.
The active-to-stalled atom's explanation claims seven days without progress, but
the atom itself tests producing without a freshness window. Freshness may be
upstream; that dependency remains to be traced. Another atom marks active goals
done when their project lifecycle_state is complete, without independent outcome
verification in that atom.

Charlie focus maps DirectionScore labels to generic strings such as "unstall and
move ... forward". This is a focus summary, not an executable accepted work plan.
These inspected atoms do not explain the separate Project.status=hibernated field;
the writer of that property remains unresolved.

### Revised next work

1. Inventory triggers and recent outputs for the remaining six agent processes.
2. Trace Project.status writers and FleetProgress/progress scoring consumers.
3. Inspect worker/session delivery and existing message/tool metadata without
   submitting prompts or exposing raw private conversations or credentials.
4. Verify the bundle artifact's review/deployment state if evidence is available.
5. Map B11–B16 to execution, evidence, sensing, security, and migration contracts.

No execution fixes or live mutations were performed. Current evidence supports
broken Flowing Indian scheduled work and weak proof of broader useful autonomy;
it does not support claiming that all agents have never done useful work.

## Deployed lifecycle writer inspection — 13:57:51 UTC

B17: inspected /opt/seedforth/current/platform/delta/delta/provisioner.py and
resource_manager.py on delta2. hibernate() saves Git state, stops the serving
process/watchers, sets registry status, and directly writes Project.status=
hibernated on project-{name}. Its graph-write exception is swallowed.

restore() starts the serving process, changes registry status to active, and emits
a restored project event. It contains no corresponding direct update of
Project.status in the inspected function. A separate event consumer could reconcile
it, so this asymmetry is an identified path to investigate, not proof of the exact
historical cause of both pilots' current status.

resource_manager_loop checks every 60 seconds by default, hibernating a bridge
idle for ten minutes with no pending work as defined by that bridge. The deployed
app.py schedules this loop at line 2732. Whether its pending-work check includes
the complete graph work population remains unverified. This is a concrete competing
controller that the upgrade must reconcile with persistent autonomous mandates.

Local architecture inspection also found that graph-model.md,
control-and-observability.md, and agent-lifecycle.md named in the old platform plan
do not exist at those architecture paths. The new review package supplies proposed
contracts; absent files were not treated as implemented design.
