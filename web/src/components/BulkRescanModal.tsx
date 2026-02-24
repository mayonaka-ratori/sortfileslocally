"use client"

import React, { useState, useEffect } from "react"
import { X, Loader2, AlertCircle, RefreshCw, CheckCircle2 } from "lucide-react"
import { MediaItem, RescanMode, bulkRescan, getScanStatus, ScanStatus } from "@/lib/api"

interface BulkRescanModalProps {
    selectedItems: MediaItem[]
    onClose: () => void
    onSuccess: () => void
}

export function BulkRescanModal({ selectedItems, onClose, onSuccess }: BulkRescanModalProps) {
    const [mode, setMode] = useState<RescanMode>("append")
    const [isStarting, setIsStarting] = useState(false)
    const [jobId, setJobId] = useState<number | null>(null)
    const [status, setStatus] = useState<ScanStatus | null>(null)
    const [error, setError] = useState<string | null>(null)

    const count = selectedItems.length
    const fileIds = selectedItems.map(item => item.id)

    // Polling for status if job is running
    useEffect(() => {
        let interval: NodeJS.Timeout
        if (jobId && !status?.error && (status?.progress_percent ?? 0) < 100) {
            interval = setInterval(async () => {
                try {
                    const s = await getScanStatus(jobId)
                    setStatus(s)
                    if (s.progress_percent >= 100 && !s.is_active) {
                        clearInterval(interval)
                    }
                } catch (err) {
                    console.error("Status check failed", err)
                }
            }, 1000)
        }
        return () => clearInterval(interval)
    }, [jobId, status])

    const handleStart = async () => {
        setIsStarting(true)
        setError(null)
        try {
            const res = await bulkRescan(fileIds, mode)
            setJobId(res.job_id)
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to start rescan")
            setIsStarting(false)
        }
    }

    if (jobId) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                    <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50">
                        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-400">
                            Rescanning {count} files
                        </h2>
                        {(!status || status.progress_percent >= 100) && (
                            <button onClick={onClose} className="p-1 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-white">
                                <X className="w-5 h-5" />
                            </button>
                        )}
                    </div>
                    <div className="p-8 flex flex-col items-center text-center space-y-6">
                        {status?.progress_percent === 100 ? (
                            <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center text-green-500 mb-2">
                                <CheckCircle2 className="w-10 h-10" />
                            </div>
                        ) : (
                            <div className="relative w-16 h-16 flex items-center justify-center">
                                <Loader2 className="w-12 h-12 animate-spin text-indigo-500" />
                                <span className="absolute text-[10px] font-bold text-white">
                                    {Math.round(status?.progress_percent || 0)}%
                                </span>
                            </div>
                        )}

                        <div className="space-y-1">
                            <h3 className="text-white font-bold">
                                {status?.progress_percent === 100 ? "Rescan Complete!" : "Processing AI Tags..."}
                            </h3>
                            <p className="text-zinc-500 text-xs truncate max-w-[280px]">
                                {status?.current_file || "Preparing models..."}
                            </p>
                        </div>

                        <div className="w-full bg-zinc-950 h-2 rounded-full overflow-hidden border border-zinc-800">
                            <div
                                className="h-full bg-indigo-600 transition-all duration-500"
                                style={{ width: `${status?.progress_percent || 0}%` }}
                            />
                        </div>

                        {status?.progress_percent === 100 && (
                            <button
                                onClick={() => {
                                    onSuccess()
                                    onClose()
                                }}
                                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-900/20 transition-all"
                            >
                                Done
                            </button>
                        )}
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50">
                    <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-400">
                        AI Rescan ({count} files)
                    </h2>
                    <button onClick={onClose} className="p-1 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-white">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    <div className="p-4 bg-indigo-600/10 border border-indigo-500/20 rounded-xl flex gap-4">
                        <div className="p-2 bg-indigo-600 rounded-lg text-white h-fit">
                            <RefreshCw className="w-5 h-5" />
                        </div>
                        <div className="space-y-1">
                            <p className="text-xs text-indigo-200 leading-relaxed">
                                This will regenerate <strong>tags, captions, and CLIP vectors</strong> for the selected files using the latest AI models.
                            </p>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Rescan Mode</label>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setMode("append")}
                                className={`flex-1 p-3 rounded-xl border flex flex-col gap-1 transition-all ${mode === "append" ? "bg-indigo-600/10 border-indigo-500 ring-1 ring-indigo-500" : "bg-zinc-950 border-zinc-800 hover:border-zinc-700"}`}
                            >
                                <span className={`text-xs font-bold ${mode === "append" ? "text-indigo-400" : "text-zinc-300"}`}>Add Missing</span>
                                <span className="text-[10px] text-zinc-500">Keep existing tags</span>
                            </button>
                            <button
                                onClick={() => setMode("overwrite")}
                                className={`flex-1 p-3 rounded-xl border flex flex-col gap-1 transition-all ${mode === "overwrite" ? "bg-red-500/10 border-red-500 ring-1 ring-red-500" : "bg-zinc-950 border-zinc-800 hover:border-zinc-700"}`}
                            >
                                <span className={`text-xs font-bold ${mode === "overwrite" ? "text-red-400" : "text-zinc-300"}`}>Overwrite</span>
                                <span className="text-[10px] text-zinc-500">Replace everything</span>
                            </button>
                        </div>
                    </div>

                    {mode === "overwrite" && (
                        <div className="flex items-start gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-[10px]">
                            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                            <p>WARNING: Overwrite will delete all existing AI-generated tags and captions for these files.</p>
                        </div>
                    )}

                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs text-center animate-in fade-in">
                            {error}
                        </div>
                    )}
                </div>

                <div className="p-4 bg-zinc-950/50 border-t border-zinc-800 flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 py-2.5 rounded-xl text-sm font-bold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleStart}
                        disabled={isStarting}
                        className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-900/20 transition-all flex items-center justify-center gap-2"
                    >
                        {isStarting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Start Rescan"}
                    </button>
                </div>
            </div>
        </div>
    )
}
