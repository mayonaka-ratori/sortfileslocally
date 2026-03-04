# LocalCurator Prime v1.0.0-beta.1

Welcome to the first beta release of **LocalCurator Prime**!

This release contains the culmination of 8 development sprints, bringing privacy-first, fully local AI media organization to your desktop.

## What's Included

- **AI-Powered Local Media Management**: Find and organize photos and videos without the cloud.
- **Semantic Search**: Use natural language to search your library (e.g., "A dog playing in the snow").
- **Intelligent Tagging & Face Recognition**: Auto-detect characters, series, and identify faces (requires "Balanced" or "Full" AI profile).
- **Video Transcription & Scene Detection**: Segment videos and search by spoken words via Whisper.
- **Deduplication Scanner**: Find identical and near-replica instances gracefully.
- **Complete Offline Operation**: Zero telemetry, and a built-in privacy network log.

## Known Limitations

- **Diskcache Dependency**: The underlying diskcache package currently poses a minor deserialization vulnerability. Future versions will migrate to SQLite caching.
- **Time Crate Compatibility**: Minor warnings regarding the `time` Rust crate version during build.
- **Code Signing Warnings**: Official code signing certificates have not yet been purchased. Windows SmartScreen or macOS Gatekeeper will throw warnings. (Bypass guide detailed below).

## How to Install

1. Download the appropriate installer for your platform from the [Releases](https://github.com/mayonaka-ratori/sortfileslocally/releases/tag/v1.0.0-beta.1) page.
2. Run the installer:
   - **Windows (.msi)**: Run the `.msi`. If SmartScreen blocks it, click "More info" -> "Run anyway".
   - **macOS (.dmg)**: Mount the DMG and drag the app to your `Applications` folder. Right-click and select "Open" to bypass Gatekeeper.
   - **Linux (.AppImage)**: Mark as executable (`chmod +x`) and run.
3. Upon first launch, complete the "First Run Wizard" to download the necessary offline AI models based on your hardware profile.

## Troubleshooting & Bug Reports

If you experience crashes, performance bottlenecks, or inference errors, we rely on your feedback to fix them before General Availability.

1. **Hardware Report**: Use the built-in diagnostic tools to export your system capabilities.
2. Attach the generated hardware diagnostic to your issue report on our [GitHub Issues](https://github.com/mayonaka-ratori/sortfileslocally/issues) page.

Thank you for testing LocalCurator Prime! All metadata and albums created during beta will be compatible with the v1.0.0 final release.
