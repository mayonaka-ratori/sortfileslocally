# ROADMAP — Local Curator Prime

## Project Status

Local Curator Prime is an offline-first, AI-powered local media manager that has completed six sprints of development. The codebase is functional with a FastAPI backend, a Next.js frontend, and a Tauri desktop shell. CI passes on all four pipelines (backend tests, frontend type/lint, i18n parity, Rust cargo check, and type-gen verification). The remote HEAD is [`6213e56`](https://github.com/mayonaka-ratori/sortfileslocally/commit/6213e56). The application can scan a user-selected directory, generate AI embeddings (CLIP, JoyTag, InsightFace, Whisper), perform sub-millisecond semantic search via FAISS, and manage tags/albums through a masonry gallery UI. Desktop packaging via Tauri + PyInstaller sidecar is implemented but pending final release hardening.

---

## Completed Milestones

| Sprint | Date       | Theme                                      | Key Deliverables                                                                                                   | Commit Range             |
| :----: | :--------- | :----------------------------------------- | :----------------------------------------------------------------------------------------------------------------- | :----------------------- |
| 1      | 2026-03-01 | Foundation Hardening                        | PyInstaller onedir migration, FAISS-SQLite self-healing integrity repair, persistent Whisper worker with Queue IPC  | `0bfa7d3`..`ff05fbf`     |
| 2      | 2026-03-02 | Backend Safety & Performance               | VRAM-aware lazy model loading with LRU eviction, SSE scan progress + path safety validation                        | `c5ab0dd`..`379a43e`     |
| 3      | 2026-03-02 | Production Networking & Frontend Resilience | CORS hardening for Tauri origins, frontend SSE integration, SQLite WAL stress tests, error boundaries              | `d527102`..`2b88578`     |
| 4      | 2026-03-03 | Type Safety & Monitoring                   | OpenAPI type generation infra, Tauri sidecar health monitoring + auto-restart, inference accuracy tests, dep audit  | `e469766`..`c164883`     |
| 5      | 2026-03-04 | Tech Debt Cleanup                          | Circular import fix (`shared_responses.py` via `TYPE_CHECKING`), API type alignment, E2E test fix, diskcache docs  | `5071703`..`6016d92`     |
| 6      | 2026-03-04 | CI/CD & Build Infrastructure               | GitHub Actions CI pipeline, production build scripts (`build_production.ps1/.sh`), benchmark infra, i18n checker, architecture docs | `99c333c`..`6213e56` |

---

## v1.0.0 Release Blockers

The following items **must** be resolved before distributing a v1.0.0 installer to end users:

1. **Code Signing** — Windows Authenticode certificate and macOS notarization via Apple Developer ID are not configured. Users will see SmartScreen/Gatekeeper warnings on unsigned binaries.
2. **First-Run Model Download UX** — The model download API exists (`POST /setup/models/download`) but requires the onboarding wizard to call it automatically. End users must not need to run CLI commands to download AI models.
3. **Installer Smoke Test on Clean Machine** — No verified install-from-scratch run on a fresh Windows 10/11 VM or macOS 12+ machine. The PyInstaller binary may have missing hidden imports or incorrect path resolution in production (see `server/main.py:get_app_data_dir()`).
4. **CSP Policy in `tauri.conf.json`** — Currently `"csp": null` ([`src-tauri/tauri.conf.json:23`](src-tauri/tauri.conf.json)). Must be set to at minimum `default-src 'self'; connect-src 'self' http://localhost:*` to prevent XSS in the webview.
5. **Updater Public Key** — Currently `"pubkey": "PLACEHOLDER_PUBLIC_KEY"` ([`src-tauri/tauri.conf.json:31`](src-tauri/tauri.conf.json)). Must be replaced with a real Ed25519 public key for Tauri's built-in updater to verify signatures.

---

## Post-v1.0.0 Roadmap

| Priority | Feature                          | Rationale                                                        | Complexity | Dependencies                  |
| :------: | :------------------------------- | :--------------------------------------------------------------- | :--------: | :---------------------------- |
| P0       | GPU VRAM profiling dashboard     | Users need visibility into model memory footprint vs. free VRAM  | Medium     | `src/core/ai_models.py`       |
| P1       | Multi-user face album galleries  | Group photos by identified person for quick browsing              | Medium     | `server/routers/gallery.py`   |
| P1       | Batch import from cloud storage  | Allow offline import of pre-downloaded cloud archives             | Medium     | `server/routers/scan.py`      |
| P2       | Plugin system for AI models      | Enable community-contributed model adapters                      | High       | `src/core/model_manager.py`   |
| P2       | Mobile companion (read-only)     | Serve the gallery on LAN for phone/tablet browsing               | Medium     | CORS, static export           |
| P3       | Federated search across devices  | Merge indices from multiple machines via mDNS                    | High       | FAISS merge, networking       |
| P3       | Custom training for face clusters | Fine-tune ArcFace on user-specific face data                     | Very High  | InsightFace, training loop    |

---

## Known Issues & Tech Debt

| Issue                                         | Severity | File(s)                                           | Workaround                                                      | Resolution Status        |
| :-------------------------------------------- | :------: | :------------------------------------------------ | :-------------------------------------------------------------- | :----------------------- |
| `diskcache` CVE-2025-69872 (pickle RCE)       | Low      | `requirements.txt`                                | Cache dir restricted to current user; no external import feature | Waiting for upstream fix |
| `time` crate RUSTSEC-2026-0009                | Low      | `src-tauri/Cargo.lock`                            | Cannot update due to `edition2024` requiring rustc ≥ 1.85        | Blocked on toolchain     |
| `test_scan_api` fails on Python 3.14 (numpy)  | Medium   | `tests/test_scan_api.py`                          | Pin Python to 3.11; exclude via `markers`                       | Will not fix (3.11 only) |
| `cargo audit` cannot run (rustc 1.84.1)       | Low      | `src-tauri/`                                      | Skipped; Rust deps not audited                                  | Upgrade rustc to ≥ 1.85  |
| GTK warnings in CI `cargo check`              | Low      | `.github/workflows/ci.yml`                        | `apt-get install libgtk-3-dev` suppresses most warnings         | Cosmetic only            |
| CSP policy is `null`                          | High     | `src-tauri/tauri.conf.json`                       | None — webview is effectively unrestricted                      | v1.0.0 blocker           |
| Updater pubkey is placeholder                 | High     | `src-tauri/tauri.conf.json`                       | Auto-update is non-functional                                   | v1.0.0 blocker           |

---

## Architecture Decision Records

| Decision                                | Rationale                                                                                                                 |
| :-------------------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **PyInstaller over Nuitka**             | Nuitka compilation times are 10-30× slower; PyInstaller onedir mode produces acceptable bundle sizes (~400 MB CPU-only). |
| **Subprocess IPC for Whisper**          | `ctranslate2` (used by `faster-whisper`) ships its own `libcudnn` that conflicts with PyTorch's when loaded in-process. A persistent worker subprocess (`src/core/whisper_worker.py`) avoids the DLL clash entirely. |
| **openapi-typescript over orval**       | orval generates runtime fetch wrappers and Axios clients. `openapi-typescript` generates only TypeScript type definitions, keeping the frontend lean and avoiding an additional runtime dependency. |
| **Vanilla pub/sub over Zustand for backend health** | The `useBackendHealth` hook (`web/src/hooks/useBackendHealth.ts`) uses `setInterval` polling + native EventSource for SSE. Introducing Zustand for a single boolean flag would over-engineer state management at this stage. |
| **FAISS over ChromaDB**                 | ChromaDB requires a running server process and uses hnswlib under the hood. FAISS-CPU is a single pip install, requires zero configuration, and delivers sub-millisecond search for up to 10M vectors. |
