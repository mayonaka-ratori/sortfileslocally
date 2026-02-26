"use client"

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { getModelStatuses, downloadModel, getDownloadProgress, ModelStatus, DownloadProgress, getAppSettings, updateAppSetting, browseFolder } from '@/lib/api';
import { DownloadCloud, CheckCircle2, HardDrive, AlertCircle, Loader2, Database, FolderOpen, Save } from 'lucide-react';

export function ModelManagerUI() {
    const t = useTranslations('settings.models');
    const common = useTranslations('common');
    const [models, setModels] = useState<ModelStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [progress, setProgress] = useState<Record<string, DownloadProgress>>({});
    const [activeDownloads, setActiveDownloads] = useState<Set<string>>(new Set());

    const [customDir, setCustomDir] = useState<string>('');
    const [savingSetting, setSavingSetting] = useState(false);

    const fetchModels = React.useCallback(async () => {
        try {
            const [modelData, settings] = await Promise.all([
                getModelStatuses(),
                getAppSettings()
            ]);
            setModels(modelData);
            setCustomDir(settings.custom_model_dir || '');
        } catch {
            setError(t('fetchError'));
        } finally {
            setLoading(false);
        }
    }, [t]);

    useEffect(() => {
        fetchModels();
    }, [fetchModels]);

    // Polling active downloads
    useEffect(() => {
        if (activeDownloads.size === 0) return;

        const interval = setInterval(async () => {
            const newProgress = { ...progress };
            const newActive = new Set(activeDownloads);
            let hasChanges = false;
            let needsRefresh = false;

            for (const key of activeDownloads) {
                try {
                    const prog = await getDownloadProgress(key);
                    if (prog) {
                        newProgress[key] = prog;
                        hasChanges = true;
                        if (prog.status === 'completed' || prog.status === 'failed') {
                            newActive.delete(key);
                            if (prog.status === 'completed') needsRefresh = true;
                        }
                    }
                } catch (e) {
                    console.error("Poll error for", key, e);
                }
            }

            if (hasChanges) setProgress(newProgress);
            if (activeDownloads.size !== newActive.size) setActiveDownloads(newActive);
            if (needsRefresh) fetchModels();

        }, 1000);

        return () => clearInterval(interval);
    }, [activeDownloads, progress, fetchModels]);

    const handleDownload = async (key: string) => {
        try {
            await downloadModel(key);
            setActiveDownloads(prev => new Set(prev).add(key));
        } catch (err: unknown) {
            console.error("Failed to download model", err);
            alert(`${t('downloadFailed')}${err instanceof Error ? err.message : String(err)}`);
        }
    };

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const handleBrowse = async () => {
        try {
            const res = await browseFolder();
            if (!res.cancelled && res.path) {
                setCustomDir(res.path);
            }
        } catch (err) {
            console.error(err);
        }
    };

    const handleSaveSetting = async () => {
        setSavingSetting(true);
        try {
            const res = await updateAppSetting('custom_model_dir', customDir);
            await fetchModels(); // Refresh to show new paths
            if (res.requires_restart) {
                alert(t('pathUpdated'));
            } else {
                alert(t('saveSuccess'));
            }
        } catch (err: unknown) {
            alert(err instanceof Error ? err.message : t('saveFailed'));
        } finally {
            setSavingSetting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex flex-col flex-1 items-center justify-center p-10 text-zinc-500 bg-zinc-900 border border-zinc-800 rounded-xl min-h-[300px]">
                <Loader2 className="w-8 h-8 animate-spin mb-4 text-indigo-500" />
                <span>{t('loading')}</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center gap-3 p-4 border border-red-900/50 bg-red-950/20 text-red-400 rounded-xl text-sm">
                <AlertCircle className="w-5 h-5 shrink-0" />
                {error}
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-8">
            {/* Global Settings Section */}
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 flex flex-col gap-4">
                <div className="flex flex-col gap-1">
                    <h3 className="text-sm font-bold flex items-center gap-2">
                        <HardDrive className="w-4 h-4 text-indigo-500" />
                        {t('storage')}
                    </h3>
                    <p className="text-xs text-zinc-500">{t('storageDesc')}</p>
                </div>

                <div className="flex flex-col gap-3">
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <input
                                type="text"
                                value={customDir}
                                onChange={(e) => setCustomDir(e.target.value)}
                                placeholder={t('defaultCachePlaceholder')}
                                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-2 text-sm text-zinc-300 focus:outline-none focus:border-indigo-500 transition-colors pl-10"
                            />
                            <FolderOpen className="w-4 h-4 absolute left-3 top-2.5 text-zinc-600" />
                        </div>
                        <button
                            onClick={handleBrowse}
                            className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2"
                            title={common('browse')}
                        >
                            <FolderOpen className="w-4 h-4" />
                            {common('browse')}
                        </button>
                        <button
                            onClick={handleSaveSetting}
                            disabled={savingSetting}
                            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
                        >
                            {savingSetting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            {common('save')}
                        </button>
                    </div>
                    <div className="flex items-start gap-2 p-3 bg-amber-950/10 border border-amber-900/20 rounded-lg">
                        <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        <p className="text-[11px] text-amber-500/80 leading-relaxed">
                            {t('pathChangeNote')}
                        </p>
                    </div>
                </div>
            </div>

            <div className="flex flex-col gap-4">
                {models.map((model) => {
                    const prog = progress[model.key];
                    const isDownloading = activeDownloads.has(model.key) || prog?.status === 'downloading';
                    const hasError = prog?.status === 'failed';

                    return (
                        <div key={model.key} className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden transition-all hover:border-zinc-700">
                            <div className="p-4 sm:p-5 flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">

                                {/* Model Info */}
                                <div className="flex flex-col gap-1">
                                    <div className="flex items-center gap-2">
                                        <h3 className="font-semibold text-zinc-100 flex items-center gap-2">
                                            <Database className="w-4 h-4 text-zinc-500" />
                                            {model.name}
                                        </h3>
                                        {model.is_downloaded && (
                                            <span className="bg-green-500/10 text-green-400 text-[10px] uppercase font-bold px-2 py-0.5 rounded flex items-center gap-1 border border-green-500/20">
                                                <CheckCircle2 className="w-3 h-3" /> {t('installed')}
                                            </span>
                                        )}
                                    </div>
                                    <div className="text-xs text-zinc-400 flex flex-wrap gap-x-4 gap-y-1 mt-1">
                                        <span className="font-mono text-zinc-500">{model.repo_id}</span>
                                        <span className="flex items-center gap-1">
                                            <HardDrive className="w-3 h-3" />
                                            {model.is_downloaded ? `${model.local_size_mb} MB` : `~${model.estimated_size_mb} MB`}
                                        </span>
                                    </div>
                                    <div className="text-[10px] text-zinc-600 font-mono mt-0.5 truncate max-w-lg" title={model.local_dir}>
                                        {model.local_dir}
                                    </div>
                                </div>

                                {/* Action Area */}
                                <div className="w-full sm:w-auto flex-shrink-0">
                                    {!model.is_downloaded && !isDownloading && (
                                        <button
                                            onClick={() => handleDownload(model.key)}
                                            className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-lg shadow-indigo-900/20"
                                        >
                                            <DownloadCloud className="w-4 h-4" />
                                            {t('downloadNow')}
                                        </button>
                                    )}

                                    {model.is_downloaded && !isDownloading && (
                                        <div className="text-sm font-medium text-zinc-500 border border-zinc-800 bg-zinc-950 px-4 py-2 rounded-lg text-center cursor-default">
                                            {t('ready')}
                                        </div>
                                    )}

                                    {isDownloading && (
                                        <div className="text-sm font-medium text-indigo-400 border border-indigo-900/50 bg-indigo-950/20 px-4 py-2 rounded-lg flex items-center justify-center gap-2 min-w-[140px]">
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            {t('downloading')}
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Progress Bar Expansion */}
                            {prog && (isDownloading || hasError) && (
                                <div className="px-5 pb-5 pt-1 border-t border-zinc-800/50 bg-zinc-950/30">
                                    <div className="flex justify-between text-[11px] text-zinc-400 mb-2 font-mono uppercase tracking-wider">
                                        <span className="truncate pr-4 flex-1">{prog.filename}</span>
                                        <span>
                                            {formatBytes(prog.downloaded_bytes)} / {formatBytes(prog.total_bytes)} ({prog.percent.toFixed(1)}%)
                                        </span>
                                    </div>
                                    <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full transition-all duration-300 ${hasError ? 'bg-red-500' : 'bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.6)]'}`}
                                            style={{ width: `${Math.max(2, prog.percent)}%` }} // Minimum width to show it's doing something
                                        />
                                    </div>
                                    {hasError && (
                                        <div className="mt-2 text-xs text-red-400 flex items-start gap-1">
                                            <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                                            {prog.error}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

