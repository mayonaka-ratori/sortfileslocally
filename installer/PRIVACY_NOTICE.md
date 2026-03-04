# Privacy Notice

LocalCurator Prime is designed with privacy as its foundational principle. By design, the application cannot "spy" on your files or exfiltrate your data.

## Core Privacy Guarantees

1. **Local-Only AI Processing**: All AI models (CLIP, Faster-Whisper, InsightFace) are executed entirely on your local machine. We do not use any cloud APIs for inference.
2. **No Data Exfiltration**: Your files, metadata, embeddings, and any generated indexes (FAISS and SQLite databases) are stored locally and never transmitted to our servers or any third party.
3. **No Telemetry**: We do not include tracking SDKs. We do not track how you use the app, how many files you scan, or your search queries.
4. **No Microphone/Camera Access**: The application reads existing media files on disk but does not request or use system hardware like your microphone or camera.
5. **No Cloud Sync**: There is no account system and no cloud synchronization feature. What happens on your machine stays on your machine.
