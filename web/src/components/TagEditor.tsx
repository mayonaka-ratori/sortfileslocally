"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import { TagCategory, TagSuggestion, suggestTags, addTags, removeTags } from "@/lib/api"
import { Plus, X, Loader2, Tag as TagIcon } from "lucide-react"

interface TagInputProps {
    tags: string[]
    category: TagCategory
    onAddTag: (tag: string) => void
    onRemoveTag: (tag: string) => void
    placeholder?: string
    autoFocus?: boolean
    className?: string
    showExistingTags?: boolean
}

export function TagInput({
    tags,
    category,
    onAddTag,
    onRemoveTag,
    placeholder = "New tag...",
    autoFocus = false,
    className = "",
    showExistingTags = true
}: TagInputProps) {
    const [isAdding, setIsAdding] = useState(autoFocus)
    const [inputValue, setInputValue] = useState("")
    const [suggestions, setSuggestions] = useState<TagSuggestion[]>([])
    const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
    const [activeIndex, setActiveIndex] = useState(-1)

    const inputRef = useRef<HTMLInputElement>(null)
    const debounceTimer = useRef<NodeJS.Timeout | null>(null)

    const fetchSuggestions = useCallback(async (query: string) => {
        if (!query.trim()) {
            setSuggestions([])
            return
        }
        setIsLoadingSuggestions(true)
        try {
            const results = await suggestTags(query, category)
            setSuggestions(results)
        } catch (err) {
            console.error("Failed to fetch suggestions", err)
        } finally {
            setIsLoadingSuggestions(false)
        }
    }, [category])

    useEffect(() => {
        if (debounceTimer.current) clearTimeout(debounceTimer.current)
        if (inputValue) {
            debounceTimer.current = setTimeout(() => {
                fetchSuggestions(inputValue)
            }, 300)
        } else {
            setSuggestions([])
        }
        return () => {
            if (debounceTimer.current) clearTimeout(debounceTimer.current)
        }
    }, [inputValue, fetchSuggestions])

    const handleAdd = (tagName: string) => {
        const cleanTag = tagName.trim()
        if (!cleanTag) return
        onAddTag(cleanTag)
        setInputValue("")
        setSuggestions([])
        // For standalone/bulk use, we might want to keep the input open
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") {
            if (activeIndex >= 0 && suggestions[activeIndex]) {
                handleAdd(suggestions[activeIndex].tag)
            } else if (inputValue) {
                handleAdd(inputValue)
            }
        } else if (e.key === "Escape") {
            setIsAdding(false)
            setInputValue("")
        } else if (e.key === "ArrowDown") {
            e.preventDefault()
            setActiveIndex(prev => Math.min(prev + 1, suggestions.length - 1))
        } else if (e.key === "ArrowUp") {
            e.preventDefault()
            setActiveIndex(prev => Math.max(prev - 1, -1))
        }
    }

    return (
        <div className={`flex flex-wrap gap-2 py-2 ${className}`}>
            {showExistingTags && tags.map((tag) => (
                <div
                    key={tag}
                    className="flex items-center gap-1.5 px-2.5 py-1 bg-zinc-800 border border-zinc-700 rounded-full text-xs text-zinc-300 group hover:border-zinc-500 transition-colors"
                >
                    <TagIcon className="w-3 h-3 text-zinc-500" />
                    <span>{tag}</span>
                    <button
                        onClick={() => onRemoveTag(tag)}
                        className="p-0.5 hover:bg-zinc-700 rounded-full text-zinc-500 hover:text-red-400 transition-colors"
                    >
                        <X className="w-3 h-3" />
                    </button>
                </div>
            ))}

            {isAdding ? (
                <div className="relative">
                    <input
                        ref={inputRef}
                        autoFocus={autoFocus}
                        type="text"
                        value={inputValue}
                        onChange={(e) => {
                            setInputValue(e.target.value)
                            setActiveIndex(-1)
                        }}
                        onKeyDown={handleKeyDown}
                        onBlur={() => {
                            // Delay blur slightly to allow suggestion click
                            setTimeout(() => setIsAdding(false), 200)
                        }}
                        className="bg-zinc-950 border border-indigo-500 rounded-full px-3 py-1 text-xs text-white outline-none w-32 focus:w-48 transition-all"
                        placeholder={placeholder}
                    />
                    {/* Suggestions Dropdown */}
                    {(suggestions.length > 0 || isLoadingSuggestions) && (
                        <div className="absolute top-full left-0 mt-1 w-48 bg-zinc-900 border border-zinc-800 rounded-lg shadow-xl z-30 max-h-48 overflow-y-auto">
                            {isLoadingSuggestions && suggestions.length === 0 && (
                                <div className="p-3 flex justify-center">
                                    <Loader2 className="w-4 h-4 animate-spin text-zinc-500" />
                                </div>
                            )}
                            {suggestions.map((s, idx) => (
                                <button
                                    key={s.tag}
                                    onClick={() => handleAdd(s.tag)}
                                    className={`w-full text-left px-3 py-2 text-xs flex justify-between items-center transition-colors ${idx === activeIndex ? "bg-indigo-600 text-white" : "text-zinc-300 hover:bg-zinc-800"
                                        }`}
                                >
                                    <span>{s.tag}</span>
                                    <span className={`text-[10px] ${idx === activeIndex ? "text-indigo-200" : "text-zinc-500"}`}>
                                        {s.count}
                                    </span>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            ) : (
                <button
                    onClick={() => {
                        setIsAdding(true)
                        setTimeout(() => inputRef.current?.focus(), 50)
                    }}
                    className="flex items-center gap-1 px-2.5 py-1 bg-zinc-900/50 border border-dashed border-zinc-700 rounded-full text-xs text-zinc-500 hover:border-zinc-500 hover:text-zinc-300 transition-colors"
                >
                    <Plus className="w-3 h-3" />
                    <span>Add Tag</span>
                </button>
            )}
        </div>
    )
}

interface TagEditorProps {
    fileId: number
    tags: string[]
    category: TagCategory
    onTagsChange: (newTags: string[]) => void
}

export function TagEditor({ fileId, tags, category, onTagsChange }: TagEditorProps) {
    const handleAddTag = async (tagName: string) => {
        try {
            const res = await addTags(fileId, [tagName], category)
            onTagsChange(res.tags)
        } catch (err) {
            console.error("Failed to add tag", err)
        }
    }

    const handleRemoveTag = async (tagName: string) => {
        try {
            const res = await removeTags(fileId, [tagName], category)
            onTagsChange(res.tags)
        } catch (err) {
            console.error("Failed to remove tag", err)
        }
    }

    return (
        <TagInput
            tags={tags}
            category={category}
            onAddTag={handleAddTag}
            onRemoveTag={handleRemoveTag}
        />
    )
}
