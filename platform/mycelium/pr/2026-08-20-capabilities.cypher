// Capability map — the graph's inventory of everything the flowing-indian agent can access.
// Kinds: persona, profile, mcp, api, interface, tool. Each links to the subagent.
// This is what makes the system "know all its capabilities" from the graph, not files.

// ---- Personas ---------------------------------------------------------------
MERGE (c:Capability {node_id: 'cap-flowing-indian-persona-charlie'})
SET c.name = 'Charlie', c.kind = 'persona', c.project = 'flowing-indian',
    c.description = 'Client-facing persona on WhatsApp. Warm, non-technical, scoped permissions.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-persona-delta'})
SET c.name = 'Delta', c.kind = 'persona', c.project = 'flowing-indian',
    c.description = 'Internal builder persona on Discord. Full technical access.';

// ---- Browser profiles (CDP) -------------------------------------------------
MERGE (c:Capability {node_id: 'cap-flowing-indian-browser-charlie'})
SET c.name = 'charlie (Chromium)', c.kind = 'profile', c.project = 'flowing-indian',
    c.description = 'Persistent logged-in Chromium, CDP port 9224, charlietheagent606@gmail.com. SSO into Vercel/Composio/analytics.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-browser-seedforth'})
SET c.name = 'seedforth (Chromium)', c.kind = 'profile', c.project = 'flowing-indian',
    c.description = 'Persistent logged-in Chromium, CDP port 9223, SeedForth Google session.';

// ---- MCP servers ------------------------------------------------------------
MERGE (c:Capability {node_id: 'cap-flowing-indian-mcp-rube'})
SET c.name = 'rube', c.kind = 'mcp', c.project = 'flowing-indian',
    c.description = 'Google services (Drive, Gmail, Sheets, Docs) via Rube MCP. Auth: RUBE_BEARER_TOKEN.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-mcp-qdrant'})
SET c.name = 'qdrant-memory', c.kind = 'mcp', c.project = 'flowing-indian',
    c.description = 'Semantic memory search. Qdrant at http://143.110.226.214:6333, collection tetrahedron-memory.';

// ---- External APIs ----------------------------------------------------------
MERGE (c:Capability {node_id: 'cap-flowing-indian-api-deepseek'})
SET c.name = 'DeepSeek', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'LLM (deepseek-v4-pro, deepseek-chat). Text + reasoning.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-openrouter'})
SET c.name = 'OpenRouter', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'LLM gateway (353 models). Vision models (qwen3-vl, gemini-2.5-flash).';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-openai'})
SET c.name = 'OpenAI', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'LLM fallback. OPENAI_API_KEY + OPENAI_API_BASE in delta.env.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-unipile'})
SET c.name = 'Unipile', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'LinkedIn + Instagram + WhatsApp messaging (api38.unipile.com:16885). DMs, connection requests, comments, posts.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-razorpay'})
SET c.name = 'Razorpay', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'Payments. Orders API + webhook for the rope-flow course SKUs.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-bunny'})
SET c.name = 'Bunny Stream', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'Video delivery. Signed embed URLs for course lessons. Account currently 401 (blocked on recovery).';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-clerk'})
SET c.name = 'Clerk', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'Auth + course entitlement (publicMetadata.courses). Email-code sign-in.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-vercel'})
SET c.name = 'Vercel', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'Deploy. flowingindian.com (prod, main branch) + preview (dev/feature branches).';

MERGE (c:Capability {node_id: 'cap-flowing-indian-api-github'})
SET c.name = 'GitHub', c.kind = 'api', c.project = 'flowing-indian',
    c.description = 'Repos. Canonical: kartiksahu/flowing-indian-website. Branches + worktrees + PRs.';

// ---- Hosted interfaces ------------------------------------------------------
MERGE (c:Capability {node_id: 'cap-flowing-indian-interface-prod'})
SET c.name = 'flowingindian.com', c.kind = 'interface', c.project = 'flowing-indian',
    c.description = 'Production site (Vercel, main branch).';

MERGE (c:Capability {node_id: 'cap-flowing-indian-interface-staging'})
SET c.name = 'Vercel preview', c.kind = 'interface', c.project = 'flowing-indian',
    c.description = 'Staging site (Vercel, dev branch). Check/approve here.';

// ---- Tools ------------------------------------------------------------------
MERGE (c:Capability {node_id: 'cap-flowing-indian-tool-browser'})
SET c.name = 'browser.py', c.kind = 'tool', c.project = 'flowing-indian',
    c.description = 'CDP browser automation (open/see/click/fill/read). Drives the logged-in Chromium profiles.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-tool-graph'})
SET c.name = 'graph-tool.py', c.kind = 'tool', c.project = 'flowing-indian',
    c.description = 'Mycelium graph read/write + QueryTrace (Hebbian).';

MERGE (c:Capability {node_id: 'cap-flowing-indian-tool-unipile'})
SET c.name = 'unipile.py', c.kind = 'tool', c.project = 'flowing-indian',
    c.description = 'LinkedIn/Instagram CLI.';

MERGE (c:Capability {node_id: 'cap-flowing-indian-tool-git'})
SET c.name = 'git', c.kind = 'tool', c.project = 'flowing-indian',
    c.description = 'Version control. Worktrees for parallel streams: rope-sale, paid-marketing, flow-studio.';

// ---- Link capabilities to the flowing-indian subagent -----------------------
MATCH (s:SubAgent {node_id: 'subagent-flowing-indian'})
MATCH (c:Capability {project: 'flowing-indian'})
MERGE (s)-[:HAS_CAPABILITY]->(c);
