import React, { useState, useEffect, useMemo } from "react"
import {
    getTagStats,
    TagStats,
    TagStat,
    TagCategory,
    renameTag,
    getUntaggedFiles,
    MediaItem,
    getThumbnailUrl
} from "@/lib/api"
import {
    Tag as TagIcon,
    TrendingUp,
    Search,
    Loader2,
    Edit2,
    Trash2,
    X,
    Check,
    FileQuestion,
    ChevronRight,
    LayoutGrid,
    ArrowUpDown
} from "lucide-react"
import Image from "next/image"
import { Sidebar } from "@/components/Sidebar"
import { TagEditorPanel } from "@/components/TagEditorPanel"
import { useTranslations } from "next-intl"

export default function TagDashboardPage() {
    const t = useTranslations("tags")
    const commonT = useTranslations("common")
    const [stats, setStats] = useState<TagStats | null>(null)
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState("")
    const [activeTab, setActiveTab] = useState<"all" | TagCategory>("all")
    const [sortBy, setSortBy] = useState<"count" | "name">("count")
    const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")

    const [editingTag, setEditingTag] = useState<{ tag: string; category: TagCategory } | null>(null)
    const [editValue, setEditValue] = useState("")
    const [isSubmitting, setIsSubmitting] = useState(false)

    const [showUntagged, setShowUntagged] = useState(false)
    const [untaggedFiles, setUntaggedFiles] = useState<MediaItem[]>([])
    const [selectedFile, setSelectedFile] = useState<MediaItem | null>(null)
    const [untaggedTotal, setUntaggedTotal] = useState(0)
    const [untaggedPage, setUntaggedPage] = useState(1)

    const fetchStats = async () => {
        try {
            const data = await getTagStats()
            setStats(data)
        } catch (error) {
            console.error("Failed to fetch tag stats:", error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchStats()
    }, [])

    const fetchUntagged = async (page: number) => {
        try {
            const data = await getUntaggedFiles(page, 50)
            setUntaggedFiles(data.files)
            setUntaggedTotal(data.total_count)
            setUntaggedPage(page)
        } catch (error) {
            console.error("Failed to fetch untagged files:", error)
        }
    }

    const handleRename = async () => {
        if (!editingTag || !editValue.trim()) return
        if (editValue.trim() === editingTag.tag) {
            setEditingTag(null)
            return
        }

        setIsSubmitting(true)
        try {
            const res = await renameTag(editingTag.tag, editValue.trim(), editingTag.category)
            alert(t("renameSuccess", { renamed: res.renamed_count, merged: res.merged_count }))
            setEditingTag(null)
            fetchStats()
        } catch {
            alert(t("renameError"))
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleDelete = async (tag: string, category: TagCategory, count: number) => {
        if (!confirm(t("confirmDelete", { tag, count }))) return

        try {
            await renameTag(tag, "", category)
            fetchStats()
        } catch {
            alert(t("deleteError"))
        }
    }

    const allTags = useMemo(() => {
        if (!stats) return []
        const combined: (TagStat & { category: TagCategory })[] = []
        if (activeTab === "all" || activeTab === "general") {
            stats.general.forEach(t => combined.push({ ...t, category: "general" }))
        }
        if (activeTab === "all" || activeTab === "character") {
            stats.character.forEach(t => combined.push({ ...t, category: "character" }))
        }
        if (activeTab === "all" || activeTab === "series") {
            stats.series.forEach(t => combined.push({ ...t, category: "series" }))
        }

        const filtered = combined.filter(t => t.tag.toLowerCase().includes(search.toLowerCase()))

        filtered.sort((a, b) => {
            if (sortBy === "count") {
                return sortOrder === "desc" ? b.count - a.count : a.count - b.count
            } else {
                return sortOrder === "desc" ? b.tag.localeCompare(a.tag) : a.tag.localeCompare(b.tag)
            }
        })

        return filtered
    }, [stats, activeTab, search, sortBy, sortOrder])

    const topTags = useMemo(() => {
        if (!stats) return []
        const combined: TagStat[] = [...stats.general, ...stats.character, ...stats.series]
        return combined.sort((a, b) => b.count - a.count).slice(0, 3)
    }, [stats])

    if (loading) {
        return (
            <div className="flex h-screen bg-zinc-950 text-white">
                <Sidebar isOpen={false} onClose={() => { }} />
                <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                </div>
            </div>
        )
    }

    return (
        <div className="flex h-screen bg-zinc-950 text-white overflow-hidden">
            <Sidebar isOpen={false} onClose={() => { }} />

            <main className="flex-1 overflow-y-auto p-8">
                <div className="max-w-6xl mx-auto">
                    <header className="mb-8">
                        <h1 className="text-3xl font-bold mb-2">{t("title")}</h1>
                        <p className="text-zinc-500">{t("subtitle")}</p>
                    </header>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                        <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-2xl">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-2 bg-indigo-500/10 rounded-lg">
                                    <TagIcon className="w-5 h-5 text-indigo-400" />
                                </div>
                                <h2 className="font-semibold text-zinc-300">{t("totalTags")}</h2>
                            </div>
                            <div className="text-4xl font-black text-white">{stats?.total_tags || 0}</div>
                            <div className="text-xs text-zinc-500 mt-2">{t("acrossCategories")}</div>
                        </div>

                        <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-2xl relative overflow-hidden group">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="p-2 bg-amber-500/10 rounded-lg">
                                        <FileQuestion className="w-5 h-5 text-amber-400" />
                                    </div>
                                    <h2 className="font-semibold text-zinc-300">{t("untaggedFiles")}</h2>
                                </div>
                                <button
                                    onClick={() => {
                                        setShowUntagged(true)
                                        fetchUntagged(1)
                                    }}
                                    className="text-xs font-bold text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1"
                                >
                                    {commonT("view")} <ChevronRight className="w-3 h-3" />
                                </button>
                            </div>
                            <div className="text-4xl font-black text-white">{stats?.untagged_count || 0}</div>
                            <div className="text-xs text-zinc-500 mt-2">{t("untaggedDesc")}</div>
                        </div>

                        <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-2xl">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="p-2 bg-emerald-500/10 rounded-lg">
                                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                                </div>
                                <h2 className="font-semibold text-zinc-300">{t("topTags")}</h2>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {topTags.map(tStat => (
                                    <div key={tStat.tag} className="flex items-center gap-2 bg-zinc-800 px-3 py-1.5 rounded-full text-xs text-zinc-300">
                                        <span className="font-medium">{tStat.tag}</span>
                                        <span className="text-zinc-500 font-mono text-[10px]">{tStat.count}</span>
                                    </div>
                                ))}
                                {topTags.length === 0 && <span className="text-zinc-600 italic text-sm">{t("noTagsFound")}</span>}
                            </div>
                        </div>
                    </div>

                    {/* Main Table Section */}
                    <div className="bg-zinc-900/30 border border-zinc-800 rounded-2xl overflow-hidden flex flex-col">
                        <div className="p-6 border-b border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="flex items-center gap-2 p-1 bg-zinc-950 rounded-xl">
                                {(["all", "general", "character", "series"] as const).map(tab => (
                                    <button
                                        key={tab}
                                        onClick={() => setActiveTab(tab)}
                                        className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${activeTab === tab
                                            ? "bg-zinc-800 text-white shadow-sm"
                                            : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900"
                                            }`}
                                    >
                                        {t(tab)}
                                    </button>
                                ))}
                            </div>

                            <div className="relative w-full md:w-72">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
                                <input
                                    type="text"
                                    placeholder={t("searchPlaceholder")}
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-2 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-zinc-600"
                                />
                            </div>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full border-collapse">
                                <thead className="bg-zinc-950/50">
                                    <tr className="text-left text-[11px] uppercase tracking-wider text-zinc-500 font-bold border-b border-zinc-800">
                                        <th
                                            className="px-6 py-4 cursor-pointer hover:text-zinc-300 transition-colors"
                                            onClick={() => {
                                                if (sortBy === "name") setSortOrder(sortOrder === "asc" ? "desc" : "asc")
                                                else { setSortBy("name"); setSortOrder("asc"); }
                                            }}
                                        >
                                            <div className="flex items-center gap-2">
                                                {t("tagName")}
                                                <ArrowUpDown className={`w-3 h-3 ${sortBy === "name" ? "text-indigo-400" : "text-zinc-700"}`} />
                                            </div>
                                        </th>
                                        <th className="px-6 py-4">{t("category")}</th>
                                        <th
                                            className="px-6 py-4 cursor-pointer hover:text-zinc-300 transition-colors"
                                            onClick={() => {
                                                if (sortBy === "count") setSortOrder(sortOrder === "asc" ? "desc" : "asc")
                                                else { setSortBy("count"); setSortOrder("desc"); }
                                            }}
                                        >
                                            <div className="flex items-center gap-2">
                                                {t("usageCount")}
                                                <ArrowUpDown className={`w-3 h-3 ${sortBy === "count" ? "text-indigo-400" : "text-zinc-700"}`} />
                                            </div>
                                        </th>
                                        <th className="px-6 py-4 text-right">{commonT("actions")}</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-zinc-800/50">
                                    {allTags.map((tItem) => (
                                        <tr key={`${tItem.category}-${tItem.tag}`} className="group hover:bg-zinc-800/20 transition-colors">
                                            <td className="px-6 py-4">
                                                {editingTag?.tag === tItem.tag && editingTag?.category === tItem.category ? (
                                                    <div className="flex items-center gap-2">
                                                        <input
                                                            autoFocus
                                                            className="bg-zinc-950 border border-indigo-500/50 rounded px-2 py-1 text-sm focus:outline-none ring-2 ring-indigo-500/20"
                                                            value={editValue}
                                                            onChange={(e) => setEditValue(e.target.value)}
                                                            onKeyDown={(e) => {
                                                                if (e.key === "Enter") handleRename()
                                                                if (e.key === "Escape") setEditingTag(null)
                                                            }}
                                                        />
                                                        <button
                                                            onClick={handleRename}
                                                            disabled={isSubmitting}
                                                            className="p-1 hover:text-emerald-400 text-zinc-500"
                                                        >
                                                            <Check className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => setEditingTag(null)}
                                                            className="p-1 hover:text-rose-400 text-zinc-500"
                                                        >
                                                            <X className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                ) : (
                                                    <span className="text-sm font-medium text-zinc-300">{tItem.tag}</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">
                                                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${tItem.category === "character" ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" :
                                                    tItem.category === "series" ? "bg-purple-500/10 text-purple-400 border border-purple-500/20" :
                                                        "bg-zinc-800 text-zinc-400 border border-zinc-700"
                                                    }`}>
                                                    {t(tItem.category)}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-sm font-mono text-zinc-500">{tItem.count}</td>
                                            <td className="px-6 py-4 text-right">
                                                <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={() => {
                                                            setEditingTag({ tag: tItem.tag, category: tItem.category })
                                                            setEditValue(tItem.tag)
                                                        }}
                                                        className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-indigo-400 transition-colors"
                                                        title={commonT("rename")}
                                                    >
                                                        <Edit2 className="w-4 h-4" />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(tItem.tag, tItem.category, tItem.count)}
                                                        className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-rose-400 transition-colors"
                                                        title={commonT("delete")}
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                    {allTags.length === 0 && (
                                        <tr>
                                            <td colSpan={4} className="px-6 py-20 text-center text-zinc-600">
                                                <TagIcon className="w-12 h-12 mx-auto mb-4 opacity-10" />
                                                <p>{t("noResults")}</p>
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </main>

            {/* Untagged Files Modal */}
            {showUntagged && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={() => setShowUntagged(false)} />
                    <div className="relative w-full max-w-6xl h-[90vh] bg-zinc-950 border border-zinc-800 rounded-3xl overflow-hidden flex flex-col shadow-2xl">
                        <div className="p-6 border-b border-zinc-800 flex items-center justify-between">
                            <div>
                                <h2 className="text-xl font-bold">{t("untaggedFiles")}</h2>
                                <p className="text-sm text-zinc-500">{t("untaggedCount", { count: untaggedTotal })}</p>
                            </div>
                            <button onClick={() => setShowUntagged(false)} className="p-2 hover:bg-zinc-900 rounded-full text-zinc-500 hover:text-white transition-colors">
                                <X className="w-6 h-6" />
                            </button>
                        </div>

                        <div className="flex-1 flex overflow-hidden">
                            {/* Grid View */}
                            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-zinc-800">
                                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                                    {untaggedFiles.map(file => (
                                        <div
                                            key={file.id}
                                            onClick={() => setSelectedFile(file)}
                                            className={`group cursor-pointer rounded-xl overflow-hidden border-2 transition-all ${selectedFile?.id === file.id ? "border-indigo-500 ring-4 ring-indigo-500/20" : "border-transparent hover:border-zinc-700"
                                                }`}
                                        >
                                            <div className="aspect-square relative bg-zinc-900">
                                                <Image
                                                    src={getThumbnailUrl(file.id)}
                                                    alt={file.file_path}
                                                    fill
                                                    className="object-cover transition-transform group-hover:scale-110"
                                                    loading="lazy"
                                                />
                                                <div className="absolute inset-x-0 bottom-0 bg-black/60 p-2 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <p className="text-[10px] truncate text-zinc-300">{file.file_path.split(/[\\/]/).pop()}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                {untaggedTotal > untaggedFiles.length && (
                                    <div className="mt-8 flex justify-center">
                                        <button
                                            onClick={() => fetchUntagged(untaggedPage + 1)}
                                            className="px-6 py-2 bg-zinc-900 hover:bg-zinc-800 text-sm font-bold rounded-full transition-colors"
                                        >
                                            {commonT("loadMore")}
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* Detail / Editor Panel */}
                            <div className="w-80 border-l border-zinc-800 bg-zinc-900/30 flex flex-col">
                                {selectedFile ? (
                                    <div className="flex flex-col h-full overflow-hidden p-4">
                                        <div className="aspect-[4/3] rounded-xl overflow-hidden bg-zinc-950 mb-4 flex items-center justify-center group relative">
                                            <Image
                                                src={getThumbnailUrl(selectedFile.id, 600)}
                                                alt={commonT("preview")}
                                                fill
                                                className="object-contain"
                                            />
                                            <div className="absolute top-2 right-2">
                                                <span className="px-2 py-0.5 bg-black/60 backdrop-blur rounded text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                                                    ID: {selectedFile.id}
                                                </span>
                                            </div>
                                        </div>

                                        <div className="mb-4">
                                            <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1">{commonT("filename")}</h3>
                                            <p className="text-sm text-zinc-300 truncate font-medium">{selectedFile.file_path.split(/[\\/]/).pop()}</p>
                                        </div>

                                        <div className="flex-1 overflow-hidden">
                                            <TagEditorPanel
                                                fileId={selectedFile.id}
                                                generalTags={selectedFile.tags}
                                                characterTags={selectedFile.character_tags}
                                                seriesTags={selectedFile.series_tags}
                                                onUpdate={async (cat, newTags) => {
                                                    const updatedFile = { ...selectedFile }
                                                    if (cat === "general") updatedFile.tags = newTags
                                                    else if (cat === "character") updatedFile.character_tags = newTags
                                                    else if (cat === "series") updatedFile.series_tags = newTags

                                                    setSelectedFile(updatedFile)
                                                    setUntaggedFiles(prev => prev.map(f => f.id === updatedFile.id ? updatedFile : f))

                                                    if (updatedFile.tags.length > 0) {
                                                        fetchStats()
                                                    }
                                                }}
                                            />
                                        </div>
                                    </div>
                                ) : (
                                    <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-zinc-600">
                                        <div className="p-4 bg-zinc-950 rounded-full mb-4">
                                            <LayoutGrid className="w-8 h-8 opacity-20" />
                                        </div>
                                        <p className="text-sm font-medium">{t("selectFileToTag")}</p>
                                        <p className="text-xs mt-2 opacity-50 italic">{t("untaggedBacklog")}</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
