import React, { useState, useEffect, useRef } from "react"
import { useTranslations } from "next-intl"
import { getModelStatuses, ModelStatus } from "@/lib/api"
import { ShieldCheck, Wifi, WifiOff, CheckCircle2, AlertCircle, Loader2, ListFilter, Trash2, Globe, Lock, ShieldAlert } from "lucide-react"
import { useNetworkLog } from "@/stores/networkLogStore"

export function NetworkPrivacyUI() {
    const t = useTranslations('settings.privacy');
    const tp = useTranslations('privacy');
    const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)
    const [models, setModels] = useState<ModelStatus[]>([])
    const [loading, setLoading] = useState(true)
    const { logs, clearLog } = useNetworkLog()
    const logContainerRef = useRef<HTMLDivElement>(null)

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

    // Auto-scroll to bottom when logs change
    useEffect(() => {
        if (logContainerRef.current) {
            logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
        }
    }, [logs])

    const downloadedCount = models.filter(m => m.is_downloaded).length
    const allDownloaded = models.length > 0 && downloadedCount === models.length

    return (
        <div className="space-y-6">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl">
                <div className="p-6 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-center">
                    <div>
                        <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100">
                            <ShieldCheck className="w-4 h-4 text-indigo-500" />
                            {t('title')}
                        </h3>
                        <p className="text-xs text-zinc-500 mt-1">{t('subtitle')}</p>
                    </div>
                </div>

                <div className="p-6 space-y-6">
                    {/* Status Indicator */}
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-zinc-400">{t('connectionStatus')}</span>
                        <div className="flex items-center gap-2 bg-zinc-950 px-3 py-1.5 rounded-full border border-zinc-800">
                            <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]'}`} />
                            <span className={`text-[10px] font-bold uppercase tracking-wider ${isOnline ? 'text-green-400' : 'text-red-400'}`}>
                                {isOnline ? t('online') : t('offline')}
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
                                <p className="text-xs font-bold text-zinc-200">{t('localFirst')}</p>
                                <p className="text-[11px] text-zinc-500 leading-relaxed">
                                    {t('localFirstDesc')}
                                </p>
                            </div>
                        </div>

                        {loading ? (
                            <div className="flex items-center gap-2 text-[10px] text-zinc-600 px-1">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                {t('checkingModels')}
                            </div>
                        ) : allDownloaded ? (
                            <div className="flex items-center gap-2 text-[10px] text-green-500 font-bold uppercase tracking-wide bg-green-500/5 px-2 py-1 rounded-md border border-green-500/10">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                {t('allCached')}
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 text-[10px] text-amber-500 font-bold uppercase tracking-wide bg-amber-500/5 px-2 py-1 rounded-md border border-amber-500/10">
                                <AlertCircle className="w-3.5 h-3.5" />
                                {t('partialCached', { count: downloadedCount, total: models.length })}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Network Activity Log */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl">
                <div className="p-6 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-center">
                    <div>
                        <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100">
                            <ListFilter className="w-4 h-4 text-indigo-500" />
                            {tp('networkLog')}
                        </h3>
                        <p className="text-xs text-zinc-500 mt-1">{tp('entries', { count: logs.length })}</p>
                    </div>
                    <button
                        onClick={clearLog}
                        className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-red-400 transition-colors"
                        title={tp('clearLog')}
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>

                <div
                    ref={logContainerRef}
                    className="max-h-[300px] overflow-y-auto bg-zinc-950/50"
                >
                    <table className="w-full text-left border-collapse">
                        <thead className="sticky top-0 bg-zinc-900 z-10">
                            <tr className="border-b border-zinc-800">
                                <th className="px-4 py-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">{tp('timestamp')}</th>
                                <th className="px-4 py-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">{tp('method')}</th>
                                <th className="px-4 py-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">{tp('url')}</th>
                                <th className="px-4 py-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider text-right">{tp('status')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/50">
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-4 py-12 text-center text-xs text-zinc-600 italic">
                                        {tp('noActivity')}
                                    </td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-zinc-800/30 transition-colors group">
                                        <td className="px-4 py-2 text-[10px] font-mono text-zinc-500">{log.timestamp}</td>
                                        <td className="px-4 py-2">
                                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                                                {log.method}
                                            </span>
                                        </td>
                                        <td className="px-4 py-2 text-[11px] text-zinc-300 font-medium truncate max-w-[200px]">
                                            {log.url}
                                        </td>
                                        <td className="px-4 py-2 text-right">
                                            <div className="flex items-center justify-end gap-1.5">
                                                <span className="text-[9px] text-zinc-600 font-mono">{log.duration}ms</span>
                                                {log.status === 'blocked' ? (
                                                    <span className="flex items-center gap-1 text-[9px] font-black uppercase text-red-500 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
                                                        <ShieldAlert className="w-2.5 h-2.5" />
                                                        {tp('blocked')}
                                                    </span>
                                                ) : !log.isLocal ? (
                                                    <span className="flex items-center gap-1 text-[9px] font-black uppercase text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                                                        <Globe className="w-2.5 h-2.5" />
                                                        {tp('external')} ({log.status})
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center gap-1 text-[9px] font-black uppercase text-green-500 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                                                        <Lock className="w-2.5 h-2.5" />
                                                        {tp('local')} ({log.status})
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
