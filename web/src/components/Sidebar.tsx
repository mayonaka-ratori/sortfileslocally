"use client"
import React, { useEffect, useState } from "react"
import { fetchFilters } from "@/lib/api"
import { LayoutGrid, Filter } from "lucide-react"
import { ScanUI } from "./ScanUI"

export interface FilterState {
    character?: string;
    series?: string;
    media_type?: string;
}

interface SidebarProps {
    onFilterChange: (filters: FilterState) => void;
    isOpen: boolean;
    onClose: () => void;
}

export function Sidebar({ onFilterChange, isOpen, onClose }: SidebarProps) {
    const [characters, setCharacters] = useState<string[]>([])
    const [seriesList, setSeriesList] = useState<string[]>([])

    const [selectedCharacter, setSelectedCharacter] = useState("All")
    const [selectedSeries, setSelectedSeries] = useState("All")
    const [selectedMediaType, setSelectedMediaType] = useState("All")

    useEffect(() => {
        fetchFilters().then(data => {
            setCharacters(data.characters)
            setSeriesList(data.series)
        }).catch(console.error)
    }, [])

    const handleFilterUpdate = (type: string, val: string) => {
        if (type === 'character') setSelectedCharacter(val)
        if (type === 'series') setSelectedSeries(val)
        if (type === 'media') setSelectedMediaType(val)

        const newFilters = {
            character: type === 'character' ? val : selectedCharacter,
            series: type === 'series' ? val : selectedSeries,
            media_type: type === 'media' ? val : selectedMediaType,
        }

        onFilterChange({
            character: newFilters.character === 'All' ? undefined : newFilters.character,
            series: newFilters.series === 'All' ? undefined : newFilters.series,
            media_type: newFilters.media_type === 'All' ? undefined : newFilters.media_type,
        })
    }

    return (
        <>
            {/* Mobile overlay */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden transition-opacity"
                    onClick={onClose}
                />
            )}

            <div className={`fixed inset-y-0 left-0 z-50 transform flex-shrink-0 w-72 h-full bg-zinc-950 border-r border-zinc-800 flex flex-col transition-transform duration-300 ease-in-out md:relative md:translate-x-0 overflow-y-auto ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
                {/* Header */}
                <div className="sticky top-0 bg-zinc-950/80 backdrop-blur z-10 p-5 pb-4">
                    <div className="flex items-center gap-2 font-black text-white px-1 tracking-tight text-xl mb-4">
                        <LayoutGrid className="w-6 h-6 text-indigo-500 shrink-0" />
                        <span className="bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">Curator Prime</span>
                    </div>
                </div>

                <div className="px-5 pb-6 flex flex-col gap-6">
                    {/* Scan Section */}
                    <ScanUI />

                    <div className="mb-6 px-2">
                        <h3 className="text-xs uppercase text-zinc-500 font-semibold mb-3 flex items-center gap-2">
                            <Filter className="w-3 h-3" /> Filters
                        </h3>

                        <div className="mb-6">
                            <label className="block text-zinc-400 mb-2 text-xs font-medium">Media Type</label>
                            <div className="flex bg-zinc-900 border border-zinc-800 rounded-lg p-1 gap-1">
                                {['All', 'image', 'video'].map((type) => (
                                    <button
                                        key={type}
                                        onClick={() => handleFilterUpdate('media', type)}
                                        className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${selectedMediaType === type
                                            ? 'bg-zinc-800 text-white shadow-sm'
                                            : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                                            }`}
                                    >
                                        {type === 'All' ? 'All' : type === 'image' ? 'Images' : 'Videos'}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="mb-4">
                            <label className="block text-zinc-400 mb-1 text-xs">Character</label>
                            <select
                                value={selectedCharacter}
                                onChange={(e) => handleFilterUpdate('character', e.target.value)}
                                className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1.5 focus:outline-none focus:border-indigo-500 transition-colors"
                            >
                                <option value="All">All Characters</option>
                                {characters.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>

                        <div className="mb-4">
                            <label className="block text-zinc-400 mb-1 text-xs">Series</label>
                            <select
                                value={selectedSeries}
                                onChange={(e) => handleFilterUpdate('series', e.target.value)}
                                className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1.5 focus:outline-none focus:border-indigo-500 transition-colors"
                            >
                                <option value="All">All Series</option>
                                {seriesList.map(c => <option key={c} value={c}>{c}</option>)}
                            </select>
                        </div>
                    </div>
                </div>
            </div>
        </>
    )
}
