# Requirements Specification — Local Curator Prime

> IEEE 830-inspired functional and non-functional requirements for Local Curator Prime v1.0.0.

---

## 1. Introduction

### 1.1 Purpose

This document defines the functional and non-functional requirements for Local Curator Prime, an offline-first desktop application for AI-powered media management. It serves as the authoritative reference for developers, testers, and contributors.

### 1.2 Scope

Local Curator Prime scans user-selected directories, extracts AI-generated metadata (tags, captions, face embeddings, audio transcriptions), indexes everything into a local SQLite + FAISS database, and exposes the library through a semantic search interface. The entire pipeline runs on the user's machine with zero network egress.

### 1.3 Definitions

| Term  | Definition                                                                                   |
| :---- | :------------------------------------------------------------------------------------------- |
| CLIP  | Contrastive Language–Image Pretraining — OpenAI model for 768-dimensional multimodal embeddings |
| FAISS | Facebook AI Similarity Search — library for sub-millisecond nearest-neighbor vector search      |
| VLM   | Vision-Language Model — a model (Florence-2) that generates natural language captions from images |
| WAL   | Write-Ahead Logging — SQLite journal mode enabling concurrent reads during writes               |
| SSE   | Server-Sent Events — HTTP streaming protocol used for real-time scan progress                   |
| IPC   | Inter-Process Communication — data exchange between Tauri (Rust) and the Python sidecar         |
| CSP   | Content Security Policy — HTTP header restricting resources the webview can load                 |

### 1.4 References

- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](api.md)
- [Dependency Audit Report](dependency-audit-2026-03-04.md)
- [ROADMAP](../ROADMAP.md)

---

## 2. Overall Description

### 2.1 Product Perspective

Local Curator Prime is a **standalone desktop application** with no cloud dependencies. It combines:

- A **Tauri v2 desktop shell** (Rust) for native window management and process lifecycle.
- A **Next.js 16 frontend** statically exported into the Tauri webview.
- A **FastAPI backend** compiled via PyInstaller and launched as a Tauri sidecar subprocess.

### 2.2 Functions Summary

- Directory scanning with hash-based deduplication and resume support.
- Multi-model AI inference: CLIP embeddings, JoyTag illustration tagging, InsightFace face detection, Whisper speech-to-text, Florence-2 VLM captioning.
- Semantic vector search (text-to-image, image-to-image, face-to-face).
- Tag management with CRUD, bulk operations, and AI regeneration.
- Static and dynamic album organization.
- EXIF/XMP metadata write-back.
- Video scene detection with per-scene search.

### 2.3 User Profile

Technical hobbyists and digital media collectors who maintain large local image/video libraries (10K–1M+ files) and require powerful organization tools without cloud-based services.

### 2.4 Operating System Requirements

| OS           | Minimum Version       | Notes                              |
| :----------- | :-------------------- | :--------------------------------- |
| Windows      | 10 (build 17763+)    | WebView2 required (bundled)        |
| macOS        | 12 (Monterey)        | WebKit native                      |
| Ubuntu/Linux | 22.04 LTS            | WebKitGTK 4.0 required             |

### 2.5 Constraints

- **Offline-only**: Zero telemetry, zero network egress after model downloads.
- **Python 3.11**: ONNX runtime and numpy C extension compatibility prevents upgrade to 3.12+.
- **CUDA 11.8** (optional): Required for GPU-accelerated inference.

---

## 3. Functional Requirements

### FR-SCAN: Directory Scanning & Discovery

| ID       | Description                                           | I/O                                         | Priority | Implementing File                   |
| :------- | :---------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-SCAN-1 | Discover all image/video files in a directory tree    | Path → file list                            | Must     | `src/core/scanner.py`               |
| FR-SCAN-2 | Compute file hash (MD5) for dedup                    | File → hash string                          | Must     | `src/core/hashing.py`               |
| FR-SCAN-3 | Validate scan path is safe (no system dirs)          | Path → boolean                              | Must     | `server/routers/scan.py`            |
| FR-SCAN-4 | Resume interrupted scan from last processed file     | Job ID → resumed scan                       | Must     | `src/data/scan_job_manager.py`      |
| FR-SCAN-5 | Stream scan progress via SSE                         | Job ID → SSE event stream                   | Must     | `server/routers/scan.py`            |
| FR-SCAN-6 | Persistent job tracking in SQLite                    | Job metadata → DB rows                      | Must     | `src/data/scan_job_manager.py`      |

### FR-AI: AI Inference Pipeline

| ID       | Description                                           | I/O                                         | Priority | Implementing File                   |
| :------- | :---------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-AI-1  | CLIP image embedding (768-dim)                        | PIL Image → `np.ndarray(768,)`              | Must     | `src/core/ai_models.py`             |
| FR-AI-2  | CLIP text embedding (768-dim)                         | String → `np.ndarray(768,)`                 | Must     | `src/core/ai_models.py`             |
| FR-AI-3  | JoyTag illustration tagging                           | Image → tag list                            | Should   | `src/core/joytag_inference.py`      |
| FR-AI-4  | InsightFace face detection (512-dim embeddings)       | BGR ndarray → face list with bbox/embedding | Must     | `src/core/ai_models.py`             |
| FR-AI-5  | Whisper audio transcription (subprocess IPC)          | Audio path → `[{start, end, text}]`         | Should   | `src/core/whisper_worker.py`        |
| FR-AI-6  | Florence-2 VLM captioning                             | Image → natural language caption            | Should   | `src/core/vlm_engine.py`            |
| FR-AI-7  | Style classification (illustration vs. photo)         | Image → `"illustration"` / `"photo"`       | Should   | `src/core/ai_models.py`             |
| FR-AI-8  | VRAM-aware lazy model loading with LRU eviction       | Available VRAM → load/evict decision        | Must     | `src/core/ai_models.py`             |
| FR-AI-9  | Batch CLIP inference                                  | `List[Image]` → `np.ndarray(N, 768)`       | Should   | `src/core/ai_models.py`             |

### FR-SEARCH: Search & Retrieval

| ID         | Description                                         | I/O                                         | Priority | Implementing File                   |
| :--------- | :-------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-SEARCH-1 | Vector similarity search via FAISS                 | Query vector + top_k → ranked results       | Must     | `src/data/db_manager.py`            |
| FR-SEARCH-2 | Hybrid query (semantic + SQL filters)              | `HybridSearchRequest` → filtered results    | Must     | `server/routers/gallery.py`         |
| FR-SEARCH-3 | Reverse image search (upload → similar images)     | Uploaded image → CLIP → FAISS results       | Should   | `server/routers/dedup.py`           |
| FR-SEARCH-4 | Face-based search (find matching faces)            | Face ID → similar faces across library      | Should   | `server/routers/gallery.py`         |
| FR-SEARCH-5 | Search history (UPSERT, 100-entry cap)             | Query → stored history entry                | Could    | `server/routers/gallery.py`         |

### FR-TAG: Tag Management

| ID       | Description                                           | I/O                                         | Priority | Implementing File                   |
| :------- | :---------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-TAG-1 | CRUD tags on a single media item                      | File ID + tags → updated tags               | Must     | `server/routers/media.py`           |
| FR-TAG-2 | Bulk add/remove/replace tags for multiple files       | File IDs + action + tags → bulk result      | Must     | `server/routers/media.py`           |
| FR-TAG-3 | AI tag regeneration (append or overwrite mode)        | File ID + mode → rescan result              | Should   | `server/routers/media.py`           |
| FR-TAG-4 | Tag suggestions (prefix autocomplete)                 | Prefix string → matching tags               | Should   | `server/routers/gallery.py`         |
| FR-TAG-5 | Rename/merge tags across library                      | Old tag + new tag → renamed count           | Should   | `server/routers/gallery.py`         |
| FR-TAG-6 | Tag statistics (usage counts, untagged files)         | None → stats by category                    | Should   | `server/routers/gallery.py`         |

### FR-ALBUM: Album Organization

| ID        | Description                                          | I/O                                         | Priority | Implementing File                   |
| :-------- | :--------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-ALBUM-1 | Create/list/update/delete albums                   | Album CRUD operations                       | Must     | `server/routers/albums.py`          |
| FR-ALBUM-2 | Static albums (manually add/remove file IDs)       | File IDs → album membership                 | Must     | `server/routers/albums.py`          |
| FR-ALBUM-3 | Dynamic albums (persisted search query JSON)       | `HybridSearchRequest` JSON → live results   | Should   | `server/routers/albums.py`          |

### FR-DEDUP: Deduplication

| ID        | Description                                          | I/O                                         | Priority | Implementing File                   |
| :-------- | :--------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-DEDUP-1 | Detect duplicate candidates (hash + vector)        | Thresholds → duplicate pairs                | Must     | `server/routers/dedup.py`           |
| FR-DEDUP-2 | Apply deduplication (delete + optional merge)      | File paths → delete result                  | Must     | `server/routers/dedup.py`           |

### FR-EXPORT: Metadata Export

| ID         | Description                                         | I/O                                         | Priority | Implementing File                   |
| :--------- | :-------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-EXPORT-1 | EXIF/XMP write-back for selected files             | File IDs + mode → export result             | Should   | `server/routers/media.py`           |
| FR-EXPORT-2 | Bulk export for entire library                     | Mode → bulk export result                   | Could    | `server/routers/media.py`           |

### FR-SCENE: Video Scene Analysis

| ID        | Description                                          | I/O                                         | Priority | Implementing File                   |
| :-------- | :--------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-SCENE-1 | Detect scenes in video (PySceneDetect)             | File ID → scene list with timestamps        | Should   | `server/routers/scenes.py`          |
| FR-SCENE-2 | Per-scene CLIP embedding and search                | Query → ranked scene results                | Should   | `server/routers/scenes.py`          |
| FR-SCENE-3 | Scene thumbnail extraction and storage             | Scene → thumbnail file path                 | Should   | `src/core/video_processor.py`       |

### FR-UI: Frontend User Interface

| ID      | Description                                            | I/O                                         | Priority | Implementing File                   |
| :------ | :----------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-UI-1 | Masonry gallery with infinite scroll                   | Media items → responsive grid               | Must     | `web/src/` (React components)       |
| FR-UI-2 | Media detail view with tag editor                      | File ID → full metadata view                | Must     | `web/src/` (React components)       |
| FR-UI-3 | SSE-powered scan progress bar                          | SSE stream → progress UI                    | Must     | `web/src/hooks/useScanProgress.ts`  |
| FR-UI-4 | Backend health status banner                           | Health check → banner component             | Must     | `web/src/hooks/useBackendHealth.ts`  |
| FR-UI-5 | Internationalization (en/ja)                           | Locale key → translated string              | Should   | `web/src/messages/`                 |
| FR-UI-6 | Dark/light/system theme support                        | Theme preference → CSS variables            | Should   | `web/` (next-themes)                |

### FR-DESKTOP: Desktop Application Lifecycle

| ID          | Description                                        | I/O                                         | Priority | Implementing File                   |
| :---------- | :------------------------------------------------- | :------------------------------------------ | :------: | :---------------------------------- |
| FR-DESKTOP-1 | Tauri window with native title bar               | Config → native window                      | Must     | `src-tauri/tauri.conf.json`         |
| FR-DESKTOP-2 | Sidecar spawn with port discovery                | Exe path → discovered port                  | Must     | `src-tauri/src/main.rs`             |
| FR-DESKTOP-3 | Sidecar crash recovery (auto-restart ×3)         | Exit event → restart attempt                | Must     | `src-tauri/src/main.rs`             |
| FR-DESKTOP-4 | Graceful shutdown (kill sidecar on window close)  | Close event → process kill                  | Must     | `src-tauri/src/main.rs`             |
| FR-DESKTOP-5 | Auto-update via Tauri Updater plugin              | GitHub Release → update prompt              | Should   | `src-tauri/tauri.conf.json`         |

---

## 4. Non-Functional Requirements

| ID          | Category    | Requirement                                                   | Measurable Criteria                              |
| :---------- | :---------- | :------------------------------------------------------------ | :----------------------------------------------- |
| NFR-PERF-1  | Performance | Scan throughput for images                                    | ≥ 5 files/sec on CPU-only (no GPU)               |
| NFR-PERF-2  | Performance | Search latency (FAISS + SQLite join)                          | ≤ 200 ms for 100K-item library                   |
| NFR-PERF-3  | Performance | Thumbnail generation latency                                  | ≤ 100 ms per JPEG thumbnail (300px)              |
| NFR-MEM-1   | Memory      | GPU VRAM ceiling (balanced profile)                           | ≤ 4 GB VRAM when all models loaded               |
| NFR-MEM-2   | Memory      | CPU RSS ceiling (no GPU)                                      | ≤ 2 GB RSS during scan (lightweight profile)     |
| NFR-SEC-1   | Security    | Zero egress after model downloads                             | No outbound connections (verifiable via privacy audit) |
| NFR-SEC-2   | Security    | CORS strictly allow-listed origins                            | Only `tauri://localhost`, `https://tauri.localhost`, `http://localhost:3000` (dev) |
| NFR-SEC-3   | Security    | No `eval()` or `Function()` in frontend                      | Verified by ESLint `no-eval` rule                |
| NFR-REL-1   | Reliability | SQLite WAL concurrent write safety                            | Verified by `tests/test_sqlite_stress.py` (100 concurrent writers) |
| NFR-REL-2   | Reliability | Sidecar restart time                                          | ≤ 10 s from crash detection to port re-discovery |
| NFR-REL-3   | Reliability | FAISS-SQLite self-healing on corruption                       | Automatic repair on startup (verified by `tests/test_index_integrity.py`) |
| NFR-BUILD-1 | Build       | CPU-only installer size                                       | ≤ 500 MB (Windows .msi)                          |

---

## 5. Data Requirements

### 5.1 SQLite Schema

The primary database (`data/media.db`, WAL mode) contains these key tables:

| Table            | Purpose                                           | Key Columns                                                 |
| :--------------- | :------------------------------------------------ | :---------------------------------------------------------- |
| `files`          | Media file metadata                               | `id`, `file_path`, `file_hash`, `media_type`, `width`, `height`, `tags` (JSON), `character_tags` (JSON), `series_tags` (JSON), `caption` |
| `faces`          | Detected face records                             | `id`, `file_id`, `face_index`, `embedding` (512-dim blob), `bbox` (JSON), `person_name` |
| `video_scenes`   | Scene segments for videos                         | `id`, `file_id`, `scene_index`, `start_time`, `end_time`, `clip_vector_id`, `thumbnail_path`, `tags` (JSON) |
| `albums`         | User-created albums                               | `id`, `name`, `is_dynamic`, `query_json`                    |
| `album_items`    | Static album membership                           | `album_id`, `file_id`                                       |
| `search_history` | Recent search queries                             | `id`, `query_text`, `filters_json`, `result_count`          |
| `settings`       | Key-value application settings                    | `key`, `value`                                              |
| `scan_jobs`      | Persistent scan job tracking                      | `id`, `target_path`, `status`, `total_files`, `processed_count` |
| `vector_mapping` | FAISS ID → file/scene ID mapping                  | `faiss_id`, `file_id`, `scene_id`                           |

### 5.2 FAISS Index

- **CLIP index**: `data/clip.index` — `IndexFlatIP`, dimension 768, normalized vectors (cosine similarity via inner product).
- **Face index**: `data/face.index` — `IndexFlatIP`, dimension 512.

### 5.3 Thumbnails

Stored in `.thumbnails/` relative to `APP_DATA_DIR`. Scene thumbnails in `.thumbnails/scenes/`.

### 5.4 AI Model Paths

Managed by `src/core/model_manager.py`. Default locations:

- Hugging Face models: `~/.cache/huggingface/hub/`
- InsightFace models: `~/.insightface/models/`
- JoyTag: `~/.cache/joytag/`
- Custom directory: configurable via `POST /setup/settings` (`custom_model_dir`).

---

## 6. Interface Requirements

### 6.1 REST API

All endpoints are served by FastAPI at `http://localhost:8000`. Full specification available via `/openapi.json`.

| Prefix       | Router File                    | Purpose                           |
| :----------- | :----------------------------- | :-------------------------------- |
| `/gallery`   | `server/routers/gallery.py`    | Media listing, search, tags, faces |
| `/media`     | `server/routers/media.py`      | Thumbnails, originals, exports, rescans |
| `/scan`      | `server/routers/scan.py`       | Scan start/resume/status, SSE     |
| `/albums`    | `server/routers/albums.py`     | Album CRUD                        |
| `/dedup`     | `server/routers/dedup.py`      | Deduplication, reverse search     |
| `/scenes`    | `server/routers/scenes.py`     | Scene detection, scene search     |
| `/setup`     | `server/routers/setup.py`      | Models, settings, backup          |
| `/demo`      | `server/routers/demo.py`       | Demo mode lifecycle               |
| `/privacy`   | `server/routers/privacy.py`    | Privacy audit, storage locations  |
| `/insights`  | `server/routers/insights.py`   | Library analysis suggestions      |
| `/health`    | `server/main.py`               | Health check (`{"status": "ok"}`) |

### 6.2 SSE Protocol

`GET /scan/status/stream/{job_id}` returns an `EventSource` stream with `text/event-stream` content type. Each event is a JSON-serialized `ScanJobResponse` object containing `progress_percent`, `current_file`, `eta_seconds`, etc.

### 6.3 Tauri IPC Events

| Event Name           | Direction         | Payload           | Purpose                          |
| :------------------- | :---------------- | :---------------- | :------------------------------- |
| `backend-restarted`  | Rust → Frontend   | `()`              | Backend sidecar successfully restarted |
| `backend-crashed`    | Rust → Frontend   | `String`          | Backend exceeded 3 restart attempts |

### 6.4 Tauri Commands

| Command              | Parameters         | Return              | Purpose                          |
| :------------------- | :----------------- | :------------------ | :------------------------------- |
| `get_backend_port`   | None               | `u16`               | Discovered sidecar port          |
| `get_backend_status` | None               | `BackendStatus`     | Port, running state, restart count |
| `restart_backend`    | None               | `String`            | Manual sidecar restart           |

### 6.5 Whisper Subprocess IPC

The Whisper worker (`src/core/whisper_worker.py`) communicates via `multiprocessing.Queue`. The parent process (AIEngine) sends file paths and receives transcription results with a 60-second timeout per file.

---

## 7. Verification Matrix

| Requirement   | Test File / CI Job                                              | Type         |
| :------------ | :-------------------------------------------------------------- | :----------- |
| FR-SCAN-1..6  | `tests/test_scan_api.py`, `tests/test_scan_job_manager.py`      | Unit + API   |
| FR-AI-1,2     | `tests/test_inference_accuracy.py` (CLIP)                       | Accuracy     |
| FR-AI-4       | `tests/test_inference_accuracy.py` (Face)                       | Accuracy     |
| FR-AI-5       | `tests/test_whisper_worker.py`, `tests/test_whisper_sub.py`     | Unit         |
| FR-AI-8       | `tests/test_optimization.py`                                    | Unit         |
| FR-SEARCH-1,2 | `tests/test_engine.py`                                         | Unit         |
| FR-SEARCH-3   | `tests/test_reverse_search.py`                                  | Integration  |
| FR-TAG-1..6   | `tests/test_tags.py`, `tests/test_tag_edit.py`, `tests/test_bulk_tags.py` | Unit         |
| FR-ALBUM-1..3 | `tests/test_album_api.py`, `tests/test_albums.py`               | Unit + API   |
| FR-DEDUP-1,2  | `tests/test_deduplication.py`, `tests/test_deduplication_merge.py` | Unit       |
| FR-EXPORT-1,2 | `tests/test_exporter.py`, `tests/test_integration_export_dedup.py` | Unit + Integration |
| FR-SCENE-1..3 | `tests/test_scenes.py`                                          | Unit         |
| FR-DESKTOP-3  | Manual (sidecar crash simulation)                               | Manual       |
| NFR-SEC-2     | `tests/test_cors.py`                                            | Unit         |
| NFR-REL-1     | `tests/test_sqlite_stress.py`                                   | Stress       |
| NFR-REL-3     | `tests/test_index_integrity.py`                                 | Unit         |
| NFR-PERF-1    | `tests/test_benchmark.py`, `scripts/benchmark_scan.py`          | Benchmark    |
| i18n parity   | `scripts/check_i18n_completeness.py` (CI job: `i18n-check`)     | CI           |
| Frontend types | CI job: `type-gen-verify`                                      | CI           |
| Rust compile  | CI job: `rust-check`                                            | CI           |
| Backend tests | CI job: `backend-test`                                          | CI           |
| Frontend lint | CI job: `frontend-check`                                        | CI           |
