let API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

import type {
    MediaItem, SearchFilters, HybridSearchResponse,
    ScanStatus, ScanJobInfo, ScanErrorInfo, ModelStatus,
    ReverseSearchResult, ExportResult, Album, TagSuggestion, BulkTagResponse,
    UntaggedFilesResponse, InsightItem, InsightsResponse, FaceData,
    SceneInfo, SceneSearchInfo, DuplicateItemInfo, DuplicatePairInfo, TagStatsInfo
} from "./api-types-bridge";

export type {
    MediaItem, SearchFilters, HybridSearchResponse,
    ScanStatus, ScanJobInfo, ScanErrorInfo, ModelStatus,
    ReverseSearchResult, ExportResult, Album, TagSuggestion, BulkTagResponse,
    UntaggedFilesResponse, InsightItem, InsightsResponse, FaceData,
    SceneInfo as Scene, SceneSearchInfo as SceneSearchResult,
    DuplicateItemInfo as DuplicateItem, DuplicatePairInfo as DuplicatePair,
    TagStatsInfo as TagStats
};

export async function initApiBase() {
    if (typeof window !== 'undefined' && ('__TAURI__' in window || ('rpc' in window))) {
        try {
            const { invoke } = await import('@tauri-apps/api/core');
            const port = await invoke<number>('get_backend_port');
            API_BASE_URL = `http://localhost:${port}`;
            console.log(`[API] Discovered backend on port ${port}`);
        } catch (err) {
            console.warn("[API] Failed to discover backend port, falling back to 8000", err);
        }
    }
}

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

        if (!response.ok) {
            const errorText = await response.text();
            let detail: string = "Request failed";
            try {
                const errorData = JSON.parse(errorText);
                const rawDetail = errorData.detail || errorData.error || errorText;
                detail = typeof rawDetail === 'string' ? rawDetail : JSON.stringify(rawDetail);
            } catch {
                detail = errorText || `Error ${response.status}`;
            }
            // We throw a structured object that callers can catch
            throw { status: response.status, detail };
        }

        return response;
    } catch (error: unknown) {
        const err = error as { status?: number; detail?: string; message?: string };
        if (err.status) throw err; // Already structured

        logRequest(500);
        if (typeof navigator !== 'undefined' && !navigator.onLine) {
            console.warn('Request failed while offline:', url);
            throw { status: 503, detail: 'You are offline. This request will retry when connection is restored.' };
        }

        // Dispatch a global event to force the backend health polling to wake up
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new Event('lcp:force-health-check'));
        }

        throw { status: 500, detail: err.message || String(error) };
    }
};

// ------------------------------------------------------------------ //
// Media & Search APIs
// ------------------------------------------------------------------ //

// Scene type is now generated from the backend — re-exported from api-types-bridge as SceneInfo → Scene

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
    return res.json();
};

export const fetchFilters = async (): Promise<{ characters: string[]; series: string[] }> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/filters`);
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
    return res.json();
};

export const getScanStatus = async (jobId: number): Promise<ScanStatus> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/status/${jobId}`);
    return res.json();
};

export const getFaces = async (fileId: number): Promise<FaceData[]> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/${fileId}/faces`);
    return res.json();
};

export const searchByFace = async (faceId: number, top_k: number = 50): Promise<MediaItem[]> => {
    const params = new URLSearchParams({ top_k: top_k.toString() });
    const res = await safeFetch(`${API_BASE_URL}/gallery/faces/${faceId}/search?${params.toString()}`, {
        method: "POST",
    });
    return res.json();
};

export const nameFace = async (faceId: number, personName: string): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/faces/${faceId}/name`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ person_name: personName }),
    });
    return res.json();
};

// ------------------------------------------------------------------ //
// Search History APIs
// ------------------------------------------------------------------ //

export interface SearchHistoryEntry {
    id: number;
    query_text: string;
    filters_json: string | null;
    result_count: number;
    executed_at: string;
}

export const getSearchHistory = async (limit: number = 20): Promise<SearchHistoryEntry[]> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/search-history?limit=${limit}`);
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

export const resumeScan = async (jobId?: number): Promise<{ message: string; job: ScanJobInfo }> => {
    const url = jobId ? `${API_BASE_URL}/scan/resume/${jobId}` : `${API_BASE_URL}/scan/resume`;
    const res = await safeFetch(url, { method: "POST" });
    return res.json();
};

export const getLatestScanJob = async (): Promise<ScanJobInfo> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/job/latest`);
    return res.json();
};

export const getScanJobErrors = async (jobId: number): Promise<ScanErrorInfo[]> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/job/${jobId}/errors`);
    return res.json();
};

export const listScanJobs = async (limit: number = 20): Promise<ScanJobInfo[]> => {
    const res = await safeFetch(`${API_BASE_URL}/scan/jobs?limit=${limit}`);
    return res.json();
};


// ------------------------------------------------------------------ //
// Model Manager APIs
// ------------------------------------------------------------------ //

export const getModelStatuses = async (): Promise<ModelStatus[]> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/models`);
    return res.json();
};

export const downloadModel = async (modelKey: string): Promise<{ message: string }> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/models/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_key: modelKey }),
    });
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
    return res.json();
};

export const completeSetup = async (): Promise<{ status: string }> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/complete`, { method: "POST" });
    return res.json();
};

export const updateAppSetting = async (key: string, value: string): Promise<{ status: string; key: string; value: string; requires_restart: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/setup/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key, value }),
    });
    return res.json();
};

// ------------------------------------------------------------------ //
// Deduplication & Reverse Search APIs
// ------------------------------------------------------------------ //

// DuplicateItem and DuplicatePair are now generated — re-exported from api-types-bridge


export const findDuplicates = async (
    thresholdImg: number = 0.95,
    thresholdVid: number = 0.98,
): Promise<DuplicatePairInfo[]> => {
    const res = await safeFetch(`${API_BASE_URL}/dedup/candidates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ threshold_img: thresholdImg, threshold_vid: thresholdVid }),
    });
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
    return res.json();
};


// ------------------------------------------------------------------ //
// Metadata Export APIs
// ------------------------------------------------------------------ //

export const exportMetadata = async (
    fileIds: number[],
    mode: "xmp" | "exif" = "xmp",
): Promise<ExportResult> => {
    const res = await safeFetch(`${API_BASE_URL}/media/export-metadata`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds, mode }),
    });
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
    return res.json();
};

// ------------------------------------------------------------------ //
// Album APIs
// ------------------------------------------------------------------ //

export const fetchAlbums = async (): Promise<Album[]> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/`);
    return res.json();
};

export const fetchAlbum = async (id: number): Promise<Album> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}`);
    return res.json();
};

export const createAlbum = async (name: string, isDynamic: boolean = false, queryJson?: string): Promise<number> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, is_dynamic: isDynamic, query_json: queryJson }),
    });
    return res.json();
};

export const updateAlbum = async (id: number, data: { name?: string; query_json?: string; cover_file_id?: number | null }): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    return res.json();
};

export const deleteAlbum = async (id: number): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}`, {
        method: "DELETE",
    });
    return res.json();
};

export const fetchAlbumMedia = async (id: number): Promise<MediaItem[]> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}/media`);
    return res.json();
};

export const addItemsToAlbum = async (id: number, fileIds: number[]): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds }),
    });
    return res.json();
};

export const removeItemsFromAlbum = async (id: number, fileIds: number[]): Promise<{ success: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/albums/${id}/items`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds }),
    });
    return res.json();
};

// ------------------------------------------------------------------ //
// Utility APIs
// ------------------------------------------------------------------ //

export const browseFolder = async (): Promise<{ path: string | null; cancelled: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/utils/browse-folder`);
    return res.json();
};

// ------------------------------------------------------------------ #
// Tag Editor APIs
// ------------------------------------------------------------------ #

export type TagCategory = "general" | "character" | "series";

export const addTags = async (fileId: number, tags: string[], category: TagCategory = "general"): Promise<{ tags: string[]; updated_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/media/${fileId}/tags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags, category }),
    });
    return res.json();
};

export const removeTags = async (fileId: number, tags: string[], category: TagCategory = "general"): Promise<{ tags: string[]; removed_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/media/${fileId}/tags`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tags, category }),
    });
    return res.json();
};

export const suggestTags = async (query: string, category?: TagCategory, limit: number = 10): Promise<TagSuggestion[]> => {
    const params = new URLSearchParams({ q: query, limit: limit.toString() });
    if (category) params.append("category", category);
    const res = await safeFetch(`${API_BASE_URL}/gallery/tags/suggest?${params.toString()}`);
    return res.json();
};

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
    return res.json();
};

// ------------------------------------------------------------------ #
// Tag Dashboard APIs
// ------------------------------------------------------------------ #

// TagStat and TagStats are now generated — re-exported from api-types-bridge as TagStatsInfo → TagStats

export const getTagStats = async (): Promise<TagStatsInfo> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/tags/stats`);
    return res.json();
};

export const getUntaggedFiles = async (page: number = 1, perPage: number = 50): Promise<UntaggedFilesResponse> => {
    const params = new URLSearchParams({ page: page.toString(), per_page: perPage.toString() });
    const res = await safeFetch(`${API_BASE_URL}/gallery/untagged?${params.toString()}`);
    return res.json();
};

export const renameTag = async (oldTag: string, newTag: string, category: TagCategory): Promise<{ renamed_count: number; merged_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/gallery/tags/rename`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ old_tag: oldTag, new_tag: newTag, category }),
    });
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
    return res.json();
};

export const bulkRescan = async (fileIds: number[], mode: RescanMode = "append"): Promise<{ status: string; job_id: number; file_count: number }> => {
    const res = await safeFetch(`${API_BASE_URL}/media/bulk-rescan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_ids: fileIds, mode }),
    });
    return res.json();
};
// ------------------------------------------------------------------ #
// Insights APIs
// ------------------------------------------------------------------ #

export const getInsights = async (): Promise<InsightsResponse> => {
    const res = await safeFetch(`${API_BASE_URL}/insights`);
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
    return res.json();
};

export const getScenes = async (fileId: number): Promise<SceneInfo[]> => {
    const res = await safeFetch(`${API_BASE_URL}/media/${fileId}/scenes`);
    return res.json();
};

export const deleteScenes = async (fileId: number): Promise<{ success: boolean; deleted_count: number }> => {
    const res = await fetch(`${API_BASE_URL}/scenes/${fileId}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to delete scenes");
    return res.json();
};

export const searchScenes = async (query: string, topK: number = 20): Promise<SceneSearchInfo[]> => {
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
    return res.json();
};

export const resetDemo = async (): Promise<{ status: string }> => {
    const res = await safeFetch(`${API_BASE_URL}/demo/reset`, { method: "POST" });
    return res.json();
};

export const getDemoStatus = async (): Promise<{ demo_mode: boolean }> => {
    const res = await safeFetch(`${API_BASE_URL}/demo/status`);
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
    return res.json();
};

export const getPrivacyStorage = async (): Promise<PrivacyStorage> => {
    const res = await safeFetch(`${API_BASE_URL}/privacy/storage`);
    return res.json();
};

