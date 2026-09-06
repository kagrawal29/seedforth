# Session Handoff -- 2026-09-05

## State
Server fully migrated: DO (143.110.226.214) -> Contabo (185.192.96.100, ssh delta2).
All 8 agents running on opencode serve with autostart=false (ephemeral model).
29,530 nodes in mycelium Neo4j. 9.4 GB RAM free on 12 GB box.

## Architecture (Current)
- Sole runtime: opencode serve (no tmux, no Claude Code)
- Model: openrouter/deepseek/deepseek-v4-pro
- Config generation: agent_lifecycle.py (no stale keys)
- Memory: agent_lifecycle docs in AGENTS.md section "Agent Lifecycle & Conversation Flow"
- Hibernate = supervisorctl stop + autostart=false (frees ~270 MB)
- Wake on message = delta restores agent, 5-8s first response

## Key URLs
- Neo4j: bolt://185.192.96.100:7687
- noVNC: http://185.192.96.100:6083/vnc.html
- Charlie CDP: localhost:9224
- GitHub: kagrawal29/delta (main branch)

## Archived
23 projects in /opt/delta/archived-projects/ on delta2. Restore with tar -xzf.

## What Changed
- Deleted lifecycle.py (tmux/Claude Code)
- Removed ClaudeCodeRunner, runtime dispatch
- Cleaned project_bridge.py (no tmux references)
- Fixed agent_lifecycle.py to write valid opencode 1.18 configs
- All defaults: runtime=opencode, model=openrouter/deepseek/deepseek-v4-pro

## If Delta Not Responding
1. supervisorctl status (check agents)
2. journalctl -u delta -f (watch for errors)
3. Check opencode jsonc configs don't have lsp.disable or custom_tool
4. Check OPENROUTER_API_KEY balance on server
5. Permissions: delta user needs o+x on /home/proj-*/ dirs

## TODOs
- Add session-level health check (is_agent_responding) to on_ready restore loop
- Consider adding OPENROUTER_API_KEY credit monitoring to delta
- Setup Uptime Kuma for fleet monitoring
