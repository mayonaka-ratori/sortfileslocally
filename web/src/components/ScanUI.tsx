import React, { useState, useEffect } from "react";
import { startScan, getScanStatus } from "@/lib/api";
import { FolderSearch, AlertTriangle, AlertCircle, Play, Loader2, RefreshCw } from "lucide-react";

export function ScanUI() {
    const [path, setPath] = useState("");
    const [forceReprocess, setForceReprocess] = useState(false);

    const [status, setStatus] = useState<any>(null);
    const [error, setError] = useState("");
    const [starting, setStarting] = useState(false);

    useEffect(() => {
        let timer: NodeJS.Timeout;
        const fetchStatus = async () => {
            try {
                const data = await getScanStatus();
                setStatus(data);
                // Poll faster when scan is active, slower when idle
                timer = setTimeout(fetchStatus, data?.is_active ? 1000 : 8000);
            } catch (err) {
                console.error("Failed to fetch scan status", err);
                timer = setTimeout(fetchStatus, 8000);
            }
        };

        fetchStatus();
        return () => clearTimeout(timer);
    }, []);

    const handleStart = async () => {
        if (!path.trim()) return;
        setStarting(true);
        setError("");

        try {
            await startScan(path.trim(), forceReprocess);
        } catch (err: any) {
            setError(err.message || "Failed to start scan");
        } finally {
            setStarting(false);
        }
    };

    const formatETA = (seconds: number) => {
        if (!seconds || seconds <= 0) return "--:--";
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}m ${s}s`;
    };

    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex flex-col gap-4 text-sm text-zinc-300 shadow-md">
            <div className="flex items-center gap-2 font-bold text-zinc-100 uppercase tracking-wider text-xs border-b border-zinc-800 pb-2">
                <FolderSearch className="w-4 h-4 text-indigo-400" />
                Folder Scanner
            </div>

            <div className="flex flex-col gap-2">
                <label className="text-xs text-zinc-500 font-medium">Source Directory</label>
                <input
                    type="text"
                    value={path}
                    onChange={(e) => setPath(e.target.value)}
                    placeholder="Enter directory path..."
                    className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 focus:outline-none focus:border-indigo-500 transition-colors placeholder-zinc-700 font-mono text-xs text-zinc-300"
                    disabled={status?.is_active}
                />
            </div>

            <div className="flex items-center gap-2">
                <input
                    type="checkbox"
                    id="forceReprocess"
                    checked={forceReprocess}
                    onChange={(e) => setForceReprocess(e.target.checked)}
                    disabled={status?.is_active}
                    className="rounded border-zinc-700 bg-zinc-900 text-indigo-500 focus:ring-indigo-500/30"
                />
                <label htmlFor="forceReprocess" className="text-xs text-zinc-400 cursor-pointer select-none">
                    Force Reprocess (Overwrites existing AI data)
                </label>
            </div>

            {error && (
                <div className="bg-red-500/10 text-red-400 p-2 rounded flex items-start gap-2 text-xs">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                </div>
            )}

            {status?.error && (
                <div className="bg-red-500/10 text-red-400 p-2 rounded flex items-start gap-2 text-xs">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>Background Scan Error: {status.error}</span>
                </div>
            )}

            {!status?.is_active ? (
                <button
                    onClick={handleStart}
                    disabled={starting || !path.trim()}
                    className="mt-2 w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-xs shadow-lg shadow-indigo-900/20"
                >
                    {starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    Start Scan
                </button>
            ) : (
                <div className="mt-2 flex flex-col gap-3 bg-zinc-950 rounded-lg p-3 border border-indigo-900/50 relative overflow-hidden">
                    <div className="flex items-center justify-between text-xs text-indigo-300 font-medium">
                        <div className="flex items-center gap-1.5 flex-1 min-w-0">
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span className="truncate">Scanning: {status?.current_file ? status.current_file.split(/[/\\]/).pop() : "Preparing..."}</span>
                        </div>
                        <span className="shrink-0 pl-2">{status?.progress_percent?.toFixed(1) || 0}%</span>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-zinc-900 rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300 ease-out shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                            style={{ width: `${Math.min(100, Math.max(0, status?.progress_percent || 0))}%` }}
                        />
                    </div>

                    <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
                        <span>{status?.processed_count || 0} / {status?.total_files || 0} Files</span>
                        <span>ETA: {formatETA(status?.eta_seconds)}</span>
                    </div>
                </div>
            )}
        </div>
    );
}
