// Model roster — system awareness of available models + capabilities (2026-08-20)
// The intelligence layer records which models exist, what they can do, and cost,
// so agents and the webhook can switch models per use case (text vs vision)
// while keeping the conversation context (session).

MERGE (m:Model {node_id: 'model-deepseek-v4-pro'})
SET m.name = 'DeepSeek V4 Pro', m.provider = 'deepseek', m.model_id = 'deepseek-v4-pro',
    m.capabilities = ['text', 'reasoning'], m.cost_in_1m = 1.44, m.cost_out_1m = 2.88,
    m.role = 'default';

MERGE (m:Model {node_id: 'model-deepseek-chat'})
SET m.name = 'DeepSeek Chat', m.provider = 'deepseek', m.model_id = 'deepseek-chat',
    m.capabilities = ['text'], m.cost_in_1m = 0.2574, m.cost_out_1m = 1.0287,
    m.role = 'fast-text';

MERGE (m:Model {node_id: 'model-qwen3-vl-8b'})
SET m.name = 'Qwen3 VL 8B', m.provider = 'openrouter', m.model_id = 'qwen/qwen3-vl-8b-instruct',
    m.capabilities = ['text', 'vision'], m.cost_in_1m = 0.117, m.cost_out_1m = 0.455,
    m.role = 'vision';

MERGE (m:Model {node_id: 'model-gemini-25-flash'})
SET m.name = 'Gemini 2.5 Flash', m.provider = 'openrouter', m.model_id = 'google/gemini-2.5-flash',
    m.capabilities = ['text', 'vision'], m.cost_in_1m = 0.3, m.cost_out_1m = 2.5,
    m.role = 'vision-high';

// Link flowing-indian's subagent to its current + available models
MATCH (s:SubAgent {node_id: 'subagent-flowing-indian'})
MATCH (m:Model {node_id: 'model-deepseek-v4-pro'})
MERGE (s)-[:USES_MODEL {current: true}]->(m);

MATCH (s:SubAgent {node_id: 'subagent-flowing-indian'})
MATCH (m:Model) WHERE m.node_id IN ['model-deepseek-chat', 'model-qwen3-vl-8b', 'model-gemini-25-flash']
MERGE (s)-[:HAS_MODEL]->(m);
