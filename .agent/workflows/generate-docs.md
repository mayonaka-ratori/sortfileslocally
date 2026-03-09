---
description: Regenerates the three core documentation files (ROADMAP.md, docs/REQUIREMENTS.md, README.md) by reading the entire codebase and producing accurate, cross-referenced documentation in English.
---

1. Activate @doc-writer persona.
2. Run `git log --oneline -30` to capture commit history.
3. Read all files in: `server/routers/`, `src/core/`, `src/data/`, `web/src/lib/`, `web/src/hooks/`, `tests/`, `scripts/`, `src-tauri/src/`, and config files (`pyproject.toml`, `tauri.conf.json`, `package.json`, `requirements.txt`).
4. Write `ROADMAP.md` with: project status, Sprint 1-6 table, v1.0.0 blockers, post-release roadmap, known issues, ADRs.
5. Write `docs/REQUIREMENTS.md` with: IEEE 830 structure, all FR/NFR with IDs and implementing files, verification matrix.
6. Write `README.md` with: complete developer onboarding, architecture diagram, all test commands, API summary, scripts reference, contributing guide.
7. Verify files exist and commit with conventional commit message.
8. Push to origin main.
