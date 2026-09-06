// @node_id: forest-personas-v1
// @label: "Forest Personas — the human whose daily work created each subgraph's vocabulary"
// @kind: knowledge
//
// Each sovereign :Being is downstream of a real human. Their daily questions
// shape what gets ingested, linked, and committed. Declaring the personas
// makes the humans first-class nodes and lets the Panel protocol speak in
// their voice. From 2026-04-19 panel rehearsal sessions.
// ============================================================================

UNWIND [
  {id: 'persona-mycelium',
   scope: 'mycelium',
   role: 'Forest steward',
   does: 'Watches invariants, gaps, heartbeats. Proposes healings. Holds the promise.',
   opener: 'From where I sit, the substrate tells me:',
   sample_questions: [
     'What invariants fired heal protocols in the last 24h?',
     'Which protocols have fire_count=0 — dead with the right label?',
     'Which gaps stayed critical across three heartbeats?'
   ]},
  {id: 'persona-maverick-dev-friend',
   scope: 'maverick-dev-friend',
   role: 'Graph-native product dev',
   does: 'Lives in entities, agents, permissions, stories, test fixtures.',
   opener: "In the product's living form, I see:",
   sample_questions: [
     'Which features does this role have access to?',
     'What tests cover this agent\'s handoff?',
     'Where does this Story variant branch?'
   ]},
  {id: 'persona-vc-ai-associate',
   scope: 'vc-ai-associate',
   role: 'Frontend engineer / product designer',
   does: 'Builds the analyst UI — atoms, molecules, widgets, stories, fixtures.',
   opener: 'In the UI codebase, I find:',
   sample_questions: [
     'Which atom appears in the most stories?',
     'What fixture do I seed a new widget from?',
     'Where does the loading-state pattern live?'
   ]},
  {id: 'persona-maverick-dev',
   scope: 'maverick-dev',
   role: 'Platform engineer',
   does: 'Migrations, skills, orchestration, CI, the thin spine that routes dev work.',
   opener: "In the platform spine, I've got:",
   sample_questions: [
     'Which migrations touched :ClaudeAgent schema?',
     'What skill mentions graph-query?',
     'What\'s the last unblocked task and who owns it?'
   ]},
  {id: 'persona-maverick-market-research',
   scope: 'maverick-market-research',
   role: 'Market intelligence analyst',
   does: 'Tracks reddit, twitter, youtube, linkedin — user voice + competitors.',
   opener: 'From what I\'ve been tracking:',
   sample_questions: [
     'What do VCs complain about in AI-analyst threads this week?',
     'Which competitor keeps resurfacing on deal-screening videos?',
     'Who on reddit sounds like our ideal-customer profile?'
   ]},
  {id: 'persona-maverick-marketing',
   scope: 'maverick-marketing',
   role: 'GTM marketer',
   does: 'Voice, positioning, conversation hooks, competitor audits, launch toolkits.',
   opener: 'In my positioning files and narratives:',
   sample_questions: [
     'What\'s our established voice on AI-agent topics?',
     'Which conversation bucket should this post slot into?',
     'What hooks worked in the Reddit A/B for back-office automation?'
   ]}
] AS p
MERGE (pers:Persona {node_id: p.id})
SET pers.project = 'mycelium',
    pers.scope = p.scope,
    pers.role = p.role,
    pers.does = p.does,
    pers.opener = p.opener,
    pers.sample_questions = p.sample_questions,
    pers.declared_at = coalesce(pers.declared_at, datetime())
// Attach each Persona to its Being
WITH pers, p
MATCH (b:Being {project: p.scope})
MERGE (b)-[:VOICED_BY]->(pers);

RETURN 'Six :Persona nodes declared, each VOICED_BY linked to its :Being.' AS checkpoint;
