import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchAlbum, fetchAlbumMedia, Album, MediaItem, SearchFilters } from '@/lib/api';
import { Sidebar } from '@/components/Sidebar';
import { GalleryGrid } from '@/components/GalleryGrid';
import { ChatPanel } from '@/components/ChatPanel';
import { Sparkles, Folder, ArrowLeft, Trash2, Edit2, Share2, Tag } from 'lucide-react';
import { useTranslations } from 'next-intl';

export default function AlbumDetailPage() {
    const t = useTranslations("albums");
    const commonT = useTranslations("common");
    const params = useParams();
    const router = useRouter();
    const albumId = parseInt(params.id as string);

    const [album, setAlbum] = useState<Album | null>(null);
    const [media, setMedia] = useState<MediaItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    useEffect(() => {
        if (!albumId) return;

        Promise.all([
            fetchAlbum(albumId),
            fetchAlbumMedia(albumId)
        ]).then(([albumData, mediaData]) => {
            setAlbum(albumData);
            setMedia(mediaData);
        }).catch(err => {
            console.error('Failed to load album data:', err);
        }).finally(() => {
            setLoading(false);
        });
    }, [albumId]);

    const queryInfo = useMemo(() => {
        if (!album?.query_json) return null;
        try {
            return JSON.parse(album.query_json) as { query: string, filters: SearchFilters };
        } catch {
            return null;
        }
    }, [album]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-zinc-950 text-zinc-500">
                <div className="animate-pulse flex flex-col items-center">
                    <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
                    {t("loadingDetail")}
                </div>
            </div>
        );
    }

    if (!album) {
        return (
            <div className="flex items-center justify-center h-screen bg-zinc-950 text-zinc-500">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-white mb-4">{t("notFound")}</h1>
                    <button onClick={() => router.push('/albums')} className="text-blue-500 hover:underline">
                        {t("back")}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <main className="flex h-screen w-full bg-zinc-950 overflow-hidden font-sans">
            <Sidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
            />

            <div className="flex-1 h-full relative border-r border-zinc-800 flex flex-col">
                <div className="p-8 pb-4 bg-zinc-950/50 backdrop-blur-sm sticky top-0 z-20">
                    <button
                        onClick={() => router.push('/albums')}
                        className="flex items-center gap-2 text-zinc-500 hover:text-white transition-colors mb-6 group text-sm font-medium"
                    >
                        <ArrowLeft className="w-4 h-4 transition-transform group-hover:-translate-x-1" />
                        {t("back")}
                    </button>

                    <div className="flex items-end justify-between">
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                {album.is_dynamic ? (
                                    <Sparkles className="w-6 h-6 text-blue-500" />
                                ) : (
                                    <Folder className="w-6 h-6 text-zinc-600" />
                                )}
                                <h1 className="text-4xl font-black text-white tracking-tight">{album.name}</h1>
                            </div>
                            <div className="flex items-center gap-4 text-zinc-500 text-sm font-medium">
                                <span>{commonT("items", { count: media.length })}</span>
                                <span className="w-1.5 h-1.5 rounded-full bg-zinc-800" />
                                <span>{t("created", { date: new Date(album.created_at).toLocaleDateString() })}</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <button className="p-2.5 bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-all active:scale-95 shadow-lg">
                                <Share2 className="w-5 h-5" />
                            </button>
                            <button className="p-2.5 bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-xl transition-all active:scale-95 shadow-lg">
                                <Edit2 className="w-5 h-5" />
                            </button>
                            <button className="p-2.5 bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-red-500 hover:bg-red-500/10 rounded-xl transition-all active:scale-95 shadow-lg">
                                <Trash2 className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {album.is_dynamic && queryInfo && (
                        <div className="mt-8 p-4 bg-zinc-900/50 border border-zinc-800/50 rounded-2xl flex flex-col gap-3">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">{t("dynamicQuery")}</span>
                                <div className="h-px flex-1 bg-zinc-800" />
                            </div>
                            <div className="flex items-center gap-4">
                                <span className="text-zinc-300 italic text-sm">&quot;{queryInfo.query}&quot;</span>
                                {Object.values(queryInfo.filters || {}).some(v => Array.isArray(v) ? v.length > 0 : !!v) && (
                                    <div className="flex flex-wrap gap-1.5 border-l border-zinc-800 pl-4">
                                        {Object.entries(queryInfo.filters || {}).flatMap(([key, val]) => (
                                            Array.isArray(val) ? val.map(v => ({ key, val: v })) : [{ key, val }]
                                        )).filter(f => !!f.val).map((filter, i) => (
                                            <div key={i} className="px-2 py-0.5 bg-zinc-950 border border-zinc-800 text-zinc-500 text-[10px] rounded-full flex items-center gap-1.5">
                                                <Tag className="w-2.5 h-2.5" />
                                                <span className="text-zinc-400 font-semibold uppercase">{filter.key}:</span>
                                                <span className="text-blue-400">{filter.val}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {!album.is_dynamic && (
                        <div className="mt-6 flex items-center justify-between p-1 bg-zinc-900 border border-zinc-800 rounded-2xl">
                            <div className="px-4 text-xs font-bold text-zinc-500 uppercase tracking-wider">
                                {t("staticCollection")}
                            </div>
                            <button className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-bold rounded-xl transition-all active:scale-95 border border-zinc-700/50">
                                {t("addItems")}
                            </button>
                        </div>
                    )}
                </div>

                <div className="flex-1 min-h-0 bg-zinc-950">
                    <GalleryGrid
                        media={media}
                        onSelect={setSelectedItem}
                        hasMore={false}
                    />
                </div>
            </div>

            {selectedItem && (
                <ChatPanel
                    item={selectedItem}
                    onClose={() => setSelectedItem(null)}
                />
            )}
        </main>
    );
}
