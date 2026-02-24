"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Scene, getScenes, detectScenes, deleteScenes } from "@/lib/api";
import { SceneCard } from "./SceneCard";
import { Loader2, RefreshCw, Trash2, PlayCircle } from "lucide-react";
import { formatTime, cn } from "@/lib/utils";
import { toast } from "sonner";

interface SceneTimelineProps {
    fileId: number;
    onSeek?: (time: number) => void;
    activeTime?: number;
}

export function SceneTimeline({ fileId, onSeek, activeTime = 0 }: SceneTimelineProps) {
    const [scenes, setScenes] = useState<Scene[]>([]);
    const [loading, setLoading] = useState(true);
    const [detecting, setDetecting] = useState(false);
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const pollCountRef = useRef(0);

    const fetchScenes = useCallback(async () => {
        try {
            const data = await getScenes(fileId);
            setScenes(data);
            if (data.length > 0 && detecting) {
                setDetecting(false);
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                    pollIntervalRef.current = null;
                }
                toast.success("Scene detection complete");
            }
        } catch {
            console.error("Failed to fetch scenes:");
            // Don't show error if we're just polling and it fails once
        } finally {
            setLoading(false);
        }
    }, [fileId, detecting]);

    const startPolling = useCallback(() => {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        pollCountRef.current = 0;

        pollIntervalRef.current = setInterval(() => {
            pollCountRef.current += 1;
            if (pollCountRef.current >= 60) {
                if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
                setDetecting(false);
                toast.error("Scene detection timed out");
                return;
            }
            fetchScenes();
        }, 3000);
    }, [fetchScenes]);

    useEffect(() => {
        fetchScenes();
        return () => {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        };
    }, [fetchScenes]);

    const handleDetect = async (force: boolean = false) => {
        try {
            setDetecting(true);
            await detectScenes(fileId, force);
            startPolling();
        } catch {
            setDetecting(false);
            toast.error("Failed to start scene detection");
        }
    };

    const handleDelete = async () => {
        if (!window.confirm("Are you sure you want to delete all detected scenes for this video?")) return;

        try {
            await deleteScenes(fileId);
            setScenes([]);
            toast.success("Scenes deleted");
        } catch {
            toast.error("Failed to delete scenes");
        }
    };

    const totalDuration = scenes.reduce((acc, s) => acc + s.duration, 0);

    if (loading && !detecting) {
        return (
            <div className="flex items-center justify-center h-48 bg-zinc-950/50 rounded-xl border border-zinc-900">
                <Loader2 className="w-6 h-6 text-blue-500 animate-spin mr-2" />
                <span className="text-zinc-400 font-medium">Loading scenes...</span>
            </div>
        );
    }

    if (scenes.length === 0 && !detecting) {
        return (
            <div className="flex flex-col items-center justify-center p-8 bg-zinc-950/50 rounded-xl border border-zinc-900 text-center">
                <div className="w-12 h-12 bg-zinc-900 rounded-full flex items-center justify-center mb-4">
                    <PlayCircle className="w-6 h-6 text-zinc-500" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-200 mb-1">No scenes detected</h3>
                <p className="text-xs text-zinc-500 mb-6 max-w-[240px]">
                    Analyzing the video helps you navigate through different parts of it quickly.
                </p>
                <button
                    onClick={() => handleDetect()}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg transition-colors flex items-center"
                >
                    <RefreshCw className="w-3.5 h-3.5 mr-2" />
                    Detect Scenes
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between px-1">
                <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-white">
                        {scenes.length} {scenes.length === 1 ? 'Scene' : 'Scenes'}
                    </h3>
                    <span className="text-[10px] font-medium text-zinc-500 bg-zinc-900 px-1.5 py-0.5 rounded">
                        Total {formatTime(totalDuration)}
                    </span>
                </div>
                {detecting && (
                    <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded-full">
                        <Loader2 className="w-3 h-3 text-blue-500 animate-spin" />
                        <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider">Analyzing video...</span>
                    </div>
                )}
            </div>

            <div className="relative group">
                <div className="overflow-x-auto pb-4 pt-1 flex gap-4 no-scrollbar scroll-smooth">
                    {scenes.map((scene) => (
                        <SceneCard
                            key={scene.id}
                            scene={scene}
                            isActive={activeTime >= scene.start_time && activeTime < scene.end_time}
                            onClick={() => onSeek?.(scene.start_time)}
                        />
                    ))}
                </div>
            </div>

            <div className="flex items-center gap-3 pt-2 border-t border-zinc-900">
                <button
                    onClick={() => handleDetect(true)}
                    disabled={detecting}
                    className="flex items-center px-3 py-1.5 text-[10px] font-bold text-zinc-400 hover:text-white bg-zinc-900 hover:bg-zinc-800 rounded-md transition-all disabled:opacity-50"
                >
                    <RefreshCw className={cn("w-3 h-3 mr-1.5", detecting && "animate-spin")} />
                    Re-detect Scenes
                </button>
                <button
                    onClick={handleDelete}
                    className="flex items-center px-3 py-1.5 text-[10px] font-bold text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 rounded-md transition-all ml-auto"
                >
                    <Trash2 className="w-3 h-3 mr-1.5" />
                    Delete All Scenes
                </button>
            </div>
        </div>
    );
}
