---
description: Run all tests and generate a summary report
---

Executes discovery and running of standalone test scripts with tabulated results.

// turbo
1. Run test runner script
   ```powershell
   ./.agent/workflows/scripts/test-runner.ps1
   ```

## Output
- Markdown table showing Test Name, Result (✅/❌), and Duration.
- Full logs saved to `tests/logs/`.
