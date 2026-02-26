"use client"

import React, { useEffect, useState } from 'react';
import { fetchAlbums, Album, getThumbnailUrl } from '@/lib/api';
import { Sidebar } from '@/components/Sidebar';
import Link from 'next/link';
import Image from 'next/image';
import { Sparkles, Folder, Plus, ChevronRight, Image as ImageIcon } from 'lucide-react';
import { useTranslations } from 'next-intl';

export default function AlbumsPage() {
    const t = useTranslations("albums");
    const commonT = useTranslations("common");
    const [albums, setAlbums] = useState<Album[]>([]);
    const [loading, setLoading] = useState(true);
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    useEffect(() => {
        fetchAlbums()
            .then(setAlbums)
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    return (
        <main className="flex h-screen w-full bg-zinc-950 overflow-hidden font-sans">
            <Sidebar
                isOpen={isSidebarOpen}
                onClose={() => setIsSidebarOpen(false)}
            />

            <div className="flex-1 h-full overflow-y-auto relative">
                <div className="max-w-7xl mx-auto p-8">
                    <div className="flex items-center justify-between mb-10">
                        <div>
                            <h1 className="text-3xl font-bold text-white mb-2">{t("title")}</h1>
                            <p className="text-zinc-500">{t("subtitle")}</p>
                        </div>
                        <button className="flex items-center gap-2 px-5 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-white font-semibold rounded-xl transition-all active:scale-95 border border-zinc-700/50 shadow-xl shadow-black/20">
                            <Plus className="w-5 h-5" />
                            {t("createAlbum")}
                        </button>
                    </div>

                    {loading ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {[1, 2, 3, 4].map(i => (
                                <div key={i} className="aspect-[4/3] rounded-2xl bg-zinc-900 animate-pulse border border-zinc-800" />
                            ))}
                        </div>
                    ) : albums.length === 0 ? (
                        <div className="flex flex-col items-center justify-center py-20 text-center">
                            <div className="w-20 h-20 bg-zinc-900 rounded-3xl flex items-center justify-center mb-6 border border-zinc-800">
                                <Folder className="w-10 h-10 text-zinc-700" />
                            </div>
                            <h2 className="text-xl font-semibold text-white mb-2">{t("empty")}</h2>
                            <p className="text-zinc-500 max-w-sm mb-8">
                                {t("emptyDesc")}
                            </p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {albums.map((album) => (
                                <Link
                                    key={album.id}
                                    href={`/albums/detail?id=${album.id}`}
                                    className="group relative bg-zinc-900 border border-zinc-800 rounded-3xl overflow-hidden hover:border-zinc-600 transition-all hover:shadow-2xl hover:shadow-black/40 hover:-translate-y-1 block"
                                >
                                    <div className="aspect-[4/3] relative bg-zinc-950 flex items-center justify-center overflow-hidden">
                                        {album.cover_file_id ? (
                                            <Image
                                                src={getThumbnailUrl(album.cover_file_id, 600)}
                                                alt={album.name}
                                                fill
                                                className="object-cover transition-transform duration-500 group-hover:scale-110 opacity-60 group-hover:opacity-100"
                                            />
                                        ) : (
                                            <div className="flex flex-col items-center gap-3 text-zinc-800 group-hover:text-zinc-500 transition-colors">
                                                <ImageIcon className="w-12 h-12" />
                                                <span className="text-xs font-bold uppercase tracking-widest">{t("emptyAlbum")}</span>
                                            </div>
                                        )}

                                        {/* Status Badge */}
                                        <div className="absolute top-4 left-4 flex items-center gap-2">
                                            {album.is_dynamic ? (
                                                <div className="px-2.5 py-1 bg-blue-600/90 backdrop-blur-md text-white text-[10px] font-bold rounded-full flex items-center gap-1.5 shadow-lg shadow-blue-600/20 uppercase tracking-wider">
                                                    <Sparkles className="w-3 h-3" />
                                                    {t("smart")}
                                                </div>
                                            ) : (
                                                <div className="px-2.5 py-1 bg-zinc-800/90 backdrop-blur-md text-zinc-300 text-[10px] font-bold rounded-full flex items-center gap-1.5 shadow-lg uppercase tracking-wider">
                                                    <Folder className="w-3 h-3" />
                                                    {t("static")}
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div className="p-5 flex items-end justify-between">
                                        <div>
                                            <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors line-clamp-1">{album.name}</h3>
                                            <p className="text-zinc-500 text-sm font-medium">{commonT("items", { count: album.item_count })}</p>
                                        </div>
                                        <div className="w-10 h-10 rounded-2xl bg-zinc-950 flex items-center justify-center text-zinc-700 group-hover:text-white transition-all border border-zinc-800 group-hover:border-zinc-700 group-hover:bg-zinc-800">
                                            <ChevronRight className="w-5 h-5" />
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </main>
    );
}
