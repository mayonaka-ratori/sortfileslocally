"use client"
import React from 'react';
import { AlertTriangle, Info } from 'lucide-react';

export type ExportMode = "xmp" | "exif";

interface MetadataExportOptionsProps {
    selectedMode: ExportMode;
    onModeChange: (mode: ExportMode) => void;
    items?: { file_path: string }[]; // Optional: for checking support
    className?: string;
}

export function MetadataExportOptions({ selectedMode, onModeChange, items, className }: MetadataExportOptionsProps) {
    const EXIF_SUPPORTED_EXT = ['.jpg', '.jpeg'];

    const unsupportedForExif = items ? items.filter(item => {
        const ext = item.file_path.toLowerCase().split('.').pop();
        return !EXIF_SUPPORTED_EXT.includes(`.${ext}`);
    }) : [];

    const hasVideo = items ? items.some(item => {
        const ext = item.file_path.toLowerCase().split('.').pop();
        return ['mp4', 'avi', 'mov', 'mkv', 'webm'].includes(ext || '');
    }) : false;

    return (
        <div className={`flex flex-col gap-4 ${className || ''}`}>
            <div className="flex flex-col gap-2">
                <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Export Format</label>
                <div className="flex bg-zinc-950 border border-zinc-800 rounded-lg p-1 gap-1">
                    <button
                        onClick={() => onModeChange("xmp")}
                        className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${selectedMode === "xmp"
                            ? 'bg-zinc-800 text-white shadow-sm'
                            : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                            }`}
                    >
                        XMP Sidecar
                    </button>
                    <button
                        onClick={() => onModeChange("exif")}
                        className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${selectedMode === "exif"
                            ? 'bg-zinc-800 text-white shadow-sm'
                            : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                            }`}
                    >
                        EXIF Overlay
                    </button>
                </div>
            </div>

            {selectedMode === "xmp" && (
                <div className="flex items-start gap-3 p-3 bg-indigo-950/10 border border-indigo-900/20 rounded-lg">
                    <Info className="w-4 h-4 text-indigo-500 shrink-0 mt-0.5" />
                    <p className="text-[11px] text-zinc-400 leading-relaxed">
                        Best for non-destructive workflows. Creates separate <code className="text-indigo-400">.xmp</code> files compatible with Lightroom, Digikam, and others. Supports all file types.
                    </p>
                </div>
            )}

            {selectedMode === "exif" && (
                <div className="flex flex-col gap-3">
                    <div className="flex items-start gap-3 p-3 bg-amber-950/10 border border-amber-900/20 rounded-lg">
                        <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        <p className="text-[11px] text-zinc-400 leading-relaxed">
                            Writes keywords and captions directly into the file. <strong className="text-amber-500/90">Warning:</strong> Only works for JPEG files. Non-JPEG files will automatically use XMP fallback.
                        </p>
                    </div>

                    {unsupportedForExif.length > 0 && (
                        <div className="flex flex-col gap-1 px-3">
                            <p className="text-[10px] text-amber-500/70 font-medium">
                                {hasVideo ? 'Videos and unsupported images detected:' : 'Unsupported formats for EXIF:'}
                            </p>
                            <div className="max-h-20 overflow-y-auto pr-1">
                                {unsupportedForExif.map((item, idx) => {
                                    const filename = item.file_path.split(/[\\/]/).pop();
                                    return (
                                        <div key={idx} className="text-[9px] text-zinc-500 font-mono truncate">
                                            • {filename}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
