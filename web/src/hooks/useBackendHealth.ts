import { useEffect, useRef, useCallback } from 'react';
import { useBackendHealthStore, backendHealthStore } from '@/stores/backendHealthStore';
import { initApiBase } from '@/lib/api';

let API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
if (typeof window !== "undefined") {
    const w = window as { __LCP_API_BASE?: string };
    if (w.__LCP_API_BASE) API_BASE = w.__LCP_API_BASE;
}

const POLL_INTERVAL_FAST = 1000;
const POLL_INTERVAL_SLOW = 5000;
const MAX_FAILURES = 3;

export function useBackendHealth() {
    const { status, lastCheckedAt, error, setStatus, setLastCheckedAt } = useBackendHealthStore();
    const failuresRef = useRef(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);
    const isCheckingRef = useRef(false);

    const checkHealth = useCallback(async (isManualRetry = false) => {
        if (isCheckingRef.current) return;
        isCheckingRef.current = true;

        if (isManualRetry) {
            setStatus('recovering');
        }

        try {
            // Re-eval API_BASE in case it was set after load
            let currentApiBase = API_BASE;
            if (typeof window !== "undefined") {
                const w = window as { __LCP_API_BASE?: string };
                if (w.__LCP_API_BASE) currentApiBase = w.__LCP_API_BASE;
            }

            // Using standard fetch bypassing safeFetch to avoid cyclic global events
            const res = await fetch(`${currentApiBase}/health`, {
                method: 'GET',
                headers: { 'Cache-Control': 'no-cache' },
            });

            if (res.ok) {
                failuresRef.current = 0;
                setStatus('healthy');
            } else {
                throw new Error(`HTTP ${res.status}`);
            }
        } catch (err) {
            failuresRef.current += 1;
            const errMsg = err instanceof Error ? err.message : 'Unknown error';

            if (failuresRef.current >= MAX_FAILURES) {
                setStatus('unhealthy', errMsg);
            }
        } finally {
            setLastCheckedAt(Date.now());
            isCheckingRef.current = false;
        }
    }, [setStatus, setLastCheckedAt]);

    useEffect(() => {
        let isSubscribed = true;

        const loop = async () => {
            if (!isSubscribed) return;
            await checkHealth();
            if (!isSubscribed) return;

            // Poll faster if we are connecting or recovering, otherwise slowly
            const currentStatus = backendHealthStore.getState().status;
            const delay = (currentStatus === 'connecting' || currentStatus === 'recovering')
                ? POLL_INTERVAL_FAST
                : POLL_INTERVAL_SLOW;

            timerRef.current = setTimeout(loop, delay);
        };

        // Start loop
        loop();

        // Listen for force checks (e.g., from api.ts fetch failures)
        const handleForceCheck = () => {
            if (timerRef.current) clearTimeout(timerRef.current);
            checkHealth();
        };
        window.addEventListener('lcp:force-health-check', handleForceCheck);

        let unlistenRestart: (() => void) | null = null;
        if (typeof window !== 'undefined' && ('__TAURI__' in window || 'rpc' in window)) {
            import('@tauri-apps/api/event').then(({ listen }) => {
                listen('backend-restarted', async () => {
                    console.log('Tauri sidecar restarted, reloading API base port...');
                    await initApiBase();
                    checkHealth();
                }).then(unlisten => {
                    unlistenRestart = unlisten;
                }).catch(console.error);
            }).catch(e => {
                console.warn("Could not import tauri event listener", e);
            });
        }

        return () => {
            isSubscribed = false;
            if (timerRef.current) clearTimeout(timerRef.current);
            window.removeEventListener('lcp:force-health-check', handleForceCheck);
            if (unlistenRestart) unlistenRestart();
        };
    }, [checkHealth]);

    return {
        status,
        lastCheckedAt,
        error,
        retryNow: () => checkHealth(true)
    };
}
