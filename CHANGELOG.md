# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0-beta.1] - 2026-03-04

### Added

- **Release Engineering**: Configured code signing workflows, Tauri updater, Content Security Policy (CSP), and CI smoke tests.
- **Installer UX**: Branded MSI/DMG installers with privacy agreements.
- **First-Run Experience**: Dynamic initialization wizard with i18n support and progressive model downloading based on hardware capabilities.
- **Hardware Diagnostics**: Cross-platform system capability reporting tool and matrix generation.
- **Beta Framework**: Beta feedback mechanics and mock update server for pipeline validation.

## [Sprint 6] - 2026-03-04

### Added

- **CI/CD Pipeline**: GitHub Actions for backend (pytest), frontend (tsc/eslint), Rust (cargo check), and API type-gen verification.
- **Build Pipeline**: `build_production.ps1` and `build_production.sh` for orchestrated PyInstaller + Tauri bundling.
- **Performance Infrastructure**: `scripts/benchmark_scan.py` for measuring stage-by-stage wall-clock, RSS, and VRAM usage.
- **i18n Checker**: `scripts/check_i18n_completeness.py` to ensure Japanese/English parity.
- **Architecture Docs**: Added `docs/ARCHITECTURE.md` with high-level system diagrams.

## [Sprint 5] - 2026-03-04

### Fixed

- **Circular Imports**: Resolved `shared_responses.py` dependency loop via `TYPE_CHECKING` and `model_rebuild()`.
- **API Type Debt**: Full alignment of manual interface in `api.ts` with generated OpenAPI types.
- **E2E Tests**: Fixed Playwright selector fragility in onboarding tour.
- **Security**: Added mitigation documentation for `diskcache` deserialization vulnerability.

## [Sprint 4] - 2026-03-03

### Added

- **Tauri Sidecar Health**: Realtime monitoring and auto-restart for the Python backend sidecar.
- **Inference Accuracy Tests**: Dedicated test suite for CLIP, Whisper, and Face detection precision.
- **Type Generation Phase 2**: Automated OpenAPI to TypeScript conversion.
- **Security Audit**: Completed dependency vulnerability scan and update (Rust 1.93.1, NPM audit).

## [Sprint 3] - 2026-03-02

### Added

- **CORS Production Config**: Strict allow-listed origins for Tauri communication.
- **Frontend SSE Integration**: Real-time scan progress stream in the UI.
- **SQLite WAL Stress Test**: Verified database integrity under high-concurrency write loads.
- **Error Boundaries**: Enhanced frontend resilience with component-level error catching.

## [Sprint 2] - 2026-03-02

### Added

- **Whisper Integration**: Persistent AI model loading for fast video transcription.
- **Gpu/VRAM Adaptive Lifecycle**: Dynamic model loading/offloading based on available VRAM.
- **Safe Path Validation**: Security checks for scan directories to prevent escape.

## [Sprint 1] - 2026-03-01

### Added

- **PyInstaller Bundling**: Initial "onedir" structure for sidecar backend.
- **FAISS-SQLite Self-heal**: Automatic repair of vector index in-sync with metadata database.
- **Whisper Worker**: Queue-based IPC for background transcription.

## [1.0.0] - 2026-02-28

### Initial Release

- **AI-powered local media management**: Automated organization and tagging.
- **Semantic Search**: Natural language querying.
- **Video Scene Detection**: Automatic segmentation.
- **Privacy Transparency**: Integrated network log and dashboard.
