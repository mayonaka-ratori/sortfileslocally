import type { components } from "@/generated/api-types";

// Explicit mappings from generated types back to manual interface names

export type MediaItem = components["schemas"]["MediaItemResponse"];
export type SearchFilters = components["schemas"]["SearchFilters"];
export type HybridSearchResponse = components["schemas"]["HybridSearchResponse"];
export type ScanStatus = components["schemas"]["ScanStatus"];
export type ScanJobInfo = components["schemas"]["ScanJobResponse"];
export type ScanErrorInfo = components["schemas"]["ScanErrorResponse"];
export type ModelStatus = components["schemas"]["ModelStatusResponse"];
export type ReverseSearchResult = components["schemas"]["ReverseSearchResponse"];
export type ExportResult = components["schemas"]["ExportResultResponse"];
export type Album = components["schemas"]["AlbumResponse"];
export type TagSuggestion = components["schemas"]["TagSuggestion"];
export type BulkTagResponse = components["schemas"]["BulkTagResponse"];
export type UntaggedFilesResponse = components["schemas"]["UntaggedFilesResponse"];
export type InsightItem = components["schemas"]["InsightItem"];
export type InsightsResponse = components["schemas"]["InsightsResponse"];
export type FaceData = components["schemas"]["FaceResponse"];
