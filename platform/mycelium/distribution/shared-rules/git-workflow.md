---
paths:
  - "**/*"
---

# Git Workflow

Keep your work synced with GitHub. Other team members and the meta intelligence system depend on seeing your work to avoid duplicate effort and share decisions.

## Branching
- Always work on a feature branch: `git checkout -b dev/{username}/{short-description}`
- If you're already on a feature branch, stay on it
- The main branch is for merges only — create a branch before making changes

## When to Commit
- After completing any task the user asked for
- After creating, modifying, or deleting files
- Before starting a different task or topic — commit current work first, then switch
- If the user asks an unrelated question while you have changes, commit first then answer
- Keep commits frequent — small commits are easier to review and revert than large ones

## How to Commit
1. Stage specific files you changed with `git add` — review what you're staging to avoid including unintended files
2. Write a clear, concise commit message describing what you did and why
3. The auto-sync hook handles `git pull` and `git push` automatically after your commit — you only need to commit

## At End of Session
- When the user wraps up: commit all remaining work so nothing is lost
- Leave the repo in a clean state for the next session
