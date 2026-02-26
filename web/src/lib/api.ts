const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const safeFetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const isLocal = url.includes('localhost') || url.includes('127.0.0.1') || url.startsWith('/');
    const method = init?.method || 'GET';
    const startTime = performance.now();

    const getSanitizedUrl = (rawUrl: string) => {
        try {
            const urlObj = new URL(rawUrl, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
            return urlObj.pathname;
        } catch {
            return rawUrl.split('?')[0];
        }
    };

    const logRequest = (status: number | 'blocked') => {
        if (typeof window !== 'undefined') {
            const addLog = (window as Window & { __ADD_NETWORK_LOG?: (entry: { timestamp: string; method: string; url: string; status: number | 'blocked'; duration: number; isLocal: boolean; }) => void }).__ADD_NETWORK_LOG;
            if (addLog) {
                addLog({
                    timestamp: new Date().toLocaleTimeString(),
                    method,
                    url: getSanitizedUrl(url),
                    status,
                    duration: Math.round(performance.now() - startTime),
                    isLocal
                });
            }
        }
    };

    if (typeof navigator !== 'undefined' && !navigator.onLine && !isLocal) {
        console.warn(`Offline: Skipping external API call to ${url}`);
        logRequest('blocked');
        // Return a mock failed response or a special offline error
        return new Response(JSON.stringify({ error: "Offline: External request skipped" }), {
            status: 503,
            statusText: "Service Unavailable (Offline)",
            headers: { 'Content-Type': 'application/json' }
        });
    }

    try {
        const response = await fetch(input, init);
        logRequest(response.status);
        return response;
    } catch (error) {
        logRequest(500);
        if (typeof navigator !== 'undefined' && !navigator.onLine) {
            console.warn('Request failed while offline:', url);
            throw new Error('You are offline. This request will retry when connection is restored.');
        }
        throw error;
    }
};

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

export interface Scene {
    id: number;
    scene_index: number;
    start_time: number;
    end_time: number;
    start_frame: number;
    end_frame: number;
    thumbnail_url: string;
    caption: string;
    tags: string[];
    character_tags: string[];
    series_tags: string[];
    duration: number;
}

export interface SceneSearchResult extends Scene {
    file_id: number;
    filename: string;
    score: number;
}

export interface SearchFilters {
    tags?: string[];
    character_tags?: string[];
    series_tags?: string[];
    media_type?: string;
    extension?: string[];
}

export interface HybridSearchResponse {
    results: MediaItem[];
    total_candidates: number;
    filters_applied: SearchFilters;
}

export interface SearchHistoryEntry {
    id: number;
    query_text: string;
    filters_json: string | null;
    result_count: number;
    executed_at: string;
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

    const res = await safeFetch(`${API_BASE_URL}/gallery/?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch media");
    return res.json();
};

export const searchMedia = async (
    query: string,
    filters: SearchFilters = {},
    top_k: number = 50
): Promise<HybridSearchResponse> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, filters, top_k }),
    });
    if (!res.ok) throw new Error("Search failed");
    return res.json();
};

export const fetchFilters = async (): Promise<{ characters: string[]; series: string[] }> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/filters`);
    if (!res.ok) throw new Error("Failed to fetch filters");
    return res.json();
};

export const chatWithImage = async (
    file_path: string,
    prompt: string
): Promise<string> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/chat`, {
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
    const res = await safeFetch(`${API_BASE_URL}/scan/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_path, force_reprocess })
    });
    if (!res.ok) throw new Error("Failed to start scan");
    return res.json();
};

export const getScanStatus = async (jobId: number): Promise<ScanStatus> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/status/${jobId}`);
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
    const res = await safeFetch(`${API_BASE_URL}/gallery/${fileId}/faces`);
    if (!res.ok) throw new Error("Failed to fetch faces");
    return res.json();
};

export const searchByFace = async (faceId: number, top_k: number = 50): Promise<MediaItem[]> => {
    const params = new URLSearchParams({ top_k: top_k.toString() });
    const res = await safeFetch(`${API_BASE_URL}/gallery/faces/${faceId}/search?${params.toString()}`, {
        method: "POST",
    });
    if (!res.ok) throw new Error("Face search failed");
    return res.json();
};

export const nameFace = async (faceId: number, personName: string): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/faces/${faceId}/name`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_name: personName }),
    });
    if (!res.ok) throw new Error("Failed to name face");
    return res.json();
};

// ------------------------------------------------------------------ //
// Search History APIs
// ------------------------------------------------------------------ //

export const getSearchHistory = async (limit: number = 20): Promise<SearchHistoryEntry[]> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/search-history?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch search history");
    return res.json();
};

export const deleteSearchHistory = async (id: number): Promise<void> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/search-history/${id}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete search history entry");
};

export const clearSearchHistory = async (): Promise<void> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/search-history`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to clear search history");
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

export const resumeScan = async (jobId?: number): Promise<{ message: string; job: ScanJobInfo }> => {
    const url = jobId ? `${API_BASE_URL}/scan/resume/${jobId}` : `${API_BASE_URL}/scan/resume`;
    const res = await safeFetch(url, { method: "POST" });
    if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Resume failed" }));
        throw new Error(data.detail || "Resume failed");
    }
    return res.json();
};

export const getLatestScanJob = async (): Promise<ScanJobInfo> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/job/latest`);
    if (!res.ok) throw new Error("No scan jobs found");
    return res.json();
};

export const getScanJobErrors = async (jobId: number): Promise<ScanErrorInfo[]> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/job/${jobId}/errors`);
    if (!res.ok) throw new Error("Failed to fetch errors");
    return res.json();
};

export const listScanJobs = async (limit: number = 20): Promise<ScanJobInfo[]> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/jobs?limit=${limit}`);
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
    const res = await safeFetch(`${API_BASE_URL}/setup/models`);
    if (!res.ok) throw new Error("Failed to fetch model statuses");
    return res.json();
};

export const downloadModel = async (modelKey: string): Promise<{ message: string }> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/models/download`, {
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
    const res = await safeFetch(`${API_BASE_URL}/setup/models/${modelKey}/progress`);
    if (!res.ok) return null;
    return res.json();
};

export interface AppSettings {
    custom_model_dir: string | null;
    setup_completed: boolean;
    execution_profile: string;
    theme: string;
    locale: string;
    demo_mode: boolean;
    last_opened: number;
    onboarding_dismissed: string;
}

export const getAppSettings = async (): Promise<AppSettings> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/settings`);
    if (!res.ok) throw new Error("Failed to fetch app settings");
    return res.json();
};

export const completeSetup = async (): Promise<{ status: string }> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/complete`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to complete setup");
    return res.json();
};

export const updateAppSetting = async (key: string, value: string): Promise<{ status: string; key: string; value: string; requires_restart: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/settings`, {
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
    const res = await safeFetch(`${API_BASE_URL}/dedup/candidates`, {
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
    const res = await safeFetch(`${API_BASE_URL}/dedup/apply`, {
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

    const res = await safeFetch(`${API_BASE_URL}/dedup/reverse-search?top_k=${topK}`, {
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
    const res = await safeFetch(`${API_BASE_URL}/media/export-metadata`, {
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
    const res = await safeFetch(`${API_BASE_URL}/media/export-all`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
    });
    if (!res.ok) throw new Error("Metadata export failed");
    return res.json();
};

// ------------------------------------------------------------------ //
// Album APIs
// ------------------------------------------------------------------ //

export interface Album {
    id: number;
    name: string;
    is_dynamic: boolean;
    query_json?: string;
    cover_file_id?: number | null;
    item_count: number;
    created_at: string;
    updated_at: string;
}

export const fetchAlbums = async (): Promise<Album[]> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/`);
    if (!res.ok) throw new Error("Failed to fetch albums");
    return res.json();
};

export const fetchAlbum = async (id: number): Promise<Album> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}`);
    if (!res.ok) throw new Error("Failed to fetch album");
    return res.json();
};

export const createAlbum = async (name: string, isDynamic: boolean = false, queryJson?: string): Promise<number> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, is_dynamic: isDynamic, query_json: queryJson }),
    });
    if (!res.ok) throw new Error("Failed to create album");
    return res.json();
};

export const updateAlbum = async (id: number, data: { name?: string; query_json?: string; cover_file_id?: number | null }): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to update album");
    return res.json();
};

export const deleteAlbum = async (id: number): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete album");
    return res.json();
};

export const fetchAlbumMedia = async (id: number): Promise<MediaItem[]> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}/media`);
    if (!res.ok) throw new Error("Failed to fetch album media");
    return res.json();
};

export const addItemsToAlbum = async (id: number, fileIds: number[]): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds }),
    });
    if (!res.ok) throw new Error("Failed to add items to album");
    return res.json();
};

export const removeItemsFromAlbum = async (id: number, fileIds: number[]): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}/items`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds }),
    });
    if (!res.ok) throw new Error("Failed to remove items from album");
    return res.json();
};

// ------------------------------------------------------------------ //
// Utility APIs
// ------------------------------------------------------------------ //

export const browseFolder = async (): Promise<{ path: string | null; cancelled: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/utils/browse-folder`);
    if (!res.ok) throw new Error("Failed to open folder dialog");
    return res.json();
};

// ------------------------------------------------------------------ #
// Tag Editor APIs
// ------------------------------------------------------------------ #

export interface TagSuggestion {
    tag: string;
    count: number;
}

export type TagCategory = "general" | "character" | "series";

export const addTags = async (fileId: number, tags: string[], category: TagCategory = "general"): Promise<{ tags: string[]; updated_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/media/${fileId}/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags, category }),
    });
    if (!res.ok) throw new Error("Failed to add tags");
    return res.json();
};

export const removeTags = async (fileId: number, tags: string[], category: TagCategory = "general"): Promise<{ tags: string[]; removed_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/media/${fileId}/tags`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags, category }),
    });
    if (!res.ok) throw new Error("Failed to remove tags");
    return res.json();
};

export const suggestTags = async (query: string, category?: TagCategory, limit: number = 10): Promise<TagSuggestion[]> => {
    const params = new URLSearchParams({ q: query, limit: limit.toString() });
    if (category) params.append("category", category);
    const res = await safeFetch(`${API_BASE_URL}/gallery/tags/suggest?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch tag suggestions");
    return res.json();
};

export interface BulkTagResponse {
    affected_count: number;
    action: string;
    tags: string[];
    errors: { file_id: number; error: string }[];
}

export const bulkUpdateTags = async (
    fileIds: number[],
    action: "add" | "remove" | "replace",
    tags: string[],
    category: TagCategory = "general"
): Promise<BulkTagResponse> => {
    const res = await safeFetch(`${API_BASE_URL}/media/bulk-tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds, action, tags, category }),
    });
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Bulk update failed" }));
        throw new Error(errorData.detail || "Bulk update failed");
    }
    return res.json();
};

// ------------------------------------------------------------------ #
// Tag Dashboard APIs
// ------------------------------------------------------------------ #

export interface TagStat {
    tag: string;
    count: number;
}

export interface TagStats {
    general: TagStat[];
    character: TagStat[];
    series: TagStat[];
    total_tags: number;
    untagged_count: number;
}

export interface UntaggedFilesResponse {
    files: MediaItem[];
    total_count: number;
}

export const getTagStats = async (): Promise<TagStats> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/tags/stats`);
    if (!res.ok) throw new Error("Failed to fetch tag stats");
    return res.json();
};

export const getUntaggedFiles = async (page: number = 1, perPage: number = 50): Promise<UntaggedFilesResponse> => {
    const params = new URLSearchParams({ page: page.toString(), per_page: perPage.toString() });
    const res = await safeFetch(`${API_BASE_URL}/gallery/untagged?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch untagged files");
    return res.json();
};

export const renameTag = async (oldTag: string, newTag: string, category: TagCategory): Promise<{ renamed_count: number; merged_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/tags/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_tag: oldTag, new_tag: newTag, category }),
    });
    if (!res.ok) throw new Error("Failed to rename tag");
    return res.json();
};

// ------------------------------------------------------------------ #
// AI Rescan APIs
// ------------------------------------------------------------------ #

export type RescanMode = "overwrite" | "append";

export const rescanFile = async (fileId: number, mode: RescanMode = "append"): Promise<{ status: string; file_id: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/media/${fileId}/rescan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
    });
    if (!res.ok) throw new Error("Failed to trigger rescan");
    return res.json();
};

export const bulkRescan = async (fileIds: number[], mode: RescanMode = "append"): Promise<{ status: string; job_id: number; file_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/media/bulk-rescan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds, mode }),
    });
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Bulk rescan failed" }));
        throw new Error(errorData.detail || "Bulk rescan failed");
    }
    return res.json();
};
// ------------------------------------------------------------------ #
// Insights APIs
// ------------------------------------------------------------------ #

export interface InsightItem {
    type: "duplicate_found" | "untagged_files" | "album_suggestion" | "low_quality_tags";
    title: string;
    message: string;
    action_url: string;
    action_label: string;
    priority: "high" | "medium" | "low";
    count: number;
    tag?: string;
    query_json?: string;
}

export interface InsightsResponse {
    insights: InsightItem[];
    generated_at: string;
}

export const getInsights = async (): Promise<InsightsResponse> => {
    const res = await safeFetch(`${API_BASE_URL}/insights`);
    if (!res.ok) throw new Error("Failed to fetch insights");
    return res.json();
};

// ------------------------------------------------------------------ #
// Scene Segmentation APIs
// ------------------------------------------------------------------ #

export const detectScenes = async (fileId: number, force: boolean = false): Promise<{ status: string; job_id?: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/scenes/${fileId}/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ force }),
    });
    if (!res.ok) throw new Error("Failed to start scene detection");
    return res.json();
};

export const getScenes = async (fileId: number): Promise<Scene[]> => {
    const res = await safeFetch(`${API_BASE_URL}/media/${fileId}/scenes`);
    if (!res.ok) throw new Error("Failed to fetch scenes");
    return res.json();
};

export const deleteScenes = async (fileId: number): Promise<{ success: boolean; deleted_count: number }> => {
    const res = await fetch(`${API_BASE_URL}/scenes/${fileId}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete scenes");
    return res.json();
};

export const searchScenes = async (query: string, topK: number = 20): Promise<SceneSearchResult[]> => {
    const params = new URLSearchParams({ query, top_k: topK.toString() });
    const res = await fetch(`${API_BASE_URL}/scenes/search?${params.toString()}`);
    if (!res.ok) throw new Error("Scene search failed");
    return res.json();
};

// ------------------------------------------------------------------ #
// Demo Mode APIs
// ------------------------------------------------------------------ #

export const startDemo = async (): Promise<{ message: string; job: ScanJobInfo }> => {
    const res = await safeFetch(`${API_BASE_URL}/demo/start`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to start demo");
    return res.json();
};

export const resetDemo = async (): Promise<{ status: string }> => {
    const res = await safeFetch(`${API_BASE_URL}/demo/reset`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to reset demo");
    return res.json();
};

export const getDemoStatus = async (): Promise<{ demo_mode: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/demo/status`);
    if (!res.ok) throw new Error("Failed to fetch demo status");
    return res.json();
};

// ------------------------------------------------------------------ #
// Privacy APIs
// ------------------------------------------------------------------ #

export interface PrivacyAuditViolation {
    file: string;
    line: number;
    pattern: string;
    context: string;
    detected: string;
}

export interface PrivacyAuditResult {
    scan_date: string;
    files_scanned: number;
    violations: PrivacyAuditViolation[];
    allowlisted_skips: number;
    verdict: 'PASS' | 'FAIL';
}

export interface PrivacyStorage {
    db: string;
    thumbnails: string;
    models: string;
}

export const runPrivacyAudit = async (): Promise<PrivacyAuditResult> => {
    const res = await safeFetch(`${API_BASE_URL}/privacy/audit`);
    if (!res.ok) throw new Error("Privacy audit failed");
    return res.json();
};

export const getPrivacyStorage = async (): Promise<PrivacyStorage> => {
    const res = await safeFetch(`${API_BASE_URL}/privacy/storage`);
    if (!res.ok) throw new Error("Failed to fetch storage locations");
    return res.json();
};

