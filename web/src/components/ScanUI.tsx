import React, { useState, useEffect, useRef } from "react";
import {
    startScan, resumeScan, getScanStatus, getLatestScanJob,
    browseFolder, ScanStatus, ScanJobInfo,
} from "@/lib/api";
import {
    FolderSearch, AlertTriangle, AlertCircle, Play,
    Loader2, RefreshCw, RotateCcw, CheckCircle2,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { ScanSummary } from "@/components/ScanSummary";
import { toast } from "sonner";

// ScanUI now optionally accepts an initial path (e.g. from Setup Wizard)
// and an onComplete callback for the Setup Wizard integration.
interface ScanUIProps {
    initialPath?: string;
    onComplete?: (job: ScanJobInfo) => void;
}

export function ScanUI({ initialPath, onComplete }: ScanUIProps) {
    const t = useTranslations("scan");
    const commonT = useTranslations("common");

    const [path, setPath] = useState(initialPath ?? "");
    const [forceReprocess, setForceReprocess] = useState(false);
    const [status, setStatus] = useState<ScanStatus | null>(null);
    const [error, setError] = useState("");
    const [starting, setStarting] = useState(false);
    const [jobId, setJobId] = useState<number | null>(null);

    // Completed job info (for ScanSummary)
    const [completedJob, setCompletedJob] = useState<ScanJobInfo | null>(null);
    // Per-file activity log (last 8)
    const [recentFiles, setRecentFiles] = useState<string[]>([]);
    // Whether the latest job is resumable
    const [latestJob, setLatestJob] = useState<ScanJobInfo | null>(null);
    const [resuming, setResuming] = useState(false);

    const prevFileRef = useRef<string>("");

    // On mount: check if there's a resumable latest job
    useEffect(() => {
        getLatestScanJob()
            .then((j) => {
                if (j && (j.status === "failed" || j.status === "running")) {
                    setLatestJob(j);
                    if (j.status === "running") {
                        setJobId(j.id);
                    }
                }
            })
            .catch((err) => {
                console.error("Failed to fetch latest scan job", err);
            });
    }, []);

    // Poll scan status
    useEffect(() => {
        let timer: NodeJS.Timeout;

        const fetchStatus = async () => {
            if (!jobId) {
                timer = setTimeout(fetchStatus, 8000);
                return;
            }
            try {
                const data = await getScanStatus(jobId);
                setStatus(data);

                // Update recent-files log when filename changes
                if (data?.current_file && data.current_file !== prevFileRef.current) {
                    prevFileRef.current = data.current_file;
                    const basename = data.current_file.split(/[/\\]/).pop() || data.current_file;
                    setRecentFiles((prev) => [basename, ...prev].slice(0, 8));
                }

                if (!data?.is_active) {
                    // Scan finished: fetch the full job info for summary
                    try {
                        const fullJob = await getLatestScanJob();
                        if (fullJob && fullJob.id === jobId) {
                            setCompletedJob(fullJob);
                            onComplete?.(fullJob);
                        }
                    } catch (err) {
                        console.error("Failed to fetch completed job detail", err);
                        toast.error(commonT("actionFailed"));
                    }
                    timer = setTimeout(fetchStatus, 8000);
                } else {
                    timer = setTimeout(fetchStatus, 1000);
                }
            } catch (err) {
                console.error("Failed to fetch scan status", err);
                timer = setTimeout(fetchStatus, 5000);
            }
        };

        fetchStatus();
        return () => clearTimeout(timer);
    }, [jobId, onComplete, commonT]);

    const handleStart = async () => {
        if (!path.trim()) return;
        setStarting(true);
        setError("");
        setCompletedJob(null);
        setRecentFiles([]);
        prevFileRef.current = "";

        try {
            const res = await startScan(path.trim(), forceReprocess);
            if (res.job?.id) {
                setJobId(res.job.id);
                setLatestJob(null);
            }
        } catch (err) {
            setError((err as Error).message || t("startError"));
        } finally {
            setStarting(false);
        }
    };

    const handleResume = async () => {
        if (!latestJob) return;
        setResuming(true);
        setError("");
        setCompletedJob(null);
        setRecentFiles([]);
        prevFileRef.current = "";

        try {
            const res = await resumeScan(latestJob.id);
            if (res.job?.id) {
                setJobId(res.job.id);
                setLatestJob(null);
            }
        } catch (err) {
            setError((err as Error).message || t("resumeError"));
        } finally {
            setResuming(false);
        }
    };

    const handleReset = () => {
        setCompletedJob(null);
        setRecentFiles([]);
        setJobId(null);
        setStatus(null);
        prevFileRef.current = "";
    };

    const formatHumanEta = (seconds: number): string => {
        if (!seconds || seconds <= 0) return "";
        const mins = Math.ceil(seconds / 60);
        if (mins < 1) return t("humanEtaSeconds");
        return t("humanEta", { mins });
    };

    // ── Completed state ────────────────────────────────────────────────
    if (completedJob) {
        return (
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 shadow-md">
                <ScanSummary job={completedJob} onScanMore={handleReset} />
            </div>
        );
    }

    const isActive = status?.is_active ?? false;

    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex flex-col gap-4 text-sm text-zinc-300 shadow-md">
            {/* Header */}
            <div className="flex items-center gap-2 font-bold text-zinc-100 uppercase tracking-wider text-xs border-b border-zinc-800 pb-2">
                <FolderSearch className="w-4 h-4 text-indigo-400" />
                {t("title")}
            </div>

            {/* Folder input */}
            <div className="flex flex-col gap-2">
                <label className="text-xs text-zinc-500 font-medium">{t("sourceDir")}</label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={path}
                        onChange={(e) => setPath(e.target.value)}
                        placeholder={t("placeholder")}
                        className="flex-1 bg-zinc-950 border border-zinc-800 rounded px-3 py-2 focus:outline-none focus:border-indigo-500 transition-colors placeholder-zinc-700 font-mono text-xs text-zinc-300"
                        disabled={isActive}
                        id="scan-folder-input"
                    />
                    <button
                        id="scan-browse-btn"
                        onClick={async () => {
                            try {
                                const { path: selectedPath, cancelled } = await browseFolder();
                                if (!cancelled && selectedPath) {
                                    setPath(selectedPath);
                                }
                            } catch (err) {
                                console.error("Browse folder failed", err);
                                setError(t("pickerError", { error: (err as Error).message }));
                            }
                        }}
                        disabled={isActive}
                        className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-2 rounded text-xs font-medium transition-colors border border-zinc-700 disabled:opacity-50"
                    >
                        {commonT("browse")}
                    </button>
                </div>
            </div>

            {/* Force reprocess */}
            <div className="flex items-center gap-2">
                <input
                    type="checkbox"
                    id="forceReprocess"
                    checked={forceReprocess}
                    onChange={(e) => setForceReprocess(e.target.checked)}
                    disabled={isActive}
                    className="rounded border-zinc-700 bg-zinc-900 text-indigo-500 focus:ring-indigo-500/30"
                />
                <label htmlFor="forceReprocess" className="text-xs text-zinc-400 cursor-pointer select-none">
                    {t("forceReprocess")}
                </label>
            </div>

            {/* Error banners */}
            {error && (
                <div className="bg-red-500/10 text-red-400 p-2 rounded flex items-start gap-2 text-xs">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{error}</span>
                </div>
            )}
            {status?.error && (
                <div className="bg-red-500/10 text-red-400 p-2 rounded flex items-start gap-2 text-xs">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{t("bgError", { error: status.error })}</span>
                </div>
            )}

            {/* Resume hint — show when there's a failed job and we're not currently active */}
            {!isActive && latestJob && latestJob.status === "failed" && !resuming && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 flex flex-col gap-2">
                    <p className="text-xs text-amber-300">{t("resumeHint")}</p>
                    <button
                        id="scan-resume-btn"
                        onClick={handleResume}
                        className="flex items-center gap-1.5 self-start bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors border border-amber-500/30"
                    >
                        <RotateCcw className="w-3.5 h-3.5" />
                        {t("resumeButton")}
                    </button>
                </div>
            )}

            {/* Active-scan: progress or idle start button */}
            {!isActive ? (
                <button
                    id="scan-start-btn"
                    onClick={handleStart}
                    disabled={starting || resuming || !path.trim()}
                    className="mt-2 w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-xs shadow-lg shadow-indigo-900/20"
                >
                    {starting || resuming
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <Play className="w-4 h-4" />}
                    {t("startButton")}
                </button>
            ) : (
                <div className="mt-2 flex flex-col gap-3 bg-zinc-950 rounded-lg p-3 border border-indigo-900/50 relative overflow-hidden">
                    {/* Current file + percent */}
                    <div className="flex items-center justify-between text-xs text-indigo-300 font-medium">
                        <div className="flex items-center gap-1.5 flex-1 min-w-0">
                            <RefreshCw className="w-3.5 h-3.5 animate-spin shrink-0" />
                            <span className="truncate">
                                {t("scanning", {
                                    file: status?.current_file
                                        ? (status.current_file.split(/[/\\]/).pop() || "")
                                        : t("preparing"),
                                })}
                            </span>
                        </div>
                        <span className="shrink-0 pl-2">{status?.progress_percent?.toFixed(1) || 0}%</span>
                    </div>

                    {/* Progress bar */}
                    <div className="w-full bg-zinc-900 rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300 ease-out shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                            style={{ width: `${Math.min(100, Math.max(0, status?.progress_percent || 0))}%` }}
                        />
                    </div>

                    {/* Count + ETA row */}
                    <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
                        <span>{t("fileCount", { count: status?.processed_count || 0, total: status?.total_files || 0 })}</span>
                        <span>{formatHumanEta(status?.eta_seconds ?? 0)}</span>
                    </div>

                    {/* Per-file recent log */}
                    {recentFiles.length > 0 && (
                        <div className="mt-1">
                            <p className="text-[9px] text-zinc-600 uppercase tracking-widest font-bold mb-1">
                                {t("recentFiles")}
                            </p>
                            <div className="flex flex-col gap-0.5 max-h-[80px] overflow-y-auto pr-1">
                                {recentFiles.map((f, i) => (
                                    <div
                                        key={i}
                                        className={`text-[10px] font-mono truncate transition-colors ${i === 0 ? "text-indigo-300" : "text-zinc-600"
                                            }`}
                                    >
                                        {i === 0 && (
                                            <CheckCircle2 className="inline w-2.5 h-2.5 mr-1 text-emerald-500" />
                                        )}
                                        {f}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
