/**
 * SSE event types for scan progress streaming.
 *
 * These types are NOT part of the OpenAPI schema because Server-Sent Events
 * cannot be described in OpenAPI 3.x. Maintain this file manually, keeping
 * the shape in sync with `event_generator()` in server/routers/scan.py.
 *
 * Endpoint: GET /scan/status/stream/{job_id}
 * Media type: text/event-stream
 */

/** Emitted while a scan job is active or has just finished. */
export interface ScanSSEEvent {
    is_active: boolean;
    error: string | null;
    current_file: string;
    processed_count: number;
    total_files: number;
    progress_percent: number;
    eta_seconds: number;
    last_updated: number;
}

/** Emitted when the job_id is not found in active memory (completed / never started). */
export interface ScanSSEUnknown {
    status: 'unknown';
    is_active: false;
}

/** Union of all possible SSE payloads from the scan stream. */
export type ScanSSEPayload = ScanSSEEvent | ScanSSEUnknown;
