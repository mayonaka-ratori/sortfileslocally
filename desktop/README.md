# Desktop App Packaging (Future)

This directory is the groundwork for packaging Local Curator Prime as a
standalone desktop application using **Tauri v2**.

## Why Tauri?

| | Tauri | Electron |
|---|---|---|
| Binary size | ~3 MB | ~150 MB |
| RAM usage | Low (system WebView) | High (bundled Chromium) |
| Backend language | Rust (can call Python) | Node.js |
| Maturity | v2 stable | Very mature |

Tauri is the better fit because:
1. We already have a **Python backend** (FastAPI + uvicorn). Tauri's Rust
   sidecar/shell command can spawn and manage the Python process.
2. The frontend is **Next.js** — Tauri can load the exported static site or
   proxy to the dev server.
3. Much smaller distribution size.

## Architecture

```
┌──────────────────────────────────────────┐
│  Tauri Shell (Rust)                      │
│  ┌────────────┐   ┌───────────────────┐  │
│  │ WebView    │   │ Sidecar: Python   │  │
│  │ (Next.js)  │◄──┤ (FastAPI backend) │  │
│  └────────────┘   └───────────────────┘  │
└──────────────────────────────────────────┘
```

## Entry Points

- **Backend**: `run_backend.py` (project root) — programmatic uvicorn launcher
  with CLI args for host/port. This is the sidecar target.
- **Frontend**: `web/` directory — `npm run build && npm run export` produces
  a static `out/` folder that Tauri's WebView can load.

## Setup Steps (when ready to implement)

1. Install Tauri CLI: `cargo install tauri-cli`
2. Initialize: `npx tauri init` (inside this `desktop/` directory)
3. Configure `tauri.conf.json`:
   - Set `build.distDir` to `../web/out`
   - Add sidecar config pointing to bundled Python + `run_backend.py`
4. Build: `npx tauri build`

## Current Status

- [x] `run_backend.py` entry point created
- [x] `start.bat` / `start.sh` launcher scripts created
- [ ] Tauri project initialized
- [ ] Sidecar configuration for Python backend
- [ ] Static export of Next.js frontend
- [ ] Production build & packaging
