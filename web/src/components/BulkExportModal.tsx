"use client"
import React, { useState } from 'react';
import { exportMetadata, MediaItem } from '@/lib/api';
import { X, Download, Loader2, Database } from 'lucide-react';
import { MetadataExportOptions, ExportMode } from './MetadataExportOptions';

interface BulkExportModalProps {
    selectedItems: MediaItem[];
    onClose: () => void;
    onSuccess: (successCount: number, failedCount: number) => void;
}

export function BulkExportModal({ selectedItems, onClose, onSuccess }: BulkExportModalProps) {
    const [isExporting, setIsExporting] = useState(false);
    const [exportMode, setExportMode] = useState<ExportMode>("xmp");

    const handleClose = () => {
        if (isExporting) {
            if (!window.confirm("Export is in progress. Close anyway?")) return;
        }
        onClose();
    };

    const handleExport = async () => {
        if (isExporting || selectedItems.length === 0 || selectedItems.length > 500) return;
        setIsExporting(true);
        try {
            const ids = selectedItems.map(item => item.id);
            const result = await exportMetadata(ids, exportMode);
            onSuccess(result.success, result.failed);
            onClose();
        } catch (e) {
            console.error("Bulk export failed", e);
            alert("Failed to export metadata for selected items.");
        } finally {
            setIsExporting(false);
        }
    };

    const isOverLimit = selectedItems.length > 500;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-zinc-800">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <Database className="w-5 h-5 text-indigo-500" />
                        Bulk Metadata Export
                    </h2>
                    <button
                        onClick={handleClose}
                        disabled={isExporting}
                        className="p-1 hover:bg-zinc-800 rounded-md transition-colors text-zinc-400 hover:text-white disabled:opacity-30"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <div className="p-6 flex flex-col gap-6">
                    <div className="flex flex-col gap-1">
                        <p className={`text-sm font-medium ${isOverLimit ? 'text-red-400' : 'text-zinc-100'}`}>
                            {isOverLimit ? 'Selection too large' : `Ready to export ${selectedItems.length} items`}
                        </p>
                        <p className="text-xs text-zinc-500">
                            {isOverLimit
                                ? 'Please select 500 or fewer files for bulk export. For larger exports, use "Export All" in Data Management settings.'
                                : 'Choose how you want the AI-generated tags and captions to be written back to your files.'}
                        </p>
                    </div>

                    {!isOverLimit && (
                        <MetadataExportOptions
                            selectedMode={exportMode}
                            onModeChange={setExportMode}
                            items={selectedItems}
                        />
                    )}
                </div>

                <div className="p-4 bg-zinc-900/50 border-t border-zinc-800 flex gap-3">
                    <button
                        onClick={handleClose}
                        disabled={isExporting}
                        className="flex-1 px-4 py-2.5 rounded-xl border border-zinc-800 text-zinc-300 hover:bg-zinc-800 transition-colors text-sm font-medium disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleExport}
                        disabled={isExporting || isOverLimit}
                        className="flex-[2] bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 disabled:opacity-100 text-white rounded-xl py-2.5 px-4 text-sm font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-indigo-900/20"
                    >
                        {isExporting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
                        {isOverLimit ? 'Selection Limit Exceeded' : `Export ${selectedItems.length} Items`}
                    </button>
                </div>
            </div>
        </div>
    );
}
