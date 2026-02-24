"use client";

import React, { useEffect, useState } from 'react';
import { getInsights, InsightItem, createAlbum } from '@/lib/api';
import {
    Copy,
    Tag,
    Folder,
    AlertTriangle,
    X,
    Loader2,
    ChevronRight,
    Sparkles,
    CheckCircle2
} from 'lucide-react';
import { useRouter } from 'next/navigation';

export const InsightsPanel: React.FC = () => {
    const [insights, setInsights] = useState<InsightItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [dismissed, setDismissed] = useState<string[]>([]);
    const [creatingAlbum, setCreatingAlbum] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        // Load dismissed insights from localStorage
        const saved = localStorage.getItem('dismissed_insights');
        if (saved) {
            try {
                const parsed = JSON.parse(saved) as { type: string, expiry: number }[];
                const now = Date.now();
                const valid = parsed.filter(p => p.expiry > now);
                setDismissed(valid.map(v => v.type));

                // Update storage with only valid items
                if (valid.length !== parsed.length) {
                    localStorage.setItem('dismissed_insights', JSON.stringify(valid));
                }
            } catch {
                console.error("Failed to parse dismissed insights");
            }
        }

        fetchInsights();
    }, []);

    const fetchInsights = async () => {
        try {
            const data = await getInsights();
            setInsights(data.insights);
        } catch (error) {
            console.error("Failed to fetch insights", error);
        } finally {
            setLoading(false);
        }
    };

    const handleDismiss = (type: string) => {
        const newDismissed = [...dismissed, type];
        setDismissed(newDismissed);

        // Save to localStorage with 24h expiry
        const saved = localStorage.getItem('dismissed_insights');
        let parsed: { type: string, expiry: number }[] = [];
        if (saved) {
            try { parsed = JSON.parse(saved); } catch (e) { }
        }

        parsed.push({ type, expiry: Date.now() + 24 * 60 * 60 * 1000 });
        localStorage.setItem('dismissed_insights', JSON.stringify(parsed));
    };

    const handleCreateAlbum = async (insight: InsightItem) => {
        if (!insight.tag || !insight.query_json) return;

        setCreatingAlbum(insight.tag);
        try {
            const albumId = await createAlbum(insight.tag, true, insight.query_json);
            // Hide this insight
            setInsights(prev => prev.filter(i => i.tag !== insight.tag));
            // Navigate or show success? Let's stay on page but show toast if we had a toast system
            // For now, removing it from UI is a good feedback.
            router.push(`/albums/${albumId}`);
        } catch (error) {
            console.error("Failed to create album", error);
            alert("Failed to create album");
        } finally {
            setCreatingAlbum(null);
        }
    };

    const getIcon = (type: string) => {
        switch (type) {
            case 'duplicate_found': return <Copy className="w-5 h-5 text-amber-400" />;
            case 'untagged_files': return <Tag className="w-5 h-5 text-indigo-400" />;
            case 'album_suggestion': return <Folder className="w-5 h-5 text-emerald-400" />;
            case 'low_quality_tags': return <AlertTriangle className="w-5 h-5 text-rose-400" />;
            default: return <Sparkles className="w-5 h-5 text-blue-400" />;
        }
    };

    const visibleInsights = insights.filter(i => !dismissed.includes(i.type));

    if (loading) {
        return (
            <div className="flex gap-4 mb-8 overflow-x-auto pb-2 scrollbar-hide">
                {[1, 2, 3].map(i => (
                    <div key={i} className="min-w-[300px] h-32 bg-zinc-900/50 border border-zinc-800 rounded-2xl animate-pulse" />
                ))}
            </div>
        );
    }

    if (visibleInsights.length === 0) {
        return (
            <div className="mb-10 p-6 bg-zinc-900/20 border border-zinc-800/50 rounded-2xl border-dashed flex items-center justify-center gap-3 text-zinc-500">
                <CheckCircle2 className="w-5 h-5 text-emerald-500/50" />
                <span className="text-sm font-medium">Your library is well organized. Nice work!</span>
            </div>
        );
    }

    return (
        <div className="mb-10 w-full">
            <div className="flex items-center gap-2 mb-4">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <h2 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Actionable Insights</h2>
            </div>

            <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
                {visibleInsights.map((insight, idx) => (
                    <div
                        key={`${insight.type}-${idx}`}
                        className="min-w-[320px] max-w-[320px] bg-zinc-900 border border-zinc-800 p-5 rounded-2xl flex flex-col relative group hover:border-zinc-700 transition-all shadow-lg"
                    >
                        <button
                            onClick={() => handleDismiss(insight.type)}
                            className="absolute top-3 right-3 p-1 hover:bg-zinc-800 rounded-md text-zinc-600 hover:text-zinc-400 transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>

                        <div className="flex items-start gap-4 mb-4">
                            <div className={`p-2.5 rounded-xl ${insight.priority === 'high' ? 'bg-rose-500/10' :
                                insight.priority === 'medium' ? 'bg-amber-500/10' : 'bg-zinc-800'
                                }`}>
                                {getIcon(insight.type)}
                            </div>
                            <div className="flex-1 min-w-0 pr-4">
                                <h3 className="font-bold text-white text-sm mb-1 truncate">{insight.title}</h3>
                                <p className="text-zinc-500 text-xs leading-relaxed line-clamp-2">
                                    {insight.message}
                                </p>
                            </div>
                        </div>

                        <div className="mt-auto pt-2">
                            {insight.type === 'album_suggestion' ? (
                                <button
                                    onClick={() => handleCreateAlbum(insight)}
                                    disabled={creatingAlbum === insight.tag}
                                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 text-white text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/20"
                                >
                                    {creatingAlbum === insight.tag ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    ) : (
                                        <Folder className="w-3.5 h-3.5" />
                                    )}
                                    Create Smart Album
                                </button>
                            ) : (
                                <button
                                    onClick={() => router.push(insight.action_url)}
                                    className="w-full py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 border border-zinc-700/50"
                                >
                                    {insight.action_label}
                                    <ChevronRight className="w-3.5 h-3.5" />
                                </button>
                            )}
                        </div>

                        {/* Priority Badge */}
                        {insight.priority === 'high' && (
                            <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-rose-500 text-[10px] font-black text-white rounded-md uppercase tracking-tighter shadow-lg">
                                Priority
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};
