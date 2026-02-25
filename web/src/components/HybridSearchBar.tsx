"use client"
import React, { useState, useEffect, useRef } from "react"
import { useTranslations } from 'next-intl';
import { Search, X, ChevronDown, Check, Image as ImageIcon, Video, Filter, Clock, Clapperboard } from "lucide-react"
import { SearchFilters, fetchFilters, getSearchHistory, deleteSearchHistory, clearSearchHistory, SearchHistoryEntry } from "@/lib/api"

interface HybridSearchBarProps {
    onSearch: (query: string, filters: SearchFilters, searchScenes?: boolean) => void
    initialQuery?: string
}

interface FilterChipProps {
    label: string
    active: boolean
    activeDropdown: string | null
    onClick: () => void
}

const FilterChip = ({ label, active, activeDropdown, onClick }: FilterChipProps) => (
    <button
        onClick={onClick}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${active
            ? "bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-900/20"
            : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
            }`}
    >
        {label}
        <ChevronDown className={`w-3 h-3 transition-transform ${active && activeDropdown === label ? "rotate-180" : ""}`} />
    </button>
)

export function HybridSearchBar({ onSearch, initialQuery = "" }: HybridSearchBarProps) {
    const t = useTranslations('search');
    const [query, setQuery] = useState(initialQuery)
    const [filters, setFilters] = useState<SearchFilters>({})
    const [availableFilters, setAvailableFilters] = useState<{ characters: string[], series: string[] }>({
        characters: [],
        series: []
    })
    const [isSceneSearch, setIsSceneSearch] = useState(false)

    const [activeDropdown, setActiveDropdown] = useState<string | null>(null)
    const [searchHistory, setSearchHistory] = useState<SearchHistoryEntry[]>([])
    const [showHistory, setShowHistory] = useState(false)
    const dropdownRef = useRef<HTMLDivElement>(null)
    const historyRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        fetchFilters().then(data => {
            setAvailableFilters({
                characters: data.characters,
                series: data.series
            })
        }).catch(console.error)
    }, [])

    const loadHistory = async () => {
        try {
            const history = await getSearchHistory(5)
            setSearchHistory(history)
        } catch (error) {
            console.error("Failed to load search history:", error)
        }
    }

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node) &&
                historyRef.current && !historyRef.current.contains(event.target as Node)) {
                setActiveDropdown(null)
                setShowHistory(false)
            }
        }
        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    const handleSearch = (e?: React.FormEvent) => {
        e?.preventDefault()
        onSearch(query, filters, isSceneSearch)
        setActiveDropdown(null)
        setShowHistory(false)
    }

    const handleHistoryClick = (item: SearchHistoryEntry) => {
        const itemFilters = item.filters_json ? JSON.parse(item.filters_json) : {}
        setQuery(item.query_text)
        setFilters(itemFilters)
        onSearch(item.query_text, itemFilters)
        setShowHistory(false)
    }

    const handleDeleteHistory = async (e: React.MouseEvent, id: number) => {
        e.stopPropagation()
        try {
            await deleteSearchHistory(id)
            setSearchHistory(prev => prev.filter(item => item.id !== id))
        } catch (error) {
            console.error("Failed to delete history item:", error)
        }
    }

    const handleClearHistory = async () => {
        try {
            await clearSearchHistory()
            setSearchHistory([])
            setShowHistory(false)
        } catch (error) {
            console.error("Failed to clear history:", error)
        }
    }

    const formatRelativeTime = (timestamp: string) => {
        const date = new Date(timestamp + "Z") // Ensure UTC
        const now = new Date()
        const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

        if (diffInSeconds < 60) return t('justNow')
        if (diffInSeconds < 3600) return t('minAgo', { count: Math.floor(diffInSeconds / 60) })
        if (diffInSeconds < 86400) return t('hrAgo', { count: Math.floor(diffInSeconds / 3600) })
        if (diffInSeconds < 172800) return t('yesterday')
        return date.toLocaleDateString()
    }

    const parseFilters = (json: string | null): string[] => {
        if (!json) return []
        try {
            const f = JSON.parse(json)
            const labels: string[] = []
            if (f.character_tags) labels.push(...f.character_tags)
            if (f.series_tags) labels.push(...f.series_tags)
            if (f.media_type) labels.push(f.media_type)
            return labels
        } catch { return [] }
    }

    const toggleFilter = (type: keyof SearchFilters, value: string) => {
        setFilters(prev => {
            const current = (prev[type] as string[]) || []
            let next: string[]
            if (current.includes(value)) {
                next = current.filter(v => v !== value)
            } else {
                next = [...current, value]
            }
            return { ...prev, [type]: next.length > 0 ? next : undefined }
        })
    }

    const setMediaType = (type: string | undefined) => {
        setFilters(prev => ({ ...prev, media_type: prev.media_type === type ? undefined : type }))
        setActiveDropdown(null)
    }

    const removeFilter = (type: keyof SearchFilters, value: string) => {
        setFilters(prev => {
            const current = (prev[type] as string[]) || []
            const next = current.filter(v => v !== value)
            return { ...prev, [type]: next.length > 0 ? next : undefined }
        })
    }

    const clearAll = () => {
        setFilters({})
        setQuery("")
        setIsSceneSearch(false)
    }


    return (
        <div className="w-full max-w-4xl mx-auto flex flex-col gap-3">
            <div className="relative" ref={dropdownRef}>
                <form onSubmit={handleSearch} className="relative group">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => {
                            setQuery(e.target.value)
                            if (e.target.value) setShowHistory(false)
                        }}
                        onFocus={() => {
                            if (!query) {
                                loadHistory()
                                setShowHistory(true)
                            }
                        }}
                        onKeyDown={(e) => {
                            if (e.key === "Escape") {
                                setShowHistory(false)
                                setActiveDropdown(null)
                            }
                        }}
                        placeholder={t('placeholder')}
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 pl-14 pr-32 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-xl"
                    />
                    <div className="absolute left-5 top-1/2 -translate-y-1/2 flex items-center gap-2">
                        {isSceneSearch ? (
                            <Clapperboard className="w-6 h-6 text-indigo-400 transition-colors" />
                        ) : (
                            <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-zinc-500 group-focus-within:text-indigo-400 transition-colors" />
                        )}
                    </div>
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                        {(query || Object.keys(filters).length > 0) && (
                            <button
                                type="button"
                                onClick={clearAll}
                                className="p-2 text-zinc-500 hover:text-white transition-colors"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        )}
                        <button
                            type="submit"
                            className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl px-5 py-2 text-sm font-bold transition-all shadow-lg shadow-indigo-900/40 active:scale-95"
                        >
                            {t('button')}
                        </button>
                    </div>
                </form>

                {/* Search History Dropdown */}
                {showHistory && searchHistory.length > 0 && (
                    <div ref={historyRef} className="absolute top-full left-0 right-0 mt-2 bg-zinc-950 border border-zinc-800 rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                        <div className="px-4 py-3 border-b border-zinc-800 flex items-center gap-2 text-zinc-400">
                            <Clock className="w-4 h-4" />
                            <span className="text-xs font-bold uppercase tracking-wider">{t('recentSearches')}</span>
                        </div>
                        <div className="max-h-80 overflow-y-auto">
                            {searchHistory.map((item) => {
                                const filterLabels = parseFilters(item.filters_json)
                                return (
                                    <div
                                        key={item.id}
                                        onClick={() => handleHistoryClick(item)}
                                        className="group w-full flex items-center justify-between px-4 py-3 hover:bg-zinc-900 cursor-pointer transition-colors border-b border-zinc-900 last:border-0"
                                    >
                                        <div className="flex flex-col gap-1 min-w-0 flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className="text-zinc-100 font-bold truncate">{item.query_text}</span>
                                                <span className="text-[10px] text-zinc-500 bg-zinc-800 px-1.5 py-0.5 rounded whitespace-nowrap">
                                                    {t('results', { count: item.result_count })}
                                                </span>
                                            </div>
                                            <div className="flex flex-wrap gap-1">
                                                {filterLabels.slice(0, 3).map((f, i) => (
                                                    <span key={i} className="text-[9px] text-zinc-500 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
                                                        {f}
                                                    </span>
                                                ))}
                                                {filterLabels.length > 3 && (
                                                    <span className="text-[9px] text-zinc-600 px-1">
                                                        {t('moreFilters', { count: filterLabels.length - 3 })}
                                                    </span>
                                                )}
                                                <span className="text-[9px] text-zinc-600 ml-auto">
                                                    {formatRelativeTime(item.executed_at)}
                                                </span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={(e) => handleDeleteHistory(e, item.id)}
                                            className="ml-4 p-2 text-zinc-700 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                                        >
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                )
                            })}
                        </div>
                        <div className="px-4 py-2 border-t border-zinc-800 bg-zinc-900/50">
                            <button
                                onClick={handleClearHistory}
                                className="text-[10px] font-bold text-zinc-500 hover:text-indigo-400 transition-colors uppercase tracking-widest"
                            >
                                {t('clearHistory')}
                            </button>
                        </div>
                    </div>
                )}

                {/* Dropdown menus */}
                {activeDropdown && (
                    <div className="absolute top-full left-0 right-0 mt-2 p-2 bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl z-50 animate-in fade-in zoom-in-95 duration-200 max-h-80 overflow-y-auto">
                        {activeDropdown === "Characters" && availableFilters.characters.map(c => (
                            <button
                                key={c}
                                onClick={() => toggleFilter("character_tags", c)}
                                className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-300 transition-colors"
                            >
                                {c}
                                {filters.character_tags?.includes(c) && <Check className="w-4 h-4 text-indigo-500" />}
                            </button>
                        ))}
                        {activeDropdown === "Series" && availableFilters.series.map(s => (
                            <button
                                key={s}
                                onClick={() => toggleFilter("series_tags", s)}
                                className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-300 transition-colors"
                            >
                                {s}
                                {filters.series_tags?.includes(s) && <Check className="w-4 h-4 text-indigo-500" />}
                            </button>
                        ))}
                        {activeDropdown === "Media Type" && (
                            <div className="flex flex-col gap-1">
                                <button
                                    onClick={() => setMediaType("image")}
                                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-300"
                                >
                                    <div className="flex items-center gap-2">
                                        <ImageIcon className="w-4 h-4 text-zinc-500" /> {t('imagesOnly')}
                                    </div>
                                    {filters.media_type === "image" && <Check className="w-4 h-4 text-indigo-500" />}
                                </button>
                                <button
                                    onClick={() => setMediaType("video")}
                                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-300"
                                >
                                    <div className="flex items-center gap-2">
                                        <Video className="w-4 h-4 text-zinc-500" /> {t('videosOnly')}
                                    </div>
                                    {filters.media_type === "video" && <Check className="w-4 h-4 text-indigo-500" />}
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Filter Buttons */}
            <div className="flex flex-wrap items-center gap-2 px-1">
                <Filter className="w-3.5 h-3.5 text-zinc-500 mr-1" />
                <FilterChip
                    label={t('characters')}
                    active={filters.character_tags !== undefined}
                    activeDropdown={activeDropdown}
                    onClick={() => setActiveDropdown(activeDropdown === "Characters" ? null : "Characters")}
                />
                <FilterChip
                    label={t('series')}
                    active={filters.series_tags !== undefined}
                    activeDropdown={activeDropdown}
                    onClick={() => setActiveDropdown(activeDropdown === "Series" ? null : "Series")}
                />
                <FilterChip
                    label={t('mediaType')}
                    active={filters.media_type !== undefined}
                    activeDropdown={activeDropdown}
                    onClick={() => setActiveDropdown(activeDropdown === "Media Type" ? null : "Media Type")}
                />

                <div className="h-4 w-[1px] bg-zinc-800 mx-1" />

                <button
                    onClick={() => setIsSceneSearch(!isSceneSearch)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all border uppercase tracking-wider ${isSceneSearch
                        ? "bg-indigo-600 border-indigo-500 text-white shadow-lg shadow-indigo-900/40"
                        : "bg-zinc-900 border-zinc-800 text-zinc-500 hover:border-zinc-700 hover:text-zinc-300"
                        }`}
                >
                    <Clapperboard className="w-3.5 h-3.5" />
                    {t('searchScenes')}
                </button>
            </div>

            {/* Active Filters */}
            <div className="flex flex-wrap gap-2">
                {filters.character_tags?.map(c => (
                    <span key={c} className="flex items-center gap-1.5 bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 px-2.5 py-1 rounded-md text-[10px] uppercase font-bold tracking-wider">
                        {c}
                        <button onClick={() => removeFilter("character_tags", c)} className="hover:text-white transition-colors">
                            <X className="w-3 h-3" />
                        </button>
                    </span>
                ))}
                {filters.series_tags?.map(s => (
                    <span key={s} className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-2.5 py-1 rounded-md text-[10px] uppercase font-bold tracking-wider">
                        {s}
                        <button onClick={() => removeFilter("series_tags", s)} className="hover:text-white transition-colors">
                            <X className="w-3 h-3" />
                        </button>
                    </span>
                ))}
                {filters.media_type && (
                    <span className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/30 text-amber-400 px-2.5 py-1 rounded-md text-[10px] uppercase font-bold tracking-wider">
                        {filters.media_type}
                        <button onClick={() => setMediaType(undefined)} className="hover:text-white transition-colors">
                            <X className="w-3 h-3" />
                        </button>
                    </span>
                )}
            </div>
        </div>
    )
}
