"use client"

import React, { useState, useEffect, useRef } from "react"
import { useTranslations } from "next-intl"
import {
    getModelStatuses,
    ModelStatus,
    runPrivacyAudit,
    PrivacyAuditResult,
    getPrivacyStorage,
    PrivacyStorage
} from "@/lib/api"
import {
    ShieldCheck, CheckCircle2, AlertCircle,
    Loader2, Trash2, Globe, Lock, ShieldAlert,
    Database, HardDrive, Cpu, Activity, Search, ShieldX, Scan
} from "lucide-react"
import { useNetworkLog } from "@/stores/networkLogStore"
import { motion, AnimatePresence } from "framer-motion"

export function NetworkPrivacyUI() {
    const t = useTranslations('settings.privacy');
    const tp = useTranslations('privacy');
    const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)
    const [models, setModels] = useState<ModelStatus[]>([])
    const [loading, setLoading] = useState(true)
    const [storage, setStorage] = useState<PrivacyStorage | null>(null)
    const [auditResult, setAuditResult] = useState<PrivacyAuditResult | null>(null)
    const [isAuditing, setIsAuditing] = useState(false)

    const { logs, clearLog } = useNetworkLog()
    const logContainerRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handleStatusChange = () => setIsOnline(navigator.onLine)
        window.addEventListener('online', handleStatusChange)
        window.addEventListener('offline', handleStatusChange)

        // Initial data fetch
        Promise.all([
            getModelStatuses().then(setModels),
            getPrivacyStorage().then(setStorage)
        ]).finally(() => setLoading(false))

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

    const handleRunAudit = async () => {
        setIsAuditing(true);
        try {
            const result = await runPrivacyAudit();
            setAuditResult(result);
        } catch (error) {
            console.error("Privacy audit failed:", error);
        } finally {
            setIsAuditing(false);
        }
    };

    const hasExternalInLog = logs.some(log => !log.isLocal && log.status !== 'blocked');
    const auditPassed = auditResult ? auditResult.verdict === 'PASS' : true;
    const isFullyPrivate = !hasExternalInLog && auditPassed;

    const downloadedCount = models.filter(m => m.is_downloaded).length
    const allDownloaded = models.length > 0 && downloadedCount === models.length

    return (
        <div className="space-y-6 max-w-4xl mx-auto pb-12">

            {/* 1. Summary Card */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className={`p-1 rounded-3xl bg-gradient-to-br transition-colors duration-500 ${isFullyPrivate
                    ? "from-emerald-500/20 via-transparent to-transparent border border-emerald-500/20"
                    : "from-amber-500/20 via-transparent to-transparent border border-amber-500/20"
                    }`}
            >
                <div className="bg-zinc-950/40 backdrop-blur-3xl rounded-[22px] p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div className="flex items-center gap-5">
                        <div className={`p-4 rounded-2xl shadow-2xl transition-all duration-500 ${isFullyPrivate ? "bg-emerald-500/10 text-emerald-500" : "bg-amber-500/10 text-amber-500"
                            }`}>
                            {isFullyPrivate ? <ShieldCheck className="w-8 h-8" /> : <ShieldAlert className="w-8 h-8" />}
                        </div>
                        <div>
                            <h2 className="text-xl font-black tracking-tight text-white flex items-center gap-2">
                                {tp('privacyScore')}
                                {!isFullyPrivate && <span className="flex h-2 w-2 rounded-full bg-amber-500 animate-pulse" />}
                            </h2>
                            <p className={`text-sm font-bold uppercase tracking-widest mt-0.5 ${isFullyPrivate ? "text-emerald-400" : "text-amber-400"
                                }`}>
                                {isFullyPrivate ? tp('auditPass') : tp('auditFail')}
                            </p>
                        </div>
                    </div>

                    <div className="flex md:flex-col gap-4">
                        <div className="flex items-center gap-3 bg-zinc-900/50 px-4 py-2 rounded-xl border border-zinc-800/50">
                            <Activity className="w-4 h-4 text-zinc-500" />
                            <div className="flex flex-col">
                                <span className="text-[10px] text-zinc-500 font-bold uppercase">{tp('entries', { count: '' }).split(' ')[0]}</span>
                                <span className="text-xs font-mono text-zinc-200">{logs.length}</span>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 bg-zinc-900/50 px-4 py-2 rounded-xl border border-zinc-800/50">
                            <Scan className="w-4 h-4 text-zinc-500" />
                            <div className="flex flex-col">
                                <span className="text-[10px] text-zinc-500 font-bold uppercase">{tp('verdict')}</span>
                                <span className={`text-xs font-bold ${auditPassed ? "text-emerald-400" : "text-amber-400"}`}>
                                    {auditResult ? auditResult.verdict : "---"}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* 2. Architecture & Data Info */}
                <div className="space-y-6">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl h-fit">
                        <div className="p-5 border-b border-zinc-800 bg-zinc-900/50">
                            <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100 uppercase tracking-wide">
                                <Lock className="w-4 h-4 text-indigo-500" />
                                {t('localFirst')}
                            </h3>
                        </div>
                        <div className="p-5 space-y-4">
                            <p className="text-[11px] text-zinc-400 leading-relaxed font-medium">
                                {t('localFirstDesc')}
                            </p>

                            {loading ? (
                                <div className="flex items-center gap-2 text-[10px] text-zinc-600">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    {t('checkingModels')}
                                </div>
                            ) : allDownloaded ? (
                                <div className="flex items-center gap-2 text-[10px] text-emerald-400 font-black uppercase tracking-wider bg-emerald-500/5 px-3 py-1.5 rounded-lg border border-emerald-500/10 w-fit">
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                    {t('allCached')}
                                </div>
                            ) : (
                                <div className="flex items-center gap-2 text-[10px] text-amber-500 font-black uppercase tracking-wider bg-amber-500/5 px-3 py-1.5 rounded-lg border border-amber-500/10 w-fit">
                                    <AlertCircle className="w-3.5 h-3.5" />
                                    {t('partialCached', { count: downloadedCount, total: models.length })}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Data Storage Section */}
                    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl">
                        <div className="p-5 border-b border-zinc-800 bg-zinc-900/50">
                            <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100 uppercase tracking-wide">
                                <Database className="w-4 h-4 text-indigo-500" />
                                {tp('dataStorage')}
                            </h3>
                        </div>
                        <div className="p-5 space-y-4">
                            <div className="space-y-3">
                                <StorageRow icon={<Database className="w-3 h-3" />} label={tp('dbPath')} value={storage?.db} />
                                <StorageRow icon={<HardDrive className="w-3 h-3" />} label={tp('cachePath')} value={storage?.thumbnails} />
                                <StorageRow icon={<Cpu className="w-3 h-3" />} label={tp('modelPath')} value={storage?.models} />
                            </div>
                        </div>
                    </div>
                </div>

                {/* 3. Privacy Audit Section */}
                <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl flex flex-col">
                    <div className="p-5 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-center">
                        <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100 uppercase tracking-wide">
                            <Search className="w-4 h-4 text-indigo-500" />
                            {tp('audit')}
                        </h3>
                        <div className="flex items-center gap-3">
                            <span className="text-[10px] text-zinc-500 font-bold hidden sm:block">
                                {isAuditing ? tp('auditRunning') : auditResult ? new Date(auditResult.scan_date).toLocaleDateString() : ""}
                            </span>
                            <button
                                onClick={handleRunAudit}
                                disabled={isAuditing}
                                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 text-white rounded-lg text-[10px] font-black uppercase tracking-wider transition-all shadow-lg shadow-indigo-500/20 flex items-center gap-2"
                            >
                                {isAuditing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Scan className="w-3 h-3" />}
                                {tp('runAudit')}
                            </button>
                        </div>
                    </div>

                    <div className="p-5 flex-1 bg-zinc-950/20 relative min-h-[200px]">
                        <AnimatePresence mode="wait">
                            {!auditResult && !isAuditing ? (
                                <motion.div
                                    key="empty"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="h-full flex flex-col items-center justify-center text-center p-6 space-y-3"
                                >
                                    <div className="p-4 bg-zinc-900 rounded-full border border-zinc-800">
                                        <ShieldCheck className="w-6 h-6 text-zinc-600" />
                                    </div>
                                    <p className="text-[11px] text-zinc-500 font-medium">
                                        {tp('auditHint')}
                                    </p>
                                </motion.div>
                            ) : isAuditing ? (
                                <motion.div
                                    key="loading"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4"
                                >
                                    <div className="relative">
                                        <div className="absolute inset-0 bg-indigo-500/20 blur-xl animate-pulse rounded-full" />
                                        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin relative" />
                                    </div>
                                    <p className="text-[11px] text-indigo-400 font-black uppercase tracking-widest animate-pulse">
                                        {tp('auditRunning')}
                                    </p>
                                </motion.div>
                            ) : auditResult ? (
                                <motion.div
                                    key="results"
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="space-y-4"
                                >
                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="p-3 bg-zinc-900/50 rounded-xl border border-zinc-800/50 text-center">
                                            <p className="text-[9px] text-zinc-500 font-bold uppercase mb-1">{tp('verdict')}</p>
                                            <p className={`text-xs font-black uppercase ${auditResult.verdict === 'PASS' ? "text-emerald-500" : "text-amber-500"}`}>
                                                {auditResult.verdict}
                                            </p>
                                        </div>
                                        <div className="p-3 bg-zinc-900/50 rounded-xl border border-zinc-800/50 text-center">
                                            <p className="text-[9px] text-zinc-500 font-bold uppercase mb-1">{tp('filesScanned', { count: '' })}</p>
                                            <p className="text-xs font-mono text-zinc-200">{auditResult.files_scanned}</p>
                                        </div>
                                    </div>

                                    {auditResult.violations.length > 0 ? (
                                        <div className="space-y-2">
                                            <p className="text-[10px] text-red-400 font-black uppercase flex items-center gap-2">
                                                <ShieldX className="w-3 h-3" />
                                                {tp('violations', { count: auditResult.violations.length })}
                                            </p>
                                            <div className="max-h-[120px] overflow-y-auto space-y-1 pr-2 custom-scrollbar">
                                                {auditResult.violations.map((v, i) => (
                                                    <div key={i} className="p-2 bg-red-500/5 border border-red-500/10 rounded text-[9px] font-mono text-zinc-400 truncate">
                                                        <span className="text-red-400 font-bold mr-2">[{v.line}]</span>
                                                        {v.file}: {v.context}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-xl flex items-center justify-center text-center">
                                            <p className="text-[10px] text-emerald-500 font-bold uppercase">
                                                {tp('noViolations')}
                                            </p>
                                        </div>
                                    )}

                                    <div className="pt-2 border-t border-zinc-800 flex justify-between items-center text-[9px] text-zinc-600 font-bold uppercase">
                                        <span>{tp('allowlisted', { count: '' }).split(' ')[0]}</span>
                                        <span className="text-zinc-400">{auditResult.allowlisted_skips}</span>
                                    </div>
                                </motion.div>
                            ) : null}
                        </AnimatePresence>
                    </div>
                </div>
            </div>

            {/* 4. Network Log Table */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden shadow-xl">
                <div className="p-6 border-b border-zinc-800 bg-zinc-900/50 flex justify-between items-center">
                    <div>
                        <h3 className="text-sm font-bold flex items-center gap-2 text-zinc-100 italic uppercase tracking-widest">
                            <Activity className="w-4 h-4 text-indigo-500" />
                            {tp('networkLog')}
                        </h3>
                        <p className="text-[10px] text-zinc-500 font-bold mt-1 uppercase tracking-tight">{t('activeHistory', { count: logs.length })}</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 bg-zinc-950 px-3 py-1.5 rounded-full border border-zinc-800">
                            <div className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                            <span className={`text-[9px] font-black uppercase tracking-wider ${isOnline ? 'text-green-500' : 'text-red-500'}`}>
                                {isOnline ? t('online') : t('offline')}
                            </span>
                        </div>
                        <button
                            onClick={clearLog}
                            className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-red-400 transition-colors"
                            title={tp('clearLog')}
                        >
                            <Trash2 className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                <div
                    ref={logContainerRef}
                    className="max-h-[350px] overflow-y-auto bg-zinc-950/20 custom-scrollbar"
                >
                    <table className="w-full text-left border-collapse">
                        <thead className="sticky top-0 bg-zinc-900/90 backdrop-blur z-10">
                            <tr className="border-b border-zinc-800">
                                <th className="px-5 py-3 text-[9px] font-black text-zinc-500 uppercase tracking-widest">{tp('timestamp')}</th>
                                <th className="px-5 py-3 text-[9px] font-black text-zinc-500 uppercase tracking-widest">{tp('method')}</th>
                                <th className="px-5 py-3 text-[9px] font-black text-zinc-500 uppercase tracking-widest">{tp('url')}</th>
                                <th className="px-5 py-3 text-[9px] font-black text-zinc-500 uppercase tracking-widest text-right">{tp('status')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/30">
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="px-4 py-20 text-center text-[11px] text-zinc-600 italic font-medium">
                                        {tp('noActivity')}
                                    </td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-zinc-800/40 transition-colors group">
                                        <td className="px-5 py-3 text-[10px] font-mono text-zinc-500">{log.timestamp}</td>
                                        <td className="px-5 py-3">
                                            <span className="text-[9px] font-black px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 uppercase tracking-tighter">
                                                {log.method}
                                            </span>
                                        </td>
                                        <td className="px-5 py-3 text-[11px] text-zinc-300 font-medium truncate max-w-[240px]">
                                            {log.url}
                                        </td>
                                        <td className="px-5 py-3 text-right">
                                            <div className="flex items-center justify-end gap-2.5">
                                                <span className="text-[9px] text-zinc-600 font-mono font-bold tracking-tighter">{log.duration}ms</span>
                                                {log.status === 'blocked' ? (
                                                    <span className="flex items-center gap-1.5 text-[9px] font-black uppercase text-red-500 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20 min-w-[80px] justify-center">
                                                        <ShieldAlert className="w-2.5 h-2.5" />
                                                        {tp('blocked')}
                                                    </span>
                                                ) : !log.isLocal ? (
                                                    <span className="flex items-center gap-1.5 text-[9px] font-black uppercase text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20 min-w-[80px] justify-center">
                                                        <Globe className="w-2.5 h-2.5" />
                                                        {tp('external')}
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center gap-1.5 text-[9px] font-black uppercase text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20 min-w-[80px] justify-center">
                                                        <Lock className="w-2.5 h-2.5" />
                                                        {tp('local')}
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

function StorageRow({ icon, label, value }: { icon: React.ReactNode, label: string, value?: string }) {
    return (
        <div className="flex flex-col space-y-1">
            <div className="flex items-center gap-2 text-[9px] font-black text-zinc-500 uppercase tracking-widest">
                {icon}
                {label}
            </div>
            <div className="px-3 py-2 bg-zinc-950/50 border border-zinc-800/50 rounded-lg group hover:border-zinc-700 transition-colors">
                <p className="text-[10px] font-mono text-zinc-400 break-all select-all">
                    {value || "..."}
                </p>
            </div>
        </div>
    )
}
