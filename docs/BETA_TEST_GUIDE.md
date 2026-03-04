# Beta Test Guide

Welcome to the LocalCurator Prime Beta Testing phase. Because our application relies heavily on local hardware running AI models (Whisper, CLIP, InsightFace), compatibility testing is crucial across environments.

## Installation Instructions

1. Download the latest installer for your platform (.msi or .dmg) from GitHub Releases.
2. Ensure you have at least **3GB to 5GB of free space** for Model downloading during the initial setup wizard.
3. Install the app. Do not block internet access initially so the models can download.

## Test Scenarios Checklist

Please verify the following scenarios run smoothly on your hardware:

- [ ] **First-Run Wizard**: Complete the 4-step wizard cleanly. Models download successfully.
- [ ] **Media Scan (100 files)**: Try scanning a directory containing ~100 images and short videos.
  - *Expected pass condition*: Progress bar responds smoothly, no crashes or Out-Of-Memory (OOM) errors.
- [ ] **Semantic Search**: Search for an object in an image (e.g., "red car on a sunny day").
- [ ] **Deduplication**: Run the deduplication tool. Mark at least 1 duplicate to keep/delete.
- [ ] **Whisper Transcription**: Load a short `.mp4` video. Check if the auto-generated captions are matching the audio accurately.
- [ ] **Metadata Export**: Export metadata into CSV.

## Reporting Issues / Bugs

When filing a bug on GitHub Issues, use the template below and make sure you attach your hardware diagnostic payload.

### Bug Report Template

```text
**Description of the bug**
A clear description of what went wrong.

**Steps to reproduce**
1. 
2. 

**Hardware Report payload**
(Go to Settings -> Diagnostics -> 'Export Hardware Report' OR run `python scripts/hardware_report.py`)
<paste JSON payload here>

**Logs**
<paste content of `%APPDATA%/LocalCuratorPrime/logs/` here>
```

## Known Limitations

- Heavy CPU/Memory usage during scanning on non-discrete GPU machines. Provide feedback if it hard-locks your system.
- Audio transcriptions currently lack language auto-detection accuracy on short clips < 2s.
