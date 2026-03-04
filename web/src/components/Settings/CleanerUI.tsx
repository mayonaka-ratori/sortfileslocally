"use client"

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { findDuplicates, applyDeduplication, DuplicatePair } from '@/lib/api';
import { Search, Trash2, ShieldAlert, Loader2, CheckCircle2 } from 'lucide-react';

export function CleanerUI() {
    const t = useTranslations('settings.cleaner');
    const common = useTranslations('common');
    const [isScanning, setIsScanning] = useState(false);
    const [candidates, setCandidates] = useState<DuplicatePair[]>([]);
    const [toDelete, setToDelete] = useState<Set<string>>(new Set());
    const [isApplying, setIsApplying] = useState(false);
    const [resultMsg, setResultMsg] = useState<string | null>(null);
    const [mergeMetadata, setMergeMetadata] = useState(false);

    const handleScan = async () => {
        setIsScanning(true);
        setCandidates([]);
        setToDelete(new Set());
        setResultMsg(null);
        try {
            const results = await findDuplicates(0.95, 0.98);
            setCandidates(results);

            // Auto-select based on recommended action
            const initialDeletes = new Set<string>();
            results.forEach(pair => {
                if (pair.recommended_action === 'keep_a') initialDeletes.add(pair.file_b.file_path);
                else if (pair.recommended_action === 'keep_b') initialDeletes.add(pair.file_a.file_path);
                // If unsure or identical, user must decide
            });
            setToDelete(initialDeletes);

        } catch (e) {
            console.error("Scan failed", e);
            alert(t('scanFailed'));
        } finally {
            setIsScanning(false);
        }
    };

    const toggleDelete = (path: string) => {
        setToDelete(prev => {
            const next = new Set(prev);
            if (next.has(path)) next.delete(path);
            else next.add(path);
            return next;
        });
    };

    const handleApply = async () => {
        if (toDelete.size === 0) return;
        if (!confirm(t('confirmDelete', { count: toDelete.size }))) return;

        setIsApplying(true);

        const mergeInto: Record<string, string> = {};
        if (mergeMetadata) {
            candidates.forEach(pair => {
                if (toDelete.has(pair.file_a.file_path) && !toDelete.has(pair.file_b.file_path)) {
                    mergeInto[pair.file_a.file_path] = pair.file_b.file_path;
                } else if (toDelete.has(pair.file_b.file_path) && !toDelete.has(pair.file_a.file_path)) {
                    mergeInto[pair.file_b.file_path] = pair.file_a.file_path;
                }
            });
        }

        try {
            const res = await applyDeduplication(Array.from(toDelete), mergeMetadata ? mergeInto : undefined);
            const msg = t('deleteSuccess', { count: res.deleted_count, mergedCount: res.merged_count || 0 });
            setResultMsg(msg);
            // Remove deleted pairs from view
            setCandidates(prev => prev.filter(p => !res.deleted.includes(p.file_a.file_path) && !res.deleted.includes(p.file_b.file_path)));
            setToDelete(new Set());
        } catch (e) {
            console.error(e);
            alert(t('deleteFailed'));
        } finally {
            setIsApplying(false);
        }
    };

    const formatBytes = (bytes: number) => {
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const formatDims = (w: number | null, h: number | null) => {
        if (!w || !h) return common('unknown');
        return `${w}x${h}`;
    };

    return (
        <div className="flex flex-col gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden transition-all hover:border-zinc-700 p-4 sm:p-5 flex flex-col gap-5">

                {/* Header Area */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                    <div className="flex flex-col gap-1">
                        <h3 className="font-semibold text-zinc-100 flex items-center gap-2">
                            <ShieldAlert className="w-4 h-4 text-orange-500" />
                            {t('title')}
                        </h3>
                        <p className="text-xs text-zinc-400 max-w-lg mt-1">
                            {t('desc')}
                        </p>
                    </div>
                    <button
                        onClick={handleScan}
                        disabled={isScanning || isApplying}
                        className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm font-medium px-4 py-2 rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50 border border-zinc-700 shrink-0"
                        aria-label={t('scanButton')}
                    >
                        {isScanning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                        {isScanning ? t('scanning') : t('scanButton')}
                    </button>
                </div>

                {resultMsg && (
                    <div className="bg-green-500/10 text-green-400 border border-green-500/20 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" />
                        {resultMsg}
                    </div>
                )}

                {/* Candidate List */}
                {candidates.length > 0 && (
                    <div className="border border-zinc-800 rounded-lg overflow-hidden bg-zinc-950">
                        <div className="p-4 bg-zinc-900 border-b border-zinc-800 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                            <span className="text-sm font-medium text-zinc-300">{t('found', { count: candidates.length })}</span>
                            <div className="flex items-center gap-4">
                                <label className="flex items-center gap-2 text-sm text-zinc-400 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={mergeMetadata}
                                        onChange={(e) => setMergeMetadata(e.target.checked)}
                                        className="rounded border-zinc-700 bg-zinc-800 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-zinc-900 w-4 h-4 cursor-pointer"
                                    />
                                    {t('mergeMetadata')}
                                </label>
                                <button
                                    onClick={handleApply}
                                    disabled={toDelete.size === 0 || isApplying}
                                    className="bg-red-600 hover:bg-red-500 text-white text-sm font-medium px-4 py-1.5 rounded-md flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isApplying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                    {t('deleteSelected', { count: toDelete.size })}
                                </button>
                            </div>
                        </div>

                        <div className="max-h-[500px] overflow-y-auto p-4 flex flex-col gap-6">
                            {candidates.map((pair) => (
                                <div key={`${pair.file_a.file_path}-${pair.file_b.file_path}`} className="flex flex-col gap-3 bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50">
                                    <div className="flex justify-between items-center text-xs text-zinc-500">
                                        <span>{t('similarity')}: {(pair.similarity * 100).toFixed(1)}%</span>
                                        <span className="text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded font-mono">{t('reason')}: {pair.reason}</span>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                                        {/* File A */}
                                        <div
                                            onClick={() => toggleDelete(pair.file_a.file_path)}
                                            className={`relative p-3 rounded-lg border cursor-pointer transition-colors flex gap-3
                                            ${toDelete.has(pair.file_a.file_path) ? 'bg-red-950/30 border-red-900/50' : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'}`}
                                        >
                                            <div className="w-5 h-5 mt-0.5 shrink-0 border rounded flex items-center justify-center bg-zinc-900 border-zinc-700">
                                                {toDelete.has(pair.file_a.file_path) && <div className="w-3 h-3 bg-red-500 rounded-sm" />}
                                            </div>
                                            <div className="flex flex-col gap-1 min-w-0 flex-1">
                                                <div className="text-sm text-zinc-200 truncate font-mono" title={pair.file_a.file_path}>
                                                    {pair.file_a.file_path.split(/[\\/]/).pop()}
                                                </div>
                                                <div className="text-xs text-zinc-500 flex gap-3">
                                                    <span>{formatBytes(pair.file_a.file_size ?? 0)}</span>
                                                    <span>{formatDims(pair.file_a.width ?? null, pair.file_a.height ?? null)}</span>
                                                </div>
                                                <div className="text-[10px] text-zinc-600 truncate mt-1">{pair.file_a.file_path}</div>
                                            </div>
                                        </div>

                                        {/* File B */}
                                        <div
                                            onClick={() => toggleDelete(pair.file_b.file_path)}
                                            className={`relative p-3 rounded-lg border cursor-pointer transition-colors flex gap-3
                                            ${toDelete.has(pair.file_b.file_path) ? 'bg-red-950/30 border-red-900/50' : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'}`}
                                        >
                                            <div className="w-5 h-5 mt-0.5 shrink-0 border rounded flex items-center justify-center bg-zinc-900 border-zinc-700">
                                                {toDelete.has(pair.file_b.file_path) && <div className="w-3 h-3 bg-red-500 rounded-sm" />}
                                            </div>
                                            <div className="flex flex-col gap-1 min-w-0 flex-1">
                                                <div className="text-sm text-zinc-200 truncate font-mono" title={pair.file_b.file_path}>
                                                    {pair.file_b.file_path.split(/[\\/]/).pop()}
                                                </div>
                                                <div className="text-xs text-zinc-500 flex gap-3">
                                                    <span>{formatBytes(pair.file_b.file_size ?? 0)}</span>
                                                    <span>{formatDims(pair.file_b.width ?? null, pair.file_b.height ?? null)}</span>
                                                </div>
                                                <div className="text-[10px] text-zinc-600 truncate mt-1">{pair.file_b.file_path}</div>
                                            </div>
                                        </div>

                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {candidates.length === 0 && !isScanning && resultMsg === null && (
                    <div className="text-center text-sm text-zinc-500 py-4">
                        {t('empty')}
                    </div>
                )}
            </div>
        </div>
    );
}
