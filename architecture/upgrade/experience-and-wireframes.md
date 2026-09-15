# Human operating experience and wireframes

Status: proposed low-fidelity design. Covers U01–U16; no frontend implemented.

## Experience structure

The home screen answers what changed, what needs me, and what happens next.
The board is a working view within each project. A command/conversation panel
provides Charlie or Delta access without losing the currently inspected context.
The default view excludes archived products and compresses repetitive telemetry.

```text
SeedForth                                    Search    Account
Home | Flowing Indian | Cajon Sensei | Team             System [admin]

Since your last review                   Updated <time> / source health
  <accepted outcome>                     View evidence
  <artifact ready for review>             Review

Needs your direction                     <number of owned decisions>
  <decision>    why now / consequence     Inspect → approve / reject / defer

Moving                                   Next
  <work> / <agent> / <last meaningful step> <planned work and dependency>

Talk to: Charlie [alignment] | Delta [execution]
```

No fabricated product metrics populate the real UI. Empty, unverified, and stale
data have explicit presentation. Low-fidelity examples above are placeholders.

## Project and board

```text
Flowing Indian       Goal <version>       Direction / scope / budget
Overview | Board | Outcomes | Team | History

Ready            Working            Review             Done
<task card>      <task card>        <task card>         <accepted work>

Blocked / paused work: visible filter and attention count
Each card: outcome, owner, latest meaningful event, evidence age, next action
```

Internal proposed/ready states appear as backlog/ready filters; claimed and
in_progress map to Working with different detail. Blocked and paused are visible
conditions rather than silently hidden cards. Cancelled work remains in history.
Drag/drop sends a transition request with expected version; server decides whether
it is permitted. Moving to Done cannot bypass required verification or review.

## Work inspector

```text
<Task>                                     State / confidence / last verified
Serves: <goal> → <milestone>                 Owner: <agent or human>
Why this work | Plan and limits | Results | Attempts | History

Current attempt: <id>   Step: <step>   Budget: used / reserved / limit
  <time> accepted direction
  <time> task claimed and permission checked
  <time> artifact produced
  <time> verification result

Artifact / diff / preview     Acceptance criteria     Independent evidence
Pause task | Abort attempt | Reassign | Request changes | Review result
Advanced: tool receipts / source lineage / raw logs / terminal
```

Controls disclose target and consequence. Pausing an attempt differs from holding
a project or stopping its process. After click show requested, acknowledged,
applied or failed; explain already committed effects. Sensitive approval shows
destination, change, cost boundary, policy, and exact artifact version.

## Journey behavior

| Journey | Entry and completion |
|---|---|
| Daily return U01 | Home summary → inspect evidence → acknowledge review window |
| Direction U02 | Charlie discussion → versioned proposal → owner acceptance → affected plan |
| Delegate U03 | Delta discussion → bounded plan/mandate → accepted sprint ID |
| Long work U04 | Leave client → later reconnect → same sprint, events, and controls |
| Deep work U05 | Open artifacts and evidence → discuss alternatives → record chosen revision |
| Team U06/U10 | Inspect role/capability/cost → propose provisioning or retirement → verified receipt |
| Controls U07/U15 | Scoped request → policy/version check → reconcile work → final outcome |
| Review U08 | Inspect criteria and exact result → accept/reject → new decision/attempt |
| Teammates U09/U14 | Authenticate → discover authorized projects → read or converse within scope |
| Absence U11 | Time-window report → accepted outcomes, incidents, costs, decisions, next work |
| Failure U12 | Attention item → cause/effects/recovery owner → verified resolution |
| Explain U13 | Select a claim → source/time/transform/authority/evidence chain |
| Mobile U16 | Single-column attention/review flow → same version-bound action semantics |

## Attention management

Separate urgent action, pending decision, and informational updates. Each interrupt
has an owner, consequence, deadline if real, and a route to resolution. Group one
underlying incident rather than create one alert per failed retry. Users configure
digest cadence and escalation channels. Unacknowledged delivery remains visible.
Critical service alerts do not require a functioning LLM to send a prepared message.

## Proposed measurable targets

These are review targets, not current guarantees: mobile and keyboard operation;
home first useful render within 3 seconds p95 on the agreed test network; durable
request acceptance within 2 seconds p95 when healthy; event display within 5 seconds
p95 after graph commit. An execution pause acknowledgement target is 10 seconds
when connected; physical effect completion depends on action class and is explicit.

User evaluation tasks: identify the next decision, explain why a task is blocked,
find an artifact's evidence, and distinguish failed work from completed work without
opening logs. Record task success and confusion rather than rely on visual approval.

## Error and offline behavior

Loading shows unresolved state; zero is displayed only for a successful empty
query. Disconnected views retain last-known timestamps and disable unsafe controls.
Reconnection reads an event cursor or fresh snapshot. Version conflicts preserve
the user's intent and show changed context. Access loss removes cached sensitive
views and never falls back to a global graph search.

Scope filters apply before summaries and search. Shared URLs identify objects,
not credentials; recipients still authenticate. Raw content and terminal access
are separately authorized and redacted. Frontend cache is disposable and cannot
become an independent task authority.
