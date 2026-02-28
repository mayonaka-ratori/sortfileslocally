# API Reference

LocalCurator Prime's backend is powered by FastAPI. When running the backend locally, you can access the Interactive Swagger documentation at `http://localhost:8000/docs`.

## Albums Router (`/albums`)

Manage static and dynamic collections of media.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| GET | `/albums/` | List all albums | None |
| POST | `/albums/` | Create a new album | `AlbumCreateRequest` |
| GET | `/albums/{id}` | Get album details | None |
| PUT | `/albums/{id}` | Update album metadata/query | `AlbumUpdateRequest` |
| DELETE | `/albums/{id}` | Delete an album | None |
| GET | `/albums/{id}/media` | Get all media items in an album | None |
| POST | `/albums/{id}/items` | Add items to a static album | `AddItemsRequest` |
| DELETE | `/albums/{id}/items` | Remove items from a static album | `AddItemsRequest` |

## Deduplication Router (`/dedup`)

Find and manage duplicate media files.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| POST | `/dedup/candidates` | Scan for duplicate candidates | `DeduplicationRequest` |
| POST | `/dedup/apply` | Delete selected duplicate files | `DeleteRequest` |
| POST | `/dedup/reverse-search` | Find similar images via upload | `File` (multipart) |

## Demo Router (`/demo`)

Manage the sample library for demonstration.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| GET | `/demo/status` | Check if demo mode is active | None |
| POST | `/demo/start` | Copy demo assets and start scan | None |
| POST | `/demo/reset` | Clear demo library and exit mode | None |

## Gallery Router (`/gallery`)

Primary interface for browsing and searching the library.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| GET | `/gallery/` | List all processed media items | None |
| POST | `/gallery/search` | Perform hybrid semantic search | `HybridSearchRequest` |
| GET | `/gallery/search-history` | Get recent search history | None |
| DELETE | `/gallery/search-history/{id}` | Delete history entry | None |
| DELETE | `/gallery/search-history` | Clear all search history | None |
| GET | `/gallery/filters` | Get unique tags for filtering | None |
| POST | `/gallery/chat` | Ask AI about a specific image (VLM) | `ChatRequest` |
| GET | `/gallery/{id}/faces` | List detected faces in a file | None |
| POST | `/gallery/faces/{face_id}/search` | Find media with similar faces | None |
| POST | `/gallery/faces/{face_id}/name` | Label a person's face | `NameFaceRequest` |
| GET | `/gallery/tags/suggest` | Get autocomplete suggestions for tags | None |
| GET | `/gallery/tags/stats` | Get usage statistics for all tags | None |
| GET | `/gallery/untagged` | List files with no AI tags | None |
| POST | `/gallery/tags/rename` | Rename a tag globally | `RenameTagRequest` |

## Insights Router (`/insights`)

Automated library analysis and suggestions.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| GET | `/insights` | Generate library insights | None |

## Media Router (`/media`)

Direct file access and individual item operations.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| GET | `/media/{file_id}/original` | Stream the original file | None |
| GET | `/media/{file_id}/thumbnail` | Get a generated thumbnail | None |
| GET | `/media/{file_id}/scenes` | List detected scenes for a video | None |
| POST | `/media/export-metadata` | Write tags to sidecars/EXIF | `ExportRequest` |
| POST | `/media/export-all` | Write tags for entire library | `ExportAllRequest` |
| POST | `/media/{file_id}/tags` | Add tags to a media item | `TagRequest` |
| DELETE | `/media/{file_id}/tags` | Remove tags from a media item | `TagRequest` |
| POST | `/media/bulk-tags` | Batch update tags (add/rem/repl) | `BulkTagRequest` |
| POST | `/media/{file_id}/rescan` | Trigger AI re-processing (single) | `RescanRequest` |
| POST | `/media/bulk-rescan` | Trigger AI re-processing (batch) | `BulkRescanRequest` |

## Privacy Router (`/privacy`)

Security and monitoring.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| GET | `/privacy/audit` | Run static analysis audit | None |
| GET | `/privacy/storage` | Get absolute data storage locations | None |

## Scan Router (`/scan`)

Library folder scanning and job management.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| POST | `/scan/start` | Start scanning a new directory | `ScanRequest` |
| POST | `/scan/resume` | Resume the latest incomplete scan | `ResumeRequest` |
| POST | `/scan/resume/{job_id}` | Resume a specific scan job | None |
| GET | `/scan/status/{job_id}` | Poll realtime scan progress | None |
| GET | `/scan/job/latest` | Get details of the latest scan job | None |
| GET | `/scan/job/{job_id}` | Get details of a specific scan job | None |
| GET | `/scan/job/{job_id}/errors` | List errors encountered during scan | None |
| GET | `/scan/jobs` | List all historic scan jobs | None |

## Scenes Router (`/scenes`)

Video-specific scene management.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| POST | `/scenes/{file_id}/detect` | Trigger scene detection | `DetectRequest` |
| DELETE | `/scenes/{file_id}` | Clear all scene metadata | None |
| GET | `/scenes/search` | Standalone scene search using semantic query | None |

## Setup Router (`/setup`)

Hardware and application configuration.

| Method | Path | Description | Body |
| :--- | :--- | :--- | :--- |
| GET | `/setup/models` | List AI model download status | None |
| GET | `/setup/models/{key}` | Get status for a specific model | None |
| POST | `/setup/models/download` | Trigger model download | `DownloadRequest` |
| GET | `/setup/models/{key}/progress` | Poll download progress | None |
| GET | `/setup/settings` | Retrieve all app settings | None |
| POST | `/setup/complete` | Mark setup wizard as finished | None |
| POST | `/setup/settings` | Update a specific setting | `SettingItem` |
| POST | `/setup/backup` | Create a manual DB backup | None |
