# Access, authority, and threat model

Status: proposed design; security controls not yet implemented or verified.
Covers A05, A14, S05–S07, S09–S10, U07–U10, U14.

## Trust boundaries

Boundaries: human/client → gateway; gateway → graph projection; request → Delta;
Delta → project agent; agent → capability broker; broker → credentials/provider;
authored source → active policy/atom; provider content → knowledge/context.
Every boundary authenticates its peer and validates scope. Model interpretation
cannot grant authority, supply a trusted principal ID, or count as human approval.

Runtime privilege and conversational authority are separate. Delta may coordinate
platform-wide operations but executes a teammate request with that teammate's
effective scope. Standing autonomous mandates are separately issued authorities.
Cross-project work needs an explicit grant for each affected scope and bridge.

## Proposed role matrix

| Operation | Admin | Project lead | Project member | Project executor |
|---|---|---|---|---|
| Read graph/project evidence | All granted scopes | Own scopes | Own scopes | Assigned scopes and inputs |
| Talk to Delta/Charlie | Yes | Scoped | Scoped | Delegation channel |
| Propose direction/work | Yes | Own projects | Own projects | Within mandate |
| Accept direction/allocate budget | Explicit admin action | Delegated limits | No default | No |
| Approve external effects | Explicit action grant | Delegated limits | Only separate grant | No self-approval |
| Add teammate/agent | Explicit scoped grant | Delegated limits | No default | Proposal only |
| Change policy/promote code | Protected admin workflow | No default | No | No |
| Emergency stop | Authorized scope | Own execution scope | Request/escalate | Stop own attempt |

Roles are grant bundles; human names, prompts, and channel membership alone are
not authorization. Administrative read access excludes secret values by default.
User approval of a result is not approval of unrelated deployment or expenditure.

## Enforcement proposal

Expose reads and command intake through a gateway. Project executors hold no general
Neo4j administrator credentials. Trusted reducers and brokers have narrow operations
and protected credentials. The current database deployment must be evaluated for
the required isolation capabilities; do not assume row-level or per-property policy
enforcement is available just because graph scope properties exist.

Use declarative query plans and parameterized allowlisted operations for project
reads. Enforce allowed roots, labels, traversals, properties, result sizes, timeouts,
and scope on every returned record, count, error, artifact, and summary. Do not run
LLM-generated arbitrary Cypher against the shared production database for members.
If later arbitrary query access is required, it needs a separately isolated dataset
and a demonstrated policy boundary, not a string filter.

Policy generations are reviewed artifacts. Task agents cannot alter active grants,
approval records, executable code, or policy evaluators. Changes use protected
promotion and independent verification. Credential values stay in a secret store;
brokers resolve short-lived narrowly scoped access when possible.

## Threat and acceptance matrix

| Threat | Required boundary/test |
|---|---|
| Prompt injection in repository/web/document | Content cannot alter grants, policy, approval or execution destination |
| Hostile tool output or graph memory | Provenance survives summaries; privileged instructions remain separate |
| Delta confused deputy | Originator scope carried through every child invocation |
| Cross-project graph traversal | IDs, relationships, aggregates, errors, search and exports cannot disclose outside scope |
| Stolen/expired client token | Audience/issuer/expiry validated; revocation blocks future authorized requests |
| Approval replay or changed artifact | One-use decision bound to action, artifact hash, scope, policy and expiry |
| Agent credential exfiltration | Secrets unavailable to model; destination and tool boundaries enforced |
| Scope change during work | Current grant epoch checked at dispatch; disconnected exposure explicitly bounded |
| Agent edits its own policy | Separate promotion principal and immutable normal execution evidence |
| SSRF via auth metadata or source links | Bound network fetch destinations and block internal/credential endpoints |
| Query/resource exhaustion | Bounded query shapes, timeouts, quotas, and recovery capacity |
| Logs or terminal leakage | Scoped access, redaction, retention, no unrestricted shell through board |

## Authentication and confirmations

Remote HTTP access requires TLS and authenticated principals. Prefer standards-based
authorization with audience-bound tokens and explicit resource scopes. Maintain a
client compatibility matrix before exposure. Tokens must not appear in URLs, Git,
graph properties, prompts, or reports. See the MCP contract for source references.

Sensitive actions initiated through an arbitrary agent client create a pending
decision bound to the authenticated person. A trusted human approval surface shows
the actual action and captures confirmation; text saying "the user approved" is
not sufficient proof. Standing grants avoid repeated confirmation for authorized
routine work. Authentication step-up is reserved for specific privileged actions.

## Recovery and known security debt

Keep protected emergency stop and operator recovery available independently of
Delta/model/Mycelium availability. Audit exceptional access after restoration.
Review the live legacy worker's embedded credential and previously documented
credential exceptions before activating migrated execution; do not reproduce values.

No design promises perfect prompt-injection detection. Release acceptance is
tested containment even when an agent follows hostile text. Mandatory authority
isolation failures block release and cannot be waived as minor UX limitations.
