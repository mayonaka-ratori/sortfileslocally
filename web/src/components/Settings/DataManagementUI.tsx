"use client"
import React, { useState } from 'react';
import { exportAllMetadata } from '@/lib/api';
import { Download, Loader2, Database } from 'lucide-react';
import { MetadataExportOptions, ExportMode } from '../MetadataExportOptions';

export function DataManagementUI() {
    const [isExporting, setIsExporting] = useState(false);
    const [exportMode, setExportMode] = useState<ExportMode>("xmp");
    const [exportResult, setExportResult] = useState<{ success: number, failed: number } | null>(null);

    const handleExportAll = async () => {
        setIsExporting(true);
        setExportResult(null);
        try {
            const result = await exportAllMetadata(exportMode);
            setExportResult({ success: result.success, failed: result.failed });
        } catch (e) {
            console.error("Export all failed", e);
            alert("Failed to export metadata.");
        } finally {
            setIsExporting(false);
        }
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden transition-all hover:border-zinc-700">
                <div className="p-4 sm:p-5 flex flex-col gap-6">
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                        <div className="flex flex-col gap-1">
                            <h3 className="font-semibold text-zinc-100 flex items-center gap-2">
                                <Database className="w-4 h-4 text-zinc-500" />
                                Export Metadata
                            </h3>
                            <p className="text-xs text-zinc-400 max-w-lg mt-1">
                                Write all AI-generated tags and captions directly to your media library files or sidecars.
                            </p>
                        </div>
                        <div className="w-full sm:w-auto flex flex-col items-end gap-2 shrink-0">
                            <button
                                onClick={handleExportAll}
                                disabled={isExporting}
                                className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 shadow-lg shadow-indigo-900/20 w-full sm:w-auto"
                            >
                                {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                                Export All Library
                            </button>
                            {exportResult && (
                                <div className="text-[10px] text-green-400 font-mono text-right w-full">
                                    ✓ {exportResult.success} exported
                                    {exportResult.failed > 0 && <span className="text-red-400 ml-1">({exportResult.failed} failed)</span>}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="pt-2 border-t border-zinc-800/50">
                        <MetadataExportOptions
                            selectedMode={exportMode}
                            onModeChange={setExportMode}
                        />
                        {exportMode === "exif" && (
                            <p className="mt-2 text-[10px] text-amber-500/80 bg-amber-950/5 border border-amber-900/10 rounded p-2 italic">
                                Note: Video files and unsupported image formats will automatically fall back to XMP sidecar export during library-wide processing.
                            </p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
