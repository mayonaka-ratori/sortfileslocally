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
    audio_transcription?: any[];
    frame_descriptions?: any[];
    snippet?: string; // Optional field for holding search match text snippet
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

export const getScanStatus = async () => {
    const res = await fetch(`${API_BASE_URL}/scan/status`);
    if (!res.ok) throw new Error("Failed to fetch scan status");
    return res.json();
};
