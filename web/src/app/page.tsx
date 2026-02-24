"use client"

import { useEffect, useState, useCallback } from "react"
import { MediaItem, fetchMedia, searchMedia, searchByFace, reverseImageSearch, SearchFilters, SceneSearchResult, searchScenes } from "@/lib/api"
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts"
import { GalleryGrid } from "@/components/GalleryGrid"
import { ChatPanel } from "@/components/ChatPanel"
import { Sidebar } from "@/components/Sidebar"
import { HybridSearchBar } from "@/components/HybridSearchBar"
import { SceneSearchResultComponent } from "@/components/SceneSearchResult"
import { Menu, Save, Film } from "lucide-react"
import SaveAlbumModal from "@/components/SaveAlbumModal"
import { InsightsPanel } from "@/components/InsightsPanel"

export default function Home() {
  const [media, setMedia] = useState<MediaItem[]>([])
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null)
  const [focusedIndex, setFocusedIndex] = useState(-1)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [currentSearch, setCurrentSearch] = useState("")
  const [currentFilters, setCurrentFilters] = useState<SearchFilters>({})
  const [searchStats, setSearchStats] = useState<{ total_candidates: number } | null>(null)
  const [sceneResults, setSceneResults] = useState<SceneSearchResult[]>([])
  const [isSceneSearchActive, setIsSceneSearchActive] = useState(false)

  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false)

  const loadMedia = useCallback(async (currentOffset: number = 0) => {
    try {
      if (currentOffset === 0) {
        setLoading(true)
      } else {
        setIsLoadingMore(true)
      }

      const limit = 50
      // Default fetch doesn't use semantic search filters yet in the backend list_media, 
      // but for Phase 2 we mainly care about the search bar.
      const data = await fetchMedia({ offset: currentOffset, limit })
      if (currentOffset === 0) {
        setMedia(data)
        setSceneResults([])
        setIsSceneSearchActive(false)
      } else {
        setMedia(prev => [...prev, ...data])
      }
      setHasMore(data.length === limit)
      setSearchStats(null)
    } catch {
      setError("Failed to load gallery.")
    } finally {
      if (currentOffset === 0) {
        setLoading(false)
      } else {
        setIsLoadingMore(false)
      }
    }
  }, [])

  const handleLoadMore = useCallback(() => {
    if (!currentSearch && hasMore && !loading && !isLoadingMore) {
      const nextOffset = offset + 50
      setOffset(nextOffset)
      loadMedia(nextOffset)
    }
  }, [currentSearch, hasMore, loading, isLoadingMore, offset, loadMedia])

  const handleSearch = useCallback(async (query: string, filters: SearchFilters = {}, searchForScenes: boolean = false) => {
    setCurrentSearch(query)
    setCurrentFilters(filters)
    setIsSceneSearchActive(searchForScenes)

    if (!query.trim() && Object.keys(filters).length === 0) {
      setOffset(0)
      loadMedia(0)
      return
    }
    try {
      setLoading(true)
      setError("")

      if (searchForScenes) {
        const results = await searchScenes(query)
        setSceneResults(results)
        setMedia([])
        setSearchStats(null)
      } else {
        const response = await searchMedia(query, filters)
        setMedia(response.results)
        setSceneResults([])
        setSearchStats({ total_candidates: response.total_candidates })
      }

      setSelectedItem(null)
      setHasMore(false)
    } catch {
      setError("Search failed.")
    } finally {
      setLoading(false)
    }
  }, [loadMedia])

  const handleFaceSearch = useCallback(async (faceId: number) => {
    setCurrentSearch(`Face Search: ID ${faceId}`)
    try {
      setLoading(true)
      setError("")
      const results = await searchByFace(faceId)

      // Keep face search results directly (they are already sorted by score)
      setMedia(results)
      setSelectedItem(null)
      setHasMore(false)
      setSearchStats(null)
    } catch {
      setError("Face Search failed.")
    } finally {
      setLoading(false)
    }
  }, [])

  const handleImageDrop = useCallback(async (file: File) => {
    setCurrentSearch(`Reverse Search: ${file.name}`)
    try {
      setLoading(true)
      setError("")
      const results = await reverseImageSearch(file)

      const mappedResults: MediaItem[] = results.map(r => ({
        id: r.id,
        file_path: r.file_path,
        media_type: r.media_type,
        width: r.width,
        height: r.height,
        duration: null,
        caption: null,
        tags: [],
        character_tags: [],
        series_tags: [],
        favorite: false,
        created_at: new Date().toISOString(),
        processed_at: new Date().toISOString(),
        snippet: `Similarity: ${(r.similarity * 100).toFixed(1)}%`
      }))

      setMedia(mappedResults)
      setSelectedItem(null)
      setHasMore(false)
    } catch {
      setError("Reverse image search failed.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!currentSearch && Object.keys(currentFilters).length === 0) {
      setOffset(0)
      loadMedia(0)
    }
  }, [currentFilters, currentSearch, loadMedia])

  const selectNext = useCallback(() => {
    setFocusedIndex(prev => (prev < media.length - 1 ? prev + 1 : prev))
  }, [media.length])

  const selectPrev = useCallback(() => {
    setFocusedIndex(prev => (prev > 0 ? prev - 1 : prev))
  }, [])

  const openSelected = useCallback(() => {
    if (focusedIndex >= 0 && focusedIndex < media.length) {
      setSelectedItem(media[focusedIndex])
      setFocusedIndex(focusedIndex) // Ensure it stays focused
    }
  }, [focusedIndex, media])

  const selectAll = useCallback(() => {
    setSelectedIds(new Set(media.map(m => m.id)))
  }, [media])

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  useKeyboardShortcuts({
    'j': selectNext,
    'k': selectPrev,
    'enter': openSelected,
    'a': selectAll,
    'shift+a': deselectAll,
  })

  // Sync focused index with selectedItem if it changes via click
  useEffect(() => {
    if (selectedItem) {
      const idx = media.findIndex(m => m.id === selectedItem.id)
      if (idx !== -1) setFocusedIndex(idx)
    }
  }, [selectedItem, media])

  return (
    <main className="flex h-screen w-full bg-zinc-950 overflow-hidden font-sans">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 h-full relative border-r border-zinc-800">
        {loading ? (
          <div className="flex items-center justify-center h-full text-zinc-500">
            <div className="animate-pulse flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-4" />
              Loading Gallery...
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full text-red-500">
            {error}
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="p-4 border-b border-zinc-800 bg-zinc-950/50 backdrop-blur-sm sticky top-0 z-20">
              <div className="flex items-center gap-4">
                <button onClick={() => setIsSidebarOpen(true)} className="md:hidden p-2 text-zinc-400 hover:text-white transition-colors">
                  <Menu className="w-6 h-6" />
                </button>
                <div className="flex-1">
                  <HybridSearchBar onSearch={handleSearch} />
                </div>
              </div>
              {searchStats && (
                <div className="mt-2 flex items-center justify-between">
                  <div className="text-[10px] text-zinc-500 font-medium uppercase tracking-widest flex items-center gap-2">
                    <span>Found {media.length} of {searchStats.total_candidates} candidates</span>
                    {Object.keys(currentFilters).length > 0 && (
                      <>
                        <span className="w-1 h-1 rounded-full bg-zinc-800" />
                        <span>Filtered by: {Object.entries(currentFilters).map(([k, v]) => `${k}=${v}`).join(", ")}</span>
                      </>
                    )}
                  </div>
                  <button
                    onClick={() => setIsSaveModalOpen(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 text-xs font-semibold rounded-lg border border-blue-500/20 transition-all active:scale-95"
                  >
                    <Save className="w-3.5 h-3.5" />
                    Save as Smart Album
                  </button>
                </div>
              )}
            </div>

            <div className="flex-1 min-h-0 overflow-y-auto">
              <div className="max-w-[1600px] mx-auto p-4 sm:p-6 lg:p-8">
                <InsightsPanel />

                {isSceneSearchActive ? (
                  <div className="space-y-6">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="p-2 bg-indigo-600/10 rounded-lg">
                        <Film className="w-5 h-5 text-indigo-400" />
                      </div>
                      <div>
                        <h2 className="text-lg font-bold text-white">Scene Search Results</h2>
                        <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider">Found {sceneResults.length} matching scenes</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 gap-4">
                      {sceneResults.map((result) => (
                        <SceneSearchResultComponent
                          key={`${result.file_id}-${result.scene_index}`}
                          result={result}
                          onPlay={async (fileId, startTime) => {
                            // Find the media item for this scene
                            // If not in current media list, we might need to fetch it
                            const item = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/gallery/${fileId}`).then(r => r.json())
                            setSelectedItem(item)
                            // The seek logic is handled in ChatPanel when it mounts with the item
                            // We can use a small delay to ensure video element is ready
                            setTimeout(() => {
                              const video = document.querySelector('video')
                              if (video) {
                                video.currentTime = startTime
                                video.play().catch(() => { })
                              }
                            }, 500)
                          }}
                        />
                      ))}
                    </div>
                    {sceneResults.length === 0 && (
                      <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
                        <Film className="w-12 h-12 mb-4 opacity-20" />
                        <p className="text-sm font-medium">No scenes match your search query.</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <GalleryGrid
                    media={media}
                    onSelect={setSelectedItem}
                    onLoadMore={handleLoadMore}
                    hasMore={hasMore}
                    onImageDrop={handleImageDrop}
                    focusedIndex={focusedIndex}
                    selectedIds={selectedIds}
                    onSelectionChange={setSelectedIds}
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Chat / Context Panel */}
      {
        selectedItem && (
          <ChatPanel
            item={selectedItem}
            onClose={() => setSelectedItem(null)}
            onFaceSearch={handleFaceSearch}
            onItemUpdate={(newItem) => {
              setSelectedItem(newItem)
              // Also update the item in the main media list to keep them in sync
              setMedia(prev => prev.map(m => m.id === newItem.id ? newItem : m))
            }}
          />
        )
      }
      {/* Modal */}
      <SaveAlbumModal
        isOpen={isSaveModalOpen}
        onClose={() => setIsSaveModalOpen(false)}
        currentQuery={currentSearch}
        currentFilters={currentFilters}
      />
    </main >
  )
}
