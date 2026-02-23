"use client"
import React, { useState, useEffect, useRef } from "react"
import { Search, X, ChevronDown, Check, Image as ImageIcon, Video, Filter } from "lucide-react"
import { SearchFilters, fetchFilters } from "@/lib/api"

interface HybridSearchBarProps {
    onSearch: (query: string, filters: SearchFilters) => void
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
    const [query, setQuery] = useState(initialQuery)
    const [filters, setFilters] = useState<SearchFilters>({})
    const [availableFilters, setAvailableFilters] = useState<{ characters: string[], series: string[] }>({
        characters: [],
        series: []
    })

    const [activeDropdown, setActiveDropdown] = useState<string | null>(null)
    const dropdownRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        fetchFilters().then(data => {
            setAvailableFilters({
                characters: data.characters,
                series: data.series
            })
        }).catch(console.error)
    }, [])

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setActiveDropdown(null)
            }
        }
        document.addEventListener("mousedown", handleClickOutside)
        return () => document.removeEventListener("mousedown", handleClickOutside)
    }, [])

    const handleSearch = (e?: React.FormEvent) => {
        e?.preventDefault()
        onSearch(query, filters)
        setActiveDropdown(null)
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
    }


    return (
        <div className="w-full max-w-4xl mx-auto flex flex-col gap-3">
            <div className="relative" ref={dropdownRef}>
                <form onSubmit={handleSearch} className="relative group">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search your library with natural language..."
                        className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 pl-14 pr-32 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-xl"
                    />
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-zinc-500 group-focus-within:text-indigo-400 transition-colors" />
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
                            Search
                        </button>
                    </div>
                </form>

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
                                        <ImageIcon className="w-4 h-4 text-zinc-500" /> Images Only
                                    </div>
                                    {filters.media_type === "image" && <Check className="w-4 h-4 text-indigo-500" />}
                                </button>
                                <button
                                    onClick={() => setMediaType("video")}
                                    className="w-full flex items-center justify-between px-3 py-2 rounded-lg hover:bg-zinc-800 text-sm text-zinc-300"
                                >
                                    <div className="flex items-center gap-2">
                                        <Video className="w-4 h-4 text-zinc-500" /> Videos Only
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
                    label="Characters"
                    active={filters.character_tags !== undefined}
                    activeDropdown={activeDropdown}
                    onClick={() => setActiveDropdown(activeDropdown === "Characters" ? null : "Characters")}
                />
                <FilterChip
                    label="Series"
                    active={filters.series_tags !== undefined}
                    activeDropdown={activeDropdown}
                    onClick={() => setActiveDropdown(activeDropdown === "Series" ? null : "Series")}
                />
                <FilterChip
                    label="Media Type"
                    active={filters.media_type !== undefined}
                    activeDropdown={activeDropdown}
                    onClick={() => setActiveDropdown(activeDropdown === "Media Type" ? null : "Media Type")}
                />
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
