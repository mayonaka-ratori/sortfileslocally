# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-02-28

### Added

- **AI-powered local media management**: Automated organization and tagging of local images and videos.
- **Advanced Model Integration**:
  - **CLIP**: Semantic image/video search.
  - **JoyTag**: High-precision tagging for illustrations and general content.
  - **InsightFace**: Face detection and recognition for people grouping.
  - **Whisper**: Audio transcription and video search via speech.
- **Semantic Search**: Natural language querying for your entire media library.
- **Video Scene Detection**: Automatic segmentation of videos into searchable scenes with individual thumbnails and captions.
- **Album Management**: Support for static and dynamic (search-based) albums.
- **Tag System**: Hierarchical tagging with bulk add/remove/rename operations.
- **First-run Setup Wizard**: Guided experience with hardware profile selection and demo mode.
- **Demo Mode**: Instant "Try with demo images" functionality that populates a sample library.
- **Onboarding Tour**: Interactive UI guide for new users.
- **I18n Support**: Full localization in English and Japanese (500+ translation keys).
- **Privacy Transparency**: Integrated dashboard with realtime network logging and static audit verification.
- **Auto-update System**: Built-in update mechanism powered by Tauri's cross-platform updater.
- **Tauri v2 Shell**: High-performance Rust-based desktop shell wrapping a Next.js 16 frontend.
- **CI/CD**: Automated GitHub Actions pipeline with cross-platform linting and testing.

### Security

- **Local-only Processing**: All AI inference (CLIP, JoyTag, etc.) runs entirely on the user's machine.
- **Privacy Enforcement**: Hard-coded blocks on external trackers; verified via static code analysis.
- **Privacy Audit**: Built-in audit script (`scripts/privacy_audit.py`) that users can run to verify no data leaves their system.

### Infrastructure

- **Test Suite**: 86 backend pytest tests and 13 Playwright E2E tests.
- **Coverage Reporting**: Integrated coverage tracking for all backend modules.
- **Model Isolation**: Comprehensive mocking and isolation for AI dependencies in test environments.
- **Packaging**: Ready for PyInstaller bundling and Tauri app build.
