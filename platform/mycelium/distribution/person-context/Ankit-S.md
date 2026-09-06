---
paths:
  - "**/*"
---

# Context for Ankit-S — 2026-04-10

## Decisions that affect your current work

- **Spec reading guides are now a NO-SKIP rule in playbook v7**: You added this on Apr 10. Every TypeScript interface/enum block needs an inline Reading Guide mapping technical fields to product concepts. This is documented in `knowledge/patterns/spec-reading-guides.md` and is now part of the settled spec review contract.

- **Fixture-first development is settled**: Service Provider pattern (React Context DI) for swapping fixtures vs. real APIs — settled in Phase 1. The channel preferences feature implementation sits on top of this. Any new notification channel features should use the same fixture injection pattern before wiring real APIs.

- **FSD audit issues are documented**: Critical issues in `knowledge/architecture/fsd-audit-critical-issues.md` — shared/ imports from widgets/ (layer inversion), DealResearchRepo not wired into ServicesProvider, 15 files exceeding 500 LOC. If you're working through ARCHITECTURE-AUDIT.md, check this entry first to avoid re-diagnosing known issues.

## Cross-team connections

- Your work on spec reading guides connects directly to Sahil's concern about AI-generated doc trustworthiness. Sahil questioned (Apr 7) whether AI-generated architecture docs can be trusted without human validation — your reading guide requirement is a concrete answer: make AI-generated specs human-verifiable by design. Sahil hasn't seen this yet.

- You and Pranav are both updating the spec-to-ship playbook for the same codebase. Pranav is focused on copilot rule-creation infrastructure quality (Apr 7). Coordinate to avoid conflicting playbook versions — your v7 reading guide addition and Pranav's copilot quality work are complementary but not yet linked.

## Expanding your questions

- The cross-session monitoring pattern you developed (Agent A watching Agent B's JSONL file every 60-120s) is not in any knowledge entry. This is a novel coordination technique worth documenting — it's directly applicable to any multi-agent build workflow.

- Your deal comparison design questions (chat-initiated vs. standalone widget, multi-deal context structure) have no knowledge entry. The Phase 1 decisions cover deal view components but not comparison layout or which metrics to highlight. If you make decisions on this feature, filing a report will prevent the next person from starting from scratch.

- Channel preferences implementation (notification channel routing, quiet hours, connection modals) also has no knowledge entry covering the decisions made. Same recommendation.
