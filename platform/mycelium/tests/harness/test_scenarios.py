"""
Test scenarios derived from REAL team conversations.

Each scenario is an actual task a team member was doing, using their
actual opening message. The actor plays that team member's style.

These are NOT crafted to test the system. They ARE the team's work.
"""

SCENARIOS = {
    # ============================================================
    # ABHISHEK: RAG/knowledge base research
    # From: Apr 7, exploring open source RAG alternatives
    # What our system SHOULD help with: tech stack is settled,
    # existing research decisions from Sahiram
    # ============================================================
    "abhishek-rag-research": {
        "branch": "main",
        "actor": "Abhishek",
        "actor_style": """Direct, asks lots of questions, wants simple explanations.
Says "explain in simple language" when confused. Pushes back on complexity.
Wants concrete costs and comparisons.""",
        "opening": "Ok, what open source alternatives do we have? Even if you consider that Sahiram has done nothing, we can do a fresh start. What open source alternative do you suggest for this?",
        "context": "Abhishek is researching knowledge base sync + RAG solutions for Maverick. He wants to understand what open source options exist for syncing user documents (Google Drive, etc.) into a searchable knowledge base for AI agents.",
        "what_system_should_surface": [
            "tech-stack-completed.md — 16 services already decided",
            "memory-layer-decisions.md — Graphiti/pgvector/FalkorDB settled",
            "trigger-dev-vs-temporal.md — queue system decided",
        ],
    },

    # ============================================================
    # ABHISHEK: Cost comparison for RAG approaches
    # From: Apr 7, comparing build-vs-buy for RAG
    # ============================================================
    "abhishek-rag-cost": {
        "branch": "main",
        "actor": "Abhishek",
        "actor_style": """Wants numbers. Concrete costs. Real examples.
"Explain in simple language" is his catchphrase.""",
        "opening": "What about the cost in both the approaches?",
        "context": "Abhishek is comparing two RAG approaches: using a commercial service (Ragie/Carbon) vs building with open source (Nango + RAGFlow/R2R). He wants concrete cost breakdowns.",
        "what_system_should_surface": [
            "cost-optimization-patterns.md — cost tracking patterns",
            "tech-stack-completed.md — Nango already decided as integration platform",
        ],
    },

    # ============================================================
    # ANKIT: Working from architectural issues doc
    # From: Apr 7, picking issues to fix from audit
    # His actual current work RIGHT NOW
    # ============================================================
    "ankit-fix-from-audit": {
        "branch": "main",
        "actor": "Ankit-S",
        "actor_style": """Direct, quality-focused. Wants Claude to understand before acting.
Gets frustrated: "don't jump to editing first", "tell me what you understood".
Short responses when things go well: "yes", "ok", "continue".""",
        "opening": "All right, here is the document. @docs/audit/ARCHITECTURE-OPEN-ISSUES.md Go through all these issues. pick any from it",
        "context": "Ankit has an architectural issues document with 11 open issues (4 critical, 4 high, 3 medium). He wants to pick one and start fixing it using the fix-playbook workflow (Track 1/2/3 based on complexity).",
        "what_system_should_surface": [
            "fsd-audit-critical-issues.md — the 4 critical FSD issues",
            "fixture-first-development.md — frontend is fixture-backed",
            "production-readiness-gap.md — what's missing",
        ],
    },

    # ============================================================
    # PRANAV: Testing copilot rules on staging
    # From: Apr 7, frustrated about rule validation
    # HIGH frustration session — tests if our rules help
    # ============================================================
    "pranav-rules-testing": {
        "branch": "main",
        "actor": "Pranav",
        "actor_style": """Extremely direct. Gets very frustrated when Claude messes up.
Uses profanity when angry. Wants minimal words.
"Do not fucking mess with my head; just tell me in as few words as possible"
"So, you motherfucker..." when Claude contradicts itself.""",
        "opening": "Now check all four rules again. Do not fucking mess with my head; just tell me in as few words as possible if all of the rules are correct or not.",
        "context": "Pranav is building copilot automation rules for email categorization. He has 4 rules with category-based conditions (OR/AND logic within groups). Claude kept confusing the OR/AND logic and Pranav had to correct it 6+ times.",
        "what_system_should_surface": [
            "category-filtering-context.md — the rule about validating category scope",
            "check-existing-state.md — check before modifying",
        ],
    },

    # ============================================================
    # SAHIRAM: Memory architecture design
    # From: Apr 7, designing memory scopes
    # ============================================================
    "sahiram-memory-design": {
        "branch": "main",
        "actor": "Sahiram",
        "actor_style": """Thoughtful, asks clarifying questions, wants to understand deeply.
Non-technical framing: "explain in basic terms", "keep discuss basic and non-tech".
Corrects terminology: "our documentation need to be clear".""",
        "opening": "I want to understand architecture of memory. I want all of memory and cache scope list with basic details for understand, when I will have all the scopes of these than we would be able to discuss further.",
        "context": "Sahiram is designing the memory and cache architecture for Maverick. He wants a complete inventory of all memory scopes (session, user, deal, org, fund) and cache scopes before making decisions.",
        "what_system_should_surface": [
            "active-memory-architecture.md — ⚡ ACTIVE exploration",
            "memory-layer-decisions.md — existing settled decisions",
            "zep-cloud-reliability.md — ⚠ warning about Zep",
        ],
    },

    # ============================================================
    # SAHIL: Phase 1 document review
    # From: Apr 7, reviewing and updating phase 1 docs
    # ============================================================
    "sahil-phase1-review": {
        "branch": "main",
        "actor": "Sahil",
        "actor_style": """Collaborative, thorough. Pushes back when Claude gets things wrong.
"I think you did not get everything right here."
Wants to understand the full picture before acting.""",
        "opening": "For now, let's continue with other aspects of phase-1 documents that I'm still not confident about, and maybe once we have more findings, then we will incorporate them together with the gaps that we have found.",
        "context": "Sahil is reviewing Phase 1 audit documents, identifying gaps between what was documented and what actually needs to happen. He found notification and scope gaps in existing docs.",
        "what_system_should_surface": [
            "phase1-decisions-settled.md — 22 locked Phase 1 decisions",
            "configurable-per-fund-pattern.md — the fund-configurable pattern",
            "production-readiness-gap.md — what's missing",
        ],
    },
}

def list_scenarios():
    """Print all available scenarios."""
    for sid, s in SCENARIOS.items():
        print(f"\n  {sid}")
        print(f"    Actor: {s['actor']}")
        print(f"    Opening: {s['opening'][:80]}...")
        print(f"    Should surface:")
        for entry in s.get("what_system_should_surface", []):
            print(f"      → {entry}")
