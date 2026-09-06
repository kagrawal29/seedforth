# SeedForth upgrade review package

Status: proposed design, 2026-09-06. Prepared for review, not deployed.

## Review objective

Review the whole operating-system upgrade before building. Useful autonomy and
its tests are a delivery requirement within the upgrade, not a separate product
discovery exercise. Flowing Indian and Cajon Sensei remain the active products.

The [program plan](../seedforth-upgrade-plan.md) defines phases 0–9. This package
makes proposed contracts and defaults concrete. The [baseline](baseline-and-findings.md)
separates live observations from design. Remaining baseline gaps must be closed
before affected migration batches, without pretending all runtime paths are known.

## Reading order

1. [Experience and wireframes](experience-and-wireframes.md): what humans operate.
2. [Portfolio and mandates](portfolio-and-mandates.md): attention and autonomy.
3. [Graph and state](graph-and-state-contract.md): identity and transition rules.
4. [Sensing and source](sensing-and-source-contract.md): how reality enters the graph.
5. [Execution and agents](execution-and-agents.md): how work actually happens.
6. [Access and threat model](access-and-threat-model.md): enforceable authority.
7. [Interfaces and MCP](interfaces-and-mcp.md): remote graph access and conversation.
8. [Tests and learning](tests-and-learning.md): independent proof and adaptation.
9. [Migration and operations](migration-and-operations.md): phased work and rollback.
10. [System-wide contracts](system-contracts.md): S01–S10 and combined failure C01.

## Proposed decisions for review

| ID | Proposed decision | Reason / tradeoff |
|---|---|---|
| D01 | Keep graph-native work and one shared interface boundary | Prevent competing task state in board, chat, and MCP |
| D02 | Canonical identity map preserves existing IDs and aliases | Avoid renaming the ecosystem during behavior migration |
| D03 | Explicit hierarchy includes milestone and goal links | Every active task needs an outcome and acceptance path |
| D04 | Adopt current platform WorkItem vocabulary with compatibility mapping | Existing UI labels remain projections; remove in_review/review ambiguity |
| D05 | Signal is a durable request; Observation is sensor evidence | Control acknowledgement cannot be confused with observed state |
| D06 | Project lifecycle and process sleep are independent | Conversational inactivity cannot archive an autonomous project |
| D07 | Write authority flows through protected graph protocols and execution brokers | Agents cannot grant permissions or rewrite completion evidence |
| D08 | MCP initially exposes graph exploration and Delta conversation | Meets preferred experience without many narrow business tools |
| D09 | No arbitrary Cypher for project members in initial remote release | Restricted declarative graph exploration provides testable isolation |
| D10 | External effects require durable intent and verified authority | Disconnects and retries cannot silently expand effects |
| D11 | Successful execution and verified progress are separate | Failed calls and housekeeping commits cannot count as goal achievement |
| D12 | Read-only board in P4, controlled execution in P5 | Useful visibility appears before broad autonomy expansion |
| D13 | Graphify integrates as a versioned observation adapter | Extraction coverage and inference remain inspectable |
| D14 | Archival is staged after inventory and history mapping | Preserve retained services and obligations |
| D15 | Release blocking tests include authority, replay, and combined failures | Passing node-presence checks cannot qualify autonomy |

These are recommendations, not recorded human approvals. No financial limits,
external communication authority, or production deployment permission is inferred.

## Decisions genuinely needed from humans

Business goal targets and budgets; who belongs to each project and may approve
actions; retained services for archived projects; notification recipients; preferred
remote clients. Proposals and fixtures can be prepared independently. These choices
gate actual grants and deployment, not completion of the architecture review.

## Definition of prepared

- Each workstream has a contract, dependencies, acceptance, and migration boundary.
- All A01–A17, S01–S10, and U01–U16 are assigned to delivery work; C01 is specified.
- Live findings B01 onward inform design without claiming unperformed verification.
- Proposed defaults, unresolved implementation research, and human choices are clear.
- The review can approve, amend, or reject specific decisions rather than restart
  a discussion about the entire vision.

A prepared design is not an implementation-ready assertion that every production
writer has been audited. Outstanding evidence and compatibility checks are explicit
preconditions in the migration plan. No live graph or runtime changes are authorized
by this package alone.
