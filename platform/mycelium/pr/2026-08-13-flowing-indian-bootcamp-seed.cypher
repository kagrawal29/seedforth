// Flowing Indian bootcamp — founding brand/strategy crystallized into the graph.
// Source: FlowStudio-VisualBoard (Kartik's digitisation of the handwritten boards
// IMG_1407..IMG_1414). Codename -> real name: Tazz=Kartik, Tizzy=Kshitiz, Dash=Deepak.
// Anchored to existing :Project proj-flowing-indian. All nodes namespaced by
// project = "flowing-indian". Idempotent (MERGE only).

// ---- Anchor -----------------------------------------------------------------
MERGE (proj:Project {node_id: 'proj-flowing-indian'})
SET proj.name = 'flowing-indian',
    proj.category = 'client',
    proj.lifecycle_state = 'active';

// ---- Mission (IMG_1408) ----------------------------------------------------
MERGE (p:Purpose {node_id: 'purpose-flowing-indian'})
SET p.label = 'Flowing Indian mission',
    p.why = 'Move people from living in their mind to living in their body; help them express their authentic self; offer alternative avenues to movement, health and wellness; provide a safe non-judgmental space for exploration and expression; build real connections and community; keep fitness fun; guide people into their State of Flow; and create a culture of movement and play.',
    p.source = 'IMG_1408',
    p.project = 'flowing-indian',
    p.declared_at = '2026-08-13';

// ---- 13 core values (IMG_1407) ---------------------------------------------
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-intuition-over-logic'})
SET v.topic = 'value', v.color = 'blue', v.label = 'Intuition over LOGIC', v.content = 'Intuition over LOGIC', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-we-before-i'})
SET v.topic = 'value', v.color = 'blue', v.label = 'WE before I', v.content = 'WE before I', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-clean-space-clean-mind'})
SET v.topic = 'value', v.color = 'green', v.label = 'Clean Space clean Mind', v.content = 'Clean Space clean Mind', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-support'})
SET v.topic = 'value', v.color = 'green', v.label = 'SUPPORT', v.content = 'SUPPORT', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-safe-space'})
SET v.topic = 'value', v.color = 'green', v.label = 'SAFE SPACE', v.content = 'SAFE SPACE', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-trust'})
SET v.topic = 'value', v.color = 'yellow', v.label = 'TRUST', v.content = 'TRUST', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-growth-and-flow'})
SET v.topic = 'value', v.color = 'yellow', v.label = 'Growth & Flow', v.content = 'Growth & Flow', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-replication'})
SET v.topic = 'value', v.color = 'orange', v.label = 'Replication', v.content = 'Replication', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-non-judgmental-space'})
SET v.topic = 'value', v.color = 'orange', v.label = 'Non-judgmental space', v.content = 'Non-judgmental space', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-transparency'})
SET v.topic = 'value', v.color = 'orange', v.label = 'Transparency', v.content = 'Transparency', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-no-toxic-positivity'})
SET v.topic = 'value', v.color = 'purple', v.label = 'No toxic positivity', v.content = 'No toxic positivity', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-fun'})
SET v.topic = 'value', v.color = 'purple', v.label = 'Fun', v.content = 'Fun', v.source = 'IMG_1407', v.project = 'flowing-indian';
MERGE (v:Knowledge {node_id: 'kn-value-flowing-indian-honesty-authenticity'})
SET v.topic = 'value', v.color = 'purple', v.label = 'Honesty & Authenticity', v.content = 'Honesty & Authenticity', v.source = 'IMG_1407', v.project = 'flowing-indian';

// ---- 17 ecosystem spokes (IMG_1414) -----------------------------------------
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-mobility-for-all'})
SET g.goal = 'Mobility for all', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-one-on-one-personal-classes'})
SET g.goal = 'One on one / Personal classes', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-sports-athletes-kids-training'})
SET g.goal = 'Sports athletes + Kids training', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-prerecorded-live-courses'})
SET g.goal = 'Pre-recorded + Live courses', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-skill-building-workshops'})
SET g.goal = 'Skill building workshops', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-personal-collective-transformation'})
SET g.goal = 'Personal + Collective transformation', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-flow-five-jams'})
SET g.goal = 'Flow + Five jams', g.category = 'events', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-podcasts-conversations'})
SET g.goal = 'Podcasts & Conversations', g.category = 'events', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-ticketed-performances'})
SET g.goal = 'Ticketed performances', g.category = 'events', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-international-retreats-intensives'})
SET g.goal = 'International events / Retreats / Intensives', g.category = 'events', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-flow-station'})
SET g.goal = 'Flow station', g.category = 'events', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-tours-exposure-festivals'})
SET g.goal = 'Tours & Exposure festivals', g.category = 'events', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-invite-only-events'})
SET g.goal = 'Invite only events', g.category = 'events', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-teacher-training-certifications'})
SET g.goal = 'Teacher Training Certifications', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-online-group-classes'})
SET g.goal = 'Online group classes', g.category = 'education', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-rent-out-studio'})
SET g.goal = 'Rent out studio', g.category = 'commerce', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';
MERGE (g:EntityGoal {node_id: 'goal-flowing-indian-merch-prop-sales'})
SET g.goal = 'Merch / Prop sales', g.category = 'commerce', g.status = 'proposed', g.source = 'IMG_1414', g.project = 'flowing-indian';

// Link spokes to the project.
MATCH (proj:Project {node_id: 'proj-flowing-indian'})
MATCH (g:EntityGoal) WHERE g.project = 'flowing-indian'
MERGE (g)-[:SERVES]->(proj);

// ---- 3 team leads (IMG_1409..1411) ------------------------------------------
MERGE (pf:EntityProfile {node_id: 'profile-flowing-indian-kartik'})
SET pf.name = 'Kartik', pf.codename = 'Tazz', pf.role = 'Big Picture & Execution Lead',
    pf.involvement = 'Face of the brand; big-picture oversight; in-person experience and people skills; lead facilitator and studio operations.',
    pf.source = 'IMG_1409', pf.project = 'flowing-indian';
MERGE (pf:EntityProfile {node_id: 'profile-flowing-indian-kshitiz'})
SET pf.name = 'Kshitiz', pf.codename = 'Tizzy', pf.role = 'Revenue & Digital Infra Lead',
    pf.involvement = 'Revenue engineering; website and marketing campaigns; experimental sessions; writing, publishing and editing; story capture; community and tree planting.',
    pf.source = 'IMG_1410', pf.project = 'flowing-indian';
MERGE (pf:EntityProfile {node_id: 'profile-flowing-indian-deepak'})
SET pf.name = 'Deepak', pf.codename = 'Dash', pf.role = 'Finance & Space Curation Lead',
    pf.involvement = 'Accounting and finances; space curation and design; content strategy; facilitation and co-hosting.',
    pf.source = 'IMG_1411', pf.project = 'flowing-indian';

MATCH (proj:Project {node_id: 'proj-flowing-indian'})
MATCH (pf:EntityProfile) WHERE pf.project = 'flowing-indian'
MERGE (pf)-[:INVOLVED_IN]->(proj);

// ---- Launch roadmap (IMG_1412) ----------------------------------------------
MERGE (m:Milestone {node_id: 'milestone-flowing-indian-website-updation'})
SET m.title = 'Website Updation', m.due = '2026-08-06', m.owner = 'Tizzy', m.status = 'completed',
    m.project = 'flowing-indian';
MERGE (m:Milestone {node_id: 'milestone-flowing-indian-rope-sale-organic-launch'})
SET m.title = 'Rope Sale Organic Launch', m.due = '2026-08-15', m.owner = 'Core Team', m.status = 'active',
    m.project = 'flowing-indian';
MERGE (m:Milestone {node_id: 'milestone-flowing-indian-paid-marketing-online-course'})
SET m.title = 'Paid Marketing & Online Course', m.due = '2026-08-28', m.owner = 'Tago / Tizzy', m.status = 'pending',
    m.project = 'flowing-indian';
MERGE (m:Milestone {node_id: 'milestone-flowing-indian-flow-studio-inauguration'})
SET m.title = 'Flow Studio Inauguration', m.due = '2026-10-01', m.owner = 'All Leads', m.status = 'pending',
    m.project = 'flowing-indian';

MATCH (proj:Project {node_id: 'proj-flowing-indian'})
MATCH (m:Milestone) WHERE m.project = 'flowing-indian'
MERGE (m)-[:MILESTONE_OF]->(proj);

// ---- Treasury & revenue splits (IMG_1413) ------------------------------------
MERGE (d:Decision {node_id: 'decision-flowing-indian-treasury-props'})
SET d.topic = 'treasury-split', d.label = 'Props',
    d.content = 'Hand-crafted props: artist share. General props: core split.',
    d.source = 'IMG_1413', d.project = 'flowing-indian';
MERGE (d:Decision {node_id: 'decision-flowing-indian-treasury-workshops'})
SET d.topic = 'treasury-split', d.label = 'Workshops',
    d.content = 'In studio: 70% facilitator / 30% studio. Out of studio: split between facilitator, studio and Tizzy.',
    d.source = 'IMG_1413', d.project = 'flowing-indian';
MERGE (d:Decision {node_id: 'decision-flowing-indian-treasury-one-on-one'})
SET d.topic = 'treasury-split', d.label = '1-on-1 Clients',
    d.content = 'Direct facilitator rate plus a treasury contribution.',
    d.source = 'IMG_1413', d.project = 'flowing-indian';
MERGE (d:Decision {node_id: 'decision-flowing-indian-treasury-retreats-events'})
SET d.topic = 'treasury-split', d.label = 'Retreats & Events',
    d.content = 'Studio, facilitators, backend team and the Flowing Indian treasury.',
    d.source = 'IMG_1413', d.project = 'flowing-indian';

MATCH (proj:Project {node_id: 'proj-flowing-indian'})
MATCH (d:Decision) WHERE d.project = 'flowing-indian'
MERGE (d)-[:GOVERNS]->(proj);

// ---- Board transcriptions (raw evidence, IMG_1407..1414) ---------------------
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1407'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1407: Our Values', t.file = 'IMG_1407.jpg',
    t.content = 'OUR VALUES. Blue: Intuition over LOGIC, WE before I. Green: Clean Space clean Mind, SUPPORT, SAFE SPACE. Yellow: TRUST, Growth & Flow. Orange: Replication, Non-judgmental space, Transparency. Purple: No toxic positivity, Fun, Honesty & Authenticity.',
    t.source = 'IMG_1407', t.project = 'flowing-indian';
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1408'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1408: Core Problem & Mission', t.file = 'IMG_1408.jpg',
    t.content = 'What problem are we solving? Living in your mind -> living in your body; expressing your authentic self; alternative avenues to movement/health/wellness; safe non-judgmental space for exploration and expression; connecting with people and building real community; fun way of keeping fit; helping people find their flow (State of Flow); creating a culture of movement and play.',
    t.source = 'IMG_1408', t.project = 'flowing-indian';
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1409'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1409: Tazz Roles', t.file = 'IMG_1409.jpg',
    t.content = 'ROLES - TAZZ. Top: good with people / in-person experience; fully available; wants to oversee everything / big picture (execution). Right: operations, facilitator. Bottom: FACE of BRAND.',
    t.source = 'IMG_1409', t.project = 'flowing-indian';
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1410'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1410: Tizzy Roles', t.file = 'IMG_1410.jpg',
    t.content = 'ROLES - TIZZY. Capture stories and moments of F&R; conducting experimental and novel sessions; digital infra / marketing campaigns; revenue engineering; writing and publishing; editing; planting trees and taking care of them; conversations and farze baazi with people.',
    t.source = 'IMG_1410', t.project = 'flowing-indian';
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1411'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1411: Dash Roles', t.file = 'IMG_1411.jpg',
    t.content = 'ROLES - DASH. Accounting and finances; content; facilitation; space curation and designing.',
    t.source = 'IMG_1411', t.project = 'flowing-indian';
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1412'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1412: Prop Sales & Launch Timelines', t.file = 'IMG_1412.jpg',
    t.content = 'PROP SALES & LAUNCHING ROPE SALE. Retreats and website sales: ads, organic Instagram, influencer collabs. Rope launch: organic (15 Aug), paid ads (28 Aug, Tago/Tizz). Website update: Tizz (6 Aug). Flow Studio inauguration: 1st week Oct (flooring, roof, plantation, pathways). Teacher training program: certification and B2B replication.',
    t.source = 'IMG_1412', t.project = 'flowing-indian';
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1413'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1413: Revenue Allocation & Treasury Model', t.file = 'IMG_1413.jpg',
    t.content = 'Treasury & revenue split architecture. Props: hand-crafted (artist share) and general split. Workshops: in studio (70% facilitator / 30% studio), out of studio split. 1-on-1 clients: direct facilitator fee. Retreats/events: studio, facilitators, backend team and Flowing Indian treasury.',
    t.source = 'IMG_1413', t.project = 'flowing-indian';
MERGE (t:Knowledge {node_id: 'kn-bootcamp-flowing-indian-img-1414'})
SET t.topic = 'bootcamp-board', t.title = 'IMG_1414: Flowing Indian Ecosystem Map', t.file = 'IMG_1414.jpg',
    t.content = 'Flowing Indian radial ecosystem. 17 distinct spokes extending from the central core hub, spanning education, workshops, international retreats, flow jams and prop commerce.',
    t.source = 'IMG_1414', t.project = 'flowing-indian';
