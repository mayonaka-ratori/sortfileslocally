"use client";
/**
 * useScanProgress — Custom React hook for SSE-based scan progress.
 *
 * Connects to GET /scan/status/stream/{jobId} (text/event-stream).
 * Falls back to polling after 3 consecutive SSE failures.
 * Cleans up the EventSource on unmount or when jobId becomes null.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import type { ScanSSEPayload, ScanSSEEvent } from "@/lib/sse-types";
import { getScanStatus } from "@/lib/api";

// Resolve API base at runtime (matches api.ts initApiBase behaviour)
function getApiBase(): string {
    if (typeof window !== "undefined") {
        const w = window as Window & { __LCP_API_BASE?: string };
        if (w.__LCP_API_BASE) return w.__LCP_API_BASE;
    }
    return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

/** Exponential backoff delays (ms) for SSE reconnection */
const BACKOFF_MS = [1000, 2000, 4000, 8000, 16000, 30000];

/** Maximum consecutive SSE errors before falling back to polling */
const MAX_SSE_ERRORS = 3;

/** Polling interval when in fallback mode (ms) */
const POLL_INTERVAL_MS = 1500;

export type ConnectionMode = "sse" | "poll" | "idle";

export interface UseScanProgressResult {
    /** Latest SSE payload from the server, or null if not yet received */
    status: ScanSSEPayload | null;
    /** True when the EventSource is in OPEN state */
    isConnected: boolean;
    /** Connection error message (null when healthy) */
    error: string | null;
    /** Current connection strategy */
    connectionMode: ConnectionMode;
}

export function useScanProgress(
    jobId: number | null,
    onComplete?: () => void
): UseScanProgressResult {
    const [status, setStatus] = useState<ScanSSEPayload | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [connectionMode, setConnectionMode] = useState<ConnectionMode>("idle");

    // Stable refs so callbacks don't cause effect re-runs
    const esRef = useRef<EventSource | null>(null);
    const retryCountRef = useRef(0);
    const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const onCompleteRef = useRef(onComplete);
    onCompleteRef.current = onComplete;
    const cancelledRef = useRef(false);

    // ── Cleanup helper ──────────────────────────────────────────────────
    const cleanup = useCallback(() => {
        esRef.current?.close();
        esRef.current = null;
        if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
        if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
        retryTimerRef.current = null;
        pollTimerRef.current = null;
        setIsConnected(false);
    }, []);

    // ── Polling fallback ────────────────────────────────────────────────
    const startPolling = useCallback((jid: number) => {
        setConnectionMode("poll");

        const poll = async () => {
            if (cancelledRef.current) return;
            try {
                // getScanStatus returns ScanStatus from state.py — shape matches ScanSSEEvent
                const data = await getScanStatus(jid);
                if (cancelledRef.current) return;

                // Cast to ScanSSEEvent since the shapes are identical  
                const payload = data as unknown as ScanSSEEvent;
                setStatus(payload);

                if (!payload.is_active) {
                    onCompleteRef.current?.();
                    return; // Stop polling
                }
            } catch {
                // Ignore transient errors, keep polling
            }
            if (!cancelledRef.current) {
                pollTimerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
            }
        };

        poll();
    }, []);

    // ── Main effect ─────────────────────────────────────────────────────
    useEffect(() => {
        if (!jobId) {
            cleanup();
            setConnectionMode("idle");
            setStatus(null);
            setError(null);
            return;
        }

        cancelledRef.current = false;
        retryCountRef.current = 0;

        const connect = () => {
            if (cancelledRef.current) return;

            const url = `${getApiBase()}/scan/status/stream/${jobId}`;

            // EventSource is not available in all environments (e.g. server-side)
            if (typeof EventSource === "undefined") {
                startPolling(jobId);
                return;
            }

            const es = new EventSource(url);
            esRef.current = es;
            setConnectionMode("sse");

            es.onopen = () => {
                if (cancelledRef.current) { es.close(); return; }
                setIsConnected(true);
                setError(null);
                retryCountRef.current = 0;
            };

            es.onmessage = (ev: MessageEvent<string>) => {
                if (cancelledRef.current) return;
                try {
                    const payload: ScanSSEPayload = JSON.parse(ev.data);
                    setStatus(payload);

                    // Check if stream is done
                    const p = payload as Partial<ScanSSEEvent & { status: string }>;
                    if (p.is_active === false || p.status === "unknown") {
                        es.close();
                        esRef.current = null;
                        setIsConnected(false);
                        onCompleteRef.current?.();
                    }
                } catch {
                    // Ignore malformed JSON frames
                }
            };

            es.onerror = () => {
                es.close();
                esRef.current = null;
                setIsConnected(false);
                if (cancelledRef.current) return;

                retryCountRef.current += 1;

                if (retryCountRef.current > MAX_SSE_ERRORS) {
                    // Give up on SSE and fall back to polling
                    setError("SSE接続失敗 — ポーリングに切り替えました");
                    startPolling(jobId);
                    return;
                }

                // Exponential backoff before retrying SSE
                const delay =
                    BACKOFF_MS[
                    Math.min(retryCountRef.current - 1, BACKOFF_MS.length - 1)
                    ];
                retryTimerRef.current = setTimeout(connect, delay);
            };
        };

        connect();

        return () => {
            cancelledRef.current = true;
            cleanup();
            setConnectionMode("idle");
        };
    }, [jobId, cleanup, startPolling]);

    return { status, isConnected, error, connectionMode };
}
