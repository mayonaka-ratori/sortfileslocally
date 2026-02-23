---
description: Automated git commit with LLM-assisted messages
---

Stages changes, generates a commit message based on the diff, and pushes.

// turbo
1. Run commit automation
   ```powershell
   ./.agent/workflows/scripts/git-commit.ps1
   ```

## Steps
1. `git add .`
2. Generate summary from `git diff --cached`.
3. `git commit -m "[summary]"`
4. `git push origin`
