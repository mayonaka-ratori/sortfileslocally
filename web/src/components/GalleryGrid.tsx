"use client"

import React, { useState, useEffect, useRef } from "react"
import { MediaItem, getThumbnailUrl, getOriginalUrl } from "@/lib/api"
import { Search, Loader2, Menu, PlayCircle, FileText } from "lucide-react"
import { useInView } from "react-intersection-observer"

const MediaCard = ({ item, onSelect }: { item: MediaItem, onSelect: (item: MediaItem) => void }) => {
    const [isHovered, setIsHovered] = useState(false);
    const hoverTimeout = useRef<NodeJS.Timeout | null>(null);

    const handleMouseEnter = () => {
        if (item.media_type === "video") {
            hoverTimeout.current = setTimeout(() => {
                setIsHovered(true);
            }, 600); // Wait 600ms before playing video preview
        }
    };

    const handleMouseLeave = () => {
        if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
        setIsHovered(false);
    };

    // Cleanup timeout on unmount
    React.useEffect(() => {
        return () => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
        };
    }, []);

    return (
        <div
            onClick={() => onSelect(item)}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            className="relative group cursor-pointer overflow-hidden rounded-xl bg-zinc-900 border border-zinc-800 hover:border-indigo-500/50 transition-all duration-300 break-inside-avoid shadow-lg flex flex-col"
        >
            <div className="relative w-full aspect-auto bg-zinc-900">
                {/* Always show thumbnail, but fade it out if video is ready */}
                <img
                    src={getThumbnailUrl(item.id, 400)}
                    alt={`Media ${item.id}`}
                    className={`w-full h-auto object-cover transition-opacity duration-300 ${isHovered && item.media_type === "video" ? 'opacity-0' : 'opacity-100'}`}
                    loading="lazy"
                />

                {isHovered && item.media_type === "video" && (
                    <video
                        src={getOriginalUrl(item.id)}
                        autoPlay
                        loop
                        muted
                        playsInline
                        className="absolute inset-0 w-full h-full object-cover rounded-xl"
                    />
                )}

                {/* Overlay gradient and badge */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

                {item.media_type === "video" && !isHovered && (
                    <div className="absolute top-3 right-3 bg-black/60 backdrop-blur text-xs px-2 py-1 rounded-md flex items-center gap-1 text-zinc-300 pointer-events-none">
                        <PlayCircle className="w-3 h-3" /> VIDEO
                    </div>
                )}
            </div>

            {/* Tags and Snippets Overlay */}
            <div className="absolute bottom-0 left-0 right-0 p-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col justify-end pointer-events-none">
                {item.character_tags.length > 0 && (
                    <div className="flex gap-1 flex-wrap mb-1">
                        {item.character_tags.slice(0, 2).map((tag, i) => (
                            <span key={i} className="text-[10px] bg-zinc-800/90 backdrop-blur rounded-sm px-1.5 py-0.5 whitespace-nowrap overflow-hidden text-ellipsis max-w-[80px] border border-zinc-700">
                                {tag}
                            </span>
                        ))}
                    </div>
                )}
            </div>

            {/* Persistent snippet below media if matched in search */}
            {item.snippet && (
                <div className="px-3 py-2 bg-indigo-950/30 border-t border-indigo-900/50">
                    <p className="text-xs text-indigo-200 line-clamp-2 leading-relaxed flex items-start gap-1">
                        <FileText className="w-3 h-3 mt-0.5 flex-shrink-0 opacity-70" />
                        <span>{item.snippet}</span>
                    </p>
                </div>
            )}
        </div>
    );
}

interface GalleryGridProps {
    media: MediaItem[]
    onSelect: (item: MediaItem) => void
    onSearch: (query: string) => void
    onLoadMore?: () => void
    hasMore?: boolean
    onMenuClick?: () => void
}

export function GalleryGrid({ media, onSelect, onSearch, onLoadMore, hasMore, onMenuClick }: GalleryGridProps) {
    const [query, setQuery] = useState("")
    const { ref, inView } = useInView()

    useEffect(() => {
        if (inView && hasMore && onLoadMore) {
            onLoadMore()
        }
    }, [inView, hasMore])

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        onSearch(query)
    }

    return (
        <div className="flex flex-col h-full w-full bg-zinc-950 text-zinc-100">
            {/* Search Header */}
            <div className="sticky top-0 z-10 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800 p-4 flex items-center gap-3">
                {onMenuClick && (
                    <button onClick={onMenuClick} className="md:hidden p-2 text-zinc-400 hover:text-white transition-colors">
                        <Menu className="w-6 h-6" />
                    </button>
                )}
                <form onSubmit={handleSearch} className="flex-1 max-w-2xl mx-auto relative">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search with AI (e.g. 'sunset at the beach')"
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-full py-3 px-12 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                    />
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500 w-5 h-5" />
                    <button
                        type="submit"
                        className="absolute right-2 top-1/2 -translate-y-1/2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full px-4 py-1.5 text-sm font-medium transition-colors"
                    >
                        Search
                    </button>
                </form>
            </div>

            {/* Grid */}
            <div className="flex-1 overflow-y-auto p-4">
                {media.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
                        <Search className="w-12 h-12 mb-4 opacity-20" />
                        <p className="text-lg">No media found. Try another search.</p>
                    </div>
                ) : (
                    <div className="columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-4 space-y-4">
                        {media.map((item) => (
                            <MediaCard key={item.id} item={item} onSelect={onSelect} />
                        ))}
                    </div>
                )}
                {hasMore && media.length > 0 && (
                    <div ref={ref} className="w-full flex justify-center py-8">
                        <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
                    </div>
                )}
            </div>
        </div>
    )
}
