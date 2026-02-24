"use client"

import React, { useState, useEffect, useRef } from "react"
import { TagCategory } from "@/lib/api"
import { TagEditor } from "./TagEditor"

interface TagEditorPanelProps {
    fileId: number
    generalTags: string[]
    characterTags: string[]
    seriesTags: string[]
    onUpdate: (category: TagCategory, newTags: string[]) => void
}

export function TagEditorPanel({ fileId, generalTags, characterTags, seriesTags, onUpdate }: TagEditorPanelProps) {
    const [activeCategory, setActiveCategory] = useState<TagCategory>("general")
    const inputRef = useRef<HTMLInputElement>(null)

    // Handle 'T' shortcut
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Only trigger if not already typing in an input/textarea
            if (
                e.key.toLowerCase() === "t" &&
                !["INPUT", "TEXTAREA"].includes((document.activeElement as HTMLElement)?.tagName)
            ) {
                e.preventDefault()
                // The TagEditor component handles its own state for isAdding,
                // so we might need to trigger that or just focus if it's already there.
                // For a better UX, 'T' should probably force open the 'Add Tag' state.
                // We'll expose a mechanism or just assume isAdding is enough.
                // Actually, let's just use the ref. The TagEditor will need to handle this.
                if (inputRef.current) {
                    inputRef.current.focus()
                } else {
                    // If the input isn't rendered yet (isAdding is false), 
                    // we need to signal TagEditor to open.
                    // Instead of complex parent-child signaling, we can just use a custom event or a prop.
                    // For now, let's keep it simple: if 'T' is pressed, we'll suggest focusing.
                    window.dispatchEvent(new CustomEvent("focus-tag-input", { detail: { category: activeCategory } }))
                }
            }
        }
        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [activeCategory])

    const categories: { label: string; key: TagCategory; tags: string[] }[] = [
        { label: "General", key: "general", tags: generalTags },
        { label: "Characters", key: "character", tags: characterTags },
        { label: "Series", key: "series", tags: seriesTags },
    ]

    return (
        <div className="flex flex-col h-full bg-zinc-900/50 rounded-xl border border-zinc-800 p-1">
            <div className="flex gap-1 p-1 bg-zinc-950/50 rounded-lg mb-2">
                {categories.map((cat) => (
                    <button
                        key={cat.key}
                        onClick={() => setActiveCategory(cat.key)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-medium transition-all ${activeCategory === cat.key
                                ? "bg-zinc-800 text-white shadow-sm"
                                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
                            }`}
                    >
                        {cat.label}
                        <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${activeCategory === cat.key ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-600"
                            }`}>
                            {cat.tags.length}
                        </span>
                    </button>
                ))}
            </div>

            <div className="flex-1 px-2 overflow-y-auto">
                {categories.map((cat) => (
                    <div key={cat.key} className={activeCategory === cat.key ? "block" : "hidden"}>
                        <TagEditor
                            fileId={fileId}
                            tags={cat.tags}
                            category={cat.key}
                            onTagsChange={(newTags) => onUpdate(cat.key, newTags)}
                        />
                    </div>
                ))}
            </div>

            <div className="p-2 border-t border-zinc-800/50 bg-zinc-900/30">
                <p className="text-[10px] text-zinc-600 italic">
                    Tip: Press <kbd className="font-sans px-1 bg-zinc-800 rounded border border-zinc-700 not-italic">T</kbd> to focus tag input.
                </p>
            </div>
        </div>
    )
}
