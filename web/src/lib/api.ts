const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface MediaItem {
    id: number;
    file_path: string;
    media_type: string;
    width: number | null;
    height: number | null;
    tags: string[];
    character_tags: string[];
    series_tags: string[];
    audio_transcription?: { text: string; start: number; end: number }[];
    frame_descriptions?: { text: string; timestamp: number }[];
    snippet?: string; // Optional field for holding search match text snippet
}

export interface ScanStatus {
    is_active: boolean;
    progress_percent: number;
    current_file: string;
    processed_count: number;
    total_files: number;
    eta_seconds: number;
    error: string | null;
}

export const fetchMedia = async (
    options: {
        limit?: number;
        offset?: number;
        character?: string;
        series?: string;
        tag?: string;
        media_type?: string;
    } = {}
): Promise<MediaItem[]> => {
    const params = new URLSearchParams();
    if (options.limit) params.append("limit", options.limit.toString());
    if (options.offset) params.append("offset", options.offset.toString());
    if (options.character) params.append("character", options.character);
    if (options.series) params.append("series", options.series);
    if (options.tag) params.append("tag", options.tag);
    if (options.media_type) params.append("media_type", options.media_type);

    const res = await fetch(`${API_BASE_URL}/gallery/?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch media");
    return res.json();
};

export const searchMedia = async (
    query: string,
    top_k: number = 50
): Promise<MediaItem[]> => {
    const params = new URLSearchParams({ query, top_k: top_k.toString() });
    const res = await fetch(`${API_BASE_URL}/gallery/search?${params.toString()}`, {
        method: "POST",
    });
    if (!res.ok) throw new Error("Search failed");
    return res.json();
};

export const fetchFilters = async (): Promise<{ characters: string[]; series: string[] }> => {
    const res = await fetch(`${API_BASE_URL}/gallery/filters`);
    if (!res.ok) throw new Error("Failed to fetch filters");
    return res.json();
};

export const chatWithImage = async (
    file_path: string,
    prompt: string
): Promise<string> => {
    const res = await fetch(`${API_BASE_URL}/gallery/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path, prompt }),
    });
    if (!res.ok) throw new Error("Chat failed");
    const data = await res.json();
    return data.answer;
};

export const getThumbnailUrl = (id: number, size: number = 400) =>
    `${API_BASE_URL}/media/${id}/thumbnail?size=${size}`;

export const getOriginalUrl = (id: number) =>
    `${API_BASE_URL}/media/${id}/original`;

export const startScan = async (target_path: string, force_reprocess: boolean = false) => {
    const res = await fetch(`${API_BASE_URL}/scan/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_path, force_reprocess })
    });
    if (!res.ok) throw new Error("Failed to start scan");
    return res.json();
};

export const getScanStatus = async (jobId: number): Promise<ScanStatus> => {
    const res = await fetch(`${API_BASE_URL}/scan/status/${jobId}`);
    if (!res.ok) throw new Error("Failed to fetch scan status");
    return res.json();
};

export interface FaceData {
    id: number;
    file_id: number;
    face_index: number;
    timestamp: number;
    bbox: number[];
    person_name: string | null;
}

export const getFaces = async (fileId: number): Promise<FaceData[]> => {
    const res = await fetch(`${API_BASE_URL}/gallery/${fileId}/faces`);
    if (!res.ok) throw new Error("Failed to fetch faces");
    return res.json();
};

export const searchByFace = async (faceId: number, top_k: number = 50): Promise<MediaItem[]> => {
    const params = new URLSearchParams({ top_k: top_k.toString() });
    const res = await fetch(`${API_BASE_URL}/gallery/faces/${faceId}/search?${params.toString()}`, {
        method: "POST",
    });
    if (!res.ok) throw new Error("Face search failed");
    return res.json();
};

export const nameFace = async (faceId: number, personName: string): Promise<{ success: boolean }> => {
    const res = await fetch(`${API_BASE_URL}/gallery/faces/${faceId}/name`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_name: personName }),
    });
    if (!res.ok) throw new Error("Failed to name face");
    return res.json();
};


// ------------------------------------------------------------------ //
// Scan Job & Resume APIs
// ------------------------------------------------------------------ //

export interface ScanJobInfo {
    id: number;
    target_path: string;
    status: string;
    total_files: number;
    processed_count: number;
    skipped_count: number;
    error_count: number;
    progress_percent: number;
    current_file: string;
    eta_seconds: number;
    started_at: number;
    updated_at: number;
    completed_at: number;
}

export interface ScanErrorInfo {
    id: number;
    job_id: number;
    file_path: string;
    error_message: string;
    occurred_at: number;
}

export const resumeScan = async (): Promise<{ message: string; job: ScanJobInfo }> => {
    const res = await fetch(`${API_BASE_URL}/scan/resume`, { method: "POST" });
    if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Resume failed" }));
        throw new Error(data.detail || "Resume failed");
    }
    return res.json();
};

export const getLatestScanJob = async (): Promise<ScanJobInfo> => {
    const res = await fetch(`${API_BASE_URL}/scan/job/latest`);
    if (!res.ok) throw new Error("No scan jobs found");
    return res.json();
};

export const getScanJobErrors = async (jobId: number): Promise<ScanErrorInfo[]> => {
    const res = await fetch(`${API_BASE_URL}/scan/job/${jobId}/errors`);
    if (!res.ok) throw new Error("Failed to fetch errors");
    return res.json();
};

export const listScanJobs = async (limit: number = 20): Promise<ScanJobInfo[]> => {
    const res = await fetch(`${API_BASE_URL}/scan/jobs?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to list jobs");
    return res.json();
};


// ------------------------------------------------------------------ //
// Model Manager APIs
// ------------------------------------------------------------------ //

export interface ModelStatus {
    key: string;
    name: string;
    source: string;
    repo_id: string;
    is_downloaded: boolean;
    local_size_mb: number;
    estimated_size_mb: number;
    local_dir: string;
}

export const getModelStatuses = async (): Promise<ModelStatus[]> => {
    const res = await fetch(`${API_BASE_URL}/setup/models`);
    if (!res.ok) throw new Error("Failed to fetch model statuses");
    return res.json();
};

export const downloadModel = async (modelKey: string): Promise<{ message: string }> => {
    const res = await fetch(`${API_BASE_URL}/setup/models/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_key: modelKey }),
    });
    if (!res.ok) throw new Error("Failed to start download");
    return res.json();
};

export interface DownloadProgress {
    model_key: string;
    filename: string;
    downloaded_bytes: number;
    total_bytes: number;
    percent: number;
    status: string;
    error: string;
}

export const getDownloadProgress = async (modelKey: string): Promise<DownloadProgress | null> => {
    const res = await fetch(`${API_BASE_URL}/setup/models/${modelKey}/progress`);
    if (!res.ok) return null;
    return res.json();
};

export interface AppSettings {
    custom_model_dir: string | null;
}

export const getAppSettings = async (): Promise<AppSettings> => {
    const res = await fetch(`${API_BASE_URL}/setup/settings`);
    if (!res.ok) throw new Error("Failed to fetch app settings");
    return res.json();
};

export const updateAppSetting = async (key: string, value: string): Promise<{ status: string; key: string; value: string; requires_restart: boolean }> => {
    const res = await fetch(`${API_BASE_URL}/setup/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
    });
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Update failed" }));
        throw new Error(errorData.detail || "Update failed");
    }
    return res.json();
};

// ------------------------------------------------------------------ //
// Deduplication & Reverse Search APIs
// ------------------------------------------------------------------ //

export interface DuplicateItem {
    file_path: string;
    file_hash: string;
    file_size: number;
    media_type: string;
    width: number | null;
    height: number | null;
    duration: number | null;
}

export interface DuplicatePair {
    file_a: DuplicateItem;
    file_b: DuplicateItem;
    similarity: number;
    recommended_action: string;
    reason: string;
}

export interface ReverseSearchResult {
    id: number;
    file_path: string;
    media_type: string;
    width: number | null;
    height: number | null;
    similarity: number;
}

export const findDuplicates = async (
    thresholdImg: number = 0.95,
    thresholdVid: number = 0.98,
): Promise<DuplicatePair[]> => {
    const res = await fetch(`${API_BASE_URL}/dedup/candidates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ threshold_img: thresholdImg, threshold_vid: thresholdVid }),
    });
    if (!res.ok) throw new Error("Deduplication scan failed");
    return res.json();
};

export const applyDeduplication = async (
    filePaths: string[],
    mergeInto?: Record<string, string>
): Promise<{ deleted_count: number; merged_count?: number; deleted: string[]; errors: string[] }> => {
    const res = await fetch(`${API_BASE_URL}/dedup/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_paths: filePaths, merge_into: mergeInto }),
    });
    if (!res.ok) throw new Error("Failed to apply deduplication");
    return res.json();
};

export const reverseImageSearch = async (
    imageFile: File,
    topK: number = 30,
): Promise<ReverseSearchResult[]> => {
    const formData = new FormData();
    formData.append("file", imageFile);

    const res = await fetch(`${API_BASE_URL}/dedup/reverse-search?top_k=${topK}`, {
        method: "POST",
        body: formData,
    });
    if (!res.ok) throw new Error("Reverse image search failed");
    return res.json();
};


// ------------------------------------------------------------------ //
// Metadata Export APIs
// ------------------------------------------------------------------ //

export interface ExportResult {
    success: number;
    failed: number;
    errors: string[];
}

export const exportMetadata = async (
    fileIds: number[],
    mode: "xmp" | "exif" = "xmp",
): Promise<ExportResult> => {
    const res = await fetch(`${API_BASE_URL}/media/export-metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds, mode }),
    });
    if (!res.ok) throw new Error("Metadata export failed");
    return res.json();
};

export const exportAllMetadata = async (
    mode: "xmp" | "exif" = "xmp",
): Promise<ExportResult> => {
    const res = await fetch(`${API_BASE_URL}/media/export-all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
    });
    if (!res.ok) throw new Error("Metadata export failed");
    return res.json();
};

// ------------------------------------------------------------------ //
// Utility APIs
// ------------------------------------------------------------------ //

export const browseFolder = async (): Promise<{ path: string | null; cancelled: boolean }> => {
    const res = await fetch(`${API_BASE_URL}/utils/browse-folder`);
    if (!res.ok) throw new Error("Failed to open folder dialog");
    return res.json();
};
