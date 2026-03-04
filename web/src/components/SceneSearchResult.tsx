"use client";

import Image from "next/image";
import { SceneSearchResult } from "@/lib/api";
import { formatTime } from "@/lib/utils";
import { Play, Film } from "lucide-react";
import { useTranslations } from "next-intl";

interface SceneSearchResultProps {
    result: SceneSearchResult;
    onPlay?: (fileId: number, time: number) => void;
}

export function SceneSearchResultComponent({ result, onPlay }: SceneSearchResultProps) {
    const t = useTranslations("gallery");
    const scorePercent = Math.round(result.score * 100);

    return (
        <div className="flex flex-col sm:flex-row gap-4 p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/50 hover:bg-zinc-900/60 hover:border-zinc-700/50 transition-all group">
            <div
                className="relative aspect-video w-full sm:w-48 flex-none rounded-lg overflow-hidden cursor-pointer"
                onClick={() => onPlay?.(result.file_id, result.start_time)}
            >
                <Image
                    src={result.thumbnail_path || ''}
                    alt={result.caption || t("scenePreview")}
                    fill
                    className="object-cover group-hover:scale-105 transition-transform duration-500"
                    sizes="(max-width: 640px) 100vw, 192px"
                />
                <div className="absolute inset-0 bg-black/20 group-hover:bg-black/0 transition-colors" />

                <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded bg-blue-600 text-[10px] font-bold text-white shadow-lg">
                    {t("similarity", { percent: scorePercent })}
                </div>

                <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-medium text-white backdrop-blur-sm">
                    {formatTime(result.start_time)} – {formatTime(result.end_time)}
                </div>

                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="w-10 h-10 rounded-full bg-blue-600/90 flex items-center justify-center shadow-xl">
                        <Play className="w-4 h-4 text-white fill-white ml-0.5" />
                    </div>
                </div>
            </div>

            <div className="flex flex-col flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-center gap-1.5 min-w-0">
                        <Film className="w-3.5 h-3.5 text-zinc-500 flex-none" />
                        <h3 className="text-sm font-semibold text-zinc-200 truncate">
                            {result.file_path.split(/[\/\\]/).pop() ?? result.file_path}
                        </h3>
                    </div>
                </div>

                <p className="text-xs text-zinc-400 line-clamp-2 mb-3 leading-relaxed italic">
                    &quot;{result.caption || t("noCaption")}&quot;
                </p>

                <div className="flex flex-wrap gap-1.5 mb-4">
                    {result.tags.slice(0, 3).map((tag, i) => (
                        <span
                            key={i}
                            className="px-2 py-0.5 rounded-full bg-zinc-800 text-[10px] text-zinc-400 font-medium"
                        >
                            #{tag}
                        </span>
                    ))}
                    {result.tags.length > 3 && (
                        <span className="px-2 py-0.5 rounded-full bg-zinc-800 text-[10px] text-zinc-400 font-medium">
                            {t("more", { count: result.tags.length - 3 })}
                        </span>
                    )}
                </div>

                <div className="mt-auto flex items-center justify-between gap-4">
                    <button
                        onClick={() => onPlay?.(result.file_id, result.start_time)}
                        className="flex items-center px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[10px] font-bold rounded-lg transition-colors border border-zinc-700/50"
                    >
                        <Play className="w-3 h-3 mr-2" />
                        {t("playFromScene")}
                    </button>
                </div>
            </div>
        </div>
    );
}
