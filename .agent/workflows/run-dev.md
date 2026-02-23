---
description: Start development environment with port checks
---

Provides a safe startup sequence for backend and frontend services.

// turbo
1. Run dev server script
   ```powershell
   ./.agent/workflows/scripts/dev-server.ps1
   ```

## Procedure
1. Verify port **8000** (Backend) and **3000** (Frontend) are free.
2. If occupied, display PID and prompt for action.
3. Start FastAPI backend (`server/main.py`).
4. Start Next.js frontend (`web/` -> `npm run dev`).
