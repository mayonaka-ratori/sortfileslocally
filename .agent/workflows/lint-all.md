---
description: Run full project linting and syntax checks
---

This workflow performs linting, formatting, and AST validation for both Python and Web components.

// turbo
1. Run the lint script
   ```powershell
   ./.agent/workflows/scripts/lint-all.ps1
   ```

## Included Checks
- **Python**: `ruff check`, `ruff format`, `python -m py_compile` (recursion).
- **Web**: `npm run lint` in `web/` directory.
