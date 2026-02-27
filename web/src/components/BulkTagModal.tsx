"use client"

import React, { useState } from "react"
import { useTranslations } from "next-intl"
import { X, Loader2, AlertCircle } from "lucide-react"
import { MediaItem, TagCategory, bulkUpdateTags, BulkTagResponse } from "@/lib/api"
import { TagInput } from "./TagEditor"

interface BulkTagModalProps {
    selectedItems: MediaItem[]
    onClose: () => void
    onSuccess: (response: BulkTagResponse) => void
}

export function BulkTagModal({ selectedItems, onClose, onSuccess }: BulkTagModalProps) {
    const t = useTranslations("bulk");
    const commonT = useTranslations("common");
    const [action, setAction] = useState<"add" | "remove" | "replace">("add")
    const [category, setCategory] = useState<TagCategory>("general")
    const [tags, setTags] = useState<string[]>([])
    const [isProcessing, setIsProcessing] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const count = selectedItems.length
    const fileIds = selectedItems.map(item => item.id)

    const handleApply = async () => {
        if (tags.length === 0) return

        setIsProcessing(true)
        setError(null)
        try {
            const res = await bulkUpdateTags(fileIds, action, tags, category)
            onSuccess(res)
            onClose()
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : "Failed to update tags";
            setError(errorMessage);
        } finally {
            setIsProcessing(false)
        }
    }

    const previewText = () => {
        const tagCount = tags.length
        const tagStr = `${tagCount} tag${tagCount !== 1 ? 's' : ''}`
        if (action === "add") return t("previewAdd", { count, tagStr })
        if (action === "remove") return t("previewRemove", { count, tagStr })
        if (action === "replace") return t("previewReplace", { category: t(category as "general" | "character" | "series"), count, tagStr })
        return ""
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" role="dialog" aria-modal="true" aria-labelledby="bulk-tag-title">
            <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50">
                    <h2 id="bulk-tag-title" className="text-sm font-bold uppercase tracking-widest text-zinc-400">
                        {t("title", { count })}
                    </h2>
                    <button
                        onClick={onClose}
                        disabled={isProcessing}
                        className="p-1 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-white transition-colors disabled:opacity-50"
                        aria-label={commonT('close')}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6 space-y-6">
                    {/* Action Selector */}
                    <div className="flex bg-zinc-950 p-1 rounded-xl border border-zinc-800">
                        {(["add", "remove", "replace"] as const).map((a) => (
                            <button
                                key={a}
                                onClick={() => setAction(a)}
                                disabled={isProcessing}
                                className={`flex-1 py-1.5 text-xs font-bold uppercase tracking-wider rounded-lg transition-all ${action === a
                                    ? "bg-indigo-600 text-white shadow-lg"
                                    : "text-zinc-500 hover:text-zinc-300"
                                    }`}
                            >
                                {t(a as "add" | "remove" | "replace")}
                            </button>
                        ))}
                    </div>

                    {/* Replace Warning */}
                    {action === "replace" && (
                        <div className="flex items-start gap-3 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-200 text-xs">
                            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                            <p>{t("replaceWarning", { category: t(category as "general" | "character" | "series") })}</p>
                        </div>
                    )}

                    {/* Category Selector */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">{t("category")}</label>
                        <select
                            value={category}
                            onChange={(e) => setCategory(e.target.value as TagCategory)}
                            disabled={isProcessing}
                            className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all appearance-none cursor-pointer"
                        >
                            <option value="general">{t("general")}</option>
                            <option value="character">{t("character")}</option>
                            <option value="series">{t("series")}</option>
                        </select>
                    </div>

                    {/* Tag Input */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">{t("tagsLabel", { action: t(action as "add" | "remove" | "replace").toLowerCase() })}</label>
                        <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-2 min-h-[100px] focus-within:ring-2 focus-within:ring-indigo-500 transition-all">
                            <TagInput
                                tags={tags}
                                category={category}
                                onAddTag={(tag) => {
                                    if (!tags.includes(tag)) setTags([...tags, tag])
                                }}
                                onRemoveTag={(tag) => setTags(tags.filter(t => t !== tag))}
                                showExistingTags={true}
                                autoFocus={true}
                                placeholder={t("placeholder", { action: t(action as "add" | "remove" | "replace").toLowerCase() })}
                            />
                        </div>
                    </div>

                    {/* Preview Area */}
                    <div className="pt-2">
                        <p className="text-center text-xs text-zinc-500 font-medium italic">
                            {tags.length > 0 ? previewText() : t("previewEmpty")}
                        </p>
                    </div>

                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs text-center animate-in fade-in duration-200">
                            {error}
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div className="p-4 bg-zinc-950/50 border-t border-zinc-800 flex gap-3">
                    <button
                        onClick={onClose}
                        disabled={isProcessing}
                        className="flex-1 py-2.5 rounded-xl text-sm font-bold text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all disabled:opacity-50"
                    >
                        {commonT("cancel")}
                    </button>
                    <button
                        onClick={handleApply}
                        disabled={isProcessing || tags.length === 0}
                        className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-900/20 transition-all flex items-center justify-center gap-2"
                    >
                        {isProcessing ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            t("applyButton", { count })
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
