"use client"
import React, { useState, useEffect, useRef } from "react"

import { MediaItem, getThumbnailUrl, getOriginalUrl } from "@/lib/api"
import { Search, Loader2, Menu, PlayCircle, FileText, CheckCircle2, Download, X, AlertCircle } from "lucide-react"
import { useInView } from "react-intersection-observer"
import Image from "next/image"
import { BulkExportModal } from "./BulkExportModal"
import { BulkTagModal } from "./BulkTagModal"
import { Album, fetchAlbums, addItemsToAlbum } from "@/lib/api"
import { Tag, FolderPlus, Folder, RefreshCw } from "lucide-react"
import { BulkRescanModal } from "./BulkRescanModal"
import { useTranslations } from "next-intl"

const MediaCard = ({
    item,
    onSelect,
    isSelected,
    isFocused,
    isSelectionMode,
    onToggleSelect
}: {
    item: MediaItem,
    onSelect: (item: MediaItem) => void,
    isSelected: boolean,
    isFocused?: boolean,
    isSelectionMode: boolean,
    onToggleSelect: (id: number) => void
}) => {
    const t = useTranslations("gallery");
    const cardRef = useRef<HTMLDivElement>(null);
    const [isHovered, setIsHovered] = useState(false);
    const hoverTimeout = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (isFocused && cardRef.current) {
            cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }, [isFocused]);

    const handleMouseEnter = () => {
        if (item.media_type === "video") {
            hoverTimeout.current = setTimeout(() => {
                setIsHovered(true);
            }, 600);
        }
    };

    const handleMouseLeave = () => {
        if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
        setIsHovered(false);
    };

    const handleClick = (e: React.MouseEvent) => {
        if (isSelectionMode || e.ctrlKey || e.metaKey) {
            e.preventDefault();
            e.stopPropagation();
            onToggleSelect(item.id);
        } else {
            onSelect(item);
        }
    };

    return (
        <div
            ref={cardRef}
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            className={`relative group cursor-pointer overflow-hidden rounded-xl bg-zinc-900 border transition-all duration-300 break-inside-avoid shadow-lg flex flex-col ${isSelected ? 'border-indigo-500 ring-2 ring-indigo-500/50' : isFocused ? 'border-indigo-400 ring-1 ring-indigo-400/30' : 'border-zinc-800 hover:border-zinc-700'}`}
        >
            <div className="relative w-full aspect-auto bg-zinc-900">
                <Image
                    src={getThumbnailUrl(item.id, 400)}
                    alt={`Media ${item.id}`}
                    width={400}
                    height={300}
                    className={`w-full h-auto object-cover transition-opacity duration-300 ${isHovered && item.media_type === "video" ? 'opacity-0' : 'opacity-100'}`}
                    loading="lazy"
                    unoptimized
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

                {/* Selection Overlay */}
                {(isSelected || isSelectionMode) && (
                    <div className="absolute top-2 left-2 z-10">
                        <div className={`rounded-full p-0.5 transition-colors ${isSelected ? 'bg-indigo-600 text-white' : 'bg-black/40 text-white/50 border border-white/20 hover:bg-black/60'}`}>
                            <CheckCircle2 className="w-5 h-5" />
                        </div>
                    </div>
                )}

                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

                {item.media_type === "video" && !isHovered && (
                    <div className="absolute top-3 right-3 bg-black/60 backdrop-blur text-xs px-2 py-1 rounded-md flex items-center gap-1 text-zinc-300 pointer-events-none">
                        <PlayCircle className="w-3 h-3" /> {t("videoBadge")}
                    </div>
                )}
            </div>

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
    onSearch?: (query: string) => void
    onLoadMore?: () => void
    hasMore?: boolean
    onMenuClick?: () => void
    onImageDrop?: (file: File) => void
    focusedIndex?: number
    selectedIds?: Set<number>
    onSelectionChange?: (ids: Set<number>) => void
    error?: string
    onRetry?: () => void
}

export function GalleryGrid({
    media,
    onSelect,
    onSearch,
    onLoadMore,
    hasMore,
    onMenuClick,
    onImageDrop,
    focusedIndex = -1,
    selectedIds: externalSelectedIds,
    onSelectionChange,
    error,
    onRetry
}: GalleryGridProps) {
    const t = useTranslations("gallery");
    const commonT = useTranslations("common");
    const [query, setQuery] = useState("")
    const [isDragging, setIsDragging] = useState(false)
    const [internalSelectedIds, setInternalSelectedIds] = useState<Set<number>>(new Set())

    const selectedIds = externalSelectedIds || internalSelectedIds
    const setSelectedIds = onSelectionChange || setInternalSelectedIds

    const [showBulkModal, setShowBulkModal] = useState(false)
    const [showBulkTagModal, setShowBulkTagModal] = useState(false)
    const [showBulkRescanModal, setShowBulkRescanModal] = useState(false)
    const [showAlbumDropdown, setShowAlbumDropdown] = useState(false)
    const [albums, setAlbums] = useState<Album[]>([])
    const { ref, inView } = useInView()

    useEffect(() => {
        if (inView && hasMore && onLoadMore) {
            onLoadMore()
        }
    }, [inView, hasMore, onLoadMore])

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault()
        onSearch?.(query)
    }

    const toggleSelect = (id: number) => {
        const next = new Set(selectedIds)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        setSelectedIds(next)
    }

    const clearSelection = () => {
        setSelectedIds(new Set())
        setShowAlbumDropdown(false)
    }

    const handleAddToAlbumClick = async () => {
        if (!showAlbumDropdown) {
            try {
                const data = await fetchAlbums()
                setAlbums(data.filter(a => !a.is_dynamic))
                setShowAlbumDropdown(true)
            } catch (err) {
                console.error("Failed to fetch albums", err)
            }
        } else {
            setShowAlbumDropdown(false)
        }
    }

    const handleAlbumSelect = async (albumId: number) => {
        try {
            await addItemsToAlbum(albumId, Array.from(selectedIds))
            const albumName = albums.find(a => a.id === albumId)?.name || commonT('album')
            alert(t("addedToAlbum", { count: selectedIds.size, name: albumName }))
            clearSelection()
        } catch (err) {
            console.error("Failed to add items to album", err)
            alert(t("addAlbumError"))
        }
    }

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
        const file = e.dataTransfer.files?.[0]
        if (file && file.type.startsWith('image/') && onImageDrop) {
            onImageDrop(file)
        }
    }

    const selectedItems = media.filter(item => selectedIds.has(item.id))

    return (
        <div className="flex flex-col h-full w-full bg-zinc-950 text-zinc-100 relative">
            {/* Search Header */}
            <div className="sticky top-0 z-10 bg-zinc-950/80 backdrop-blur-md border-b border-zinc-800 p-4 flex items-center gap-3">
                {onMenuClick && (
                    <button
                        onClick={onMenuClick}
                        className="md:hidden p-2 text-zinc-400 hover:text-white transition-colors"
                        aria-label={commonT('actions')}
                    >
                        <Menu className="w-6 h-6" />
                    </button>
                )}
                <form
                    onSubmit={handleSearch}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`flex-1 max-w-2xl mx-auto relative transition-all rounded-full ${isDragging ? 'ring-2 ring-indigo-500 bg-indigo-500/10' : ''}`}
                >
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder={t("searchPlaceholder")}
                        className={`w-full bg-zinc-900 border ${isDragging ? 'border-indigo-500' : 'border-zinc-800'} rounded-full py-3 px-12 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all`}
                    />
                    <Search className={`absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 transition-colors ${isDragging ? 'text-indigo-400' : 'text-zinc-500'}`} />
                    <button
                        type="submit"
                        className="absolute right-2 top-1/2 -translate-y-1/2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full px-4 py-1.5 text-sm font-medium transition-colors"
                    >
                        {t("searchButton")}
                    </button>
                </form>
            </div>

            {/* Selection Toolbar */}
            {selectedIds.size > 0 && (
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-4 px-6 py-3 bg-indigo-600 rounded-2xl shadow-2xl shadow-indigo-900/40 animate-in slide-in-from-bottom-4 duration-300">
                    <div className="flex items-center gap-2 border-r border-indigo-500 pr-4 mr-1">
                        <span className="text-white font-bold text-sm leading-none">{selectedIds.size}</span>
                        <span className="text-indigo-100 text-xs font-medium uppercase tracking-tight">{t("selected", { count: selectedIds.size })}</span>
                    </div>

                    <button
                        onClick={() => setShowBulkTagModal(true)}
                        className="flex items-center gap-2 text-white hover:text-indigo-100 transition-colors py-1"
                    >
                        <Tag className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">{t("editTags")}</span>
                    </button>

                    <div className="relative">
                        <button
                            onClick={handleAddToAlbumClick}
                            className="flex items-center gap-2 text-white hover:text-indigo-100 transition-colors py-1"
                        >
                            <FolderPlus className="w-4 h-4" />
                            <span className="text-xs font-bold uppercase tracking-wider">{t("addToAlbum")}</span>
                        </button>

                        {showAlbumDropdown && (
                            <div className="absolute bottom-full mb-2 left-0 w-48 bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200">
                                <div className="p-2 border-b border-zinc-800">
                                    <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 px-2">{t("selectAlbum")}</span>
                                </div>
                                <div className="max-h-60 overflow-y-auto p-1">
                                    {albums.length === 0 ? (
                                        <div className="p-4 text-center">
                                            <p className="text-xs text-zinc-500">{t("noAlbums")}</p>
                                        </div>
                                    ) : (
                                        albums.map(album => (
                                            <button
                                                key={album.id}
                                                onClick={() => handleAlbumSelect(album.id)}
                                                className="w-full text-left px-3 py-2 rounded-lg text-xs font-medium text-zinc-300 hover:text-white hover:bg-indigo-600 transition-all flex items-center gap-2"
                                            >
                                                <Folder className="w-3.5 h-3.5 opacity-50" />
                                                <span className="truncate">{album.name}</span>
                                            </button>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={() => setShowBulkModal(true)}
                        className="flex items-center gap-2 text-white hover:text-indigo-100 transition-colors py-1"
                    >
                        <Download className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">{t("exportMeta")}</span>
                    </button>
                    <button
                        onClick={() => setShowBulkRescanModal(true)}
                        className="flex items-center gap-2 text-white hover:text-indigo-100 transition-colors py-1"
                    >
                        <RefreshCw className="w-4 h-4" />
                        <span className="text-xs font-bold uppercase tracking-wider">{t("rescan")}</span>
                    </button>
                    <button
                        onClick={clearSelection}
                        className="p-1 hover:bg-indigo-700 rounded-md transition-colors text-indigo-100"
                        title={t("clearSelection")}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>
            )}

            {/* Grid */}
            <div className="flex-1 overflow-y-auto p-4">
                {error ? (
                    <div className="flex flex-col items-center justify-center h-64 text-red-400 gap-4">
                        <AlertCircle className="w-12 h-12 opacity-50" />
                        <p className="text-sm font-medium">{error}</p>
                        {onRetry && (
                            <button
                                onClick={onRetry}
                                className="flex items-center gap-2 px-6 py-2 bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-bold rounded-xl border border-zinc-700 transition-all select-none active:scale-95"
                            >
                                <RefreshCw className="w-4 h-4" />
                                {commonT("retry")}
                            </button>
                        )}
                    </div>
                ) : media.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
                        <Search className="w-12 h-12 mb-4 opacity-20" />
                        <p className="text-lg">{t("emptySearch")}</p>
                    </div>
                ) : (
                    <div className="columns-2 md:columns-3 lg:columns-4 xl:columns-5 gap-4 space-y-4">
                        {media.map((item, index) => (
                            <MediaCard
                                key={item.id}
                                item={item}
                                onSelect={onSelect}
                                isSelected={selectedIds.has(item.id)}
                                isFocused={index === focusedIndex}
                                isSelectionMode={selectedIds.size > 0}
                                onToggleSelect={toggleSelect}
                            />
                        ))}
                    </div>
                )}
                {hasMore && media.length > 0 && !error && (
                    <div ref={ref} className="w-full flex justify-center py-8">
                        <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
                    </div>
                )}
            </div>

            {showBulkTagModal && (
                <BulkTagModal
                    selectedItems={selectedItems}
                    onClose={() => setShowBulkTagModal(false)}
                    onSuccess={(res) => {
                        alert(t("updateTagsSuccess", { count: res.affected_count }));
                        clearSelection();
                    }}
                />
            )}
            {showBulkModal && (
                <BulkExportModal
                    selectedItems={selectedItems}
                    onClose={() => setShowBulkModal(false)}
                    onSuccess={(success, failed) => {
                        alert(t("exportSuccess", { success, failed }));
                        clearSelection();
                    }}
                />
            )}
            {showBulkRescanModal && (
                <BulkRescanModal
                    selectedItems={selectedItems}
                    onClose={() => setShowBulkRescanModal(false)}
                    onSuccess={() => {
                        alert(t("rescanSuccess"));
                        clearSelection();
                    }}
                />
            )}
        </div>
    )
}
