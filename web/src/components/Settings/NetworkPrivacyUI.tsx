"use client"

import React, { useState, useEffect } from "react"
import { getModelStatuses, ModelStatus } from "@/lib/api"
import { ShieldCheck, Wifi, WifiOff, CheckCircle2, AlertCircle, Loader2 } from "lucide-react"

export function NetworkPrivacyUI() {
    const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)
    const [models, setModels] = useState<ModelStatus[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const handleStatusChange = () => setIsOnline(navigator.onLine)
        window.addEventListener('online', handleStatusChange)
        window.addEventListener('offline', handleStatusChange)

        getModelStatuses()
            .then(setModels)
            .finally(() => setLoading(false))

        return () => {
            window.removeEventListener('online', handleStatusChange)
            window.removeEventListener('offline', handleStatusChange)
        }
    }, [])

    const downloadedCount = models.filter(m => m.is_downloaded).length
    const allDownloaded = models.length > 0 && downloadedCount === models.length

    return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden">
            <div className="p-6 border-b border-zinc-800 bg-zinc-900/50">
                <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100">
                    <ShieldCheck className="w-4 h-4 text-indigo-500" />
                    Network & Privacy
                </h3>
                <p className="text-xs text-zinc-500 mt-1">LocalCuratorPrime runs entirely on your device. No data is sent to external servers.</p>
            </div>

            <div className="p-6 space-y-6">
                {/* Status Indicator */}
                <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-zinc-400">Connection Status</span>
                    <div className="flex items-center gap-2 bg-zinc-950 px-3 py-1.5 rounded-full border border-zinc-800">
                        <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]'}`} />
                        <span className={`text-[10px] font-bold uppercase tracking-wider ${isOnline ? 'text-green-400' : 'text-red-400'}`}>
                            {isOnline ? 'Online' : 'Offline'}
                        </span>
                        {isOnline ? <Wifi className="w-3 h-3 text-zinc-600" /> : <WifiOff className="w-3 h-3 text-zinc-600" />}
                    </div>
                </div>

                {/* Local Guarantee Box */}
                <div className="p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-xl space-y-3">
                    <div className="flex gap-3">
                        <div className="p-2 bg-indigo-500/10 rounded-lg shrink-0">
                            <ShieldCheck className="w-5 h-5 text-indigo-400" />
                        </div>
                        <div className="space-y-1">
                            <p className="text-xs font-bold text-zinc-200">Local-First Architecture</p>
                            <p className="text-[11px] text-zinc-500 leading-relaxed">
                                All media analysis, face detection, and semantic search happen locally on your hardware. Even when online, your data never leaves this machine.
                            </p>
                        </div>
                    </div>

                    {loading ? (
                        <div className="flex items-center gap-2 text-[10px] text-zinc-600 px-1">
                            <Loader2 className="w-3 h-3 animate-spin" />
                            Checking model availability...
                        </div>
                    ) : allDownloaded ? (
                        <div className="flex items-center gap-2 text-[10px] text-green-500 font-bold uppercase tracking-wide bg-green-500/5 px-2 py-1 rounded-md border border-green-500/10">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            All AI models are cached locally. Full functionality available offline.
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 text-[10px] text-amber-500 font-bold uppercase tracking-wide bg-amber-500/5 px-2 py-1 rounded-md border border-amber-500/10">
                            <AlertCircle className="w-3.5 h-3.5" />
                            {downloadedCount} / {models.length} models downloaded. Some features may require internet to download missing weights.
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
