# Claude Code Skills

This directory holds Claude Code skills that extend any Claude Code session with team-specific capabilities. Skills auto-activate when Claude Code detects matching contexts.

## Installation

### For Individual Setup

```bash
bash install.sh
```

This copies all skills from `skills/` to `~/.claude/skills/` (creates directory if needed).

### For Team Setup

The Maverick setup script (`setup-team.sh` in the root) invokes this automatically for all team members.

## Available Skills

### mycelium.md

Query the team's living knowledge graph to find prior decisions, patterns, solutions, and architectural insights.

**Frontmatter triggers:**
- User asks "has anyone done X", "is there already", "what did we decide"
- User is about to implement something where a pattern might exist
- User mentions decisions, invariants, protocols, or design patterns

**Invocation:** The skill teaches Claude to run the `mycelium` CLI via the Bash tool. The CLI is installed globally by `setup-team.sh` (Slice E-A). Commands used: `mycelium --target prod ask`, `mycelium --target prod shell`, `mycelium --target prod status`. No MCP server required.

**Example:** "Should we use Unipile for LinkedIn?" → skill activates → returns the team's prior decision and test coverage.

## How Skills Work

Claude Code reads the YAML frontmatter of each skill file (`name`, `description`, `triggers`). When a session starts:

1. Claude Code matches your question against all trigger patterns
2. If a trigger matches, the skill loads automatically
3. You gain access to the skill's tools for this session
4. The skill's body (markdown) becomes context for your Claude LLM

**You don't manually invoke skills.** Just ask a question that matches a trigger, and the skill loads. If you want to disable a skill temporarily, remove it from `~/.claude/skills/`.

## Skill Format

Each skill is a markdown file with two sections:

### Frontmatter (YAML)
```yaml
---
name: skill-identifier
description: One-line human-readable description
triggers:
  - pattern 1
  - pattern 2
  - pattern 3
---
```

**Triggers:** Natural language patterns that activate the skill. Use plain English, not regex. Examples:
- "user asks about X"
- "user is about to Y"
- "user mentions Z"

### Body (Markdown)
Documentation and instructions for Claude. Include:
- What the skill does
- What tools it provides
- When to use each tool
- Examples of good usage
- Examples of bad usage

## Creating New Skills

1. Create a new `.md` file in this directory
2. Include frontmatter with `name`, `description`, and `triggers`
3. Write clear markdown explaining the skill and its tools
4. Test by running `bash install.sh`, then starting a Claude Code session
5. Commit and push

Skills are discovered by Claude Code automatically on startup. No configuration needed.

## Notes

- Skills are read-only for Claude Code sessions — they can't write to your repo or execute code
- Skills are shared across all sessions from the same machine
- If a skill has a tool that requires authentication (e.g., GitHub token), it must be configured in `~/.claude/settings.json`
- Skill descriptions and triggers should be clear and concise — they're used for matching, not displayed to users
