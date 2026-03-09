"use client"
import React from "react"
import Link from "next/link"
import { useTranslations } from 'next-intl';
import { LayoutGrid, Settings, BookOpen, Sparkles, Folder, Tag } from "lucide-react"
import { useEffect, useState } from "react"
import { fetchAlbums, Album } from "@/lib/api"
import { ScanUI } from "./ScanUI"
import { PrivacyBadge } from "./PrivacyBadge"

export interface FilterState {
    character?: string;
    series?: string;
    media_type?: string;
}

interface SidebarProps {
    onFilterChange?: (filters: FilterState) => void;
    isOpen: boolean;
    onClose: () => void;
    className?: string;
}

export function Sidebar({ isOpen, onClose, className = "" }: SidebarProps) {
    const t = useTranslations('sidebar');
    const [albums, setAlbums] = useState<Album[]>([])

    useEffect(() => {
        fetchAlbums().then(setAlbums).catch(console.error)
    }, [])

    return (
        <>
            {/* Mobile overlay */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden transition-opacity"
                    onClick={onClose}
                />
            )}

            <div
                data-testid="sidebar"
                className={`fixed inset-y-0 left-0 z-50 transform flex-shrink-0 w-72 h-full bg-zinc-950 border-r border-zinc-800 flex flex-col transition-transform duration-300 ease-in-out md:relative md:translate-x-0 overflow-y-auto ${isOpen ? 'translate-x-0' : '-translate-x-full'} ${className}`}
            >
                {/* Header */}
                <div className="sticky top-0 bg-zinc-950/80 backdrop-blur z-10 p-5 pb-4">
                    <div className="flex items-center gap-2 font-black text-white px-1 tracking-tight text-xl mb-4">
                        <LayoutGrid className="w-6 h-6 text-indigo-500 shrink-0" />
                        <span className="bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">{t('appName')}</span>
                    </div>
                </div>

                <div className="px-5 pb-6 flex flex-col gap-6">
                    {/* Scan Section */}
                    <ScanUI />

                    <div className="mb-6 px-2">
                        <h3 className="text-xs uppercase text-zinc-500 font-semibold mb-3 flex items-center gap-2">
                            <LayoutGrid className="w-3 h-3 text-indigo-500" /> {t('library')}
                        </h3>

                        <div className="flex flex-col gap-1">
                            <Link href="/" onClick={onClose} className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-white bg-zinc-800/50 transition-colors">
                                <LayoutGrid className="w-4 h-4 text-indigo-500" />
                                {t('allMedia')}
                            </Link>
                            <Link href="/albums" onClick={onClose} className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors">
                                <BookOpen className="w-4 h-4 text-indigo-500" />
                                {t('albums')}
                            </Link>
                            <Link href="/tags" onClick={onClose} className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors">
                                <Tag className="w-4 h-4 text-indigo-500" />
                                {t('tags')}
                            </Link>

                            {albums.length > 0 && (
                                <div className="mt-2 ml-4 flex flex-col gap-1 border-l border-zinc-900">
                                    {albums.slice(0, 5).map(album => (
                                        <Link
                                            key={album.id}
                                            href={`/albums/${album.id}`}
                                            onClick={onClose}
                                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-500 hover:text-white hover:bg-zinc-800/50 transition-colors group"
                                        >
                                            {album.is_dynamic ? (
                                                <Sparkles className="w-3 h-3 text-blue-500/50 group-hover:text-blue-400 Transition-colors" />
                                            ) : (
                                                <Folder className="w-3 h-3 text-zinc-600 group-hover:text-zinc-400 Transition-colors" />
                                            )}
                                            <span className="truncate">{album.name}</span>
                                        </Link>
                                    ))}
                                    {albums.length > 5 && (
                                        <Link href="/albums" onClick={onClose} className="px-3 py-1 text-[10px] text-zinc-600 hover:text-zinc-400">
                                            {t('moreAlbums', { count: albums.length - 5 })}
                                        </Link>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer Link */}
                <div className="mt-auto p-4 border-t border-zinc-800 bg-zinc-950/80 backdrop-blur z-10 space-y-4">
                    <div className="px-3">
                        <PrivacyBadge />
                    </div>
                    <Link href="/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-white hover:bg-zinc-800/50 transition-colors">
                        <Settings className="w-4 h-4" />
                        {t('settings')}
                    </Link>
                </div>
            </div>
        </>
    )
}
